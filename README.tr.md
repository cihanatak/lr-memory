![Living Runtime: Claude Code için açık kaynak eklentiler LR Memory ve COL](https://raw.githubusercontent.com/cihanatak/lr-memory/main/assets/banner.jpg)

# Claude Code için LR Memory

[English](README.md)

Uzun Claude Code oturumları, sohbet özetlenince işin ipini kaybeder. Her yeni oturum eskilerden habersiz başlar ve geçen hafta yaptığın bir düzeltmeyi yeniden yapman gerekir. LR Memory üçünü de çözer:

1. **Özetlemeyi aşan çalışma notu.** Claude Code sohbeti özetlemeden hemen önce bir kanca kaydı okur. Özetlerin en çok kaybettiklerini saklar: son mesajlarının birebir hâli, açık işler, değişen dosyalar, commit'ler ve son test sonuçları. Özetlemeden hemen sonra bunlardan çıkan kısa bir not (en çok 9.000 karakter) tam kayda giden yolla birlikte yeni bağlama geri konur.
2. **Bütün geçmiş oturumlarda arama.** Claude Code'un `~/.claude/projects` altında tuttuğu bütün kayıtlar için yerel bir arama dizini: senin mesajların, Claude'un cevapları, commit'ler, komutlar, özetler, alt ajan raporları ve hafıza dosyaları. `recall` becerisi, daha önce yapılmış bir şeyi yeniden yapmadan ya da tahmin etmeden önce Claude'a bu dizinde aratır. Cevap tarih, oturum ve commit ile gelir.
3. **Uyku: kendi sözlerin hafızaya döner.** Açarsan günde bir kez, ya da her `/lr-memory:sleep` çalıştırdığında, bir geçiş her projede son geçişten beri söylediklerini okur. Verdiğin kalıcı kurallar ve düzeltmeler Claude Code'un kendi hafıza klasörüne yazılır; sonraki her oturum onu yükler. Olan bir şeyden çıkarılan ders ise başka bir geçiş onu yeni bir kanıtla destekleyene kadar bekler.

Not ve arama için sunucu, ağ ya da model çağrısı gerekmez. Modeli çağıran tek parça uykudur: yeni mesajı olan her proje için bir kez, yalnız sen çalıştırınca ya da açınca. Hepsi Python'un standart kütüphanesi, üç kanca ve iki beceriden oluşur.

## Kurulum

Claude Code içinde:

```
/plugin marketplace add cihanatak/lr-memory
/plugin install lr-memory@living-runtime
```

Ardından Claude Code'u yeniden başlat. Kancalar açılışta yüklenir.

**Gerekenler:**
- Claude Code. 2.1.235 ve 2.1.308 ile denendi.
- `PATH` üzerinde `python3`, `python` ya da `py` adıyla Python 3.9 veya üstü.
- `sh`. macOS ve Linux'ta zaten var. Windows'ta Claude Code kancaları Git Bash ile çalıştırır ve `sh` oradan gelir.
- Uyku için `PATH` üzerinde, terminalden oturumu açılmış `claude` komutu: `claude` çalıştır, ardından `/login`. Uyku kendi `claude`'unu başlatır ve içinden çalıştığı oturumun girişini ödünç alamaz; Claude Code o girişi araçlara ve kancalara verdiği kabuktan çıkarır. Claude Code'u yalnız Claude masaüstü uygulamasında kullanıyorsan bu girişi bir kez yap.

## Kullanım

- **Not** senden bir şey istemez. Her özetlemeden sonra kendiliğinden gelir; otomatik özetlemede de `/compact` ile de.
- **Hatırlama** için geçmişi kendi sözlerinle sorman yeter:
  - "Geçen sefer giriş yönlendirmesini nasıl düzeltmiştik?"
  - "Önbellek anahtarını hangi commit değiştirdi?"
  - "Yeniden deneme sınırında ne karar vermiştik?"

  Claude kayıtta arar, uyan konuşmayı açar ve kaynağıyla cevap verir. Bir şey bulamazsa tahmin etmez, bulamadığını söyler.
- **Kabuktan kullanmak** istersen, bu makinedeki tam komut notun içinde yazar. Biçimi şöyledir:

  ```bash
  sh <eklenti klasörü>/scripts/run.sh search staging proxy port
  sh <eklenti klasörü>/scripts/run.sh show 3f2a9c1e:5852
  ```

  Aramayı daraltmak için `--kind user,commit`, `--since 2026-10-20`, `--session 3f2a9c1e` ya da `-k 5` kullanılır.
- **Uyku** sen isteyince çalışır:
  - `/lr-memory:sleep` hemen bir geçiş yapar. Neyin yazıldığını, neyin beklediğini ve neyin reddedildiğini, maliyetiyle birlikte token olarak bildirir.
  - `/lr-memory:sleep --dry-run` aynısını gösterir ama hiçbir şey yazmaz.
  - Kendiliğinden günde bir kez çalışması için `LR_MEMORY_SLEEP` değişkenini `daily` yap. O zaman 20 saatten sonraki ilk oturum açılışı arka planda bir geçiş başlatır.
  - Her rapor `~/.claude/lr-memory/sleep/reports/` altında saklanır.

## Nasıl çalışır

```mermaid
flowchart LR
  T[("Kayıtlar<br/>~/.claude/projects")] -->|PreCompact kancası| R["İz kaydı: sözlerin, açık işler,<br/>dosyalar, commit'ler, testler"]
  S["Claude Code'un özeti"] -->|PostCompact kancası| R
  R -->|"SessionStart (compact) kancası"| N["Yeni bağlamda<br/>çalışma notu"]
  T -->|"artımlı dizinleme"| I[("SQLite FTS5 dizini")]
  I -->|"recall becerisi"| A["Tarih, oturum ve<br/>commit ile cevap"]
  T -->|"uyku, günde bir kez"| M[("Claude Code'un hafıza klasörü:<br/>MEMORY.md ve kural başına bir dosya")]
```

**Tasarım kararları:**
- **Birebir, yeniden yazılmış değil.** Özet ana fikri korur. Ama "eski göçe dokunma" gibi bir düzeltme genel bir cümleye döner, dosya ve commit izleri de ilk gidenlerdir. Not bunları kayıttan mekanik olarak alır.
- **Kaydın kopyası değil, kayda bir dizin.** Kaynak her zaman kayıtların kendisidir. Arama, her biri kaynağıyla birkaç kısa sonuç döndürür; model gerekeni açar.
- **Hafif kök bulmalı düz sözcük araması.** Gömme, vektör deposu ya da sunucu gerekmez. Harfler katlanır (ı→i, ş→s, aksanlar düşer) ve her sorgu sözcüğü ilk beş harfine indirilir. Türkçede bu, tam bir kök bulucu kadar iyi çalışır (Can ve ark., JASIST 2008). Böylece `düzeltmiştik` aranınca `düzeltme` de bulunur; İngilizcede `comparator` aranınca `compare` bulunur. Sözcüğün tamamını taşıyan sonuç, yalnız kesik biçimi taşıyanın önüne geçer. Parçalardan oluşan bir ad (`listed_commits`, `predict.py`) bütün olarak eşleşir.
- **Asla yol kesmez.**
  - Hata veren bir kanca 0 ile çıkar ve `errors.log`'a yazar; özetlemeyi ya da oturum açılışını hiç durdurmaz.
  - Her arama önce yalnız son aramadan beri eklenenleri dizinler, en yeni oturumlardan başlayarak. Uzun bir geçmişte ilk arama 40 saniye sonra dizinlemeyi bırakır ve ne kadar kaldığını söyler.
  - Arama, içinde bulunulan oturumun son özetlemeden beri söylediklerini dışarıda bırakır. Onlar zaten bağlamdadır; yoksa az önce sorulan soru ilk sonuç olarak geri gelirdi.
  - Oturum açılışında dizin arka planda güncellenir.
- **Anahtarlar dışarıda kalır.** Anahtar biçimli dizgiler dizine girmeden maskelenir: Anthropic, OpenAI, GitHub, AWS, Google, Slack, Hugging Face anahtarları ve özel anahtarlar. Bir arama asla anahtar yazdıramaz.
- **Uyku yalnız kaydın desteklediğini yazar.**
  - Her öneri ya senin sözlerini birebir alıntılar ya da bu oturumlardaki bir commit'i gösterir. Gösterdiği mesajda geçmeyen bir alıntı düşer; anahtara ya da parolaya benzeyen her şey de düşer.
  - Açıkça söylediğin kalıcı bir kural, tercih ya da yasak aynı gün yazılır.
  - Olan bir şeyden çıkarılan ders önce aday olarak bekler; hiçbir oturum onu görmez. Başka bir geçiş onu daha önce olmayan bir kanıtla desteklerse kurala döner. 14 gün içinde yeniden desteklenmeyen aday söner; sonraki kanıtın çürüttüğü aday geri çekilir. Yeniden oynatma yanlış bir genellemeyi de doğrusu kadar kolay güçlendirir: LR'de bir kez yanlış okunmuş tek bir ölçüm, altmış kat yanlış bir kurala dönmüştü.
  - Güncelleme tarihli bir başlıkla sona eklenir, hiçbir şeyi yeniden yazmaz. Bir kural yalnız senin sözlerinle emekliye ayrılır ve `memory/_retired/` altına taşınır. Her dosya değişmeden önce yedeklenir.
  - Var olan bir kuralın zaten söylediği bir şeyi yeniden söylemek zorunda kaldıysan, rapor o kuralın adını verir: o kural tutmamıştır.
  - Yapıştırılan metin senin sözün değildir, dışarıda kalır.
- **Uyku yol kesmez.**
  - Başlattığı `claude -p` boş bir klasörde çalışır: araç yok, MCP sunucusu yok, kanca yok, oturum kaydı yok.
  - Bir oturum projenin `MEMORY.md` dosyasına yazarken ya da Claude Code'un kendi hafıza birleştirmesi orada çalışırken o projeyi atlar.
  - Claude Code'un `autoMemoryEnabled` ve `autoMemoryDirectory` ayarlarına uyar.

## Yazarın makinesinde ölçülenler

- **Dizin:** 575 kayıt (6,6 GB) sıfırdan 41 saniyede dizinlendi: 77.471 parça, 129 MB'lık bir dizin. Sonrasında bir arama, Python'un açılışı dahil yaklaşık yarım saniye sürüyor.
- **Arama çıktısı:** bir arama 0,4–1,2 KB yazar, yani birkaç yüz token. Aynı sözcükler için ham `.jsonl` dosyalarında grep 0,3–4,5 MB yazdı.
- **Token yükü:** uzun oturumlarla geçen bir günde 1.108 model çağrısında 586 milyon token okundu; çağrı başına ortanca 543.000. Her tur bütün bağlamı yeniden okur, bu yüzden uzun bağlam her turda maliyet çıkarır.
  - Claude Code'un özetleme penceresini düşürmek (`settings.json` içinde `"autoCompactWindow": 400000`) her turu ucuzlatır.
  - Özetleme o zaman daha sık olur; bunu güvenli kılan da çalışma notudur.
- **Uyku:**
  - Altı mesajlı ve bir commit'li bir projede geçiş Sonnet 5.5 ile 9 saniye sürdü ve 3.631 token harcadı. Her biri bir alıntıya dayanan üç değişiklik yaptı: iki yeni kural ve kullanıcının yeniden söylemek zorunda kaldığı kurala bir ek. Rapor o kuralın adını verdi.
  - Yazarın kendi makinesinde ilk geçiş, günün 979 MB'lık kayıtlarından 38 mesaj okurdu; bu okuma 2,5 saniye sürüyor. İstemi yaklaşık 26.000 token olurdu; bunun çoğu, orada zaten duran 410 hafıza dosyasının tek satırlık açıklamaları.

## Ayarlar

Bunlar ortam değişkeni olarak verilir, örneğin `~/.claude/settings.json` içinde `"env"` altında:

| Değişken | Varsayılan | Anlamı |
| --- | --- | --- |
| `LR_MEMORY_LANG` | otomatik | `en` ya da `tr`. Otomatik seçim, mesajların Türkçe görünüyorsa Türkçe yazar. |
| `LR_MEMORY_DATA` | `~/.claude/lr-memory` | Dizinin ve iz kayıtlarının tutulduğu yer. |
| `LR_MEMORY_TRANSCRIPTS` | `~/.claude/projects` | Kayıtların okunduğu yer. |
| `LR_MEMORY_SLEEP` | kapalı | `daily`, 20 saatten sonraki ilk oturum açılışında bir uyku geçişi başlatır. |
| `LR_MEMORY_SLEEP_MODEL` | varsayılan modelin | Uykunun modeli, örneğin `sonnet` ya da `opus`. |
| `LR_MEMORY_CLAUDE` | `PATH` üzerindeki `claude` | Uykunun çalıştırdığı `claude` komutu. |

`CLAUDE_CONFIG_DIR` verilmişse ona uyulur.

## Gizlilik ve kaldırma

Not ve dizin senin makinende kalır. Dizin, anahtarları maskelenmiş olarak yalnız senin kayıtlarındaki metni tutar. Uyku, okuduğu mesajları anahtarları maskelenmiş olarak, her oturumun yaptığı gibi kendi Claude Code girişinle modele gönderir.

Kaldırmak için önce `/plugin uninstall lr-memory@living-runtime` çalıştır, ardından `~/.claude/lr-memory` klasörünü sil. Bu klasörde dizin, iz kayıtları ve uykunun raporları, adayları ve yedekleri durur. Uykunun yazdığı hafıza dosyaları Claude Code'un hafıza klasöründe kalır; onları da diğerleri gibi düzenleyebilir ya da silebilirsin.

## Geliştirme

```bash
python -m pytest tests
```

Testler yalnız geçici klasörler kullanır. Gerçek `~/.claude`'u hiç okumaz, Claude'u başlatmaz ve ağa çıkmaz.

## COL, buradaki öbür eklenti

Bu pazaryerinde LR Memory'den bağımsız ikinci bir eklenti var. **COL** üç iş yapar:
- Claude'un son mesajını gerçekten çalışanla karşılaştırır: andığı commit var olmalı, verdiği dosya diskte olmalı, söylediği test sayısı gerçek test çıktısında geçmeli.
- Uzun işlerden ve geri alınamayan adımlardan önce ölçülebilir öngörülerden bir defter tutar ve onları sonuçlarla karşılaştırır.
- Bir anahtar taşıyacak commit'i ya da push'u durdurur.

Yereldir, hiç model çağırmaz.

```
/plugin install col@living-runtime
```

Ayrıntılar: [plugins/col/README.tr.md](plugins/col/README.tr.md).

LR Memory, yazarın ajan çalışma ortamı LR'den (Living Runtime) ayrıldı. Orada Ekim 2026'dan beri çalışıyor.

## Lisans

MIT
