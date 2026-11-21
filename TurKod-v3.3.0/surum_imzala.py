"""Release aracı - pakete KONMAZ.

Kurulum dosyasından latest.json üretir ve manifest ile AYNI özel anahtarla imzalar.
    python surum_imzala.py --kurulum dist\\TurKod-Setup-3.1.0.exe ^
        --url https://github.com/KULLANICI/DEPO/releases/download/v3.1.0/TurKod-Setup-3.1.0.exe ^
        --ozel-anahtar D:\\gizli\\turkod_private.pem [--notlar "Neler değişti"]

Çıktı: kurulum dosyasının yanında latest.json ve latest.json.sig.
Üçünü (Setup.exe, latest.json, latest.json.sig) aynı yayına yükle.

Linux ve macOS paketleri AYNI latest.json'a eklenir (turkod_ide/updater.py "platforms"
alanından kendi paketini seçer). Her paket kendi sisteminde derlenir; latest.json'ı
bir öncekinin üzerine ekleyerek büyüt:
    python surum_imzala.py --kurulum dist/TurKod-Setup-3.4.0.exe --url ... --ozel-anahtar K
    python surum_imzala.py --platform linux-x86_64 --kurulum dist/TurKod-3.4.0-x86_64.AppImage \\
        --url ... --ozel-anahtar K --mevcut dist/latest.json
    python surum_imzala.py --platform macos-arm64 --kurulum dist/TurKod-3.4.0-macos-arm64.dmg \\
        --url ... --ozel-anahtar K --mevcut dist/latest.json
Platform adları: windows, linux-x86_64, linux-aarch64, macos-arm64, macos-x86_64.
Üst düzey url/sha256/size alanları HER ZAMAN Windows kurulumudur: 3.3.0 ve öncesi
Windows sürümleri yalnızca onları okur. Windows paketi yoksa bu alanlar yazılmaz.
"""
import argparse
import base64
import json
import re
import sys
from pathlib import Path

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding

from manifest_imzala import _gomulu_public_key, _ozel_anahtar_yukle, _sha256

PLATFORMLAR = ("windows", "linux-x86_64", "linux-aarch64", "macos-arm64", "macos-x86_64")


def bildirim_olustur(surum, platform, url, sha256, boyut, notlar="", mevcut=None):
    """latest.json içeriği. mevcut verilirse (aynı sürümün) diğer paketleri korunur."""
    if mevcut is not None:
        if str(mevcut.get("version")) != surum:
            raise ValueError(f"--mevcut başka bir sürüme ait ({mevcut.get('version')!r}); "
                             f"bu derleme {surum!r}.")
        bildirim = dict(mevcut)
        paketler = dict(bildirim.get("platforms") or {})
        # Eski biçimde (platforms yok) üst düzey alanlar Windows paketidir.
        if "windows" not in paketler and "url" in bildirim:
            paketler["windows"] = {k: bildirim[k] for k in ("url", "sha256", "size")
                                   if k in bildirim}
    else:
        bildirim = {"version": surum}
        paketler = {}
    paketler[platform] = {"url": url, "sha256": sha256, "size": boyut}
    bildirim["platforms"] = paketler
    if platform == "windows":
        bildirim.update(paketler["windows"])
    if notlar or "notes" not in bildirim:
        bildirim["notes"] = notlar
    # Okunurluk: sürüm, Windows alanları, notlar, platformlar.
    sira = ["version", "url", "sha256", "size", "notes", "platforms"]
    return {k: bildirim[k] for k in sira if k in bildirim}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kurulum", required=True)
    ap.add_argument("--url", required=True)
    ap.add_argument("--ozel-anahtar", required=True)
    ap.add_argument("--notlar", default="")
    ap.add_argument("--platform", default="windows", choices=PLATFORMLAR)
    ap.add_argument("--mevcut", help="eklenecek mevcut latest.json (diğer sistemlerin paketleri)")
    a = ap.parse_args()

    kurulum = Path(a.kurulum).resolve()
    surum = (Path(__file__).resolve().parent / "surum.txt").read_text(encoding="utf-8").strip()
    if not re.fullmatch(r"\d+\.\d+\.\d+", surum):
        sys.exit(f"surum.txt geçersiz: {surum!r}")
    if not a.url.lower().startswith("https://"):
        sys.exit("--url https ile başlamalı.")
    if not kurulum.is_file():
        sys.exit(f"Kurulum dosyası yok: {kurulum}")

    mevcut = None
    if a.mevcut:
        try:
            mevcut = json.loads(Path(a.mevcut).read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            sys.exit(f"--mevcut okunamadı: {e}")
    try:
        bildirim = bildirim_olustur(surum, a.platform, a.url, _sha256(kurulum),
                                    kurulum.stat().st_size, a.notlar, mevcut)
    except ValueError as e:
        sys.exit(f"HATA: {e}")
    if "windows" not in bildirim["platforms"]:
        print("UYARI: Windows paketi yok. 3.3.0 ve öncesi Windows sürümleri bu latest.json'ı "
              "okuyamaz; Windows kurulumunu da ekle.", file=sys.stderr)
    veri = json.dumps(bildirim, ensure_ascii=False, indent=2).encode("utf-8")

    anahtar = _ozel_anahtar_yukle(a.ozel_anahtar)
    gomulu = _gomulu_public_key()
    if gomulu is not None and gomulu.public_numbers() != anahtar.public_key().public_numbers():
        sys.exit("HATA: Bu özel anahtar signing.py'deki public key'in eşi değil.")

    pss = padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH)
    imza = anahtar.sign(veri, pss, hashes.SHA256())
    anahtar.public_key().verify(imza, veri, pss, hashes.SHA256())

    (kurulum.parent / "latest.json").write_bytes(veri)
    (kurulum.parent / "latest.json.sig").write_text(base64.b64encode(imza).decode("ascii"), encoding="utf-8")
    print(f"latest.json ve latest.json.sig yazıldı: {kurulum.parent} (sürüm {surum}; "
          f"paketler: {', '.join(sorted(bildirim['platforms']))})")


if __name__ == "__main__":
    main()
