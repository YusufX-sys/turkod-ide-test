"""PyInstaller ve normal Python icin yol yardimcilari."""
import os
import sys
import tempfile
from pathlib import Path

try:
    from . import platform_katmani
except ImportError:
    import platform_katmani


def kaynak_kok() -> str:
    """Kaynak dosyalarin kok dizinini bulur."""
    if getattr(sys, "frozen", False):
        return sys._MEIPASS

    return str(Path(__file__).resolve().parents[1])


def kaynak_yolu(dosya_adi: str = "") -> str:
    """Paket icindeki kaynak dosyalar icin yol uretir."""
    base = kaynak_kok()

    if dosya_adi:
        return os.path.join(base, dosya_adi)

    return base


def kullanici_eki() -> str:
    """Linux/macOS'ta paylaşılan /tmp'deki adlar kullanıcıya özel olsun diye
    "-<uid>" eki (başka kullanıcı aynı adla klasör/bağlantı hazırlayamasın).
    Windows'ta %TEMP% zaten kullanıcıya özeldir: ek yok."""
    if platform_katmani.windows_mu() or not hasattr(os, "getuid"):
        return ""
    return f"-{os.getuid()}"


def gecici_klasor_adi() -> str:
    return "TurKod" + kullanici_eki()


def port_dosyasi_adi() -> str:
    return "turkod_backend_port" + kullanici_eki()


def port_dosyasi_yolu() -> str:
    """Sunucunun portunu yazdığı dosya (arayüz bağlanırken okur; bkz.
    turkod_flutter/lib/main.dart AppConfig.portDosyasi). Windows'ta
    %TEMP%\\turkod_backend_port (kullanıcıya özel). Linux/macOS'ta paylaşılan
    /tmp yerine kullanıcının veri klasöründe "backend_port": başka bir
    kullanıcı sahte bir port yazıp arayüzü kendi sunucusuna yönlendiremesin.
    Arayüz kullanıcı kimliğini (uid) bilmediği için /tmp'de uid ekli ad
    kullanılamazdı."""
    if platform_katmani.windows_mu():
        return os.path.join(tempfile.gettempdir(), "turkod_backend_port")
    klasor = platform_katmani.veri_klasoru()
    try:
        os.makedirs(klasor, exist_ok=True)
    except OSError:
        pass
    return os.path.join(klasor, "backend_port")


def calisma_yolu(dosya_adi: str = "") -> str:
    """Yazilabilir calisma zamani dosyalari icin yol uretir."""
    if getattr(sys, "frozen", False):
        base = platform_katmani.veri_klasoru()
    else:
        # Geliştirme ortamında kaynak kodu proje köküne yazmak yerine,
        # kullanıcıya ait tek bir yazılabilir klasör kullanmak daha güvenlidir.
        base = os.path.join(os.path.expanduser("~"), ".turkod")

    # Klasör oluşturulamazsa (aynı adlı bir dosya var, izin yok, veri klasörü
    # bozuk) eskiden dictionary.py içe aktarılırken backend çöküyor, program
    # hiç açılmıyordu. Geçici klasöre düşülür; o da olmazsa kullanılabilir
    # olmasa da bir yol döndürülür (yazma noktaları zaten hataları yakalıyor).
    for aday in (base, os.path.join(tempfile.gettempdir(), gecici_klasor_adi())):
        try:
            os.makedirs(aday, exist_ok=True)
            base = aday
            break
        except OSError:
            continue

    if dosya_adi:
        return os.path.join(base, dosya_adi)

    return base
