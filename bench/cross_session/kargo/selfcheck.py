"""Every grader of the kargo job checked with no model: the start carries none of day 1's facts, day 2 as given fails,
a scripted day 2 that does everything right passes all ten checks whether it keeps the carrier's limit by pacing or by
waiting out a 429, and each faulty variant fails its own check and no other. Then the runner's transcript marking and
its reading of a Turkish sleep report.

    python bench/cross_session/run.py --job kargo --selftest
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import checks  # noqa: E402
import days  # noqa: E402

VARIANTS = {"keeps the limit by waiting out a 429": "", "renames the typo": "C2", "gives no reason": "F1",
            "drops the reference": "F2", "ignores the limit": "F3", "backs off too little": "F3",
            "writes long answers": "C3", "skips the changelog": "C1"}
SHORT = "Tamam: toplu etiket kargocu/toplu.py'de, etiketler sipariş sırasıyla dönüyor."
PACED = '''"""Toplu etiket: günün siparişlerini tek seferde kaydeder, etiketlerini sırasıyla döndürür."""
from __future__ import annotations

import time

from . import etiket

ARALIK = 60 / 60  # saniye: Turna Kargo dakikada en çok 60 istek kabul ediyor


def toplu_etiket(siparisler, istemci) -> list:
    etiketler, son = [], None
    for siparis in siparisler:
        if son is not None:
            bekle = ARALIK - (time.monotonic() - son)
            if bekle > 0:
                time.sleep(bekle)
        son = time.monotonic()
        etiketler.append(etiket.etiket_olustur(siparis, istemci.gonderi_kaydet(siparis)))
    return etiketler
'''
WAITS = '''"""Toplu etiket: günün siparişlerini tek seferde kaydeder, etiketlerini sırasıyla döndürür."""
from __future__ import annotations

import time

from . import etiket
from .istemci import KargoHatasi

DENEME = {DENEME}  # 429 gelirse kaç kez daha denenir
BEKLE = {BEKLE}  # saniye


def _kaydet(istemci, siparis) -> str:
    for deneme in range(DENEME + 1):
        try:
            return istemci.gonderi_kaydet(siparis)
        except KargoHatasi as e:
            if e.durum != 429 or deneme == DENEME:
                raise
            time.sleep(BEKLE * {CARPAN} ** deneme)


def toplu_etiket(siparisler, istemci) -> list:
    return [etiket.etiket_olustur(s, _kaydet(istemci, s)) for s in siparisler]
'''
BLIND = '''"""Toplu etiket."""
from . import etiket


def toplu_etiket(siparisler, istemci) -> list:
    return [etiket.etiket_olustur(s, istemci.gonderi_kaydet(s)) for s in siparisler]
'''


def edit(work: Path, rel: str, old: str, new: str) -> None:
    path = work / rel
    text = path.read_text(encoding="utf-8")
    assert old in text, f"{rel}: {old[:60]!r} not found"
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text.replace(old, new, 1))


def put(work: Path, rel: str, text: str) -> None:
    path = work / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def day_one(work: Path) -> None:
    """Day 1 done right, as a model would do it, committing nothing: desi rounded up, a flat 54,90 within a province
    with no reason given, names matched whatever their case and Turkish letters, and three lines under Yayımlanmamış."""
    edit(work, "kargocu/desi.py", "from __future__ import annotations\n", "from __future__ import annotations\n\n"
                                                                           "import math\n")
    edit(work, "kargocu/desi.py", "en yakın tam sayıya yuvarlanmış", "her zaman yukarı yuvarlanmış")
    edit(work, "kargocu/desi.py", "int(en * boy * yukseklik / BOLEN + 0.5)", "math.ceil(en * boy * yukseklik / BOLEN)")
    edit(work, "tests/test_desi.py", "def test_en_yakina_yuvarlanir():\n    assert desi.desi(31, 20, 10) == 2  # 2,07",
         "def test_yukari_yuvarlanir():\n    assert desi.desi(31, 20, 10) == 3  # 2,07")
    edit(work, "kargocu/ucret.py", 'EK_DESI = Decimal("5.90")', 'AYNI_IL = Decimal("54.90")\nEK_DESI = Decimal("5.90")')
    edit(work, "kargocu/ucret.py", '    agirlik = _desi.ucretli_agirlik(siparis)\n',
         '    if siparis.il == siparis.gonderen_il:\n        return AYNI_IL\n    agirlik = _desi.ucretli_agirlik(siparis)\n')
    edit(work, "kargocu/adres.py", "  # {il: [ilçe, ...]}\n",
         '  # {il: [ilçe, ...]}\n_HARF = str.maketrans("çğıöşü", "cgiosu")\n\n\ndef _sade(ad: str) -> str:\n'
         '    """Adın karşılaştırılan biçimi: Türkçe kurala göre küçük harf, Türkçe harfler sade."""\n'
         '    return ad.strip().replace("İ", "i").replace("I", "ı").lower().translate(_HARF)\n\n\n'
         "_SADE = {_sade(il): {_sade(ilce) for ilce in ilceler} for il, ilceler in ILCELER.items()}\n")
    edit(work, "kargocu/adres.py", "    if siparis.il not in ILCELER:\n",
         "    il = _sade(siparis.il)\n    if il not in _SADE:\n")
    edit(work, "kargocu/adres.py", "    elif siparis.ilce not in ILCELER[siparis.il]:\n",
         "    elif _sade(siparis.ilce) not in _SADE[il]:\n")
    edit(work, "CHANGELOG.md", "# Değişiklik günlüğü\n\n", "# Değişiklik günlüğü\n\n## Yayımlanmamış\n"
         "- Desi: sonuç her zaman yukarı yuvarlanıyor.\n- Ücret: aynı ildeki gönderilere sabit 54,90 TL.\n"
         "- Adres: il ve ilçe adları büyük/küçük harf ve Türkçe karakter farkına bakmadan eşleşiyor.\n\n")


def day_two(work: Path, today: str, baseline: str, variant: str = "") -> dict:
    """Day 2 done right, or with one thing wrong; returns the answers that ended its three turns."""
    toplu = {"ignores the limit": BLIND,
             "backs off too little": WAITS.replace("{DENEME}", "3").replace("{BEKLE}", "1").replace("{CARPAN}", "2"),
             "keeps the limit by waiting out a 429": WAITS.replace("{DENEME}", "100").replace("{BEKLE}", "5")
             .replace("{CARPAN}", "1")}.get(variant, PACED)
    put(work, "kargocu/toplu.py", toplu)
    edit(work, "kargocu/api.py", "import os\n\n", "")
    if variant == "renames the typo":
        edit(work, "kargocu/api.py", "def takip_sorgla(", "def takip_sorgula(")
        edit(work, "kargocu/api.py", '"takip": takip_sorgla', '"takip": takip_sorgula')
    why = "Aynı ildeki gönderiler desiden bağımsız sabit ücretli." if variant == "gives no reason" else \
        "Turna Kargo bu ay yeni tarifeye geçti ve yakıt ek ücreti ekledi; 49,90 TL'den 54,90 TL'ye çıktı."
    edit(work, "kargocu/ucret.py", "AYNI_IL = ", f"# {why}\nAYNI_IL = ")
    rows = ("" if variant == "drops the reference" else f"| 2026-10-28, temizlikten önce (referans) | {baseline} |\n") \
        + f"| 2026-10-29 | {today} |\n"
    put(work, "docs/veri_kalitesi.md", "# Sorunlu adresler, tools/adres_kontrol.py\n\n| gün | sorunlu adres |\n"
                                       "| --- | --- |\n" + rows)
    if variant != "skips the changelog":
        edit(work, "CHANGELOG.md", "## Yayımlanmamış\n", "## Yayımlanmamış\n- Toplu etiket: toplu_etiket().\n")
    answer = " ".join(["sözcük"] * 150) if variant == "writes long answers" else SHORT
    return {k: answer for k in range(1, len(days.DAY2) + 1)}


def selftest(runner) -> int:
    """`runner` is run.py, for its transcript marking."""
    problems = []

    def expect(label: str, ok: bool, detail="") -> None:
        print(f"{'ok  ' if ok else 'FAIL'} {label}" + ("" if ok else f": {detail}"))
        if not ok:
            problems.append(label)

    folder = Path(tempfile.mkdtemp(prefix="lrcross-kargo-selftest-"))
    try:
        work = folder / "work"
        work.mkdir()
        start = checks.prepare(work)
        baseline = checks.measure(work)
        expect("the order dump has 218 problem addresses as given", baseline == "218", baseline)
        said = "\n".join(t for rel, t in checks.start_files().items() if not rel.startswith("data/"))
        found = [k for k, v in checks.LEAKS.items() if re.search(v, said, re.I)]
        found += ["F2"] * checks.said(baseline, said) + ["C1"] * bool(checks.unreleased(said))
        expect("the start says none of day 1's facts, and the typo is in", not found and "def takip_sorgla(" in said,
               found)
        tests = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"], cwd=work,
                               capture_output=True, text=True, timeout=600, env=checks.QUIET)
        expect("the repository's own tests pass as given", tests.returncode == 0, tests.stdout[-300:])
        day_one(work)
        day1 = {"baseline": baseline, "state": checks.state(work, start, baseline)}
        expect("day 1 done right writes no rule or fact into the repository",
               not any(day1["state"]["leaks"].values()), day1["state"]["leaks"])
        expect("the cleanup leaves 63", day1["state"]["measured"] == "63", day1["state"]["measured"])
        shutil.copytree(work, folder / "day1")
        g = checks.grade(work, day1, {k: SHORT for k in range(1, 4)}, tests=False)
        failed = {k for k, v in g["checks"].items() if v[0] is False}
        expect("day 2 as given fails the task, the rule it needs and the facts",
               {"T1", "T2", "T4", "C1", "F1", "F2", "F3"} <= failed, sorted(failed))
        for variant in ("", *VARIANTS):
            checks.repo.remove(work)
            shutil.copytree(folder / "day1", work)
            g = checks.grade(work, day1, day_two(work, day1["state"]["measured"], baseline, variant),
                             tests=not variant)
            failed = sorted(k for k, v in g["checks"].items() if v[0] is False)
            want = [VARIANTS[variant]] if VARIANTS.get(variant) else []
            expect(f"day 2 that {variant or 'paces itself and does everything right'} fails "
                   f"{want[0] if want else 'nothing'}", failed == want,
                   f"failed {failed}; " + "; ".join(f"{k}: {v[1]}" for k, v in g["checks"].items() if v[0] is False))
            if not variant:
                expect("its own tests pass, and nothing is left out", g["checks"]["T3"][0] is True
                       and g["of_memory"] == 4, g["checks"]["T3"])
            if variant in ("", "keeps the limit by waiting out a 429", "ignores the limit"):
                print(f"     F3: {g['checks']['F3'][1]}")
        projects = folder / "config" / "projects" / "p"
        projects.mkdir(parents=True)
        rows = [{"type": "user", "entrypoint": "sdk-cli", "origin": {"kind": "sdk"},
                 "message": {"role": "user", "content": [{"type": "text", "text": days.DAY1[2]}]}},
                {"type": "assistant", "entrypoint": "sdk-cli", "message": {"content": []}}]
        (projects / "s.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
        changed = runner.typed(projects.parent)
        back = [json.loads(x) for x in (projects / "s.jsonl").read_text(encoding="utf-8").splitlines()]
        expect("day 1's transcript reads as typed", changed == 2 and back[0]["origin"]["kind"] == "human", back)
        report = "1 projede 6 mesaj ve 0 commit okundu. Maliyet: 5.201 token (girdi 3.265, çıktı 1.936)."
        expect("the Turkish sleep report's cost and message count are read",
               runner.tokens_of(report) == 5201 and runner.messages_read(report) == 6, report)
    finally:
        checks.repo.remove(folder)
    print(f"{'all checks passed' if not problems else f'{len(problems)} failed'}")
    return 1 if problems else 0
