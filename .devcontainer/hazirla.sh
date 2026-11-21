#!/usr/bin/env bash
# Codespace ilk açıldığında bir kez çalışır (devcontainer.json: postCreateCommand).
# TürKod'un (Flutter + gömülü Python) Linux'ta ihtiyaç duyduğu kütüphaneleri kurar.
set -euo pipefail

sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    libgtk-3-0 libblkid1 liblzma5 \
    libgl1 libegl1 libgles2 libgl1-mesa-dri \
    fonts-dejavu-core fonts-noto-color-emoji \
    zenity xdg-utils \
    espeak-ng \
    file
sudo apt-get clean

chmod +x .devcontainer/turkod_ac.sh 2>/dev/null || true
echo
echo "Hazır. TürKod'u açmak için terminale yaz:  bash .devcontainer/turkod_ac.sh"
