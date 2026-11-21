"""İşletim sistemine bağlı işlerin tek kapısı (Windows, Linux, macOS).

TürKod'un geri kalanı `os.name` / `sys.platform` / `taskkill` / `winreg`
kullanmaz; bu paketteki işlevleri çağırır. Her işlev, çağrıldığı anda
`sys.platform`'a bakarak doğru uygulamayı seçer (testlerde sys.platform
taklit edilerek Linux/macOS yolları da denenebilir).

Paketin adı bilerek `platform` değildir: turkod_ide/ klasörü sys.path'e
girdiğinde (ör. yerel_sunucu.py doğrudan çalıştırılınca) Python'un standart
`platform` modülünü gölgelerdi.

Bu pakete BAĞLANAMAYAN dosyalar: runner.py (kullanıcı programının içinde
çalışan şablon), exe_terminali.py (EXE'nin içine konur) ve yerel_sunucu.py
(ayrı Python süreciyle çalışır). Onlar kendi küçük denetimlerini tutar.

Ortak arayüz:
    AD                         "windows" | "linux" | "macos" (içe aktarıldığı an)
    secili()                   o anki sisteme ait modül
    windows_mu() / macos_mu() / linux_mu()
    veri_tabani(yedek)         %LOCALAPPDATA% / ~/.local/share / ~/Library/Application Support
    veri_klasoru(yedek)        <veri_tabani>/TurKod
    gizli_surec_ayarlari()     Popen için ek ayarlar (konsol penceresi açma, ayrı süreç grubu)
    sureci_agacla_oldur(pid)   süreci alt süreçleriyle birlikte zorla kapatır
    kendi_agacimi_oldur()      bu sürecin alt süreçlerini (ve Windows'ta kendisini) kapatır
    surec_yasiyor(pid)
    ebeveyni_izle(pid, bitince)
    terminalde_ac(komut, cwd)  komutu yeni bir terminal penceresinde başlatır
    editoru_ayri_baslat(exe, dosyalar)
    ekrani_temizle()
    konus(metin, dur)          metni sesli okur (bitene ya da dur gelene dek bekler)
    gizli_veri(veri, coz)      kullanıcıya bağlı şifreleme (Windows DPAPI), yoksa None
    kabuk_kod_sayfasi()
    entegrasyon_durumu()       PATH'teki `turkod` komutu ve .trpy ilişkisi
    path_e_ekle() / path_ten_cikar()
    dosya_iliskisi_kur() / dosya_iliskisi_kaldir()
    kullanici_python_bul()     kullanıcı programlarını çalıştıran Python (gömülü / PATH)
    gomulu_python_yol_dizini() IDE terminali için PATH'e konan klasör
"""
import sys

from . import linux, macos, windows
from ._ortak import PlatformHatasi  # noqa: F401  (dışarıya açık)


def _ad(platform_adi=None):
    p = platform_adi if platform_adi is not None else sys.platform
    if p == "win32" or p == "cygwin":
        return "windows"
    if p == "darwin":
        return "macos"
    return "linux"   # linux ve diğer POSIX sistemler (freebsd ...)


AD = _ad()

_MODULLER = {"windows": windows, "linux": linux, "macos": macos}


def secili():
    """Şu anki sys.platform'a ait uygulama modülü."""
    return _MODULLER[_ad()]


def windows_mu():
    return _ad() == "windows"


def macos_mu():
    return _ad() == "macos"


def linux_mu():
    return _ad() == "linux"


# --------------------------------------------------------------------------
# Ortak arayüz: her çağrı o anki sisteme yönlendirilir.
# --------------------------------------------------------------------------
def veri_tabani(yedek=None):
    return secili().veri_tabani(yedek)


def veri_klasoru(yedek=None):
    import os
    return os.path.join(veri_tabani(yedek), "TurKod")


def gizli_surec_ayarlari():
    return secili().gizli_surec_ayarlari()


def sureci_agacla_oldur(pid, zaman_asimi=5, sessiz=True):
    return secili().sureci_agacla_oldur(pid, zaman_asimi=zaman_asimi, sessiz=sessiz)


def kendi_agacimi_oldur():
    return secili().kendi_agacimi_oldur()


def surec_yasiyor(pid):
    return secili().surec_yasiyor(pid)


def ebeveyni_izle(pid, bitince):
    return secili().ebeveyni_izle(pid, bitince)


def terminalde_ac(komut, cwd=None):
    return secili().terminalde_ac(komut, cwd)


def editoru_ayri_baslat(exe, dosyalar=()):
    return secili().editoru_ayri_baslat(exe, dosyalar)


def ekrani_temizle():
    return secili().ekrani_temizle()


def konus(metin, dur=None):
    return secili().konus(metin, dur)


def gizli_veri(veri, coz):
    return secili().gizli_veri(veri, coz)


def kabuk_kod_sayfasi():
    return secili().kabuk_kod_sayfasi()


def entegrasyon_durumu():
    return secili().entegrasyon_durumu()


def path_e_ekle():
    return secili().path_e_ekle()


def path_ten_cikar():
    return secili().path_ten_cikar()


def dosya_iliskisi_kur():
    return secili().dosya_iliskisi_kur()


def dosya_iliskisi_kaldir():
    return secili().dosya_iliskisi_kaldir()


# --------------------------------------------------------------------------
# Kullanıcı programlarını çalıştıran Python
# --------------------------------------------------------------------------
def turkod_komutu_dosyasi():
    """Paketli uygulamada `turkod` komutunun (konsollu giriş) dosyası:
    Windows'ta <backend>\\turkod.exe, Linux/macOS'ta <backend>/turkod."""
    import os
    from ._ortak import backend_dizini
    return os.path.join(backend_dizini(), "turkod.exe" if windows_mu() else "turkod")


def editor_dosyasi():
    """Paketli uygulamada TürKod editörünün (Flutter) çalıştırılabilir dosyası."""
    from ._ortak import backend_dizini
    return secili().editor_dosyasi(backend_dizini())


def gomulu_python_dizini():
    """<backend>/_internal/python_embed (paketli uygulamada)."""
    from ._ortak import gomulu_python_dizini as _dizin
    return _dizin()


def gomulu_python_goreli():
    """Hata mesajlarında gösterilen göreli yol (ör. _internal/python_embed/python.exe)."""
    return secili().GOMULU_PYTHON_GORELI


def gomulu_python_yol_dizini():
    """IDE terminalinde `python` / `pip` bulunsun diye PATH'in başına konan klasör."""
    return secili().gomulu_python_yol_dizini(gomulu_python_dizini())


def kullanici_python_bul():
    """Kullanıcı programlarını çalıştıracak Python ya da None.

    Paketli uygulamada önce gömülü Python (python_embed); yoksa PATH'teki Python
    (Windows: python.exe/python, Linux/macOS: python3/python); geliştirici
    kipinde o da yoksa bu sürecin Python'u. pythonw.exe, python.exe'ye çevrilir
    (çıktısı görünsün)."""
    import os
    paketli = bool(getattr(sys, "frozen", False))
    python = None
    if paketli:
        aday = secili().gomulu_python(gomulu_python_dizini())
        if os.path.exists(aday):
            python = aday
    if not python:
        python = secili().sistem_python()
    if not python and not paketli:
        python = sys.executable
    if python and python.lower().endswith("pythonw.exe"):
        python = python[:-len("pythonw.exe")] + "python.exe"
    return python
