#!/usr/bin/env bash
# TürKod — macOS paketi (TurKod.app + .dmg). Windows'taki build_release.ps1'in karşılığı.
#
# Xcode kurulu bir Mac'te, proje kökünden çalıştır:
#     bash platformlar/macos/build_macos.sh --ozel-anahtar ~/gizli/turkod_private.pem \
#         --kimlik "Developer ID Application: Ad Soyad (TAKIMKODU)" --noter-profili turkod
#
# Seçenekler:
#     --ozel-anahtar <pem>   Manifest imzası için özel anahtar (yoksa --imzasiz gerekir)
#     --surum <X.Y.Z>        Boşsa surum.txt okunur
#     --imzasiz              Manifesti imzalamadan dene (yalnızca deneme paketi)
#     --kimlik "<ad>"        codesign kimliği (Developer ID Application). Verilmezse
#                            uygulama yerel (ad-hoc) imzalanır: yalnızca bu Mac'te açılır,
#                            başka Mac'lerde Gatekeeper engeller.
#     --noter-profili <ad>   `xcrun notarytool store-credentials <ad>` ile kaydedilmiş
#                            profil. Verilirse .dmg Apple'a noterliğe gönderilir ve
#                            sonuç .dmg'ye zımbalanır (staple). --kimlik gerektirir.
#     --indirme-url <url>    Verilirse latest.json + .sig üretilir/güncellenir (güncelleme
#                            bildirimi). Paketin yayındaki https indirme adresi.
#     --mevcut-latest <yol>  Diğer sistemlerin paketlerini içeren latest.json; bu paket
#                            ona eklenir (Windows paketi her zaman bulunmalı).
#
# Gerekenler: Xcode + komut satırı araçları, flutter (macOS masaüstü açık),
# python3 + pyinstaller ve backend bağımlılıkları, curl.
#
# Paket düzeni (platform_ayarlari.dart ve platform_katmani bunu bekler):
#     TurKod.app/Contents/MacOS/TurKod                         editör (Flutter)
#     TurKod.app/Contents/Resources/backend/turkod_backend     sunucu (PyInstaller)
#     TurKod.app/Contents/Resources/backend/turkod             `turkod` komutu
#     TurKod.app/Contents/Resources/backend/_internal/python_embed/bin/python3
#     TurKod.app/Contents/Resources/belgeler/                  kitap ve lisanslar
set -euo pipefail

KOK="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
FLUTTER_DIZINI="$KOK/turkod_flutter"
DIST="$KOK/dist/macos"
IZINLER_APP="$FLUTTER_DIZINI/macos/Runner/Release.entitlements"
IZINLER_BACKEND="$KOK/platformlar/macos/backend.entitlements"

OZEL_ANAHTAR=""; SURUM=""; IMZASIZ=0; KIMLIK=""; NOTER=""; INDIRME_URL=""; MEVCUT_LATEST=""
while [ $# -gt 0 ]; do
    case "$1" in
        --ozel-anahtar)  OZEL_ANAHTAR="$2"; shift 2 ;;
        --surum)         SURUM="$2"; shift 2 ;;
        --imzasiz)       IMZASIZ=1; shift ;;
        --kimlik)        KIMLIK="$2"; shift 2 ;;
        --noter-profili) NOTER="$2"; shift 2 ;;
        --indirme-url)   INDIRME_URL="$2"; shift 2 ;;
        --mevcut-latest) MEVCUT_LATEST="$2"; shift 2 ;;
        *) echo "Bilinmeyen seçenek: $1" >&2; exit 2 ;;
    esac
done

hata() { echo "HATA: $*" >&2; exit 1; }
adim() { echo; echo "=== $*"; }

# --- 0. Ön kontrol ---------------------------------------------------------------
adim "0/8 Ön kontrol"
[ "$(uname -s)" = "Darwin" ] || hata "Bu betik yalnızca macOS'ta çalışır."
[ -n "$SURUM" ] || SURUM="$(tr -d ' \r\n' < "$KOK/surum.txt")"
[ -n "$SURUM" ] || hata "Sürüm bulunamadı (surum.txt boş)."
if [ "$IMZASIZ" -eq 0 ]; then
    [ -n "$OZEL_ANAHTAR" ] || hata "--ozel-anahtar gerekli (denemek için --imzasiz)."
    [ -f "$OZEL_ANAHTAR" ] || hata "Özel anahtar bulunamadı: $OZEL_ANAHTAR"
fi
[ -z "$NOTER" ] || [ -n "$KIMLIK" ] || hata "--noter-profili için --kimlik gerekli."
if [ -n "$INDIRME_URL" ]; then
    [ "$IMZASIZ" -eq 0 ] || hata "--indirme-url imzasız derlemeyle kullanılamaz."
    [ -n "$NOTER" ] || hata "--indirme-url için noterlik (--noter-profili) gerekir: noterliksiz .dmg'yi başka Mac'ler açmaz."
fi
for k in flutter python3 pyinstaller codesign hdiutil curl file; do
    command -v "$k" >/dev/null || hata "'$k' bulunamadı."
done
MIMARI="$(uname -m)"   # arm64 (Apple Silicon) ya da x86_64 (Intel): paket bu Mac'e göre üretilir
echo "Sürüm: $SURUM | Mimari: $MIMARI | İmza: ${KIMLIK:-yerel (ad-hoc)}"

# --- 1. Flutter --------------------------------------------------------------------
adim "1/8 Flutter (macos, release)"
rm -rf "$FLUTTER_DIZINI/.dart_tool/flutter_build"
( cd "$FLUTTER_DIZINI" && flutter build macos --release )
FLUTTER_APP="$FLUTTER_DIZINI/build/macos/Build/Products/Release/TurKod.app"
[ -x "$FLUTTER_APP/Contents/MacOS/TurKod" ] || hata "Flutter çıktısı yok: $FLUTTER_APP"

# --- 2. PyInstaller ----------------------------------------------------------------
adim "2/8 PyInstaller (onedir)"
rm -rf "$DIST/backend" "$KOK/build/pyi-macos"
( cd "$KOK" && pyinstaller --noconfirm --clean --distpath "$DIST" \
      --workpath "$KOK/build/pyi-macos" turkod_backend.spec )
[ -x "$DIST/backend/turkod_backend" ] || hata "PyInstaller çıktısı yok."

# --- 3. Paket düzeni ---------------------------------------------------------------
adim "3/8 Paket düzeni"
APP="$DIST/TurKod.app"
rm -rf "$APP"
cp -R "$FLUTTER_APP" "$APP"
KAYNAK="$APP/Contents/Resources"
cp -R "$DIST/backend" "$KAYNAK/backend"
if [ -d "$KOK/belgeler" ]; then
    cp -R "$KOK/belgeler" "$KAYNAK/belgeler"
else
    echo "UYARI: belgeler/ yok; kitap ve lisanslar pakete girmeyecek." >&2
fi

# --- 4. Gömülü Python --------------------------------------------------------------
adim "4/8 python_embed (kullanıcı programlarını çalıştıran Python)"
bash "$KOK/platformlar/python_embed_hazirla.sh" "$KAYNAK/backend/_internal/python_embed"

# --- 5. codesign (içten dışa) ------------------------------------------------------
# Manifest (adım 6) codesign'dan SONRA üretilir: codesign Mach-O dosyalarının içine
# imza yazar, manifest ise dosyaların son hâlinin SHA-256'sını tutmalı (Windows'ta
# da manifest Authenticode'dan sonra imzalanır).
adim "5/8 codesign"
if [ -n "$KIMLIK" ]; then
    IMZA=(--force --timestamp --options runtime --sign "$KIMLIK")
else
    IMZA=(--force --sign -)
fi
# a) backend/ içindeki her Mach-O dosyası, en derindekinden başlayarak.
#    Çalıştırılabilir olanlar (turkod_backend, turkod, python3.x) izinlerle imzalanır.
find "$KAYNAK/backend" -type f -print0 |
    while IFS= read -r -d '' f; do
        tur="$(file -b "$f")"
        case "$tur" in *Mach-O*) ;; *) continue ;; esac
        printf '%s\t%s\n' "$(awk -F/ '{print NF}' <<<"$f")" "$f"
    done | sort -rn | cut -f2- |
    while IFS= read -r f; do
        if file -b "$f" | grep -q "executable"; then
            codesign "${IMZA[@]}" --entitlements "$IZINLER_BACKEND" "$f"
        else
            codesign "${IMZA[@]}" "$f"
        fi
    done
# b) Flutter'ın kendi çerçeveleri (FlutterMacOS.framework ve eklentiler).
if [ -d "$APP/Contents/Frameworks" ]; then
    for c in "$APP/Contents/Frameworks/"*; do
        codesign "${IMZA[@]}" "$c"
    done
fi
# c) Uygulamanın kendisi (en son; içeriği mühürler).
codesign "${IMZA[@]}" --entitlements "$IZINLER_APP" "$APP"
codesign --verify --strict --verbose=2 "$APP"

# --- 6. Manifest + 7. duman testi --------------------------------------------------
adim "6/8 Manifest imzası"
if [ "$IMZASIZ" -eq 1 ]; then
    echo "UYARI: --imzasiz: manifest imzalanmadı (yalnızca deneme)." >&2
else
    python3 "$KOK/manifest_imzala.py" --dizin "$KAYNAK/backend" --surum "$SURUM" \
        --ozel-anahtar "$OZEL_ANAHTAR" --haric "_internal/python_embed/*"
    # Manifest dosyası backend/ içine yazıldı: uygulama mührü yenilenir.
    codesign "${IMZA[@]}" --entitlements "$IZINLER_APP" "$APP"
    codesign --verify --strict --verbose=2 "$APP"
fi

adim "7/8 Duman testi"
"$KAYNAK/backend/turkod" --surum | grep -q "$SURUM" || hata "turkod --surum sürümü göstermedi."
DENEME="$(mktemp -d)"
printf 'yazdır("turkod_ok", 2 + 3)\n' > "$DENEME/deneme.trpy"
"$KAYNAK/backend/turkod" "$DENEME/deneme.trpy" | grep -q "turkod_ok 5" \
    || hata "turkod bir .trpy dosyasını çalıştıramadı."
rm -rf "$DENEME"
echo "turkod komutu bir .trpy dosyasını çalıştırdı."

# --- 8. .dmg + noterlik ------------------------------------------------------------
adim "8/8 .dmg"
DMG="$KOK/dist/TurKod-$SURUM-macos-$MIMARI.dmg"
SAHNE="$(mktemp -d)"
cp -R "$APP" "$SAHNE/"
ln -s /Applications "$SAHNE/Applications"     # sürükle-bırak kurulum
rm -f "$DMG"
hdiutil create -volname "TürKod" -srcfolder "$SAHNE" -ov -format UDZO "$DMG"
rm -rf "$SAHNE"
if [ -n "$KIMLIK" ]; then
    codesign --force --timestamp --sign "$KIMLIK" "$DMG"
fi
if [ -n "$NOTER" ]; then
    echo "Noterliğe gönderiliyor (birkaç dakika sürebilir)..."
    xcrun notarytool submit "$DMG" --keychain-profile "$NOTER" --wait
    xcrun stapler staple "$DMG"
    spctl --assess --type open --context context:primary-signature --verbose=2 "$DMG" || true
fi
echo "Hazır: $DMG"

# --- 9. Güncelleme bildirimi (latest.json + .sig) ----------------------------------
if [ -n "$INDIRME_URL" ]; then
    adim "9/9 latest.json"
    python3 "$KOK/surum_imzala.py" --platform "macos-$MIMARI" \
        --kurulum "$DMG" --url "$INDIRME_URL" --ozel-anahtar "$OZEL_ANAHTAR" \
        ${MEVCUT_LATEST:+--mevcut "$MEVCUT_LATEST"}
fi
[ -n "$KIMLIK" ] || echo "NOT: Yerel (ad-hoc) imza: bu .dmg yalnızca bu Mac'te denemek içindir."
echo
echo "Tamam."
