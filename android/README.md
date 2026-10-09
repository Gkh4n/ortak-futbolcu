# Ortak Futbolcu Android

Android WebView sürümü, çevrim içi oyunun şu adresini kullanır:
https://ortak-futbolcu.onrender.com

Kullanıcı hesapları, davet kodları, maçlar ve turnuvalar aynı sunucu üzerindedir.
WebSocket desteğiyle web oyuncuları ve APK oyuncuları birlikte oynar.
İnternet gereklidir, çevrimdışı oyun değildir.

Java 17, AGP 8.7.3, Gradle 8.9 ve Android SDK 35 ile derle.

GitHub Actions > Android APK workflow başarılı olduğunda Releases sayfasındaki
`ortak-futbolcu-v0.1.0.apk` dosyasını indir.

Bu ilk sürüm DEBUG imzalı test APK'sıdır. Her otomatik derlemede debug anahtarı
değişebileceğinden güncellemede üzerine kurulum garanti değildir.
Play Store için sabit anahtarla imzalı release build üretilecek.
