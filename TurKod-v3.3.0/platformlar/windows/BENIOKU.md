# Windows

Bu klasör, TürKod'un yalnızca Windows'a özgü derleme ve paketleme dosyaları içindir.
Ortak kod (`turkod_ide/`, `turkod_flutter/lib/`) burada değil, proje kökünde kalır.

## Şu an proje kökünde duran Windows dosyaları

Bu dosyalar henüz taşınmadı, çünkü betikler yolları proje köküne göre buluyor
(`$PSScriptRoot`). Taşınacaklarsa betiklerdeki yollar da birlikte güncellenmeli.

- `hazirla_ve_derle.ps1`, `build_release.ps1`: derleme betikleri
- `turkod.iss`: Inno Setup kurulum betiği
- `sihirbaz/`, `sihirbaz_gorsel_uret.py`: kurulum sihirbazı görselleri
- `turkod_backend.spec`: PyInstaller tanımı (Linux/macOS ile paylaşılabilir)
- `turkod_flutter/windows/`: Flutter'ın Windows yürütücüsü
- `turkod_ide/kodi_ses.ps1`: Kodi'nin sesi (Windows ses motoru)
- `turkod_ide/entegrasyon.py`: sistem kaydı, PATH ve `.trpy` dosya ilişkisi

## Paket

- Çıktı: `TurKod-Setup-<sürüm>.exe` (Inno Setup)
- İmza: Authenticode (`signtool.exe`)
- Ayrıntı: `nasıl-build-edilir.txt`
