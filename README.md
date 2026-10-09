# ORTAK FUTBOLCU — Paylaşılabilir çevrim içi futbol düellosu

Replit kullanılmadan, **FastAPI + WebSocket + PostgreSQL/SQLite + saf JavaScript** ile hazırlanmış mobil uyumlu web oyunu.

## Oyuncu deneyimi

1. Her oyuncu benzersiz bir **kullanıcı adı** (3–20 harf/rakam/alt çizgi) ve şifreyle ücretsiz hesap açar. Aynı isim ikinci defa alınamaz. Şifreler düz metin olarak tutulmaz. Giriş oturumu 30 gün geçerlidir.
2. Oyuncu **1v1 ODA KUR** veya **TURNUVA KUR**'u seçer ve çıkan **DAVET BAĞLANTISINI KOPYALA** düğmesiyle arkadaşlarına linki gönderir.
3. Arkadaş linki açar; kendine ait kullanıcı adıyla kayıt olur/giriş yapar ve doğrudan odaya ya da turnuvaya katılır. Aynı kişi kendi hesabıyla rakibin iki yerini birden dolduramaz.
4. Her iki taraf gizlice takım seçer. Aynı takım seçilirse futbolcu aranmadan, puansız şekilde tur tamamlanır ve takım kilitlenir.
5. Farklı kulüplerin ortak futbolcusunu ilk doğru yanıtlayan +1 alır. 7 turdan önce 3 puan galibiyet; 7. tur bitiminde yüksek skor galibiyet; eşitlikte sınırsız ani ölüm uzatması vardır.
6. 4/8/16 kişilik tek eleme turnuvalarında her eşleşmenin elenen takım listesi sıfırdan başlar. Oyuncular link ve tur tablosundan maçlarına girer.

Başlangıç kulüp/futbolcu listesi demo niteliğindedir; **tam kapsamlı, doğrulanmış futbol geçmişi veritabanı değildir**.

## Kendi bilgisayarında test

Python 3.10+ kuruluysa:

```bash
pip install -r requirements-local.txt
python server.py
```

`http://localhost:8000` adresini aç. Başka bir tarayıcı veya cihazda başka bir kullanıcı hesabı açarak test edebilirsin. Yerel geliştirmede kullanıcı hesapları `data/accounts.sqlite3` dosyasına kaydedilir.

## Arkadaşlarınla internette oynamak için yayınla — Render

`render.yaml` otomatik yayınlama dosyası pakete dahildir. Şu aşamada herhangi bir canlı URL üretilmemiştir. En kısa yol:

1. ZIP içindeki **`ortak-futbolcu` klasörünün içindeki dosyaları**, GitHub üzerinde **yeni, ayrı bir depoya** (`ortak-futbolcu` gibi) yükle. GitHub'da **New repository → Add file → Upload files** kullan. `render.yaml`, `server.py`, `accounts.py`, `game.py`, `requirements.txt` ve `static/` klasörü deponun **kökünde** olmalı. Başka oyunlarının depolarını değiştirme.
2. [Render Dashboard](https://dashboard.render.com/) hesabına gir. **New → Blueprint** seç, yeni GitHub deposunu bağla ve `render.yaml`'ı uygula.
3. Blueprint; Frankfurt'ta bir **Free Python Web Service** ile **Free PostgreSQL** veritabanı oluşturur. Render'ın vereceği `https://<senin-adresin>.onrender.com` adresini aç.
4. **Kayıt ol**, **1V1 ODA KUR**, **DAVET BAĞLANTISINI KOPYALA** sırasıyla ilerle. Arkadaşın linke tıklayıp kendi hesabını açarak katılır. Aynı işlem turnuva için de geçerlidir.

**Önemli ücretsiz plan kısıtları:** Render Free Web Service 15 dakika boş kaldığında uykuya geçebilir; ilk istek yaklaşık bir dakika sürebilir. Sunucu uyandığında veya yeniden dağıtıldığında devam eden maçlar/turnuvalar sunucu belleğinden silinir. Hesaplar PostgreSQL'de kalır; ancak **ücretsiz Render PostgreSQL 30 gün sonra sona erer**. Kalıcı kullanıcı hesapları için süre bitmeden veritabanını ücretli plana taşımanız veya kalıcı bir başka PostgreSQL veritabanına bağlamanız gerekir. Render ücretsiz kaynak ve trafik sınırları değişebilir. Canlıya almadan önce güncel koşulları kontrol et.

Ücretli kalıcı bir Postgres bağlantın varsa **DATABASE_URL** ortam değişkeniyle onu bağlayabilirsin; uygulama veritabanını kendi kurar. `--workers 1` gerekir; odalar şu an tek uygulama sürecinin belleğinde tutuluyor. Üretime geçiş için durumların kalıcı DB/Redis üzerinde tutulması ve anti-abuse/rate limit mekanizmalarının güçlendirilmesi gerekir.

## Yapı

- `server.py` — FastAPI API, WebSocket, server-authoritative oyun/turnuva state ve davet linki
- `accounts.py` — kullanıcı hesapları, parola hash'leri, oturumlar, PostgreSQL/SQLite desteği
- `game.py` — kulüp/futbolcu demo verisi, tur, skor, eleme ve uzatma kuralları
- `static/` — responsive web arayüzü ve giriş/oda/turnuva ekranları
- `render.yaml` — Render yayınlama ve PostgreSQL Blueprint
- `tests/` — otomatik backend ve oyun kuralları testleri

Uygulama HTTPS/WSS üzerinden sunulmalıdır. Hesabın için şifre kurtarma, e-posta doğrulaması ve moderasyon bu beta sürümünde henüz yoktur. Gizli belirteçler client-side localStorage'da tutulur; XSS riskine karşı CSP ve güvenlik denetimi yapılmadan ciddi ölçekte yayınlanmamalıdır.

## v0.3 — 11 tur sınırı, profil, puan tablosu
- Ana ekrandan geri tuşu çıkış onayı ister; arkadaş/katılım/profil/sıralama ekranlarında geri doğrudan ana ekrana gider.
- Devam eden 1v1 maçtan **AYRIL** dendiğinde sunucu otomatik hükmen **0–3** kaydeder, rakibe galibiyet ve 3 lig puanı verir. İnternet kesintisi tek başına hükmen yenilgi sayılmaz.
- Normal 7 tur eşitse 8–11 arası uzatma oynanır; 11. tur sonunda hala berabereyse resmi maç sonucu **beraberlik**. Galibiyet 3, beraberlik 1, mağlubiyet 0 lig puanıdır.
- 4/8/16 kişilik eleme turnuvasındaki beraberlikler ayrı maç olarak kaydedilir ve eşleşme için **rövanş** başlatılır (kura ya da sahte galip yok).
- `GET /api/users/{username}/profile`: oyuncunun oynadığı maç, galibiyet, beraberlik, mağlubiyet, lig puanı, son 12 maç.
- `GET /api/leaderboard`: tüm oyuncuların puan sıralaması.
- 226 örnek futbolcu ve 84 kulüp; 2026 Gabriel Jesus -> Barcelona güncellemesi, Ronaldo için takım çiftine göre ad çözümleme. Seçilen futbolcu arşivinin **tam ve canlı transfer feedi olmadığına** dikkat edin; oyuncularla devam eden doğrulama gerekiyor.


## Kulüp armaları (v0.4.2)

Maç ve tek kişilik antrenman ekranları kullanıcı tarafından belirlenen sabit sırada **60 kulüp** gösterir. Arama yalnızca bu 60 kulüp arasında yapılır; diğer kulüpler futbolcu geçmişi ve cevap doğrulama kayıtlarında korunur. Her seçilebilir kulübün gerçek amblemi `static/crests/01.svg`–`60.svg` altında yerel olarak sunulur.

Amblem görselleri [JoseArroyave/football-logos](https://github.com/JoseArroyave/football-logos) kataloğundan alınmıştır (repo MIT lisanslıdır). Kulüp armaları ve markaları ilgili hak sahiplerinin ticari markalarıdır; katalog lisansı kulüp marka haklarının devredildiği anlamına gelmez.
