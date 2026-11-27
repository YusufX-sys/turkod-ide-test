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
    alt_surec_ortami(env)      dış program için ortam (paketin LD_LIBRARY_PATH'i geri alınır)
    path_tamamla()             açılışta PATH'e eksik klasörleri ekler (macOS: Homebrew)
    yazi_tipi_aileleri()       sistemdeki yazı tipi aileleri (Windows: None)
    son_terminal_hatasi()      terminalde_ac False dönünce nedeni (Türkçe) ya da None
"""
import os
import sys

from . import linux, macos, windows
from ._ortak import PlatformHatasi  # noqa: F401  (dışarıya açık)
from ._ortak import alt_surec_ortami  # noqa: F401  (dışarıya açık)
from ._ortak import eksik_path_klasorleri, path_ekleri_uygula


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
    """True: terminal açıldı. False: açılamadı; nedeni son_terminal_hatasi()'nda."""
    return secili().terminalde_ac(komut, cwd)


def son_terminal_hatasi():
    """Son terminalde_ac False döndüyse kullanıcıya gösterilecek Türkçe neden
    (ör. "Terminal programı bulunamadı ..." ya da macOS'ta Otomasyon izni) ya da None.
    terminalde_ac hata fırlatmaz: çağıranlardan biri (`turkod --kabuk-pencere`)
    hatayı yakalamıyor."""
    return getattr(secili(), "son_terminal_hatasi", lambda: None)()


def path_tamamla():
    """Sunucunun açılışında çağrılır: bu sürecin PATH'inde olmayan beklenen
    klasörleri (macOS: /opt/homebrew/bin, /opt/homebrew/sbin, /usr/local/bin;
    Linux/macOS: ~/.local/bin) PATH'in SONUNA ekler. Windows'ta bir şey yapmaz.
    Yeni PATH'i döndürür."""
    yeni = path_ekleri_uygula(os.environ.get("PATH", ""), eksik_path_klasorleri())
    if yeni != os.environ.get("PATH", ""):
        os.environ["PATH"] = yeni
    return yeni


def yazi_tipi_aileleri():
    """Sistemdeki yazı tipi ailelerinin sıralı listesi ya da None (bilinmiyor;
    Windows'ta çağıran kendi yolunu kullanır). macOS'ta Tk bu süreçte AÇILMAZ."""
    return secili().yazi_tipi_aileleri()


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
def cop_kutusu_adi():
    """"Geri Dönüşüm Kutusu" (Windows), "Çöp Kutusu" (macOS), "Çöp" (Linux)."""
    return secili().COP_KUTUSU_ADI


def cop_kutusu_var_mi(yol):
    """Linux/macOS: öğe çöp kutusuyla aynı diskte mi (Windows: ide_core kendi bakar)."""
    return secili().cop_kutusu_var_mi(yol)


def cop_kutusuna_tasi(yol):
    """Linux/macOS: öğeyi çöp kutusuna taşır; hata olursa OSError."""
    return secili().cop_kutusuna_tasi(yol)


def bellek_gb():
    """(toplam, kullanılabilir) GB ya da None (Windows: yerel_modeller kendi ölçer)."""
    return secili().bellek_gb()


def mikrofon_komutu(ornekleme):
    """Linux/macOS: 16 bit tek kanal ham ses akıtan kayıt komutu ya da None."""
    return secili().mikrofon_komutu(ornekleme)


def mikrofon_yok_mesaji():
    return getattr(secili(), "MIKROFON_YOK", "Bu sistemde mikrofon desteklenmiyor.")


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
