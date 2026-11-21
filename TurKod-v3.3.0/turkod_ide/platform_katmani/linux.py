"""Linux uygulaması (yalnızca standart kütüphane).

Veri klasörü  : $XDG_DATA_HOME/TurKod (varsayılan ~/.local/share/TurKod)
Terminal      : x-terminal-emulator, gnome-terminal, konsole ... sırayla denenir
Kodi'nin sesi : spd-say, espeak-ng ya da espeak; hiçbiri yoksa ses kapalı
`turkod`      : ~/.local/bin/turkod bağlantısı
.trpy         : ~/.local/share/mime (text/x-turkod) + .desktop dosyası
"""
import os
import subprocess

from . import _posix
from ._ortak import PlatformHatasi, backend_dizini
from ._posix import (  # noqa: F401  (ortak arayüzün parçası)
    GOMULU_PYTHON_GORELI, editoru_ayri_baslat, ebeveyni_izle, ekrani_temizle,
    gizli_surec_ayarlari, gizli_veri, gomulu_python, gomulu_python_yol_dizini, sistem_python,
    kabuk_kod_sayfasi, kendi_agacimi_oldur, path_e_ekle, path_ten_cikar, surec_yasiyor,
    sureci_agacla_oldur,
)


def veri_tabani(yedek=None):
    xdg = os.environ.get("XDG_DATA_HOME")
    if xdg and os.path.isabs(xdg):
        return xdg
    return os.path.join(os.path.expanduser("~"), ".local", "share")


# Önek argümanlarından sonra çalıştırılacak komut ve argümanları gelir.
TERMINALLER = (
    ("x-terminal-emulator", ("-e",)),
    ("gnome-terminal", ("--",)),
    ("konsole", ("-e",)),
    ("xfce4-terminal", ("-x",)),
    ("mate-terminal", ("-x",)),
    ("tilix", ("-e",)),
    ("kitty", ()),
    ("alacritty", ("-e",)),
    ("xterm", ("-e",)),
)


def terminalde_ac(komut, cwd=None):
    """Komutu yeni bir terminal penceresinde başlatır; terminal yoksa False."""
    onek = _posix.ilk_bulunan(TERMINALLER)
    if not onek:
        return False
    try:
        subprocess.Popen([*onek, *komut], cwd=cwd, close_fds=True, start_new_session=True)
        return True
    except OSError:
        return False


SES_MOTORLARI = (
    ("spd-say", ("-l", "tr", "-w")),
    ("espeak-ng", ("-v", "tr")),
    ("espeak", ("-v", "tr")),
)


def konus(metin, dur=None):
    if not metin:
        return
    onek = _posix.ilk_bulunan(SES_MOTORLARI)
    if not onek:
        raise PlatformHatasi("Konuşma sesi bulunamadı. 'speech-dispatcher' ya da "
                             "'espeak-ng' paketini kurarsan Kodi konuşabilir.")
    _posix.sesli_oku([*onek, metin], dur)


# --------------------------------------------------------------------------
# .trpy ilişkisi (freedesktop): MIME türü + .desktop dosyası
# --------------------------------------------------------------------------
MIME_TURU = "text/x-turkod"
MASAUSTU_DOSYASI = "turkod-calistir.desktop"
_MIME_XML = """<?xml version="1.0" encoding="UTF-8"?>
<mime-info xmlns="http://www.freedesktop.org/standards/shared-mime-info">
  <mime-type type="text/x-turkod">
    <comment>TürKod programı</comment>
    <sub-class-of type="text/plain"/>
    <glob pattern="*.trpy"/>
  </mime-type>
</mime-info>
"""


def _veri_alt(*parcalar):
    return os.path.join(veri_tabani(), *parcalar)


def _yollar():
    # AppImage'da kalıcı yol AppImage dosyasıdır; AppRun --terminal'ı sunucuya iletir.
    return {
        "mime": _veri_alt("mime", "packages", "turkod-trpy.xml"),
        "masaustu": _veri_alt("applications", MASAUSTU_DOSYASI),
        "backend": _posix.appimage_yolu() or os.path.join(backend_dizini(), "turkod_backend"),
    }


def editor_dosyasi(backend):
    """<uygulama>/turkod_flutter (backend/ klasörünün bir üstü)."""
    return os.path.join(os.path.dirname(backend), "turkod_flutter")


def _calistir(komut):
    try:
        subprocess.run(komut, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=20)
    except (OSError, subprocess.SubprocessError):
        pass


def _veritabanlarini_yenile():
    _calistir(["update-mime-database", _veri_alt("mime")])
    _calistir(["update-desktop-database", _veri_alt("applications")])


def _iliski_etkin_mi():
    y = _yollar()
    try:
        with open(y["masaustu"], encoding="utf-8") as f:
            icerik = f.read()
    except OSError:
        return False
    return os.path.isfile(y["mime"]) and y["backend"] in icerik


def dosya_iliskisi_kur():
    y = _yollar()
    os.makedirs(os.path.dirname(y["mime"]), exist_ok=True)
    os.makedirs(os.path.dirname(y["masaustu"]), exist_ok=True)
    with open(y["mime"], "w", encoding="utf-8") as f:
        f.write(_MIME_XML)
    with open(y["masaustu"], "w", encoding="utf-8") as f:
        f.write("[Desktop Entry]\n"
                "Type=Application\n"
                "Name=TürKod ile çalıştır\n"
                "Comment=TürKod programını çalıştırır\n"
                f'Exec="{y["backend"]}" --terminal %f\n'
                f"MimeType={MIME_TURU};\n"
                "NoDisplay=true\n"
                "Terminal=false\n")
    _veritabanlarini_yenile()
    _calistir(["xdg-mime", "default", MASAUSTU_DOSYASI, MIME_TURU])


def dosya_iliskisi_kaldir():
    y = _yollar()
    for yol in (y["mime"], y["masaustu"]):
        try:
            os.remove(yol)
        except FileNotFoundError:
            pass
    _veritabanlarini_yenile()


def entegrasyon_durumu():
    yok = _posix.entegrasyon_destegi_yok()
    if yok:
        return yok
    kullanici_path, sistem_path = _posix.path_durumu()
    iliski = _iliski_etkin_mi()
    return {
        "destekleniyor": True,
        "path": kullanici_path or sistem_path,
        "path_sistemde": sistem_path,
        "iliskilendir": iliski,
        "iliski_kullanicida": iliski,
        "iliski_sistemde": False,
        "path_dizini": _posix.kullanici_bin_dizini(),
    }
