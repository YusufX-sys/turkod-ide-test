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


COP_KUTUSU_ADI = "Çöp Kutusu"


def cop_kutusu_klasoru():
    return os.path.join(os.path.expanduser("~"), ".Trash")


def cop_kutusu_var_mi(yol):
    return _posix.ayni_disk_mi(yol, cop_kutusu_klasoru())


def cop_kutusuna_tasi(yol):
    """Öğeyi ~/.Trash'e taşır (aynı adda öğe varsa "ad 2" ...)."""
    kok = cop_kutusu_klasoru()
    os.makedirs(kok, exist_ok=True)
    mutlak = os.path.abspath(yol)
    ad = _posix.benzersiz_ad(kok, os.path.basename(mutlak.rstrip("/")) or "adsiz")
    os.rename(mutlak, os.path.join(kok, ad))


def bellek_gb():
    """(toplam, kullanılabilir) GB. macOS'ta os.sysconf("SC_AVPHYS_PAGES") yoktur:
    toplam sysctl hw.memsize'dan, kullanılabilir vm_stat'tan (boş + etkin olmayan
    + temizlenebilir sayfalar) okunur."""
    try:
        toplam = int(subprocess.run(["sysctl", "-n", "hw.memsize"], capture_output=True,
                                    text=True, timeout=5).stdout.strip())
    except (OSError, ValueError, subprocess.SubprocessError):
        return None
    bos = 0.0
    try:
        cikti = subprocess.run(["vm_stat"], capture_output=True, text=True, timeout=5).stdout
        import re
        sayfa = int((re.search(r"page size of (\d+)", cikti) or [0, 4096])[1])
        sayilar = {m.group(1): int(m.group(2))
                   for m in re.finditer(r"^Pages ([a-z ]+):\s+(\d+)", cikti, re.M)}
        bos = sum(sayilar.get(k, 0) for k in ("free", "inactive", "purgeable",
                                               "speculative")) * sayfa
    except (OSError, ValueError, subprocess.SubprocessError):
        pass
    return toplam / 2**30, bos / 2**30


# macOS'ta hazır bir komut satırı kayıt programı yoktur; SoX (`brew install sox`)
# kuruluysa kullanılır.
MIKROFON_PROGRAMLARI = (
    ("rec", lambda o: ["-q", "-t", "raw", "-b", "16", "-e", "signed-integer", "-c", "1",
                       "-r", str(o), "-"]),
    ("sox", lambda o: ["-q", "-d", "-t", "raw", "-b", "16", "-e", "signed-integer", "-c", "1",
                       "-r", str(o), "-"]),
)
MIKROFON_YOK = ("macOS'ta mikrofonu dinlemek için SoX gerekiyor. Terminalde "
                "'brew install sox' ile kurarsan Kodi'yle sesli konuşabilirsin.")


def mikrofon_komutu(ornekleme):
    return _posix.mikrofon_komutu(ornekleme, MIKROFON_PROGRAMLARI)


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
