#!/usr/bin/env bash
# TürKod arayüz (entegrasyon) testlerini Linux ya da macOS'ta çalıştırır.
#
# Testler turkod_flutter/integration_test/ içindedir: gerçek uygulamayı gerçek
# Python sunucusuyla açar, menülere tıklar, editöre yazar, kısayollara basar ve
# sonucu denetler. Windows'ta aynı testler `flutter test ... -d windows` ile çalışır.
#
# Kullanım (proje kökünden):  bash platformlar/arayuz_testleri.sh [sonuç klasörü]
# Gerekenler: flutter (masaüstü açık), python3 + requirements.txt paketleri;
# Linux'ta ayrıca Xvfb ve ImageMagick (ekransız masaüstü ve ekran görüntüleri).
#
# Çıkış kodu: herhangi bir test çöker ya da bir madde "KALDI" olursa 1.
# Sonuç klasörüne her testin günlüğü, raporları, OZET.txt ve ekran görüntüleri yazılır.
# (macOS'un hazır bash'i 3.2'dir: "set -u" ve boş dizi açılımı kullanılmaz.)
set -o pipefail

KOK="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SONUC="${1:-$KOK/../sonuc}"
mkdir -p "$SONUC/ekranlar"
SONUC="$(cd "$SONUC" && pwd)"

case "$(uname -s)" in
    Linux)  CIHAZ="linux" ;;
    Darwin) CIHAZ="macos" ;;
    *) echo "Bu betik yalnızca Linux ve macOS içindir." >&2; exit 2 ;;
esac

# --- Ekran: Linux'ta ekransız masaüstü (Xvfb) ------------------------------------
if [ "$CIHAZ" = "linux" ] && [ -z "${DISPLAY:-}" ]; then
    Xvfb :99 -screen 0 1400x900x24 >/dev/null 2>&1 &
    XVFB=$!
    export DISPLAY=:99
    sleep 2
fi

# --- Ekran görüntüleri: 20 saniyede bir (en çok 60) --------------------------------
(
    n=0
    while [ $n -lt 60 ]; do
        sleep 20
        n=$((n + 1))
        dosya="$SONUC/ekranlar/$(printf '%02d' $n).png"
        if [ "$CIHAZ" = "macos" ]; then
            screencapture -x "$dosya" 2>/dev/null
        else
            import -window root "$dosya" 2>/dev/null
        fi
    done
) &
EKRAN=$!

temizle() {
    kill "$EKRAN" 2>/dev/null
    [ -n "${XVFB:-}" ] && kill "$XVFB" 2>/dev/null
}
trap temizle EXIT

cd "$KOK/turkod_flutter" || exit 2
flutter pub get >/dev/null || exit 2

COKEN=""
# calistir <günlük adı> <test dosyası> <profil klasörü> [aşama]
calistir() {
    local ad="$1" dosya="$2" profil="$3" asama="${4:-1}"
    echo
    echo "=== $ad ($dosya, $CIHAZ)"
    TURKOD_TEST_PROFIL="$profil" TURKOD_TEST_ASAMA="$asama" \
        flutter test "integration_test/$dosya" -d "$CIHAZ" 2>&1 | tee "$SONUC/$ad.log"
    local kod=$?
    # Testin profil klasörüne yazdığı rapor dosyaları
    cp "$profil"/*.txt "$SONUC/" 2>/dev/null
    [ $kod -eq 0 ] || COKEN="$COKEN $ad"
}

# Testler, kullanıcının ayarlarına dokunmamak için adı belli önekle başlayan boş bir
# profil klasörü ister (testin içindeki güvenlik denetimi).
yeni_profil() { mktemp -d "${TMPDIR:-/tmp}/$1XXXXXX"; }

PROFIL="$(yeni_profil turkod_eksik_)"
calistir duzeltmeler-1 duzeltmeler_test.dart "$PROFIL" 1
calistir duzeltmeler-2 duzeltmeler_test.dart "$PROFIL" 2   # aynı profil: kurtarma denetimi
calistir eksikler eksikler_test.dart "$(yeni_profil turkod_eksik_)"
calistir turkce-ceviri turkce_ceviri_test.dart "$(yeni_profil turkod_ceviri_)"
calistir yeni-ozellikler yeni_ozellikler_test.dart "$(yeni_profil turkod_yeni_)"

# --- Özet ------------------------------------------------------------------------
{
    echo "TürKod arayüz testleri — $CIHAZ — $(date '+%Y-%m-%d %H:%M')"
    echo
    echo "Geçen maddeler: $(cat "$SONUC"/*.log | grep -c '|GEÇTİ|')"
    echo "Kalan maddeler: $(cat "$SONUC"/*.log | grep -c '|KALDI|')"
    cat "$SONUC"/*.log | grep '|KALDI|' | sed 's/^/  /'
    echo
    echo "Eksik raporu (bilgi için; testi düşürmez):"
    cat "$SONUC"/eksikler.log | grep '^RAPOR|EKSİK|' | sed 's/^/  /'
    [ -z "$COKEN" ] || echo "Çöken ya da başarısız biten testler:$COKEN"
} | tee "$SONUC/OZET.txt"

if [ -n "$COKEN" ] || grep -q '|KALDI|' "$SONUC"/*.log; then
    exit 1
fi
echo "Bütün arayüz testleri geçti."
