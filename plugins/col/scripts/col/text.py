"""Everything COL says, in English and Turkish."""
from __future__ import annotations

TEXT = {
    "en": {
        "rule_predict": ("COL is on. Before a background job or a step that cannot be taken back (git push, a deploy, "
                         "a publish), put a measurable prediction in the command's description: 'Prediction [key]: "
                         "<what> <number or range> (~<time>)'. When the result is in, write 'Result [key]: <observed "
                         "number>' in your reply; COL compares the two from the numbers."),
        "rule_claims": ("When you stop, COL checks your last message: a commit you name must exist, a file you cite "
                        "must be on disk, and a test count you give must appear in real test output."),
        "calibration": "Your record in this folder: {held} of the last {n} compared predictions held.",
        "calibration_misses": " Of the misses, {low} came in below the range and {high} above.",
        "calibration_time": " Durations: {short} of {timed} took less time than predicted, {long} more.",
        "claims_head": "COL: these claims in your last message are not backed by what ran or what exists:",
        "claims_tail": "Fix the message: show the evidence, or take the claim back.",
        "path": "'{what}' is cited, but it is not on disk",
        "commit": "'{what}' is called a commit, but no repository in reach has it",
        "tests": "'{what}' is said, but no real test output shows {n} passing tests",
        "no-tools": "no tool ran in this turn, yet the message says new work was done",
        "commit-claim": ("the message says something was committed ('{what}'), but no commit ran in this turn and "
                         "no commit id is given"),
        "gate_job": ("COL prediction ledger: write the expected result before starting a background job. Add a "
                     "measurable prediction to the command's description: 'Prediction [key]: <what> <number or "
                     "range> (~<time>)', for example 'Prediction [tests]: 41 passed, 0 failed (~2 min)'. When the "
                     "result is in, write 'Result [key]: <observed number>' in your reply; COL compares them."),
        "gate_final": ("COL prediction ledger: '{step}' cannot be taken back or reaches the outside world. First write "
                       "its expected effect in the command's description: 'Prediction [key]: <what> <number or "
                       "range> (~<time>)', for example 'Prediction [push]: main moves 1 commit ahead, CI green "
                       "(~3 min)'. When it is done, write 'Result [key]: <observed>' in your reply."),
        "due_head": "COL prediction ledger: these predictions are waiting for a result:",
        "due_tail": "If the result is in, write 'Result [key]: <observed number>' in your reply; if not, ignore this.",
        "secrets_head": "COL key scan: this commit or push would put these into the repository:",
        "secrets_line": "- {where}: {kind} ({mask}), fingerprint {fp}",
        "secrets_tail": ("Take the key out of the file (move it to an environment variable or a git-ignored file) "
                         "and try again. If you are sure it is a false alarm, ask the user; if they agree, add the "
                         "fingerprint as a line to {allow}."),
        "mask": "{head}… ({n} characters)",
        "kinds": {"anthropic": "Anthropic key", "openai": "OpenAI key", "github": "GitHub token",
                  "gitlab": "GitLab token", "aws": "AWS access key", "google": "Google API key",
                  "slack": "Slack token", "stripe": "Stripe live key", "huggingface": "Hugging Face token",
                  "npm": "npm token", "kaggle": "Kaggle key", "private": "private key",
                  "file": "a file that holds secrets"},
        "problems": {"path": "file not on disk", "commit": "unknown commit", "tests": "test count not in any output",
                     "no-tools": "work claimed with no tool run", "commit-claim": "commit claimed, none ran"},
        "r_head": "COL report, the last {days} days",
        "r_empty": "Nothing recorded in the last {days} days.",
        "r_claims": "Claim check: {turns} finished turns checked, {flagged} flagged, {blocked} blocked.",
        "r_kinds": "  Flagged: {kinds}.",
        "r_labels": ("  How the blocks turned out, from the answers to them: {right} right, {wrong} wrong, "
                     "{unclear} unclear."),
        "r_ledger": "Prediction ledger: {preds} predictions, {results} results.",
        "r_compared": "  Compared: {held} held, {missed} missed, {nc} could not be compared.",
        "r_grounded": "  {grounded} of {results} results give a number that appears in real tool output.",
        "r_way": "  Misses: {low} below the range, {high} above.",
        "r_misses": "  Recent misses:",
        "r_open": "  Waiting for a result: {open}.",
        "r_hyp": "  Hypotheses: {tested} tested, {out} ruled out.",
        "r_gate": "  Launches stopped for a missing prediction: {gate}.",
        "r_secrets": "Key scan: {n} commits or pushes stopped ({kinds}).",
        "r_data": "Logs: {path}",
    },
    "tr": {
        "rule_predict": ("Bu oturumda COL açık. Arka plan işinden ya da geri alınamayan bir adımdan (git push, "
                         "dağıtım, yayın) önce komutun description alanına ölçülebilir bir öngörü yaz: 'Öngörü "
                         "[anahtar]: <ne> <sayı ya da aralık> (~<süre ya da saat>)'. Sonuç gelince cevabında 'Sonuç "
                         "[anahtar]: <gözlenen sayı>' yaz; COL ikisini sayılardan karşılaştırır."),
        "rule_claims": ("Durduğunda COL son mesajını denetler: andığın commit var olmalı, verdiğin dosya diskte "
                        "olmalı, söylediğin test sayısı gerçek test çıktısında geçmeli."),
        "calibration": "Bu klasördeki kaydın: karşılaştırılan son {n} öngörünün {held} tanesi tuttu.",
        "calibration_misses": " Tutmayanlardan {low} tanesi aralığın altında, {high} tanesi üstünde kaldı.",
        "calibration_time": " Süreler: {timed} sürenin {short} tanesi öngörüden kısa, {long} tanesi uzun sürdü.",
        "claims_head": "COL: son mesajındaki şu iddialar çalışan araçlarla ya da diskteki durumla desteklenmiyor:",
        "claims_tail": "Mesajı düzelt: ya kanıtı göster ya da iddiayı geri al.",
        "path": "'{what}' anılıyor ama diskte yok",
        "commit": "'{what}' commit olarak anılıyor ama erişilen hiçbir depoda yok",
        "tests": "'{what}' deniyor ama gerçek test çıktılarında {n} geçen test görünmüyor",
        "no-tools": "bu turda hiçbir araç çalışmadı ama mesaj yeni iş yapıldığını söylüyor",
        "commit-claim": ("mesaj commit yapıldığını söylüyor ('{what}') ama bu turda commit çalışmadı ve commit "
                         "kimliği verilmemiş"),
        "gate_job": ("COL öngörü defteri: arka plan işini başlatmadan önce beklenen sonucu yaz. Komutun description "
                     "alanına ölçülebilir bir öngörü ekle: 'Öngörü [anahtar]: <ne> <sayı ya da aralık> (~<süre ya da "
                     "saat>)', örneğin 'Öngörü [testler]: 41 geçer, 0 düşer (~2 dk)'. Sonuç gelince cevabında 'Sonuç "
                     "[anahtar]: <gözlenen sayı>' yaz; karşılaştırmayı COL yapar."),
        "gate_final": ("COL öngörü defteri: '{step}' geri alınamaz ya da dışarıya gider. Önce beklenen etkiyi komutun "
                       "description alanına yaz: 'Öngörü [anahtar]: <ne> <sayı ya da aralık> (~<süre ya da saat>)', "
                       "örneğin 'Öngörü [gönderim]: main 1 commit ilerler, CI yeşil (~3 dk)'. Bitince cevabında "
                       "'Sonuç [anahtar]: <gözlenen>' yaz."),
        "due_head": "COL öngörü defteri: sonucu bekleyen öngörüler var:",
        "due_tail": "Sonuç geldiyse cevabında 'Sonuç [anahtar]: <gözlenen sayı>' yaz; gelmediyse bunu görmezden gel.",
        "secrets_head": "COL anahtar taraması: bu commit ya da push depoya şunları koyacak:",
        "secrets_line": "- {where}: {kind} ({mask}), parmak izi {fp}",
        "secrets_tail": ("Anahtarı dosyadan çıkar (bir ortam değişkenine ya da .gitignore'daki bir dosyaya taşı) ve "
                         "yeniden dene. Yanlış alarm olduğundan eminsen kullanıcıya sor; onaylarsa parmak izini "
                         "{allow} dosyasına bir satır olarak ekle."),
        "mask": "{head}… ({n} karakter)",
        "kinds": {"anthropic": "Anthropic anahtarı", "openai": "OpenAI anahtarı", "github": "GitHub tokenı",
                  "gitlab": "GitLab tokenı", "aws": "AWS erişim anahtarı", "google": "Google API anahtarı",
                  "slack": "Slack tokenı", "stripe": "Stripe canlı anahtarı", "huggingface": "Hugging Face tokenı",
                  "npm": "npm tokenı", "kaggle": "Kaggle anahtarı", "private": "özel anahtar",
                  "file": "gizli bilgi dosyası"},
        "problems": {"path": "diskte olmayan dosya", "commit": "bilinmeyen commit",
                     "tests": "çıktıda görünmeyen test sayısı", "no-tools": "araçsız iş iddiası",
                     "commit-claim": "çalışmayan commit iddiası"},
        "r_head": "COL raporu, son {days} gün",
        "r_empty": "Son {days} günde kayıt yok.",
        "r_claims": ("İddia kontrolü: biten {turns} turun {flagged} tanesinde sorun bulundu, {blocked} tanesi "
                     "durduruldu."),
        "r_kinds": "  Bulunanlar: {kinds}.",
        "r_labels": ("  Durdurmalar, onlara verilen cevaplara göre: {right} doğru, {wrong} yanlış, {unclear} "
                     "belirsiz."),
        "r_ledger": "Öngörü defteri: {preds} öngörü, {results} sonuç.",
        "r_compared": "  Karşılaştırma: {held} tuttu, {missed} tutmadı, {nc} karşılaştırılamadı.",
        "r_grounded": "  {results} sonucun {grounded} tanesindeki sayı gerçek araç çıktısında geçiyor.",
        "r_way": "  Tutmayanlar: {low} tanesi aralığın altında, {high} tanesi üstünde.",
        "r_misses": "  Son tutmayanlar:",
        "r_open": "  Sonuç bekleyen: {open}.",
        "r_hyp": "  Hipotezler: {tested} denendi, {out} elendi.",
        "r_gate": "  Öngörüsüz başlatılmak istenip durdurulan iş: {gate}.",
        "r_secrets": "Anahtar taraması: {n} commit ya da push durduruldu ({kinds}).",
        "r_data": "Kayıtlar: {path}",
    },
}


def t(lang: str, key: str, **kw) -> str:
    text = TEXT.get(lang, TEXT["en"]).get(key) or TEXT["en"][key]
    return text.format(**kw) if kw else text


def name(lang: str, group: str, key: str) -> str:
    return TEXT.get(lang, TEXT["en"])[group].get(key) or TEXT["en"][group].get(key, key)
