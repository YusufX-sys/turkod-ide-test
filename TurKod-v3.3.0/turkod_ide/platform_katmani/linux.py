"""Linux uygulaması (yalnızca standart kütüphane).

Veri klasörü  : $XDG_DATA_HOME/TurKod (varsayılan ~/.local/share/TurKod)
Terminal      : xdg-terminal-exec, ptyxis, gnome-terminal, konsole ... sırayla denenir
Kodi'nin sesi : spd-say, espeak-ng ya da espeak; hiçbiri yoksa ses kapalı
`turkod`      : ~/.local/bin/turkod bağlantısı
.trpy         : ~/.local/share/mime (text/x-turkod) + .desktop dosyası
"""
import os
import re
import subprocess

from . import _posix
from ._ortak import PlatformHatasi, alt_surec_ortami, backend_dizini
from ._posix import (  # noqa: F401  (ortak arayüzün parçası)
    GOMULU_PYTHON_GORELI, ebeveyni_izle, ekrani_temizle,
    gizli_surec_ayarlari, gizli_veri, gomulu_python, gomulu_python_yol_dizini, sistem_python,
    kabuk_kod_sayfasi, kendi_agacimi_oldur, path_e_ekle, path_ten_cikar, surec_yasiyor,
    sureci_agacla_oldur,
)

_SON_TERMINAL_HATASI = [None]


def son_terminal_hatasi():
    return _SON_TERMINAL_HATASI[0]


def veri_tabani(yedek=None):
    xdg = os.environ.get("XDG_DATA_HOME")
    if xdg and os.path.isabs(xdg):
        return xdg
    return os.path.join(os.path.expanduser("~"), ".local", "share")


# Önek argümanlarından sonra çalıştırılacak komut ve argümanları gelir.
# Sıra: önce masaüstünün seçtiği terminal (xdg-terminal-exec), sonra yaygın
# terminaller; Debian'ın x-terminal-emulator'ı en sonda (-e'yi her terminal
# aynı anlamda almıyor).
TERMINALLER = (
    ("xdg-terminal-exec", ()),
    ("ptyxis", ("--new-window", "--")),      # GNOME 47+ (Fedora, Ubuntu 25.10)
    ("kgx", ("--",)),                        # GNOME Console
    ("gnome-terminal", ("--",)),
    ("konsole", ("-e",)),
    ("xfce4-terminal", ("-x",)),
    ("mate-terminal", ("-x",)),
    ("tilix", ("-e",)),
    ("foot", ()),
    ("wezterm", ("start", "--")),
    ("alacritty", ("-e",)),
    ("kitty", ()),
    ("xterm", ("-e",)),
    ("x-terminal-emulator", ("-e",)),
)
TERMINAL_YOK = ("Terminal programı bulunamadı (gnome-terminal, konsole, xterm ...). "
                "Birini kurmalısın.")


def terminalde_ac(komut, cwd=None):
    """Komutu yeni bir terminal penceresinde başlatır; terminal yoksa False
    (nedeni son_terminal_hatasi())."""
    _SON_TERMINAL_HATASI[0] = None
    onek = _posix.ilk_bulunan(TERMINALLER)
    if not onek:
        _SON_TERMINAL_HATASI[0] = TERMINAL_YOK
        return False
    try:
        subprocess.Popen([*onek, *komut], cwd=cwd, close_fds=True, start_new_session=True,
                         env=alt_surec_ortami())
        return True
    except OSError as e:
        _SON_TERMINAL_HATASI[0] = f"Terminal açılamadı: {e}"
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
    # "--": "-" ile başlayan metin seçenek sanılmasın (üç program da getopt kullanır).
    _posix.sesli_oku([*onek, "--", metin], dur)


def yazi_tipi_aileleri():
    """`fc-list : family` çıktısındaki aileler (virgülle ayrılmış adlar bölünür)."""
    try:
        sonuc = subprocess.run(["fc-list", ":", "family"], capture_output=True, text=True,
                               timeout=15, env=alt_surec_ortami(),
                               stdin=subprocess.DEVNULL)
    except (OSError, ValueError, subprocess.SubprocessError):
        return None
    if sonuc.returncode != 0 or not isinstance(sonuc.stdout, str):
        return None
    aileler = set()
    for satir in sonuc.stdout.splitlines():
        # fc-list özel karakterleri ters eğik çizgiyle kaçırır ("\-", "\,").
        for ad in re.split(r"(?<!\\),", satir):
            ad = re.sub(r"\\(.)", r"\1", ad).strip()
            if ad:
                aileler.add(ad)
    return sorted(aileler)


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


COP_KUTUSU_ADI = "Çöp"


def cop_kutusu_klasoru():
    """freedesktop.org çöp kutusu: $XDG_DATA_HOME/Trash (varsayılan ~/.local/share/Trash)."""
    return os.path.join(veri_tabani(), "Trash")


def cop_kutusu_var_mi(yol):
    return _posix.ayni_disk_mi(yol, cop_kutusu_klasoru())


def cop_kutusuna_tasi(yol):
    """Öğeyi freedesktop.org Trash standardına göre taşır: dosya Trash/files'a,
    geri yükleme bilgisi Trash/info/<ad>.trashinfo'ya. Dosyalar uygulaması
    (Nautilus, Dolphin ...) öğeyi buradan geri yükleyebilir."""
    import time
    import urllib.parse
    kok = cop_kutusu_klasoru()
    dosyalar, bilgi = os.path.join(kok, "files"), os.path.join(kok, "info")
    os.makedirs(dosyalar, exist_ok=True)
    os.makedirs(bilgi, exist_ok=True)
    mutlak = os.path.abspath(yol)
    taban = os.path.basename(mutlak.rstrip("/")) or "adsiz"
    kok_ad, uzanti = os.path.splitext(taban)
    ad, n = taban, 1
    # .trashinfo O_EXCL ile oluşturulur: aynı anda silen başka bir program
    # (Dosyalar uygulaması) aynı adı alırsa onun kaydının üstüne yazılmaz.
    while True:
        bilgi_yolu = os.path.join(bilgi, ad + ".trashinfo")
        if not os.path.lexists(os.path.join(dosyalar, ad)):
            try:
                fd = os.open(bilgi_yolu, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
                break
            except FileExistsError:
                pass
        n += 1
        ad = f"{kok_ad} {n}{uzanti}"
    with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
        f.write("[Trash Info]\n"
                f"Path={urllib.parse.quote(mutlak)}\n"
                f"DeletionDate={time.strftime('%Y-%m-%dT%H:%M:%S')}\n")
    try:
        os.rename(mutlak, os.path.join(dosyalar, ad))
    except OSError:
        os.remove(bilgi_yolu)
        raise


def bellek_gb():
    """(toplam, kullanılabilir) GB: /proc/meminfo (MemAvailable, önbellek dahil)."""
    degerler = {}
    try:
        with open("/proc/meminfo", encoding="ascii") as f:
            for satir in f:
                ad, _, kalan = satir.partition(":")
                parca = kalan.split()
                if parca:
                    degerler[ad] = int(parca[0])   # kB
    except (OSError, ValueError):
        return None
    if "MemTotal" not in degerler:
        return None
    bos = degerler.get("MemAvailable", degerler.get("MemFree", 0))
    return degerler["MemTotal"] / 2**20, bos / 2**20


# arecord (alsa-utils) masaüstü dağıtımlarının çoğunda kuruludur.
MIKROFON_PROGRAMLARI = (
    ("arecord", lambda o: ["-q", "-f", "S16_LE", "-r", str(o), "-c", "1", "-t", "raw"]),
    ("parecord", lambda o: ["--raw", "--format=s16le", f"--rate={o}", "--channels=1"]),
    ("rec", lambda o: ["-q", "-t", "raw", "-b", "16", "-e", "signed-integer", "-c", "1",
                       "-r", str(o), "-"]),
)
MIKROFON_YOK = ("Mikrofonu dinleyecek bir program bulunamadı. 'alsa-utils' paketini "
                "(arecord) kurarsan Kodi'yle sesli konuşabilirsin.")


def mikrofon_komutu(ornekleme):
    return _posix.mikrofon_komutu(ornekleme, MIKROFON_PROGRAMLARI)


def editor_dosyasi(backend):
    """<uygulama>/turkod_flutter (backend/ klasörünün bir üstü). AppImage'dan
    çalışıyorsak AppImage dosyasının kendisi (AppRun argümansız ya da dosya
    argümanlarıyla editörü açar)."""
    return _posix.appimage_yolu() or os.path.join(os.path.dirname(backend), "turkod_flutter")


def editoru_ayri_baslat(exe, dosyalar=()):
    """AppImage'da editör AppImage DOSYASIYLA başlatılır: AppImage'ın bağlı klasörü
    (/tmp/.mount_XXXX) onu başlatan süreç bitince kaldırılır; oradaki
    turkod_flutter'ı doğrudan çalıştırmak editörü yarıda bırakırdı."""
    appimage = _posix.appimage_yolu()
    if not appimage:
        return _posix.editoru_ayri_baslat(exe, dosyalar)
    try:
        subprocess.Popen([appimage, *[os.path.abspath(d) for d in dosyalar]],
                         cwd=os.path.dirname(appimage) or None, close_fds=True,
                         start_new_session=True, stdin=subprocess.DEVNULL,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         env=alt_surec_ortami())
        return True
    except OSError:
        return False


def _calistir(komut):
    """Komutu çalıştırır; başarılıysa (çıkış kodu 0) True."""
    try:
        sonuc = subprocess.run(komut, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                               stdin=subprocess.DEVNULL, timeout=20, env=alt_surec_ortami())
    except (OSError, ValueError, subprocess.SubprocessError):
        return False
    return sonuc.returncode == 0


# Araç -> onu getiren paket (hata iletisinde gösterilir).
_ARAC_PAKETI = {
    "update-mime-database": "shared-mime-info",
    "update-desktop-database": "desktop-file-utils",
    "xdg-mime": "xdg-utils",
}


def _veritabanlarini_yenile():
    """Başarısız olan araçların listesi."""
    eksik = []
    if not _calistir(["update-mime-database", _veri_alt("mime")]):
        eksik.append("update-mime-database")
    if not _calistir(["update-desktop-database", _veri_alt("applications")]):
        eksik.append("update-desktop-database")
    return eksik


def _exec_argumani(s):
    """.desktop Exec= satırı için tırnaklı argüman (freedesktop Desktop Entry
    belirtimi): tırnak içinde " ` $ \\ kaçırılır, % → %%; ardından değer
    "string" türü olduğu için ters eğik çizgiler bir kez daha ikilenir."""
    ic = (s.replace("\\", "\\\\").replace('"', '\\"').replace("`", "\\`")
          .replace("$", "\\$").replace("%", "%%"))
    return '"' + ic.replace("\\", "\\\\") + '"'


def _iliski_etkin_mi():
    y = _yollar()
    try:
        with open(y["masaustu"], encoding="utf-8") as f:
            icerik = f.read()
    except OSError:
        return False
    return os.path.isfile(y["mime"]) and _exec_argumani(y["backend"]) in icerik


def dosya_iliskisi_kur():
    y = _yollar()
    os.makedirs(os.path.dirname(y["mime"]), exist_ok=True)
    os.makedirs(os.path.dirname(y["masaustu"]), exist_ok=True)
    with open(y["mime"], "w", encoding="utf-8", newline="\n") as f:
        f.write(_MIME_XML)
    with open(y["masaustu"], "w", encoding="utf-8", newline="\n") as f:
        f.write("[Desktop Entry]\n"
                "Type=Application\n"
                "Name=TürKod ile çalıştır\n"
                "Comment=TürKod programını çalıştırır\n"
                f"Exec={_exec_argumani(y['backend'])} --terminal %f\n"
                f"MimeType={MIME_TURU};\n"
                "NoDisplay=true\n"
                "Terminal=false\n")
    eksik = _veritabanlarini_yenile()
    if not _calistir(["xdg-mime", "default", MASAUSTU_DOSYASI, MIME_TURU]):
        eksik.append("xdg-mime")
    if eksik:
        paketler = ", ".join(f"'{_ARAC_PAKETI[a]}'" for a in eksik)
        ek = "paketi" if len(eksik) == 1 else "paketleri"
        raise PlatformHatasi(
            ".trpy dosyaları TürKod'la ilişkilendirilemedi: bunun için bilgisayarda "
            f"{paketler} {ek} kurulu olmalı. Kurup yeniden dene.")


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
    _, sistem_path = _posix.path_durumu()
    # Kullanıcı bağlantısı ancak ~/.local/bin kabuğun PATH'indeyse "açık" sayılır.
    kullanici_path = _posix.kullanici_path_etkin()
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
