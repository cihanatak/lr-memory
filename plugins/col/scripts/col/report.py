"""COL's record from its own logs: what the claim check flagged and blocked, how the predictions turned out, and what
the key scan stopped. Local files only; no model is asked."""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone

from col import common, predict
from col.text import name, t


def _days(days: float) -> str:
    return str(int(days)) if float(days).is_integer() else str(days)


def report(days: float = 30, lang: str = "") -> str:
    lang = lang or common.lang()
    since = common.iso(datetime.now(timezone.utc) - timedelta(days=days))
    recent = lambda rows: [r for r in rows if str(r.get("at", "")) >= since]  # noqa: E731
    checks, outcomes, gates = recent(common.read_log("checks")), recent(common.read_log("outcomes")), recent(
        common.read_log("gate"))
    secrets = recent([r for r in common.read_log("secrets") if r.get("found")])
    ledger = recent(predict.rows())
    out = [t(lang, "r_head", days=_days(days)), ""]
    if not (checks or ledger or gates or secrets):
        return "\n".join([*out, t(lang, "r_empty", days=_days(days)), "", t(lang, "r_data", path=common.DATA)])
    if checks:
        flagged = [r for r in checks if r.get("problems")]
        out.append(t(lang, "r_claims", turns=len(checks), flagged=len(flagged),
                     blocked=sum(bool(r.get("blocked")) for r in checks)))
        kinds = Counter(p.get("kind") for r in flagged for p in r["problems"] if isinstance(p, dict))
        if kinds:
            out.append(t(lang, "r_kinds", kinds=", ".join(f"{name(lang, 'problems', k)} {n}"
                                                          for k, n in kinds.most_common())))
        if outcomes:
            labels = Counter(r.get("label") for r in outcomes)
            out.append(t(lang, "r_labels", right=labels["right"], wrong=labels["wrong"], unclear=labels["unclear"]))
        out.append("")
    preds = [r for r in ledger if r.get("type") == "prediction"]
    results = [r for r in ledger if r.get("type") == "result"]
    if preds or results or gates:
        calib = [r for r in results if r.get("kind") != "hypothesis"]
        tested = [r for r in results if r.get("kind") == "hypothesis"]
        out.append(t(lang, "r_ledger", preds=len(preds), results=len(results)))
        if calib:
            verdicts = Counter(r.get("verdict") for r in calib)
            out.append(t(lang, "r_compared", held=verdicts["held"], missed=verdicts["missed"],
                         nc=verdicts["not comparable"]))
            out.append(t(lang, "r_grounded", grounded=sum(bool(r.get("grounded")) for r in calib), results=len(calib)))
        misses = [r for r in calib if r.get("verdict") == "missed"]
        if misses:
            ways = Counter((r.get("direction") or {}).get("way") for r in misses)
            out.append(t(lang, "r_way", low=ways["low"], high=ways["high"]))
            out.append(t(lang, "r_misses"))
            out += [f"  - [{r.get('key')}] {str(r.get('prediction', ''))[:90]} → {str(r.get('text', ''))[:90]}"
                    for r in misses[-5:]]
        closed = {(r.get("session"), r.get("key")) for r in results}
        waiting = [p for p in preds if (p.get("session"), p.get("key")) not in closed]
        if waiting:
            out.append(t(lang, "r_open", open=len(waiting)))
        if tested:
            out.append(t(lang, "r_hyp", tested=len(tested), out=sum(r.get("verdict") == "missed" for r in tested)))
        if gates:
            out.append(t(lang, "r_gate", gate=len(gates)))
        out.append("")
    if secrets:
        kinds = Counter(f.get("kind") for r in secrets for f in r.get("found", []))
        named = ", ".join(f"{name(lang, 'kinds', k)} {n}" for k, n in kinds.most_common())
        out.append(t(lang, "r_secrets", n=len(secrets), kinds=named))
        out.append("")
    out.append(t(lang, "r_data", path=common.DATA))
    return "\n".join(out)
