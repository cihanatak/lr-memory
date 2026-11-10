"""The 13 aims: fixed content in both languages, and how a scorecard (when the user keeps one) is laid over them."""
from __future__ import annotations

import json
from pathlib import Path

STATUSES = ("works", "partial", "fails", "unused", "unclear", "unmeasured")

# id, part, aim, region key, analogy, yardstick, live numbers (metric keys collected by collect.py)
AIMS = [
    {"id": 1, "part": "LR", "region": "dlpfc", "metrics": ["compactions", "episodes"],
     "aim": {"tr": "Sohbet hiç kapanmaz, özetlemede bilgi kaybolmaz",
             "en": "The conversation never closes; compaction loses nothing"},
     "analogy": {"tr": "Dorsolateral prefrontal korteks, çalışma belleğini ayakta tutar",
                 "en": "Dorsolateral prefrontal cortex, keeps working memory up"},
     "yardstick": {"tr": "Özetlemeden sonra gereken bilgi yerinde mi; her özetlemede iz kaydı var mı",
                   "en": "Whether what is needed is still there after a compaction; a trace kept at every one"}},
    {"id": 2, "part": "LR", "region": "hippocampus", "metrics": ["recall_searches", "sessions_on_record"],
     "aim": {"tr": "Yaşanan birebir kaydedilir, gerekince bulunur",
             "en": "What happened is kept word for word and found when needed"},
     "analogy": {"tr": "Hipokampus, epizodik bellek ve ipucundan hatırlama",
                 "en": "Hippocampus, episodic memory and recall from a cue"},
     "yardstick": {"tr": "Geçmişe dönük sorularda aramanın doğru kaydı bulma oranı",
                   "en": "How often a search finds the right record for a question about the past"}},
    {"id": 3, "part": "LR", "region": "temporal", "metrics": ["rules", "rules_added"],
     "aim": {"tr": "Düzeltmeler ve doğrulanmış dersler kurala döner",
             "en": "Corrections and confirmed lessons become rules"},
     "analogy": {"tr": "Ön temporal neokorteks, anlamsal bellek", "en": "Anterior temporal neocortex, semantic memory"},
     "yardstick": {"tr": "Kullanıcı düzeltmelerinin kaçının kurala döndüğü",
                   "en": "How many of the user's corrections became rules"}},
    {"id": 4, "part": "LR", "region": "striatum", "metrics": ["cue_reminders", "cue_rules", "rules_with_cue"],
     "aim": {"tr": "Kural gereken anda kendiliğinden geri gelir",
             "en": "A rule comes back on its own at the moment it applies"},
     "analogy": {"tr": "Bazal gangliyonlar, ipucuyla tetiklenen alışkanlık",
                 "en": "Basal ganglia, habits triggered by a cue"},
     "yardstick": {"tr": "Yazılı bir kural varken tekrarlanan hatanın kural hatırlatıldığında düşmesi",
                   "en": "Whether a repeated mistake drops once its written rule is brought back"}},
    {"id": 5, "part": "LR", "region": "thalamus", "metrics": ["sleep_passes", "sleep_last", "candidates"],
     "aim": {"tr": "Gece pekiştirir, işe yaramayanı söndürür",
             "en": "Consolidates at night and lets the useless fade"},
     "analogy": {"tr": "Uykuda talamokortikal iğcikler ve hipokampus–korteks yeniden oynatımı",
                 "en": "Thalamocortical spindles and hippocampal–cortical replay in sleep"},
     "yardstick": {"tr": "Gece geçişinin yazdığı kuralların doğruluğu ve kapanan adaylar",
                   "en": "How right the rules a nightly pass writes are, and which candidates it closes"}},
    {"id": 6, "part": "LR", "region": "cerebellum", "metrics": [],
     "aim": {"tr": "Aynı hata ikinci kez yapılmaz", "en": "The same mistake is not made twice"},
     "analogy": {"tr": "Beyincik, hatadan denetimli öğrenme", "en": "Cerebellum, supervised learning from error"},
     "yardstick": {"tr": "Aynı sınıftan düzeltmenin yeniden gelme oranı",
                   "en": "How often a correction of the same kind comes back"}},
    {"id": 7, "part": "LR", "region": "parietal", "metrics": ["context_median"],
     "aim": {"tr": "Bağlam küçük kalır, kalite düşmez", "en": "Context stays small and quality does not drop"},
     "analogy": {"tr": "Arka parietal korteks, dikkatin seçimi", "en": "Posterior parietal cortex, selection by attention"},
     "yardstick": {"tr": "Çağrı başına bağlam tokenı ve aynı işte kalite",
                   "en": "Context tokens per call, and quality on the same work"}},
    {"id": 8, "part": "COL", "region": "acc", "metrics": ["checks", "claims_caught"],
     "aim": {"tr": "Yapılmamış iş \"bitti\" diye sunulmaz", "en": "Work that was not done is never reported as done"},
     "analogy": {"tr": "Ön singulat korteks, hata ve çatışma izleme",
                 "en": "Anterior cingulate cortex, error and conflict monitoring"},
     "yardstick": {"tr": "Yakalanan yanlış iddialar ve kaçanlar", "en": "False claims caught, and those that slipped"}},
    {"id": 9, "part": "COL", "region": "tpj", "metrics": ["intent_looks", "intent_turned_back", "intent_tokens"],
     "aim": {"tr": "Gerçekten ne istendiği anlaşılır, iş o yöne gider",
             "en": "What is really wanted is understood and the work goes that way"},
     "analogy": {"tr": "Temporoparietal kavşak ve medial prefrontal korteks, karşıdakinin niyetini okuma",
                 "en": "Temporoparietal junction and medial prefrontal cortex, reading another's intent"},
     "yardstick": {"tr": "Amaç kaçırmalarının tur sonunda yakalanma oranı",
                   "en": "How often a missed aim is caught at the end of a turn"}},
    {"id": 10, "part": "COL", "region": "ofc",
     "metrics": ["pred_recorded", "pred_held", "pred_missed", "pred_uncompared", "pred_hit", "guard_stopped",
                 "secrets_stopped"],
     "aim": {"tr": "Büyük adımdan önce öngörü, sonra karşılaştırma; yasak korunur",
             "en": "A prediction before a big step, a comparison after; what is forbidden stays protected"},
     "analogy": {"tr": "Orbitofrontal korteks ve alt frontal girus, beklenen sonuç ve ket vurma",
                 "en": "Orbitofrontal cortex and inferior frontal gyrus, expected outcome and inhibition"},
     "yardstick": {"tr": "Öngörülerin karşılaştırılma oranı; durdurulan yasak yazmalar ve anahtarlar",
                   "en": "How many predictions get compared; forbidden writes and keys stopped"}},
    {"id": 11, "part": "scnc", "region": "frontopolar", "metrics": ["hypothesis_lines"],
     "aim": {"tr": "İlk açıklamaya atlanmaz, rakip açıklamalar kurulur",
             "en": "No jumping to the first explanation; rivals are set up"},
     "analogy": {"tr": "Frontopolar korteks, alternatifleri bekletme",
                 "en": "Frontopolar cortex, holding alternatives in reserve"},
     "yardstick": {"tr": "Bir hata karşısında rakip açıklama yazılan durumlar",
                   "en": "Failures met with written rival explanations"}},
    {"id": 12, "part": "scnc", "region": "lc", "metrics": ["scnc_skill_calls"],
     "aim": {"tr": "Kararı ucuz bir deney verir", "en": "A cheap experiment decides"},
     "analogy": {"tr": "Locus coeruleus, beklenmedik belirsizlikte keşfe geçiş",
                 "en": "Locus coeruleus, switching to exploration under unexpected uncertainty"},
     "yardstick": {"tr": "Rakipleri ayıran tek bir deneyin koşulduğu durumlar",
                   "en": "Cases where one experiment that tells the rivals apart was run"}},
    {"id": 13, "part": "scnc", "region": "vta",
     "metrics": ["streak2", "streak3", "streak_share", "scnc_reminders", "scnc_third_after"],
     "aim": {"tr": "Düzeltme kök sebebe yapılır, aynı ölçümle doğrulanır",
             "en": "The fix goes to the root cause and is verified with the same measurement"},
     "analogy": {"tr": "Orta beyin dopamin hücreleri, öngörü hatasıyla güncelleme",
                 "en": "Midbrain dopamine cells, updating from prediction error"},
     "yardstick": {"tr": "Aynı komutun ikinci başarısızlıktan sonra üçüncüye gitme oranı",
                   "en": "How often the same command goes from a second failure to a third"}},
]


def _both(v) -> dict | None:
    """{"tr", "en"} from a scorecard field; a missing language falls back to the other."""
    if isinstance(v, str):
        return {"tr": v, "en": v} if v else None
    if not isinstance(v, dict):
        return None
    tr, en = v.get("tr") or v.get("en"), v.get("en") or v.get("tr")
    return {"tr": tr, "en": en} if tr or en else None


def load_scorecard(path, missing_paths: list) -> tuple:
    """(aims by id, {"path", "as_of", "source"}) or ({}, None) when there is none."""
    if not path:
        return {}, None
    p = Path(path)
    if not p.is_file():
        missing_paths.append(str(p))
        return {}, None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}, {"path": str(p), "error": "unreadable"}
    if not isinstance(data, dict):
        return {}, {"path": str(p), "error": "unreadable"}
    by = {}
    for a in data.get("aims") or []:
        if isinstance(a, dict) and isinstance(a.get("id"), int):
            by[a["id"]] = a
    return by, {"path": str(p), "as_of": data.get("as_of"), "source": data.get("source")}


def build(card: dict, metrics: dict) -> list:
    out = []
    for a in AIMS:
        c = card.get(a["id"]) or {}
        status = c.get("status") if c.get("status") in STATUSES else "unmeasured"
        out.append({**a,
                    "status": status,
                    "on_card": bool(c),
                    "status_text": _both(c.get("status_text")),
                    "yardstick": _both(c.get("yardstick")) or a["yardstick"],
                    "measured": _both(c.get("measured")),
                    "measured_on": c.get("measured_on"),
                    "evidence": c.get("evidence"),
                    "live": [k for k in a["metrics"] if k in metrics]})
    return out
