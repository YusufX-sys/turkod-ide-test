#!/usr/bin/env bash
# TürKod'u Codespace'in masaüstünde açar.
#
#   bash .devcontainer/turkod_ac.sh            -> editörü (arayüz) masaüstünde açar
#   bash .devcontainer/turkod_ac.sh kabuk      -> TürKod Kabuğu'nu bu terminalde açar
#   bash .devcontainer/turkod_ac.sh <dosya.trpy> -> programı bu terminalde çalıştırır
#   bash .devcontainer/turkod_ac.sh --yenile   -> en son AppImage'ı yeniden indirir
#
# AppImage, "Platform denemesi" iş akışının (hedef: linux) EN SON başarılı
# çalıştırmasından indirilir; önce o iş akışını çalıştırmış olmalısın. Codespace'te
# FUSE olmadığından AppImage çalıştırılmaz, içi bir kez açılır (~/turkod/uygulama).
set -euo pipefail

KLASOR="$HOME/turkod"
UYGULAMA="$KLASOR/uygulama"
export DISPLAY="${DISPLAY:-:1}"

hata() { echo "HATA: $*" >&2; exit 1; }

indir() {
    command -v gh >/dev/null || hata "gh (GitHub CLI) bulunamadı."
    rm -rf "$KLASOR"
    mkdir -p "$KLASOR"
    echo "En son Linux paketi aranıyor..."
    local kimlikler
    if ! kimlikler="$(gh run list --workflow platform-denemesi.yml --status success \
            --limit 20 --json databaseId --jq '.[].databaseId' 2>&1)"; then
        echo "$kimlikler" >&2
        cat >&2 <<'NOT'

GitHub'a erişilemedi. Codespace'in kendi izni Actions dosyalarını okumaya
yetmiyor olabilir. Kendi hesabınla bir kez giriş yap, sonra betiği yeniden çalıştır:

    unset GITHUB_TOKEN
    gh auth login --web
    bash .devcontainer/turkod_ac.sh --yenile
NOT
        exit 1
    fi
    for k in $kimlikler; do
        if gh run download "$k" --name linux-appimage --dir "$KLASOR" >/dev/null 2>&1; then
            echo "Paket, $k numaralı çalıştırmadan indirildi."
            break
        fi
    done
    local appimage
    appimage="$(ls "$KLASOR"/*.AppImage 2>/dev/null | head -n 1 || true)"
    [ -n "$appimage" ] || hata "AppImage bulunamadı. Önce Actions'ta 'Platform denemesi' iş akışını 'linux' hedefiyle çalıştır (paketler 3 gün saklanır)."
    chmod +x "$appimage"
    echo "Paket açılıyor (FUSE gerekmeden)..."
    ( cd "$KLASOR" && "$appimage" --appimage-extract >/dev/null )
    mv "$KLASOR/squashfs-root" "$UYGULAMA"
    rm -f "$appimage"
}

if [ "${1:-}" = "--yenile" ] || [ ! -x "$UYGULAMA/AppRun" ]; then
    indir
    [ "${1:-}" = "--yenile" ] && shift || true
fi

case "${1:-}" in
    "")
        echo "TürKod açılıyor. Tarayıcıda 'TürKod masaüstü' sekmesine (6080) geç; parola: vscode"
        nohup "$UYGULAMA/AppRun" > "$KLASOR/arayuz.log" 2>&1 &
        echo "Arayüz günlüğü: $KLASOR/arayuz.log"
        echo "Sunucu günlüğü: ~/.local/share/TurKod/backend.log"
        ;;
    kabuk)
        exec "$UYGULAMA/AppRun" --turkod kabuk
        ;;
    *)
        exec "$UYGULAMA/AppRun" --turkod "$@"
        ;;
esac
