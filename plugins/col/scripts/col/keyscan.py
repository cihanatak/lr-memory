"""Key scan before a commit or a push. Deterministic, zero tokens.

A commit is judged on what it will record: the staged diff, the tracked changes when -a is given, and the files a
`git add` earlier in the same command is about to stage (the hook runs before the command, so they are not staged
yet). A push is judged on the commits no remote has yet. Only added lines count. A hit blocks the command and names
the file, the line and the kind of key, never the key. Any failure of the scan lets the command through: a broken
scanner must not stop the user's work.
"""
from __future__ import annotations

import hashlib
import os
import re
import shlex
import subprocess
from pathlib import Path

from col import common
from col.text import name, t

PATTERNS = {
    "anthropic": r"sk-ant-[A-Za-z0-9_\-]{20,}",
    "openai": r"(?<![\w-])sk-(?:proj-)?[A-Za-z0-9_\-]{32,}",
    "github": r"\bgh[pousr]_[A-Za-z0-9]{36,}|\bgithub_pat_[A-Za-z0-9_]{60,}",
    "gitlab": r"\bglpat-[A-Za-z0-9_\-]{20,}",
    "aws": r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b",
    "google": r"\bAIza[0-9A-Za-z_\-]{35}\b",
    "slack": r"\bxox[abprs]-[A-Za-z0-9\-]{10,}",
    "stripe": r"\b(?:sk|rk)_live_[0-9a-zA-Z]{24,}",
    "huggingface": r"\bhf_[A-Za-z0-9]{30,}",
    "npm": r"\bnpm_[A-Za-z0-9]{36}\b",
    "kaggle": r"KAGGLE_KEY\s*[=:]\s*[\"']?[0-9a-f]{32}",
    "private": r"-----BEGIN (?:RSA |EC |OPENSSH |DSA |PGP |ENCRYPTED )?PRIVATE KEY-----",
}
COMPILED = {kind: re.compile(p) for kind, p in PATTERNS.items()}
# git's own prefilter for a push: only commits whose diff touches one of these are read in full (on a 66-commit image
# repository, reading every patch took about 3 s and this about 1 s); a superset of PATTERNS
PICKAXE = (r"sk-ant-|sk-proj-|sk-[A-Za-z0-9_-]{32}|AKIA[0-9A-Z]|ASIA[0-9A-Z]|gh[pousr]_|github_pat_|glpat-|AIza|"
           r"xox[abprs]-|[sr]k_live_|hf_[A-Za-z0-9]|npm_[A-Za-z0-9]|KAGGLE_KEY|PRIVATE KEY-----")
SECRET_FILE = re.compile(r"(?:^|/)(?:\.env(?:\.[\w-]+)?|id_rsa|id_ed25519|kaggle\.json|\.?credentials\.json|"
                         r"[^/]+\.pem|[^/]+\.p12|[^/]+\.pfx)$", re.I)
EXAMPLE_FILE = re.compile(r"\.env\.(?:example|sample|template|dist)$", re.I)
HEREDOC = re.compile(r"<<-?\s*['\"]?(\w+)['\"]?[^\n]*\n.*?\n\s*\1\b", re.S)
SEGMENTS = re.compile(r"&&|\|\||;|\||\n")
MAX_BYTES = 4 << 20
ALLOW = "secret_allow.txt"


def redact(text: str) -> str:
    """Text with every key-shaped string replaced by its kind, for a log."""
    for kind, rx in COMPILED.items():
        text = rx.sub(f"[{kind}]", text)
    return text


def _path(p: str, here: str) -> str:
    p = p.strip("'\"")
    if os.name == "nt":  # Git Bash writes /c/x for C:/x
        p = re.sub(r"^/([a-zA-Z])/", lambda m: f"{m.group(1).upper()}:/", p)
    return str(Path(here) / p) if here and not re.match(r"^[A-Za-z]:[\\/]|^[\\/~]", p) else os.path.expanduser(p)


def git_calls(cmd: str, cwd: str) -> list:
    """(repo, subcommand, args) for each git call in a shell command, following `cd`; heredoc bodies are data.
    Without a known folder (no cwd, no cd, no -C) the call is skipped: a guessed repository is the wrong one."""
    out, here = [], cwd or ""
    for seg in SEGMENTS.split(HEREDOC.sub(" ", cmd)):
        try:
            toks = [x.strip("'\"") for x in shlex.split(seg, posix=False)]
        except ValueError:
            toks = seg.split()
        if not toks:
            continue
        if toks[0].lower() in ("cd", "set-location", "pushd") and len(toks) > 1:
            here = _path(toks[1], here)
            continue
        i = next((k for k, x in enumerate(toks) if Path(x).name.lower() in ("git", "git.exe")), None)
        if i is None:
            continue
        repo, j = here, i + 1
        while j < len(toks) and toks[j].startswith("-"):
            if toks[j] == "-C" and j + 1 < len(toks):
                repo = _path(toks[j + 1], here)
            j += 2 if toks[j] in ("-C", "-c") else 1
        if j < len(toks) and repo:
            out.append((repo, toks[j].lower(), toks[j + 1:]))
    return out


def _git(repo: str, *args: str) -> str:
    try:  # the hook has 20 s in all; one slow repository must not use them up
        r = subprocess.run(["git", "-C", repo, *args], capture_output=True, timeout=7)
    except subprocess.TimeoutExpired:
        common.log("secrets", {"timeout": " ".join(args[:3])})
        return ""
    return r.stdout[:MAX_BYTES].decode("utf-8", errors="replace") if r.returncode == 0 else ""


def _added_lines(diff: str):
    """(file, line, text) for every added line of a unified diff or of `git log -p` output."""
    path, line = None, 0
    for raw in diff.splitlines():
        if raw.startswith("+++ "):
            path = None if raw.endswith("/dev/null") else raw[4:].removeprefix("b/")
        elif raw.startswith("@@"):
            m = re.search(r"\+(\d+)", raw)
            line = int(m.group(1)) if m else 0
        elif raw.startswith("+") and path:
            yield path, line, raw[1:]
            line += 1
        elif not raw.startswith("-") and path:
            line += 1


def _untracked(repo: str, paths: list) -> list:
    return [p for p in _git(repo, "ls-files", "--others", "--exclude-standard", "-z", "--", *paths).split("\0") if p]


def _file_lines(repo: str, rel: str):
    f = Path(repo) / rel
    try:
        if f.stat().st_size > MAX_BYTES:
            return
        data = f.read_bytes()
    except OSError:
        return
    if b"\0" in data[:8000]:  # binary
        return
    for n, text in enumerate(data.decode("utf-8", errors="replace").splitlines(), 1):
        yield rel, n, text


def _changes(calls: list) -> tuple:
    """The added lines and the new file names that the commits and pushes in this command would send."""
    lines, files, staged_soon = [], set(), {}
    for repo, sub, args in calls:
        if sub == "add":
            paths = [a for a in args if not a.startswith("-")]
            everything = not paths or any(a in ("-A", "--all", "-u", "--update") for a in args) or "." in paths
            staged_soon.setdefault(repo, set()).update(["."] if everything else paths)
        elif sub == "commit":
            diff = _git(repo, "diff", "--cached", "-U0", "--no-color", "--no-ext-diff")
            if any(a in ("-a", "--all") or re.match(r"^-[a-zA-Z]*a[a-zA-Z]*$", a) for a in args):
                diff += "\n" + _git(repo, "diff", "-U0", "--no-color", "--no-ext-diff")
            soon = sorted(staged_soon.pop(repo, set()))
            if soon:
                diff += "\n" + _git(repo, "diff", "-U0", "--no-color", "--no-ext-diff", "--", *soon)
                for rel in _untracked(repo, soon):
                    files.add(rel)
                    lines.extend(_file_lines(repo, rel))
            lines.extend(_added_lines(diff))
            files.update(re.findall(r"^\+\+\+ b/(.+)$", diff, re.M))
        elif sub == "push":
            pos = [a for a in args if not a.startswith("-")]
            src = pos[1].lstrip("+").split(":")[0] if len(pos) > 1 and pos[1].lstrip("+").split(":")[0] else "HEAD"
            rng = [src, "--not", "--remotes", "-n", "200"]
            for c in _git(repo, "log", "--format=%H", "-E", "-G" + PICKAXE, *rng).split()[:20]:
                lines.extend(_added_lines(_git(repo, "show", "-U0", "--no-color", "--no-ext-diff", "--format=", c)))
            files.update(n for n in _git(repo, "log", "--format=", "--name-only", "--diff-filter=A", *rng)
                         .splitlines() if n.strip())
    return lines, files


def fingerprint(secret: str) -> str:
    return hashlib.sha256(secret.encode("utf-8")).hexdigest()[:16]


def _allowed() -> set:
    try:
        lines = (common.DATA / ALLOW).read_text(encoding="utf-8").splitlines()
    except OSError:
        return set()
    return {x.strip() for x in lines if x.strip() and not x.strip().startswith("#")}


def scan(cmd: str, cwd: str, lang: str = "en") -> list:
    """Findings as {kind, file, line, mask, fp}. The secret itself never leaves this function."""
    calls = [c for c in git_calls(cmd, cwd) if c[1] in ("add", "commit", "push")]
    if not any(c[1] in ("commit", "push") for c in calls):
        return []
    allowed = _allowed()
    lines, files = _changes(calls)
    found, seen = [], set()
    for rel in sorted(files):
        if SECRET_FILE.search(rel) and not EXAMPLE_FILE.search(rel) and fingerprint(rel) not in allowed:
            found.append({"kind": "file", "file": rel, "line": 0, "mask": rel, "fp": fingerprint(rel)})
    for rel, n, text in lines:
        for kind, rx in COMPILED.items():
            for m in rx.finditer(text):
                fp = fingerprint(m.group(0))
                if fp in allowed or (rel, fp) in seen:
                    continue
                seen.add((rel, fp))
                found.append({"kind": kind, "file": rel, "line": n, "fp": fp,
                              "mask": t(lang, "mask", head=m.group(0)[:4], n=len(m.group(0)))})
    return found


def gate(session: str, tool: str, inp: dict, cwd: str, lang: str = "en"):
    """The reason to refuse a commit or a push that would carry a key, else None."""
    cmd = str(inp.get("command", ""))
    if tool not in ("Bash", "PowerShell") or "git" not in cmd or not re.search(r"\b(?:commit|push)\b", cmd):
        return None
    found = scan(cmd, cwd, lang)
    if not found:
        return None
    common.log("secrets", {"session": session, "found": [{k: f[k] for k in ("kind", "file", "line", "fp")}
                                                         for f in found]})
    lines = [t(lang, "secrets_line", where=f"{f['file']}:{f['line']}" if f["line"] else f["file"],
               kind=name(lang, "kinds", f["kind"]), mask=f["mask"], fp=f["fp"]) for f in found[:8]]
    return "\n".join([t(lang, "secrets_head"), *lines, t(lang, "secrets_tail", allow=common.DATA / ALLOW)])
