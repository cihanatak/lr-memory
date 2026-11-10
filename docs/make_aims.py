#!/usr/bin/env python3
"""Writes docs/AIMS.md and docs/AIMS.tr.md from the two places the aims live: plugins/mind/scripts/mind/aims.py (what
each aim is) and docs/scorecard.json (where it stands). The README's short table comes from the same data; a test
keeps all three from drifting apart.

usage: python docs/make_aims.py            write both files
       python docs/make_aims.py --table en  print the README's table
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

DOCS = Path(__file__).resolve().parent
sys.path.insert(0, str(DOCS.parent / "plugins" / "mind" / "scripts"))
from mind import aims  # noqa: E402

MARK = {"works": "✓", "partial": "◐", "fails": "✕", "unused": "○", "unclear": "?", "unmeasured": "·"}
WORD = {"en": {"works": "works", "partial": "partial", "fails": "fails", "unused": "unused", "unclear": "unclear",
               "unmeasured": "not measured"},
        "tr": {"works": "çalışıyor", "partial": "kısmen", "fails": "tutmuyor", "unused": "kullanılmıyor",
               "unclear": "belirsiz", "unmeasured": "ölçülmedi"}}
PARTS = {"en": {"LR": "LR: memory", "COL": "COL: self-check", "scnc": "scnc: finding causes"},
         "tr": {"LR": "LR: hafıza", "COL": "COL: öz denetim", "scnc": "scnc: sebep bulma"}}
T = {
    "en": {
        "title": "# The 13 aims", "other": "[Türkçe](AIMS.tr.md)",
        "intro": [
            "Living Runtime does not try to add intelligence to Claude Code. It tries to make better use of the "
            "intelligence that is already there: to remember, to check itself, and to find the cause when something "
            "fails. That comes to thirteen aims in three parts. Each aim has a yardstick, and a status that is written "
            "only after a measurement.",
            "- **LR** (memory, aims 1 to 7) is in this repository as the `lr-memory` plugin.\n"
            "- **COL**, the Cognitive Operating Loop (self-check, aims 8 to 10), is in this repository as the `col` "
            "plugin.\n"
            "- **scnc** (finding causes, aims 11 to 13) is the author's skill for an unknown cause: rival "
            "explanations, one cheap experiment that tells them apart, a fix at the root. Its automatic part ships "
            "inside `col`, as the check that asks for rival explanations when a fix does not hold.",
            "The [mind panel](../plugins/mind/README.md) shows these aims with live numbers from your own files."],
        "stand": "## Where they stand", "as_of": "As of {as_of}:", "cols": "| # | Aim | Status | Yardstick | Last "
        "measurement |\n| --- | --- | --- | --- | --- |",
        "not_all": "Not every aim holds yet, and this page says which. The measurements were made on the author's "
                   "own record, with one reader; they are not a benchmark.",
        "analogy": "## The brain regions are an analogy",
        "analogy_text": "The panel puts each aim on a brain region. It is a way to read the system, not a claim about "
                        "brains.",
        "analogy_cols": "| # | Aim | Region and what it stands for |\n| --- | --- | --- |",
        "words": "## Status words",
        "words_list": [("works", "measured, and it holds"), ("partial", "measured, and part of it holds"),
                       ("fails", "measured, and it does not hold"),
                       ("unused", "the mechanism is there and is not being used"),
                       ("unclear", "measured, and the numbers cannot tell"),
                       ("unmeasured", "no measurement; the panel shows this for every aim until you keep a "
                                      "scorecard")],
        "own": "## Your own scorecard",
        "own_text": "The statuses above are the author's. On your machine the panel shows every aim as not measured "
                    "until you keep a scorecard: a JSON file at `~/.claude/mind/scorecard.json` (or `--scorecard "
                    "FILE`) in the shape of [scorecard.json](scorecard.json). A text field may be one string or "
                    "`{\"en\": …, \"tr\": …}`.",
    },
    "tr": {
        "title": "# 13 amaç", "other": "[English](AIMS.md)",
        "intro": [
            "Living Runtime, Claude Code'a zekâ eklemeye çalışmaz. Var olan zekâyı daha iyi kullanmaya çalışır: "
            "hatırlamak, kendini denetlemek, bir şey bozulunca sebebini bulmak. Bu, üç bölümde on üç amaç eder. Her "
            "amacın bir ölçütü var; durumu ancak bir ölçümden sonra yazılır.",
            "- **LR** (hafıza, amaç 1–7) bu depoda `lr-memory` eklentisidir.\n"
            "- **COL**, Cognitive Operating Loop (öz denetim, amaç 8–10), bu depoda `col` eklentisidir.\n"
            "- **scnc** (sebep bulma, amaç 11–13) yazarın, sebebi bilinmeyen durumlar için becerisidir: rakip "
            "açıklamalar, onları ayıran ucuz tek deney, kök sebebe düzeltme. Kendiliğinden çalışan kısmı `col` içinde "
            "gelir: bir düzeltme tutmadığında rakip açıklama isteyen kontrol.",
            "[Zihin paneli](../plugins/mind/README.tr.md) bu amaçları kendi dosyalarınızdan okunan canlı sayılarla "
            "gösterir."],
        "stand": "## Ne durumdalar", "as_of": "{as_of} itibarıyla:", "cols": "| # | Amaç | Durum | Ölçüt | Son ölçüm |"
        "\n| --- | --- | --- | --- | --- |",
        "not_all": "Amaçların bir kısmı henüz tutmuyor; bu sayfa hangileri olduğunu yazar. Ölçümler yazarın kendi "
                   "kaydında, tek okuyucuyla yapıldı; bir kıyaslama testi değildir.",
        "analogy": "## Beyin bölgeleri bir benzetmedir",
        "analogy_text": "Panel her amacı bir beyin bölgesine koyar. Bu, sistemi okumanın bir yoludur; beyin hakkında "
                        "bir iddia değildir.",
        "analogy_cols": "| # | Amaç | Bölge ve neyi temsil ettiği |\n| --- | --- | --- |",
        "words": "## Durum sözcükleri",
        "words_list": [("works", "ölçüldü ve tutuyor"), ("partial", "ölçüldü, bir kısmı tutuyor"),
                       ("fails", "ölçüldü ve tutmuyor"), ("unused", "mekanizma var ama kullanılmıyor"),
                       ("unclear", "ölçüldü, sayılar ayırt edemiyor"),
                       ("unmeasured", "ölçüm yok; siz bir karne tutana kadar panel her amacı böyle gösterir")],
        "own": "## Kendi karneniz",
        "own_text": "Yukarıdaki durumlar yazarındır. Sizin makinenizde panel, siz bir karne tutana kadar her amacı "
                    "ölçülmedi diye gösterir: `~/.claude/mind/scorecard.json` yolunda (ya da `--scorecard DOSYA`), "
                    "[scorecard.json](scorecard.json) biçiminde bir JSON dosyası. Metin alanları tek bir dize ya da "
                    "`{\"en\": …, \"tr\": …}` olabilir.",
    },
}


def card() -> dict:
    return json.loads((DOCS / "scorecard.json").read_text(encoding="utf-8"))


def rows(lang: str) -> list:
    """One dict per aim: the fixed content of aims.py with the scorecard laid over it."""
    by = {a["id"]: a for a in card()["aims"]}
    out = []
    for a in aims.AIMS:
        c = by.get(a["id"], {})
        status = c.get("status") if c.get("status") in aims.STATUSES else "unmeasured"
        pick = lambda v: (v.get(lang) or v.get("en") or "") if isinstance(v, dict) else (v or "")  # noqa: E731
        out.append({"id": a["id"], "part": a["part"], "aim": a["aim"][lang], "analogy": a["analogy"][lang],
                    "status": status, "badge": f"{MARK[status]} {WORD[lang][status]}",
                    "yardstick": pick(c.get("yardstick")) or a["yardstick"][lang],
                    "measured": pick(c.get("measured")) or WORD[lang]["unmeasured"]})
    return out


def cell(text: str) -> str:
    return str(text).replace("|", "\\|").replace("\n", " ")


def counts(lang: str) -> str:
    rs = rows(lang)
    return " · ".join(f"**{sum(r['status'] == s for r in rs)}** {WORD[lang][s]}" for s in aims.STATUSES
                      if any(r["status"] == s for r in rs))


def table(lang: str) -> str:
    """The README's short table: number, part, aim, status."""
    head = {"en": "| # | Part | Aim | Status |", "tr": "| # | Bölüm | Amaç | Durum |"}[lang]
    return "\n".join([head, "| --- | --- | --- | --- |"] + [
        f"| {r['id']} | {r['part']} | {cell(r['aim'])} | {r['badge']} |" for r in rows(lang)])


def render(lang: str) -> str:
    t, c, rs = T[lang], card(), rows(lang)
    src = c.get("source")
    src = (src.get(lang) or src.get("en") or "") if isinstance(src, dict) else (src or "")
    out = [t["title"], t["other"], *t["intro"], t["stand"], t["as_of"].format(as_of=c.get("as_of", "")) + " " +
           counts(lang) + ".", src, t["not_all"]]
    for part in ("LR", "COL", "scnc"):
        out.append(f"### {PARTS[lang][part]}")
        out.append("\n".join([t["cols"]] + [
            f"| {r['id']} | {cell(r['aim'])} | {r['badge']} | {cell(r['yardstick'])} | {cell(r['measured'])} |"
            for r in rs if r["part"] == part]))
    out += [t["analogy"], t["analogy_text"], "\n".join([t["analogy_cols"]] + [
        f"| {r['id']} | {cell(r['aim'])} | {cell(r['analogy'])} |" for r in rs])]
    out += [t["words"], "\n".join(f"- **{MARK[s]} {WORD[lang][s]}**: {d}" for s, d in t["words_list"])]
    out += [t["own"], t["own_text"]]
    return "\n\n".join(x for x in out if x) + "\n"


def main(argv: list) -> int:
    if argv[:1] == ["--table"]:
        sys.stdout.reconfigure(encoding="utf-8")
        print(table(argv[1] if len(argv) > 1 else "en"))
        return 0
    for lang, name in (("en", "AIMS.md"), ("tr", "AIMS.tr.md")):
        with open(DOCS / name, "w", encoding="utf-8", newline="\n") as f:
            f.write(render(lang))
        print(DOCS / name)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
