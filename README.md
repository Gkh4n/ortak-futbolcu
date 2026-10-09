# ORTAK FUTBOLCU

İki oyuncunun gizli takım seçtiği ve **iki takımda da oynamış futbolcuyu ilk bilenin** puan kazandığı çevrim içi futbol düellosu.

## Oyna

Bu depo, FastAPI/WebSocket ile çalışan tam bir web uygulamasıdır. Yalnızca GitHub Pages'e yüklemek yeterli değildir; Python web sunucusu gerektirir.

- Her oyuncu benzersiz kullanıcı adı + şifreyle hesap oluşturur.
- Bir oyuncu **1V1 ODA KUR** butonuna basar ve oluşturulan davet bağlantısını paylaşır.
- Arkadaşı linke girer, kendi hesabıyla giriş yapar ve odaya katılır.
- 4, 8 veya 16 oyunculu eleme turnuvası da oluşturulabilir.

## Maç kuralları

- Takımlar gizli seçilir. Farklı takımlar seçildiyse ortak futbolcu bulunur; ilk doğru cevap +1 puandır.
- İkisi aynı takımı seçerse futbolcu aranmaz, kimse puan almaz. O tur sayılır.
- Seçilen bütün takımlar o maç için elenir, sonraki turlarda tekrar seçilemez.
- 7. tur bitmeden 3 puana ulaşan maçı kazanır. 7 tur sonunda önde olan kazanır.
- 7 tur sonunda eşitse uzatmada ilk öne geçen kazanır.
- Ortak futbolcusu bulunmayan iki farklı takım gelirse tur sayılmadan yeniden seçim yapılır.

## Yerelde çalıştırma

Python 3.10+:

```bash
python -m pip install -r requirements-local.txt
python server.py
```

Tarayıcıdan `http://localhost:8000` adresini aç.

Test:
```bash
PYTHONPATH=. python -m pytest -q
```

## Render'da yayınlama

GitHub deposu: `https://github.com/Gkh4n/ortak-futbolcu`

Render > **New > Blueprint** > bu depoyu seç > `render.yaml` ile kurulumu uygula. Blueprint ücretsiz Python web servisi ve ücretsiz PostgreSQL veritabanı tanımlar. Canlı bağlantı ancak Render dağıtımı tamamlanınca oluşur. Render servisinin URL'sinden arkadaşına oda veya turnuva davet bağlantısı gönderebilirsin.

Alternatif olarak Render Python web servisi:
- Build: `pip install -r requirements.txt`
- Start: `uvicorn server:app --host 0.0.0.0 --port $PORT --workers 1`
- Region: Frankfurt
- `DATABASE_URL`: PostgreSQL bağlantısı (hesapları kalıcı tutmak için gerekli)
- Health check: `/api/health`

## Sınırlar

Bu sürüm oyun mekaniğini test etmek için seçilmiş **örnek futbolcu geçmişleri** kullanır. Tam ve dış kaynaktan sürekli doğrulanan bir futbolcu veritabanı değildir. Oda ve turnuva durumları sunucu belleğindedir; sunucu yeniden başlarsa aktif maçlar sıfırlanır. **Render ücretsiz PostgreSQL 30 gün sonunda sona erebilir**; hesapları uzun vadeli tutmak için uygun kalıcı veritabanı gerekir. Ücretsiz web servisinde uyku/soğuk başlangıç gecikmesi olabilir.

## Proje dosyaları

`server.py`: API ve WebSocket, `game.py`: oyun kuralları, `accounts.py`: üyelik, `static/`: mobil web arayüzü, `tests/`: testler, `render.yaml`: Render Blueprint.

Replit kullanılmaz.
