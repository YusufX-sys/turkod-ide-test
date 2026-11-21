"""Platform uygulamalarının paylaştığı küçük yardımcılar."""
import os
import sys


class PlatformHatasi(RuntimeError):
    """Bu sistemde yapılamayan ya da başarısız olan platform işi."""


def paketli_mi():
    return bool(getattr(sys, "frozen", False))


def backend_dizini():
    """Paketli uygulamada turkod_backend(.exe)'nin bulunduğu klasör."""
    return os.path.dirname(os.path.abspath(sys.executable))


def kaynak_dizini():
    """PyInstaller veri klasörü (_internal) ya da turkod_ide/ klasörü."""
    if paketli_mi():
        return getattr(sys, "_MEIPASS", os.path.join(backend_dizini(), "_internal"))
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def gomulu_python_dizini():
    """Paketli uygulamada kullanıcı programlarını çalıştıran Python'un klasörü:
    <backend>/_internal/python_embed (Windows: robocopy ile kopyalanan Python,
    Linux/macOS: python-build-standalone)."""
    return os.path.join(backend_dizini(), "_internal", "python_embed")


def ayni_yol(a, b):
    return os.path.normcase(a.strip().rstrip("\\/")) == os.path.normcase(b.strip().rstrip("\\/"))
