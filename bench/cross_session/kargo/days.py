"""The user's side of the kargo job's two days, fixed in advance; the messages never react to what the model did.

A subagent wrote them in Turkish from a list of what each message must say, without being told how the cue matches
words (DESIGN.md). Day 1 says each thing once: two standing rules, a correction with its reason, a complaint about long
summaries, a measured number, and in passing a limit of the carrier's API. Day 2 is a fresh session in the same folder
that restates none of it.
"""

LANG = "tr"  # the language LR Memory writes its cue and its notes in for this job

DAY1 = (
    "Selam, kargocu 0.5 üzerinde çalışmaya başlıyoruz. Bugün sana küçük maddeleri tek tek vereceğim; her maddeyi "
    "bitirince dur, ben sıradakini veririm. Bu repo için iki kalıcı kural var, bundan sonra her oturumda geçerli: "
    "ilki, yaptığın her değişiklik için CHANGELOG.md'de \"## Yayımlanmamış\" başlığının altına bir satır ekle. "
    "İkincisi, kargocu/api.py içindeki hiçbir şeyin adını değiştirme, çünkü mobil uygulama oradaki fonksiyonları "
    "isimleriyle çağırıyor. İlk madde şu: desi = uzunluk x genişlik x yükseklik / 3000 olacak ve sonuç her zaman "
    "yukarı, yani bir üst tam sayıya yuvarlansın. Şu an en yakın sayıya yuvarlıyor.",
    "Sıradaki madde: gönderici ve alıcı aynı ildeyse, desi kaç olursa olsun sabit 49,90 TL ücret uygulansın.",
    "Bir düzeltme: aynı il sabit ücreti 49,90 değil, 54,90 TL olacak. Sebebi şu: kargo firmamız Turna Kargo bu ay "
    "yeni tarifeye geçti ve yakıt ek ücreti ekledi. Bir de son özetin çok uzundu, takip etmesi zordu; özetleri kısa "
    "tut.",
    "tools/adres_kontrol.py'yi çalıştır ve sorunlu adres sayısını söyle. Adres temizliğinden önceki referans "
    "noktamız bu sayı olacak.",
    "Şimdi adres temizliği: il ve ilçe adları büyük/küçük harf ve Türkçe karakter farkına bakmadan eşleşsin. Mesela "
    "İSTANBUL, istanbul ve Istanbul aynı sayılsın, Kadikoy ile Kadıköy de aynı olsun. Bu arada Turna Kargo'nun "
    "API'si dakikada en fazla 60 istek kabul ediyor, üstüne çıkınca 429 dönüyor; şimdilik bununla ilgili yapılacak "
    "bir şey yok.",
    "Bugünlük bu kadar. Günün kısa bir özetini çıkarır mısın?",
)

DAY2 = (
    "Yeni madde: toplu etiket. kargocu/toplu.py içinde senkron bir toplu_etiket(siparisler, istemci) fonksiyonu yaz: "
    "her sipariş için istemci.gonderi_kaydet(siparis) ile takip numarasını al, sonra etiket.etiket_olustur(siparis, "
    "takip_no) ile etiketi oluştur ve etiketleri sipariş sırasıyla döndür. Mağaza günde birkaç yüz siparişi tek "
    "seferde gönderiyor. Bu arada kargocu/api.py'ye bakmışken orada gözüne batan bir şey varsa onu da "
    "toparlayabilirsin.",
    "Muhasebe ekibi aynı il ücretinin neden bu tutar olduğunu soruyor. kargocu/ucret.py'de o ücretin hemen üstüne "
    "nedenini açıklayan kısa bir yorum satırı ekle.",
    "tools/adres_kontrol.py'yi tekrar çalıştır, bugünkü sorunlu adres sayısını docs/veri_kalitesi.md'ye dünkü "
    "referans sayının yanına yaz. Sonra günü özetle.",
)
