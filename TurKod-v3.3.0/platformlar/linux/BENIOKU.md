# Linux

Bu klasör, TürKod'un yalnızca Linux'a özgü derleme ve paketleme dosyaları içindir.
Ortak kod (`turkod_ide/`, `turkod_flutter/lib/`) burada değil, proje kökünde kalır.

## Dosyalar

- `build_linux.sh`: Flutter (linux) + PyInstaller + gömülü Python + manifest + duman
  testi + paketler. Çıktı: `dist/TurKod-<sürüm>-linux-<mimari>.tar.gz` ve
  `dist/TurKod-<sürüm>-<mimari>.AppImage`. Çalıştırma:
  `bash platformlar/linux/build_linux.sh --ozel-anahtar <pem>` (seçenekler betiğin başında).
- `AppRun`: AppImage'ın giriş noktası. Argümansız → editör, `--terminal dosya.trpy` →
  terminal penceresi, `--turkod ...` → `turkod` komutu.
- `turkod.desktop`: uygulama menüsü girdisi (AppImage'ın içine konur).
- `.trpy` MIME türü ayrı dosya değil: `turkod_ide/platform_katmani/linux.py` Ayarlar'dan
  kurar.
- Henüz yok: `.deb` paketi, küçük boyutlu simgeler (şimdilik yalnızca 256 px).

## AppImage notu

AppImage her açılışta rastgele bir klasöre (`/tmp/.mount_XXXX`) bağlanır. Bu yüzden
`~/.local/bin/turkod` bir bağlantı değil, AppImage dosyasını `--turkod` ile çağıran küçük
bir betiktir; `.trpy` ilişkisi de AppImage dosyasını `--terminal` ile çağırır. AppImage
taşınırsa Ayarlar'dan bu ikisini bir kez kapatıp açmak yeterli. `.tar.gz` sürümünde
doğrudan bağlantı kullanılır.

Flutter'ın GTK 3 kütüphaneleri AppImage'a gömülmez; hedef bilgisayarda kurulu olmalı
(masaüstü dağıtımlarının hepsinde vardır).

## Notlar

- Derleme bir Linux makinede ya da WSL2 (Ubuntu) içinde yapılır;
  Windows'tan Linux paketi üretilemez.
- Gömülü Python için python-build-standalone (taşınabilir CPython 3.12) kullanılır:
  `platformlar/python_embed_hazirla.sh dist/TurKod/backend/_internal/python_embed`
  (macOS ile ortak betik).
- Kodi'nin sesi: `spd-say` ya da `espeak-ng`; yoksa ses kapalı kalır.
- `turkod` komutu: `~/.local/bin/turkod` bağlantısı.
- Veri klasörü: `~/.local/share/TurKod`.
- Flutter klasörü: `turkod_flutter/linux/` açıldı (2026-11-21). Çalıştırılabilir dosya
  `turkod_flutter`, uygulama kimliği `org.turkod.TurKod`, pencere başlığı "TürKod".
- Paket düzeni: `<uygulama>/turkod_flutter` ve `<uygulama>/backend/turkod_backend`
  (arayüz sunucuyu buradan bulur: `turkod_flutter/lib/platform_ayarlari.dart`).
- `.trpy` ilişkisi ve `turkod` komutu Ayarlar'dan kurulabiliyor
  (`turkod_ide/platform_katmani/linux.py`).
- IDE içindeki tarayıcı yok; sayfalar sistem tarayıcısında (`xdg-open`) açılır.
- Uygulama içi güncelleme: AppImage kendini yeniler (yeni AppImage indirilir, SHA-256
  denetlenir, eski dosyanın yerine konur, yeniden başlatılır). `.tar.gz` kurulumu
  kendini güncelleyemez; yeni sürüm elle kurulur. `latest.json` için
  `build_linux.sh --indirme-url <adres> --mevcut-latest <Windows'un latest.json'ı>`.
- Kod yazı tipi: DejaVu Sans Mono (çoğu dağıtımda kurulu).
