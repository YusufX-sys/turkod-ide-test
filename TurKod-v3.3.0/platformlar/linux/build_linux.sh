#!/usr/bin/env bash
# TürKod — Linux paketi (AppImage + .tar.gz). Windows'taki build_release.ps1'in karşılığı.
#
# Bir Linux makinesinde ya da WSL2 (Ubuntu) içinde, proje kökünden çalıştır:
#     bash platformlar/linux/build_linux.sh --ozel-anahtar ~/gizli/turkod_private.pem
#
# Seçenekler:
#     --ozel-anahtar <pem>   Manifest imzası için özel anahtar (yoksa --imzasiz gerekir)
#     --surum <X.Y.Z>        Boşsa surum.txt okunur (tek sürüm kaynağı)
#     --imzasiz              Manifesti imzalamadan dene (yalnızca deneme paketi)
#     --appimage-yok         Yalnızca .tar.gz üret
#     --indirme-url <url>    Verilirse latest.json + .sig üretilir/güncellenir (güncelleme
#                            bildirimi). Paketin yayındaki https indirme adresi.
#     --mevcut-latest <yol>  Diğer sistemlerin paketlerini içeren latest.json; bu paket
#                            ona eklenir (Windows paketi her zaman bulunmalı).
#
# Gerekenler: flutter (linux masaüstü açık: `flutter config --enable-linux-desktop`),
# clang, cmake, ninja-build, pkg-config, libgtk-3-dev, python3 + pyinstaller ve
# backend bağımlılıkları (nasıl-build-edilir.txt'deki pip listesi), curl.
# AppImage için appimagetool: PATH'te yoksa APPIMAGETOOL=<yol> ver ya da betik indirir.
#
# Paket düzeni (platform_ayarlari.dart ve platform_katmani bunu bekler):
#     TurKod/turkod_flutter            editör (Flutter)
#     TurKod/lib/, TurKod/data/        Flutter kütüphaneleri ve varlıkları
#     TurKod/backend/turkod_backend    sunucu (PyInstaller)
#     TurKod/backend/turkod            `turkod` komutu
#     TurKod/backend/_internal/python_embed/bin/python3   kullanıcı programlarının Python'u
#     TurKod/belgeler/                 kitap ve lisanslar
set -euo pipefail

KOK="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
FLUTTER_DIZINI="$KOK/turkod_flutter"
DIST="$KOK/dist/linux"
CIKIS="$DIST/TurKod"

OZEL_ANAHTAR=""; SURUM=""; IMZASIZ=0; APPIMAGE=1; INDIRME_URL=""; MEVCUT_LATEST=""
while [ $# -gt 0 ]; do
    case "$1" in
        --ozel-anahtar) OZEL_ANAHTAR="$2"; shift 2 ;;
        --surum)        SURUM="$2"; shift 2 ;;
        --imzasiz)      IMZASIZ=1; shift ;;
        --appimage-yok) APPIMAGE=0; shift ;;
        --indirme-url)  INDIRME_URL="$2"; shift 2 ;;
        --mevcut-latest) MEVCUT_LATEST="$2"; shift 2 ;;
        *) echo "Bilinmeyen seçenek: $1" >&2; exit 2 ;;
    esac
done

hata() { echo "HATA: $*" >&2; exit 1; }
adim() { echo; echo "=== $*"; }

# --- 0. Ön kontrol ---------------------------------------------------------------
adim "0/7 Ön kontrol"
[ "$(uname -s)" = "Linux" ] || hata "Bu betik yalnızca Linux'ta (ya da WSL2'de) çalışır."
[ -n "$SURUM" ] || SURUM="$(tr -d ' \r\n' < "$KOK/surum.txt")"
[ -n "$SURUM" ] || hata "Sürüm bulunamadı (surum.txt boş)."
if [ "$IMZASIZ" -eq 0 ]; then
    [ -n "$OZEL_ANAHTAR" ] || hata "--ozel-anahtar gerekli (denemek için --imzasiz)."
    [ -f "$OZEL_ANAHTAR" ] || hata "Özel anahtar bulunamadı: $OZEL_ANAHTAR"
fi
if [ -n "$INDIRME_URL" ]; then
    [ "$IMZASIZ" -eq 0 ] || hata "--indirme-url imzasız derlemeyle kullanılamaz."
    [ "$APPIMAGE" -eq 1 ] || hata "--indirme-url için AppImage gerekir (.tar.gz kendini güncelleyemez)."
fi
for k in flutter python3 pyinstaller curl tar; do
    command -v "$k" >/dev/null || hata "'$k' bulunamadı."
done
case "$(uname -m)" in
    x86_64|amd64)  FL_MIMARI="x64";   AI_MIMARI="x86_64" ;;
    aarch64|arm64) FL_MIMARI="arm64"; AI_MIMARI="aarch64" ;;
    *) hata "Desteklenmeyen mimari: $(uname -m)" ;;
esac
echo "Sürüm: $SURUM | Mimari: $AI_MIMARI"

# --- 1. Flutter --------------------------------------------------------------------
adim "1/7 Flutter (linux, release)"
# Simge yazı tipi önbelleği (Windows betiğindeki aynı sorun): yeni simgeler boş kare görünmesin.
rm -rf "$FLUTTER_DIZINI/.dart_tool/flutter_build"
( cd "$FLUTTER_DIZINI" && flutter build linux --release )
FLUTTER_CIKTI="$FLUTTER_DIZINI/build/linux/$FL_MIMARI/release/bundle"
[ -x "$FLUTTER_CIKTI/turkod_flutter" ] || hata "Flutter çıktısı yok: $FLUTTER_CIKTI/turkod_flutter"

# --- 2. PyInstaller ----------------------------------------------------------------
adim "2/7 PyInstaller (onedir)"
rm -rf "$DIST/backend" "$KOK/build/pyi-linux"
( cd "$KOK" && pyinstaller --noconfirm --clean --distpath "$DIST" \
      --workpath "$KOK/build/pyi-linux" turkod_backend.spec )
[ -x "$DIST/backend/turkod_backend" ] || hata "PyInstaller çıktısı yok."

# --- 3. Gömülü Python --------------------------------------------------------------
adim "3/7 python_embed (kullanıcı programlarını çalıştıran Python)"
bash "$KOK/platformlar/python_embed_hazirla.sh" "$DIST/backend/_internal/python_embed"

# --- 4. Paket düzeni ---------------------------------------------------------------
adim "4/7 Paket düzeni"
rm -rf "$CIKIS"
mkdir -p "$CIKIS"
cp -a "$FLUTTER_CIKTI/." "$CIKIS/"
cp -a "$DIST/backend" "$CIKIS/backend"
if [ -d "$KOK/belgeler" ]; then
    cp -a "$KOK/belgeler" "$CIKIS/belgeler"
    rm -f "$CIKIS/belgeler/KITAP_BAKIM.md"    # iç belge (kitabın bakımı): pakete girmez
else
    echo "UYARI: belgeler/ yok; kitap ve lisanslar pakete girmeyecek." >&2
fi

# --- 5. Manifest imzası ------------------------------------------------------------
adim "5/7 Manifest imzası"
if [ "$IMZASIZ" -eq 1 ]; then
    echo "UYARI: --imzasiz: manifest imzalanmadı (yalnızca deneme)." >&2
else
    python3 "$KOK/manifest_imzala.py" --dizin "$CIKIS/backend" --surum "$SURUM" \
        --ozel-anahtar "$OZEL_ANAHTAR" --haric "_internal/python_embed/*"
fi

# --- 6. Duman testi ----------------------------------------------------------------
adim "6/7 Duman testi"
"$CIKIS/backend/turkod" --surum | grep -q "$SURUM" || hata "turkod --surum sürümü göstermedi."
DENEME="$(mktemp -d)"
printf 'yazdır("turkod_ok", 2 + 3)\n' > "$DENEME/deneme.trpy"
"$CIKIS/backend/turkod" "$DENEME/deneme.trpy" | grep -q "turkod_ok 5" \
    || hata "turkod bir .trpy dosyasını çalıştıramadı."
rm -rf "$DENEME"
echo "turkod komutu bir .trpy dosyasını çalıştırdı."

# --- 7. Paketler -------------------------------------------------------------------
adim "7/7 Paketler"
TAR="$KOK/dist/TurKod-$SURUM-linux-$AI_MIMARI.tar.gz"
tar -C "$DIST" -czf "$TAR" TurKod
echo "Hazır: $TAR"

if [ "$APPIMAGE" -eq 1 ]; then
    APPDIR="$DIST/TurKod.AppDir"
    rm -rf "$APPDIR"
    mkdir -p "$APPDIR/usr/lib" "$APPDIR/usr/share/applications" \
             "$APPDIR/usr/share/icons/hicolor/256x256/apps"
    cp -a "$CIKIS" "$APPDIR/usr/lib/turkod"
    install -m 755 "$KOK/platformlar/linux/AppRun" "$APPDIR/AppRun"
    # .desktop dosyasının adı uygulama kimliğiyle aynı (my_application.cc: g_set_prgname
    # ve application-id = org.turkod.TurKod): Wayland'de pencere bu adla eşleşir.
    cp "$KOK/platformlar/linux/turkod.desktop" "$APPDIR/org.turkod.TurKod.desktop"
    cp "$KOK/platformlar/linux/turkod.desktop" \
       "$APPDIR/usr/share/applications/org.turkod.TurKod.desktop"
    cp "$FLUTTER_DIZINI/assets/icon/app_icon.png" "$APPDIR/turkod.png"
    cp "$FLUTTER_DIZINI/assets/icon/app_icon.png" \
       "$APPDIR/usr/share/icons/hicolor/256x256/apps/turkod.png"

    ARAC="${APPIMAGETOOL:-$(command -v appimagetool || true)}"
    if [ -z "$ARAC" ]; then
        ARAC="$KOK/build/appimagetool-$AI_MIMARI.AppImage"
        if [ ! -x "$ARAC" ]; then
            echo "appimagetool indiriliyor..."
            mkdir -p "$KOK/build"
            curl -fL --retry 3 -o "$ARAC" \
                "https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-$AI_MIMARI.AppImage" \
                || hata "appimagetool indirilemedi (APPIMAGETOOL=<yol> ver ya da --appimage-yok)."
            chmod +x "$ARAC"
        fi
    fi
    APPIMAGE_DOSYASI="$KOK/dist/TurKod-$SURUM-$AI_MIMARI.AppImage"
    # FUSE olmayan ortamlarda (WSL2, Docker) appimagetool kendini açarak çalışır.
    ARCH="$AI_MIMARI" APPIMAGE_EXTRACT_AND_RUN=1 "$ARAC" "$APPDIR" "$APPIMAGE_DOSYASI"
    echo "Hazır: $APPIMAGE_DOSYASI"
fi

# --- 8. Güncelleme bildirimi (latest.json + .sig) ----------------------------------
if [ -n "$INDIRME_URL" ]; then
    adim "8/8 latest.json"
    python3 "$KOK/surum_imzala.py" --platform "linux-$AI_MIMARI" \
        --kurulum "$APPIMAGE_DOSYASI" --url "$INDIRME_URL" --ozel-anahtar "$OZEL_ANAHTAR" \
        ${MEVCUT_LATEST:+--mevcut "$MEVCUT_LATEST"}
fi

echo
echo "Tamam."
