# 13 amaç

[English](AIMS.md)

Living Runtime, Claude Code'a zekâ eklemeye çalışmaz. Var olan zekâyı daha iyi kullanmaya çalışır: hatırlamak, kendini denetlemek, bir şey bozulunca sebebini bulmak. Bu, üç bölümde on üç amaç eder. Her amacın bir ölçütü var; durumu ancak bir ölçümden sonra yazılır.

- **LR** (hafıza, amaç 1–7) bu depoda `lr-memory` eklentisidir.
- **COL**, Cognitive Operating Loop (öz denetim, amaç 8–10), bu depoda `col` eklentisidir.
- **scnc** (sebep bulma, amaç 11–13) yazarın, sebebi bilinmeyen durumlar için becerisidir: rakip açıklamalar, onları ayıran ucuz tek deney, kök sebebe düzeltme. Kendiliğinden çalışan kısmı `col` içinde gelir: bir düzeltme tutmadığında rakip açıklama isteyen kontrol.

[Zihin paneli](../plugins/mind/README.tr.md) bu amaçları kendi dosyalarınızdan okunan canlı sayılarla gösterir.

## Ne durumdalar

2026-11-11 itibarıyla: **2** çalışıyor · **4** kısmen · **4** tutmuyor · **2** kullanılmıyor · **1** belirsiz.

Yazarın kendi makinesi; bu eklentilerin parçası olduğu özel sistemin tamamı (LR, COL, scnc). 7 Kasım 2026 öncesi kayıt: etiketlenmiş 14 gece, 471 operatör mesajı, 74 düzeltme. 7 Kasım'dan beri 28 günlük açık/kapalı deney sürüyor; sayıları 5 Aralık'a kadar kapalı.

Amaçların bir kısmı henüz tutmuyor; bu sayfa hangileri olduğunu yazar. Ölçümler yazarın kendi kaydında, tek okuyucuyla yapıldı; bir kıyaslama testi değildir.

### LR: hafıza

| # | Amaç | Durum | Ölçüt | Son ölçüm |
| --- | --- | --- | --- | --- |
| 1 | Sohbet hiç kapanmaz, özetlemede bilgi kaybolmaz | ✕ tutmuyor | Özetlemeden sonra eski bilginin elde kalan payı | Tek özetlemede Claude Code'un özeti de kayıpsız, LR'nin payı 0. Üst üste özetlemede eski operatör mesajlarının ~%90'ını ikisi de taşımıyor; not ~2 puan ekliyor |
| 2 | Yaşanan birebir kaydedilir, gerekince bulunur | ◐ kısmen | Aranan bilginin kaynağı ilk 3 sonuçta mı | 9 soruda 8; gerçek mesaj sorgu olunca 8'de 3 tam, 3 kısmi |
| 3 | Düzeltmeler ve doğrulanmış dersler kurala döner | ✓ çalışıyor | Düzeltmelerin kaçından kural doğdu | 74 düzeltmenin en az 24'ünden bir kural ya da ek doğdu (alt sınır; tek okuyucu) |
| 4 | Kural gereken anda kendiliğinden geri gelir | ✕ tutmuyor | Kural yazılıyken düzeltme geldiyse, kural o sırada geri gelmiş miydi | Önceden kuralı olan (var ya da kısmen) 57 düzeltmenin 3'ünde kuralın ipucu son 24 saatte gelmişti; ipucu en az bir kez gelen kural 15 |
| 5 | Gece pekiştirir, işe yaramayanı söndürür | ◐ kısmen | Yazılan ve sönen kural | 16 gecede 32 kural yazıldı; dosya 408'den 452'ye, hiç açılmayan 210'dan 242'ye çıktı; söndürme yok |
| 6 | Aynı hata ikinci kez yapılmaz | ✕ tutmuyor | Kuralı önceden yazılı olan düzeltme | 74'ün 24'ü (%32); 33'ünde ilgili ama daha genel bir kural vardı |
| 7 | Bağlam küçük kalır, kalite düşmez | ◐ kısmen | Çağrı başına bağlam ve düzeltme oranı | 518,8 binden 236,4 bine (−%54), çoğu Claude Code ayarından; düzeltme oranı anlamlı değişmedi |

### COL: öz denetim

| # | Amaç | Durum | Ölçüt | Son ölçüm |
| --- | --- | --- | --- | --- |
| 8 | Yapılmamış iş "bitti" diye sunulmaz | ✓ çalışıyor | Tutmayan iddia: yakalanan ve operatöre ulaşan | 1.370 turda 15 yakalandı; operatörün 74 düzeltmesinin 1'i bu türden |
| 9 | Gerçekten ne istendiği anlaşılır, iş o yöne gider | ✕ tutmuyor | Yanlış anlama düzeltmesi | 74'ün 18'i; hakem 369 bakış, 13 geri çevirme, 1,79 milyon token; amaç kaçırmayı 7 örnekte 0 kez yakaladı |
| 10 | Büyük adımdan önce öngörü, sonra karşılaştırma; yasak korunur | ◐ kısmen | Öngörü kaydı ve karşılaştırma, durdurulan yasak yazma | 820 öngörü kaydedildi; 371'i sayıyla karşılaştırıldı (146 tuttu, 225 tutmadı), 139'u karşılaştırılamadı, 310'unun sonucu yok; 6 yasak yazma durduruldu |

### scnc: sebep bulma

| # | Amaç | Durum | Ölçüt | Son ölçüm |
| --- | --- | --- | --- | --- |
| 11 | İlk açıklamaya atlanmaz, rakip açıklamalar kurulur | ○ kullanılmıyor | Hipotez satırı | 24 Eki–7 Kas'ta 3 satır, tek sohbette; kayıt 0 |
| 12 | Kararı ucuz bir deney verir | ○ kullanılmıyor | Deney adımının kullanımı | Kullanılmıyor |
| 13 | Düzeltme kök sebebe yapılır, aynı ölçümle doğrulanır | ? belirsiz | İkinci hatadan üçüncüye geçiş | Ekim tabanı 127'de 33 (%26); 30 Eki–7 Kas 11'de 1 (%9), fark ayırt edilemiyor (p = 0,19); "aynı ölçümle doğrulama" ölçülmedi |

## Beyin bölgeleri bir benzetmedir

Panel her amacı bir beyin bölgesine koyar. Bu, sistemi okumanın bir yoludur; beyin hakkında bir iddia değildir.

| # | Amaç | Bölge ve neyi temsil ettiği |
| --- | --- | --- |
| 1 | Sohbet hiç kapanmaz, özetlemede bilgi kaybolmaz | Dorsolateral prefrontal korteks, çalışma belleğini ayakta tutar |
| 2 | Yaşanan birebir kaydedilir, gerekince bulunur | Hipokampus, epizodik bellek ve ipucundan hatırlama |
| 3 | Düzeltmeler ve doğrulanmış dersler kurala döner | Ön temporal neokorteks, anlamsal bellek |
| 4 | Kural gereken anda kendiliğinden geri gelir | Bazal gangliyonlar, ipucuyla tetiklenen alışkanlık |
| 5 | Gece pekiştirir, işe yaramayanı söndürür | Uykuda talamokortikal iğcikler ve hipokampus–korteks yeniden oynatımı |
| 6 | Aynı hata ikinci kez yapılmaz | Beyincik, hatadan denetimli öğrenme |
| 7 | Bağlam küçük kalır, kalite düşmez | Arka parietal korteks, dikkatin seçimi |
| 8 | Yapılmamış iş "bitti" diye sunulmaz | Ön singulat korteks, hata ve çatışma izleme |
| 9 | Gerçekten ne istendiği anlaşılır, iş o yöne gider | Temporoparietal kavşak ve medial prefrontal korteks, karşıdakinin niyetini okuma |
| 10 | Büyük adımdan önce öngörü, sonra karşılaştırma; yasak korunur | Orbitofrontal korteks ve alt frontal girus, beklenen sonuç ve ket vurma |
| 11 | İlk açıklamaya atlanmaz, rakip açıklamalar kurulur | Frontopolar korteks, alternatifleri bekletme |
| 12 | Kararı ucuz bir deney verir | Locus coeruleus, beklenmedik belirsizlikte keşfe geçiş |
| 13 | Düzeltme kök sebebe yapılır, aynı ölçümle doğrulanır | Orta beyin dopamin hücreleri, öngörü hatasıyla güncelleme |

## Durum sözcükleri

- **✓ çalışıyor**: ölçüldü ve tutuyor
- **◐ kısmen**: ölçüldü, bir kısmı tutuyor
- **✕ tutmuyor**: ölçüldü ve tutmuyor
- **○ kullanılmıyor**: mekanizma var ama kullanılmıyor
- **? belirsiz**: ölçüldü, sayılar ayırt edemiyor
- **· ölçülmedi**: ölçüm yok; siz bir karne tutana kadar panel her amacı böyle gösterir

## Kendi karneniz

Yukarıdaki durumlar yazarındır. Sizin makinenizde panel, siz bir karne tutana kadar her amacı ölçülmedi diye gösterir: `~/.claude/mind/scorecard.json` yolunda (ya da `--scorecard DOSYA`), [scorecard.json](scorecard.json) biçiminde bir JSON dosyası. Metin alanları tek bir dize ya da `{"en": …, "tr": …}` olabilir.
