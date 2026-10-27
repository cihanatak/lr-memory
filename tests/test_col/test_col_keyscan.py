"""The key scan before a commit or a push: a key on its way into a repository stops the command, and the reason names
the file, the line and the kind of key, never the key. A broken scan lets the command through."""
import subprocess

from col import hooks, keyscan
from .colkit import bash, logged

# built at run time, so that no key-shaped string sits in this file
KEY = "sk-" + "ant-" + "api03-" + "A1b2C3d4" * 6
AWS = "AKIA" + "ABCDEFGHIJ234567"
PUSH = "Push. Prediction [push]: 1 commit ahead (~1 min)"


def test_a_staged_key_stops_the_commit_and_is_never_repeated(col_data, repo):
    r, _, git = repo
    (r / "ok.py").write_text("print('hello')\n")
    (r / "conf.py").write_text(f"name = 'x'\nkey = '{KEY}'\n")
    git("add", "ok.py")
    assert bash(r, "git commit -m ok") is None  # conf.py is not staged
    git("add", "conf.py")
    reason = bash(r, 'git commit -m "add config"')
    assert "Anthropic key" in reason and "conf.py:2" in reason and keyscan.fingerprint(KEY) in reason
    assert KEY not in reason and KEY[8:] not in reason
    found = logged(col_data, "secrets")[0]["found"]
    assert [(f["kind"], f["file"], f["line"]) for f in found] == [("anthropic", "conf.py", 2)]
    assert KEY not in (col_data / "secrets.jsonl").read_text(encoding="utf-8")


def test_what_the_same_command_is_about_to_stage_is_scanned(repo):
    r, _, _ = repo
    (r / "conf.py").write_text(f"key = '{KEY}'\n")
    for cmd in ("git add . && git commit -m wip", "git add -A; git commit -m wip", "git commit -am wip",
                f"cd {r.as_posix()} && git add conf.py && git commit -m wip",
                f"git -C {r.as_posix()} add . && git -C {r.as_posix()} commit -m wip"):
        reason = bash(r.parent if r.as_posix() in cmd else r, cmd)
        if cmd == "git commit -am wip":
            assert reason is None, cmd  # -a stages tracked files only, and conf.py is new
        else:
            assert "conf.py:1" in reason, cmd
    assert bash(r, "git add other.py && git commit -m wip") is None  # conf.py stays out


def test_a_push_is_judged_on_the_commits_no_remote_has(repo, tmp_path):
    r, _, git = repo
    (r / "conf.py").write_text(f"key = '{AWS}'\n")
    git("add", "conf.py")
    git("commit", "-q", "-m", "config")
    assert "AWS access key" in bash(r, "git push -u origin HEAD", PUSH)
    (r / "conf.py").write_text("key = os.environ['KEY']\n")
    git("commit", "-q", "-am", "env")
    assert "conf.py:1" in bash(r, "git push -u origin HEAD", PUSH)  # the history still carries the key
    bare = tmp_path / "remote.git"
    subprocess.run(["git", "init", "-q", "--bare", str(bare)], check=True)
    git("remote", "add", "origin", str(bare))
    git("push", "-q", "origin", "HEAD")  # straight through git: the key has left already
    (r / "readme.md").write_text("hi\n")
    git("add", "readme.md")
    git("commit", "-q", "-m", "readme")
    assert bash(r, "git push origin HEAD", PUSH) is None


def test_taking_a_key_out_is_not_stopped(repo):
    r, _, git = repo
    (r / "conf.py").write_text(f"key = '{KEY}'\n")
    git("add", "conf.py")
    git("commit", "-q", "-m", "oops")
    (r / "conf.py").write_text("key = os.environ['KEY']\n")
    assert bash(r, "git add conf.py && git commit -m fix") is None  # only added lines count


def test_a_secrets_file_is_named_and_an_example_file_is_not(repo):
    r, _, _ = repo
    (r / ".env").write_text("DEBUG=1\n")
    (r / ".env.example").write_text("DEBUG=1\n")
    reason = bash(r, "git add .env .env.example && git commit -m env")
    assert "- .env: a file that holds secrets" in reason and ".env.example" not in reason


def test_an_allowed_fingerprint_passes(col_data, repo):
    r, _, _ = repo
    (r / "conf.py").write_text(f"key = '{KEY}'\n")
    assert keyscan.fingerprint(KEY) in bash(r, "git add . && git commit -m wip")
    col_data.mkdir(parents=True, exist_ok=True)
    (col_data / "secret_allow.txt").write_text(f"# a test key\n{keyscan.fingerprint(KEY)}\n", encoding="utf-8")
    assert bash(r, "git add . && git commit -m wip") is None


def test_the_scan_can_be_turned_off(repo, monkeypatch):
    r, _, _ = repo
    (r / "conf.py").write_text(f"key = '{KEY}'\n")
    monkeypatch.setenv("COL_SECRETS", "off")
    assert bash(r, "git add . && git commit -m wip") is None


def test_logs_keep_only_the_shape_of_a_key(col_data, tmp_path):
    assert keyscan.redact(f"curl -H 'x-api-key: {KEY}' -d id={AWS}") == "curl -H 'x-api-key: [anthropic]' -d id=[aws]"
    assert bash(tmp_path, f"curl -H 'x-api-key: {KEY}' https://api.example.com > out.json", "fetch", True)
    text = (col_data / "gate.jsonl").read_text(encoding="utf-8")
    assert KEY not in text and "[anthropic]" in text


def test_a_broken_scan_lets_the_command_through(col_data, monkeypatch, capsys):
    def broken(*args, **kwargs):
        raise RuntimeError("the scanner broke")

    monkeypatch.setattr(keyscan, "scan", broken)
    hooks.pre_tool({"tool_name": "Bash", "session_id": "s", "cwd": ".", "tool_input": {"command": "git commit -m x"}})
    assert capsys.readouterr().out == ""
    assert "the scanner broke" in (col_data / "errors.log").read_text(encoding="utf-8")
