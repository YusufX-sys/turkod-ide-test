#!/usr/bin/env bash
# TürKod — kullanıcı programlarını çalıştıran gömülü Python'u hazırlar (Linux ve macOS).
#
# Windows'taki build_release.ps1 "3/7 python_embed" adımının karşılığı. Windows'ta
# kurulu bir Python klasörü kopyalanır; Linux/macOS'ta bu çalışmaz (Python kurulduğu
# yola ve sistem kütüphanelerine bağlıdır). Onun yerine taşınabilir, hazır derlenmiş
# python-build-standalone (CPython 3.12) indirilir.
#
# Kullanım (Linux makinesinde, WSL2'de ya da Mac'te):
#     bash platformlar/python_embed_hazirla.sh <hedef klasör>
# Örnek:
#     bash platformlar/python_embed_hazirla.sh dist/TurKod/backend/_internal/python_embed
#
# Sonuç düzeni:  <hedef>/bin/python3, <hedef>/bin/pip3, <hedef>/lib/python3.12/...
# turkod_ide/platform_katmani bu düzeni bekler (_posix.gomulu_python).
#
# Ortam değişkenleri (isteğe bağlı):
#     PBS_ETIKET      python-build-standalone sürüm etiketi   (varsayılan aşağıda)
#     PBS_PYTHON      CPython sürümü                          (varsayılan aşağıda)
#     PBS_ARSIV       İndirilmiş arşivin yolu (indirme yapılmaz)
#     SHA_ATLA=1      SHA256 denetimini atla (önerilmez)
#     KUTUPHANELER    pip ile kurulacak liste (varsayılan: kullanici_kutuphaneleri.txt)
#
# Sürümü değiştirirken etiket ve CPython sürümünün aynı sürüm sayfasında birlikte
# bulunduğunu denetle: https://github.com/astral-sh/python-build-standalone/releases
set -euo pipefail

PBS_ETIKET="${PBS_ETIKET:-20241016}"
PBS_PYTHON="${PBS_PYTHON:-3.12.7}"
PY_KISA="${PBS_PYTHON%.*}"                       # 3.12

KOK="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
KUTUPHANELER="${KUTUPHANELER:-$KOK/kullanici_kutuphaneleri.txt}"

hata() { echo "HATA: $*" >&2; exit 1; }
adim() { echo; echo "== $*"; }

[ $# -eq 1 ] || hata "Kullanım: $0 <hedef klasör>"
HEDEF="$1"

# --- 1. Sistem ve mimari -------------------------------------------------------
case "$(uname -s)" in
    Linux)  SISTEM="unknown-linux-gnu" ;;
    Darwin) SISTEM="apple-darwin" ;;
    *)      hata "Bu betik yalnızca Linux ve macOS içindir (Windows: build_release.ps1)." ;;
esac
case "$(uname -m)" in
    x86_64|amd64)  MIMARI="x86_64" ;;
    arm64|aarch64) MIMARI="aarch64" ;;
    *)             hata "Desteklenmeyen işlemci mimarisi: $(uname -m)" ;;
esac
DOSYA="cpython-${PBS_PYTHON}+${PBS_ETIKET}-${MIMARI}-${SISTEM}-install_only_stripped.tar.gz"
ADRES="https://github.com/astral-sh/python-build-standalone/releases/download/${PBS_ETIKET}"

sha256() {
    if command -v sha256sum >/dev/null; then sha256sum "$1" | cut -d' ' -f1
    else shasum -a 256 "$1" | cut -d' ' -f1; fi
}

GECICI="$(mktemp -d)"
trap 'rm -rf "$GECICI"' EXIT

# --- 2. İndir ve doğrula -------------------------------------------------------
adim "1/4 python-build-standalone: $DOSYA"
if [ -n "${PBS_ARSIV:-}" ]; then
    ARSIV="$PBS_ARSIV"
    [ -f "$ARSIV" ] || hata "PBS_ARSIV bulunamadı: $ARSIV"
else
    ARSIV="$GECICI/$DOSYA"
    curl -fL --retry 3 -o "$ARSIV" "$ADRES/$DOSYA" || hata "İndirilemedi: $ADRES/$DOSYA"
fi
if [ "${SHA_ATLA:-0}" != "1" ]; then
    curl -fsSL --retry 3 -o "$GECICI/SHA256SUMS" "$ADRES/SHA256SUMS" \
        || hata "SHA256SUMS indirilemedi (SHA_ATLA=1 ile atlanabilir)."
    BEKLENEN="$(awk -v d="$DOSYA" '$2 == d || $2 == "*"d {print $1}' "$GECICI/SHA256SUMS")"
    [ -n "$BEKLENEN" ] || hata "SHA256SUMS içinde $DOSYA yok."
    [ "$(sha256 "$ARSIV")" = "$BEKLENEN" ] || hata "SHA256 tutmuyor: $DOSYA"
    echo "SHA256 doğru."
fi

# --- 3. Aç ---------------------------------------------------------------------
adim "2/4 $HEDEF klasörüne açılıyor"
tar -xzf "$ARSIV" -C "$GECICI"                   # arşivin içinde python/ klasörü var
[ -x "$GECICI/python/bin/python3" ] || hata "Arşivde python/bin/python3 yok."
rm -rf "$HEDEF"
mkdir -p "$(dirname "$HEDEF")"
mv "$GECICI/python" "$HEDEF"
# Windows'taki robocopy /XD karşılığı: kullanıcının işine yaramayan büyük klasörler.
for d in test idlelib turtledemo; do
    rm -rf "$HEDEF/lib/python$PY_KISA/$d"
done
rm -rf "$HEDEF/include" "$HEDEF/share"
PY="$HEDEF/bin/python3"

# --- 4. Kütüphaneler -----------------------------------------------------------
adim "3/4 Kullanıcı kütüphaneleri ($KUTUPHANELER)"
if [ -f "$KUTUPHANELER" ]; then
    "$PY" -m pip install --no-warn-script-location --disable-pip-version-check \
        -r "$KUTUPHANELER"
fi

# pip'in bin/ içine yazdığı betiklerin ilk satırında bu makinedeki MUTLAK Python yolu
# var: paket başka klasöre taşınınca çalışmazlar (Windows'ta Scripts\ bu yüzden
# siliniyor). Yolu kendi klasörüne göre bulan /bin/sh başlangıcıyla değiştirilir.
for b in "$HEDEF"/bin/*; do
    [ -f "$b" ] && [ ! -L "$b" ] || continue
    ilk="$(head -c 2 "$b" 2>/dev/null || true)"
    [ "$ilk" = "#!" ] || continue
    head -n 1 "$b" | grep -q "python" || continue
    {
        printf '#!/bin/sh\n'
        printf "'''exec' \"\$(dirname -- \"\$0\")/python3\" \"\$0\" \"\$@\"\n"
        printf "' '''\n"
        tail -n +2 "$b"
    } > "$b.yeni"
    chmod +x "$b.yeni"
    mv "$b.yeni" "$b"
done

# --- 5. Doğrula (build_release.ps1 ve hazirla_ve_derle.ps1 ile aynı denetimler) --
adim "4/4 Doğrulama"
"$PY" -I -X utf8 -c "import sys, os, tkinter, turtle, ssl, sqlite3, ctypes, pip; \
sys.exit(0 if os.path.samefile(sys.prefix, sys.argv[1]) else 3)" "$HEDEF" \
    || hata "python_embed kendi kendine yetmiyor (3 = sys.prefix başka klasörde)."
if grep -qx "pygame" "$KUTUPHANELER" 2>/dev/null; then
    "$PY" -I -X utf8 -c "import pygame, sympy; print('ok')" >/dev/null \
        || hata "pygame / sympy içe aktarılamadı."
fi
"$HEDEF/bin/pip3" --version >/dev/null || hata "pip3 çalışmıyor."
echo "python_embed hazır: $PY ($("$PY" -c 'import platform; print(platform.python_version())'))"
