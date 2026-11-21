# macOS

Bu klasör, TürKod'un yalnızca macOS'a özgü derleme ve paketleme dosyaları içindir.
Ortak kod (`turkod_ide/`, `turkod_flutter/lib/`) burada değil, proje kökünde kalır.

## Dosyalar

- `build_macos.sh`: Flutter (macos) + PyInstaller + gömülü Python + codesign (içten
  dışa) + manifest + duman testi + `.dmg` + isteğe bağlı noterlik. Çıktı:
  `dist/TurKod-<sürüm>-macos-<mimari>.dmg`. Çalıştırma:
  `bash platformlar/macos/build_macos.sh --ozel-anahtar <pem> --kimlik "Developer ID Application: ..." --noter-profili <profil>`.
  `--kimlik` verilmezse yerel (ad-hoc) imza: paket yalnızca o Mac'te açılır.
- `backend.entitlements`: sunucu ve gömülü Python için imza izinleri
  (`allow-unsigned-executable-memory`, `disable-library-validation`).
- Uygulamanın kendi izinleri ve `.trpy` türü: `turkod_flutter/macos/Runner/`.
- Henüz yok: `.dmg` arka planı, Intel + Apple Silicon ortak (universal) paket
  (şimdilik paket, derlendiği Mac'in mimarisine göre üretilir).

## Noterlik için bir kerelik hazırlık

`xcrun notarytool store-credentials turkod --apple-id <e-posta> --team-id <TAKIM>`
(uygulamaya özel parola Apple hesabından alınır). Sonra `--noter-profili turkod`.

## Notlar

- Derleme yalnızca bir Mac'te (Xcode kurulu) yapılabilir.
- Dağıtım için Apple Developer hesabı, `codesign` ve noterlik (notarization) gerekir;
  imzasız uygulamayı Gatekeeper açtırmaz. Gömülü Python'daki her `.so`/`.dylib`
  ayrıca imzalanmalı.
- Gömülü Python için python-build-standalone (taşınabilir CPython 3.12) kullanılır:
  `platformlar/python_embed_hazirla.sh <TurKod.app>/Contents/Resources/backend/_internal/python_embed`
  (Linux ile ortak betik). İçindeki her `.so`/`.dylib` imzalama adımında ayrıca imzalanır.
- Kodi'nin sesi: `say` komutu.
- Kısayollarda Ctrl yerine Cmd kullanılır (kod tarafı yapıldı: `platform_ayarlari.dart`).
- Veri klasörü: `~/Library/Application Support/TurKod`.
- Flutter klasörü: `turkod_flutter/macos/` açıldı (2026-11-21). Uygulama `TurKod.app`,
  paket kimliği `org.turkod.TurKod` (Apple hesabına göre değiştirilebilir).
- `Runner/*.entitlements`: sandbox KAPALI (arayüz sunucuyu başlatıp kullanıcının
  dosyalarını açabilsin), ağ istemcisi/sunucusu açık. Sunucunun (Python) kendi imza
  izinleri (`allow-unsigned-executable-memory`) paketleme adımında eklenecek.
- `Runner/Info.plist`: `.trpy` dosya türü (`org.turkod.trpy`) tanımlandı. Finder'dan
  çift tıklanan dosyanın uygulamaya iletilmesi (`application(_:openFiles:)`) henüz yok.
- Paket düzeni: sunucu `TurKod.app/Contents/Resources/backend/turkod_backend` yolunda
  aranır.
- IDE içindeki tarayıcı yok; sayfalar sistem tarayıcısında (`open`) açılır.
- Uygulama içi güncelleme: yeni `.dmg` indirilir, SHA-256 denetlenir ve açılır; TürKod
  kapanır, kullanıcı yeni sürümü Uygulamalar klasörüne sürükler. `latest.json` için
  `build_macos.sh --indirme-url <adres> --mevcut-latest <latest.json>` (noterlik şart).
