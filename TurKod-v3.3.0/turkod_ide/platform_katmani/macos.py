"""macOS uygulaması (yalnızca standart kütüphane).

Veri klasörü  : ~/Library/Application Support/TurKod
Terminal      : Terminal.app (osascript ile)
Kodi'nin sesi : `say` (Türkçe ses "Yelda" varsa o)
`turkod`      : ~/.local/bin/turkod bağlantısı
.trpy         : uygulama paketinin Info.plist'inden gelir (buradan değiştirilmez)
"""
import os
import shlex
import shutil
import subprocess

from . import _posix
from ._ortak import PlatformHatasi
from ._posix import (  # noqa: F401  (ortak arayüzün parçası)
    GOMULU_PYTHON_GORELI, editoru_ayri_baslat, ebeveyni_izle, ekrani_temizle,
    gizli_surec_ayarlari, gizli_veri, gomulu_python, gomulu_python_yol_dizini, sistem_python,
    kabuk_kod_sayfasi, kendi_agacimi_oldur, path_e_ekle, path_ten_cikar, surec_yasiyor,
    sureci_agacla_oldur,
)


def veri_tabani(yedek=None):
    return os.path.join(os.path.expanduser("~"), "Library", "Application Support")


def editor_dosyasi(backend):
    """TurKod.app/Contents/MacOS/TurKod (sunucu Contents/Resources/backend içinde)."""
    return os.path.join(os.path.dirname(os.path.dirname(backend)), "MacOS", "TurKod")


def _applescript_metni(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def terminal_betigi(komut, cwd=None):
    """Terminal.app'te çalıştırılacak AppleScript."""
    kabuk = shlex.join(komut)
    if cwd:
        kabuk = f"cd {shlex.quote(cwd)} && {kabuk}"
    return (f"tell application \"Terminal\"\n"
            f"  do script {_applescript_metni(kabuk)}\n"
            f"  activate\n"
            f"end tell")


def terminalde_ac(komut, cwd=None):
    try:
        subprocess.Popen(["osascript", "-e", terminal_betigi(komut, cwd)], close_fds=True,
                         start_new_session=True, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL)
        return True
    except OSError:
        return False


TURKCE_SES = "Yelda"


def _turkce_ses_var_mi():
    try:
        cikti = subprocess.run(["say", "-v", "?"], capture_output=True, text=True,
                               timeout=10).stdout
    except (OSError, subprocess.SubprocessError):
        return False
    return any(s.split()[:1] == [TURKCE_SES] for s in cikti.splitlines())


def konus(metin, dur=None):
    if not metin:
        return
    if not shutil.which("say"):
        raise PlatformHatasi("macOS'un konuşma komutu (say) bulunamadı.")
    komut = ["say"]
    if _turkce_ses_var_mi():
        komut += ["-v", TURKCE_SES]
    _posix.sesli_oku([*komut, metin], dur)


def dosya_iliskisi_kur():
    """macOS'ta .trpy ilişkisi uygulama paketinin Info.plist'indedir; yapılacak iş yok."""


def dosya_iliskisi_kaldir():
    raise PlatformHatasi(".trpy dosyalarının hangi uygulamayla açılacağını Finder'da "
                         "'Bilgi Al > Birlikte Aç' bölümünden değiştirebilirsin.")


def entegrasyon_durumu():
    yok = _posix.entegrasyon_destegi_yok()
    if yok:
        return yok
    kullanici_path, sistem_path = _posix.path_durumu()
    return {
        "destekleniyor": True,
        "path": kullanici_path or sistem_path,
        "path_sistemde": sistem_path,
        "iliskilendir": True,
        "iliski_kullanicida": False,
        "iliski_sistemde": True,
        "path_dizini": _posix.kullanici_bin_dizini(),
    }
