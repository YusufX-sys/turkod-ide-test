# Devir Notu: TürKod'u Windows, Linux ve macOS'a uyumlu yapma

Bu not, işe başka bir bilgisayarda devam edebilmek için yazıldı. Claude Code'a
şunu demen yeterli:

> `platformlar/DEVIR_NOTU.md` dosyasını oku ve oradan devam et.

Tarih: 2026-11-21 · Sürüm: 3.3.0

---

## 0. Sohbeti yeni bilgisayarda sürdürme

**Önerilen yol: bu not + hafıza klasörü, yeni bir sohbet.**
1. Projeyi GitHub'dan indir. `platformlar/` klasörü depoda yoksa USB ile kopyala.
2. Bölüm 6'daki dosyaları (CLAUDE.md, hafıza klasörü, anahtar ...) yeni bilgisayara götür.
3. Claude Code'u proje klasöründe aç ve bu notu okut.

Bu yol her sistemde çalışır ve git işlemi gerektirmez. Eski sohbetin kelimesi kelimesine
dökümü gelmez, ama işin özü bu notta.

**Tam sohbet dökümü gerekiyorsa: `.jsonl` dosyasını kopyalamak.**
- Sohbet, eski bilgisayarda
  `~/.claude/projects/C--Users-<kullanıcı>-Desktop-turkod-ide-repo-TurKod-v3-3-0/`
  içinde `96d6a5e6-b725-4e38-bb4a-8e8e1db88524.jsonl` olarak duruyor.
- Bu dosyayı yeni bilgisayara kopyala. Proje klasöründe terminalde
  `claude --resume <dosyanın tam yolu>` ile açılır.
- Resmî bir taşıma özelliği değil. Dökümün içindeki `C:\...` yolları başka bilgisayarda
  bozuk kalabilir. Masaüstü uygulamasının listesinde de görünmeyebilir.

**Diğer yollar (bu proje için uygun değil):**
- *Masaüstü uygulamasında Open in → Cloud, sonra `claude --teleport`:* Sohbet buluta
  özet olarak taşınır. Teleport için değişikliklerin commit edilip GitHub'a push edilmiş
  olması gerekir. Ayrıca `CLAUDE.md` `.gitignore`'da olduğu için oraya gitmez.
- *Remote Control (`/remote-control`):* Eski bilgisayar açık kalmak zorunda. Yalnızca
  telefondan ya da tarayıcıdan aynı sohbeti sürdürmek içindir.
- *`/export`:* Sohbeti okunur bir metin dosyasına yazar. Geri yüklenemez.

---

## 1. Şu ana kadar ne yapıldı

- Proje incelendi. Windows'a bağlı yerler tek tek bulundu (aşağıda, bölüm 3).
- Proje içinde `platformlar/windows`, `platformlar/linux`, `platformlar/macos`
  klasörleri açıldı. Her birinde o sisteme özgü dosyaları anlatan bir `BENIOKU.md` var.
- **Kodda hiçbir şey değiştirilmedi.** Mevcut Windows dosyaları taşınmadı, çünkü derleme
  betikleri yolları proje köküne göre buluyor (`$PSScriptRoot`). Taşınırlarsa
  betiklerdeki yollar da güncellenmeli.
- Eski bilgisayarda C: sürücüsü %99 doluydu (1,6 GB boş). Bu yüzden iş başka
  bilgisayara taşınıyor.
- **2026-11-21: Adım 1 bitti.** Python platform katmanı `turkod_ide/platform_katmani/`
  (ad bilerek `platform` değil: standart `platform` modülünü gölgelerdi). Testler:
  `tests/test_platform_katmani.py`. `runner.py`, `exe_terminali.py`, `yerel_sunucu.py`
  ayrı süreçte çalıştığı için katmana bağlanamaz.
- **2026-11-21: Adım 2 bitti (derleme denenmedi).** Flutter tarafında sisteme göre
  değişenler `turkod_flutter/lib/platform_ayarlari.dart` içinde (yazı tipi, sunucu yolu,
  veri klasörü, macOS Cmd kısayolları, tarayıcı). `turkod_flutter/linux/` ve
  `turkod_flutter/macos/` açıldı. Testler: `test/platform_ayarlari_test.dart`.
  Yazı tipi gömülmedi; sistemde hazır olan kullanılıyor (Menlo / DejaVu Sans Mono).
- **2026-11-21: Adım 3 bitti (Linux/macOS'ta denenmedi).** Kullanıcı Python'unu bulma
  kuralı tek yerde: `platform_katmani.kullanici_python_bul()` (Windows:
  `python_embed\python.exe`, Linux/macOS: `python_embed/bin/python3`). Hazırlama betiği:
  `platformlar/python_embed_hazirla.sh <hedef>` (python-build-standalone indirir, SHA256
  denetler, `kullanici_kutuphaneleri.txt`'yi kurar, `bin/` betiklerini taşınabilir yapar,
  doğrular). Varsayılan sürüm `PBS_ETIKET=20241016`, `PBS_PYTHON=3.12.7`; ilk
  çalıştırmada sürüm sayfasında bu ikilinin bulunduğunu denetle.
  `turkod_backend.spec`: `.ico` simgeleri yalnızca Windows'ta.
- **2026-11-21: Adım 4 betikleri yazıldı (hiçbiri çalıştırılmadı).**
  `platformlar/linux/build_linux.sh` (AppImage + .tar.gz, `AppRun`, `turkod.desktop`) ve
  `platformlar/macos/build_macos.sh` (.app + codesign + .dmg + noterlik,
  `backend.entitlements`). AppImage için `turkod` komutu ve `.trpy` ilişkisi AppImage
  dosyasını çağırır (`_posix.appimage_yolu`). Editör yolu sisteme göre
  (`platform_katmani.editor_dosyasi`). macOS'ta belgeler `Contents/Resources/belgeler`
  (`yardim.dart` oraya da bakar). Betikler `bash ...` ile çalıştırılır (Windows'ta
  yazıldıkları için çalıştırma izni gelmeyebilir).
- **2026-11-21: Adım 5 bitti (Linux/macOS'ta denenmedi).** Tek `latest.json`, içinde
  `platforms` alanı (`windows`, `linux-x86_64`, `linux-aarch64`, `macos-arm64`,
  `macos-x86_64`). Üst düzey `url/sha256/size` HER ZAMAN Windows kurulumu: 3.3.0 ve
  öncesi yalnızca bunları okur. `turkod_ide/updater.py` kendi paketini seçer
  (`paket_anahtari`, `kurulum_turu`): Windows → Inno Setup (değişmedi), Linux AppImage →
  dosya yerinde yenilenir (`guncelleme_uygula` komutu) ve yeniden başlatılır, macOS →
  yeni `.dmg` açılır, TürKod kapanır. Linux `.tar.gz` kendini güncelleyemez ("yeni sürüm
  var" der). Testler: `tests/test_guncelleme_platformlari.py`.

  **Yayın sırası:** (1) Windows'ta `build_release.ps1 -IndirmeUrl ...` → `dist\latest.json`.
  (2) Bu dosyayı Linux'a kopyala: `build_linux.sh ... --indirme-url <AppImage adresi>
  --mevcut-latest <latest.json>`. (3) Çıkan `latest.json`'ı Mac'e kopyala:
  `build_macos.sh ... --indirme-url <dmg adresi> --mevcut-latest <latest.json>`.
  (4) Bütün paketleri ve EN SON `latest.json` + `latest.json.sig`'i AYNI GitHub
  yayınına yükle (`releases/latest/download/latest.json` adresinden okunur).
  Elle: `python surum_imzala.py --platform <ad> --kurulum <dosya> --url <adres>
  --ozel-anahtar <pem> --mevcut <latest.json>`.
- **2026-11-21: Sürüm 4.0.0.** `surum.txt`, `pubspec.yaml`, `turkod.iss`,
  `duzeltmeler_test.dart` 4.0.0; sürüm notları `çeşitlinotlar/4.0 notlar.txt`. Kitap
  HENÜZ güncellenmedi (s.8 "yalnızca Windows 10/11", s.72 tarayıcı, s.74 ses, kısayol
  tablosunda Mac'te Cmd notu): Linux/macOS denendikten sonra yapılacak.
- **Linux/macOS denemesi (Linux ya da Mac olmadan):** depo kökünde
  `.github/workflows/platform-denemesi.yml`. Yalnızca elle başlatılır (Actions →
  Platform denemesi → Run workflow → hedef: testler / linux / macos / hepsi). Paketler
  `--imzasiz` derlenir; ekran görüntüleri, günlükler ve paketler "Artifacts" altında 3 gün
  durur. Özel depoda dakika ve depolama sınırı var: önce "testler", sonra tek tek
  "linux" / "macos". Elle deneme: AppImage'ı Ubuntu canlı USB'de, .dmg'yi ödünç bir
  Mac'te aç (imzasız: Sistem Ayarları → Gizlilik ve Güvenlik → Yine de Aç).
- **2026-11-21: İlk gerçek denemeler (özel test deposu `turkod-ide-test`, GitHub
  Actions):** Python testleri Ubuntu 22.04 ve macOS (arm64) üzerinde geçiyor. Linux
  AppImage (183 MB, ~6 dk) ve macOS .dmg (339 MB, ~12 dk) derlendi, duman testi geçti,
  uygulama açıldı ve sunucu bağlandı (ekran görüntüleri alındı). Bu denemelerde düzeltilen:
  macOS'ta hata ayıklayıcının yerel modüle girmemesi (/var → /private/var), Kodi sohbet
  numarası çakışması (3.3'ten), Windows'a bağlı iki test. Sonra: macOS menü çubuğu
  Türkçe ve TürKod menülerinden üretiliyor (`_MenuBar._macMenuleri`, PlatformMenuBar),
  uygulama adı "TürKod" (Info.plist CFBundleName/DisplayName, bölge `tr`), pencere
  1280x800 ortada (MainFlutterWindow.swift); macOS'ta henüz derlenip görülmedi.
  Açık kalanlar: elle arayüz denemesi (canlı USB / ödünç Mac); kitap; .dmg boyutu.
- **Linux'u tarayıcıda arayüzüyle denemek:** depo kökünde `.devcontainer/` (GitHub
  Codespaces + masaüstü). Actions'ın son `linux` paketini indirip açar
  (`bash .devcontainer/turkod_ac.sh`; `kabuk` ile TürKod Kabuğu). Kullanım:
  `.devcontainer/BENIOKU.md`. Denendi (2026-11-21): masaüstü açıldı, TürKod çalıştı,
  dosya açma ve Çalıştır çalıştı. Bulunan hata: IDE terminalindeki `turkod` komutu ve
  TürKod Kabuğu düğmesi Linux/macOS'ta `turkod.exe` arıyordu (düzeltildi:
  `platform_katmani.turkod_komutu_dosyasi`; yeni derlemede denenecek). Kullanıcı da
  elle denedi: TürKod Kabuğu, Kodi (API'siz), kaplumbağa ve Güncelleştirmeler sorunsuz.
- **Arayüz (entegrasyon) testleri Linux/macOS'ta:** `turkod_flutter/integration_test/`
  testleri kısayolda macOS'ta Cmd basar (`ortak_platform.dart`). Çalıştırıcı:
  `platformlar/arayuz_testleri.sh` (Linux'ta Xvfb; profil klasörleri, OZET.txt, 20 sn'de
  bir ekran görüntüsü). İş akışı hedefleri: `arayuz-linux`, `arayuz-macos`,
  `arayuz-windows` (karşılaştırma). Yeni senaryo eklemek: integration_test/ altına
  `*_test.dart`, sonra betikteki listeye bir `calistir` satırı.
  İlk `arayuz-linux` (#7, 2026-11-22): testler çalıştı ama 5'i de düştü. Düzeltilen test
  varsayımları: `mutlak_mı("C:/a")` (yalnızca Windows'ta mutlak) ve `küpkök(27)`
  (Linux'ta 3.0000000000000004). Kalan: menü öğesine tıklanamama ("would not hit
  test"), Ctrl+W, Hakkında, Klavye kısayolları penceresi, kurtarma. Önce aynı testlerin
  Windows'ta geçip geçmediği (`arayuz-windows`) görülmeli: testler 3.3 arayüzüne göre
  eskimiş olabilir.
- **Yapı:** Kod TEK; Windows/Linux/macOS için ayrı kopya yoktur. Sisteme göre değişen
  kod iki dosyada toplanır: `turkod_ide/platform_katmani/` ve
  `turkod_flutter/lib/platform_ayarlari.dart`. `platformlar/<sistem>/` yalnızca o
  sistemin derleme/paketleme dosyaları içindir.

## 2. Genel durum

Temel zaten üç sisteme uygun: Flutter arayüzü, Python/FastAPI sunucusu ve PyInstaller
hepsinde çalışır. Asıl iş iki parça:

1. Windows'a sıkı bağlı birkaç parçayı bir **platform katmanının** arkasına almak.
2. Her sistem için **ayrı bir paketleme hattı** kurmak. PyInstaller ve Flutter başka
   bir sistem için derleme yapamaz; her paket kendi sisteminde üretilir.

## 3. Windows'a bağlı yerler

| Alan | Dosyalar | Sorun |
|---|---|---|
| Sistem kaydı, PATH, `.trpy` dosya ilişkisi | `turkod_ide/entegrasyon.py` | `winreg`, `ctypes.windll` |
| Süreç başlatma/kapatma | `turkod_ide/calistirici.py`, `ide_core.py`, `surec_izleyici.py`, `exe_terminali.py`, `akilli_duzeltici.py` | `taskkill /F /T`, `creationflags`, `OpenProcess` |
| EXE'ye dönüştürme | `turkod_ide/exe_donusturucu.py`, `turkod_flutter/lib/exe_donusturme.dart` | Her sistem kendi çalıştırılabilir dosyasını üretmeli |
| Kodi'nin sesi | `turkod_ide/kodi_ses.py` + `kodi_ses.ps1` | PowerShell ses motoru |
| Gömülü tarayıcı | `turkod_flutter/lib/main.dart` (`webview_windows`) | Yalnızca Windows |
| Sunucu dosyasının adı | `main.dart` içinde `packagedBackendExe` (`turkod_backend.exe`) | Sabit `.exe` adı ve yol |
| Veri klasörü | `turkod_ide/paths.py`, `backend_main.py` | `LOCALAPPDATA` |
| Yazı tipi | Dart'ta 3 yerde `'Consolas'` | Linux/macOS'ta yok |
| Kısayollar | `main.dart` (58 kısayol) | macOS'ta Ctrl yerine Cmd |
| Paketleme | `hazirla_ve_derle.ps1`, `build_release.ps1`, `turkod.iss` | PowerShell + Inno Setup |
| Flutter platform klasörleri | yalnızca `turkod_flutter/windows/` var | `linux/`, `macos/` yok |

Bir kısmı zaten `os.name == "nt"` / `sys.platform` ile ayrılmış, ama dağınık durumda.

## 4. Yapılacaklar (sırasıyla)

### Adım 1: Python platform katmanı
- `turkod_ide/platform/` altında `windows.py`, `linux.py`, `macos.py` açılır. Hepsi
  aynı işlevleri sunar: `veri_klasoru()`, `sureci_agacla_oldur(pid)`,
  `terminalde_ac(dosya)`, `dosya_iliskisi_kur()`, `path_e_ekle()`, `konus(metin)`.
  Diğer dosyalardan `os.name` kontrolleri kalkar.
- Klasörler `platformdirs` ile bulunur:
  - Windows: `%LOCALAPPDATA%\TurKod`
  - Linux: `~/.local/share/TurKod`
  - macOS: `~/Library/Application Support/TurKod`
- Süreç kapatma: POSIX'te `start_new_session=True` + `os.killpg`, ya da üç sistemde
  `psutil`.
- `--parent-pid` izleme: `psutil.pid_exists` (Linux'ta ek olarak `PR_SET_PDEATHSIG`).
- `.trpy` çift tıklama: macOS'ta `open -a Terminal`; Linux'ta `x-terminal-emulator`,
  `gnome-terminal`, `konsole` sırayla denenir.
- Kodi'nin sesi: macOS'ta `say`, Linux'ta `spd-say` / `espeak-ng`; yoksa ses kapalı.
- Her `open()` ve `subprocess` çağrısında `encoding="utf-8"`; `PYTHONUTF8=1`.
- Windows'ta davranış değişmemeli: mevcut testler (`tests/`) bunu doğrular.

### Adım 2: Flutter tarafı
- `webview_windows` yalnızca Windows'ta. Linux/macOS'ta `desktop_webview_window` ya da
  sistem tarayıcısı (`url_launcher`).
- Sunucu dosyasının adı ve yolu sisteme göre seçilir (macOS'ta `.app/Contents/Resources/...`).
- Kod yazı tipi uygulamaya gömülür (JetBrains Mono ya da DejaVu Sans Mono), `Consolas` kalkar.
- Kısayollar: `SingleActivator(..., meta: Platform.isMacOS, control: !Platform.isMacOS)`;
  macOS menüsü için `PlatformMenuBar`.
- `flutter create --platforms=linux,macos .` ile platform klasörleri açılır.

### Adım 3: Gömülü Python
Windows'taki "Python klasörünü kopyala" yöntemi Linux/macOS'ta çalışmaz. Bunun yerine
**python-build-standalone** (taşınabilir CPython 3.12) kullanılır.

### Adım 4: Paketleme
| | Windows | Linux | macOS |
|---|---|---|---|
| Nerede derlenir | Windows | Linux ya da WSL2 | **Mac + Xcode şart** |
| Paket | Inno Setup `.exe` (mevcut) | AppImage, isteğe bağlı `.deb` | `.app` → `.dmg` |
| İmza | Authenticode (mevcut) | Gerekmez | Apple Developer hesabı + `codesign` + noterlik |

macOS'ta imza izinlerine `com.apple.security.cs.allow-unsigned-executable-memory`
eklenmeli. Gömülü Python'daki her `.so`/`.dylib` ayrıca imzalanmalı.

### Adım 5: Güncelleyici
Manifest imzası her sistemde aynı şekilde çalışır. Her sistem için ayrı bir manifest ve
ayrı indirme dosyası gerekir. macOS'ta en kolayı yeni `.dmg`'yi indirip açmak.

**Önerilen sıra:** Adım 1 → Adım 2 → önce Linux (WSL2'de AppImage, ucuz ve hataların
çoğunu yakalar) → sonra macOS → testleri üç sistemde çalıştırma.

## 5. Çalışma kuralları (eski bilgisayardaki Claude hafızasından)

Bunlar Claude'un eski bilgisayardaki hafızasında duruyordu. Yeni bilgisayarda
kendiliğinden gelmez.

- **Yalnızca Türkçe.** Kullanıcıya her metin Türkçe olmalı.
- **Git/GitHub yok.** Claude hiçbir git komutu çalıştırmaz (okuma amaçlı olanlar dahil),
  commit, push ya da yayımlama yapmaz. Yedekler dosya kopyası olarak alınır.
  Commit ve push'u kullanıcı kendisi yapar.
- **İmzalı manifest.** `turkod_ide/` altında bir dosya değişince manifest yeniden
  imzalanmalı: `python kaynak_imzala.py --imzala --surum X.Y.Z --ozel-anahtar <anahtar yolu>`,
  kontrol için `--dogrula`. İmzalayıcı `turkod_ide/` içinde CRLF satır sonu kabul etmez.
- **Sürüm numarası** dört yerde: `surum.txt`, `turkod_flutter/pubspec.yaml`, `turkod.iss`,
  `integration_test/duzeltmeler_test.dart`.
- **Kitap:** Kullanıcıya görünen her değişiklikte `belgeler/TurKod_ile_Kodlama_Macerasi.pdf`
  güncellenir. Kaynak dosyası yoktur; araçlar `tools/kitap/`, kontrol listesi
  `belgeler/KITAP_BAKIM.md`. Dil: 7 yaşındaki çocuğa "sen" diye seslenen sıcak Kodi dili,
  asla resmî kılavuz dili. İçindekiler her sayfayı göstermeli.
- **Sürüm notları:** Kullanıcıya görünen her yenilik ya da düzeltmeden sonra
  `<sürüm> notlar.txt` güncellenir (UTF-8, CRLF, sonda satır sonu yok).
- **Windows'a özgü teknik notlar:** Git Bash `sed -i` CRLF'yi bozar; ters eğik çizgi
  içeren düzenlemeler heredoc ile değil, Edit/Write ile yapılır. `ISCC.exe`'yi sözdizimi
  denetimi için çalıştırma: `dist\TurKod-Setup-<sürüm>.exe` dosyasını siler.

## 6. Yeni bilgisayara ayrıca götürülecekler (GitHub'da yok)

| Ne | Not |
|---|---|
| `CLAUDE.md` | `.gitignore`'da. İçindeki bilgisayara özgü yollar yeni bilgisayara göre düzeltilmeli |
| `.claude/` | Proje ayarları, `.gitignore`'da |
| Claude hafıza klasörü | `~/.claude/projects/<proje>/memory/`. Bölüm 5'teki kurallar zaten burada özetli |
| `platformlar/` klasörü | Yeni açıldı. Kullanıcı commit edip push etmezse GitHub'da yoktur |
| İmzalama anahtarı (`*_private.pem`) | **Asla GitHub'a konmaz.** USB ya da şifreli bir yolla taşınır |
| Sürüm notları dosyası | Depo dışında, `çeşitlinotlar` klasöründe |
| `dist/`, `build/`, `python_embed` kopyası | Taşınmaz, yeni bilgisayarda yeniden üretilir |
