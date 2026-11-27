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


# --------------------------------------------------------------------------
# Dış programların ortamı ve PATH
# --------------------------------------------------------------------------
def sistem_adi():
    """"windows" | "linux" | "macos": sys.platform'a ÇAĞRILDIĞI ANDA bakar."""
    p = sys.platform
    if p in ("win32", "cygwin"):
        return "windows"
    if p == "darwin":
        return "macos"
    return "linux"


# macOS'ta Finder / Dock'tan açılan uygulamanın PATH'i yalnızca
# /usr/bin:/bin:/usr/sbin:/sbin olur: Homebrew araçları (sox, rec, brew, git,
# node) bulunamaz. Bu klasörler (yoksa) PATH'in SONUNA eklenir.
MACOS_PATH_EKLERI = ("/opt/homebrew/bin", "/opt/homebrew/sbin", "/usr/local/bin")


def eksik_path_klasorleri(ad=None):
    """Bu sistemde PATH'te bulunması beklenen ek klasörler (sırasıyla)."""
    ad = ad or sistem_adi()
    if ad == "windows":
        return ()
    yerel_bin = os.path.join(os.path.expanduser("~"), ".local", "bin")
    if ad == "macos":
        return (*MACOS_PATH_EKLERI, yerel_bin)
    return (yerel_bin,)


def path_ekleri_uygula(path, klasorler):
    """PATH metninin sonuna, içinde olmayan klasörleri ekler (sıra korunur)."""
    parcalar = [p for p in (path or "").split(os.pathsep) if p]
    for k in klasorler:
        if k not in parcalar:
            parcalar.append(k)
    return os.pathsep.join(parcalar)


# PyInstaller önyükleyicisi paketli uygulamada bu değişkenleri kendi _internal
# klasörüne ayarlar, eski değeri <AD>_ORIG'de saklar. Dış programlar (terminal,
# Flutter editörü, ses/mikrofon araçları, kullanıcının Python'u) bu ayarla
# açılırsa paketteki kütüphaneleri yükleyip çökebilir.
_KUTUPHANE_DEGISKENLERI = {
    "linux": ("LD_LIBRARY_PATH",),
    "macos": ("DYLD_LIBRARY_PATH", "DYLD_FRAMEWORK_PATH"),
}


def _paketin_icinde_mi(yol, kokler):
    try:
        yol = os.path.realpath(yol)
    except (OSError, ValueError):
        return False
    return any(yol == k or yol.startswith(k.rstrip(os.sep) + os.sep) for k in kokler)


def alt_surec_ortami(env=None):
    """Dış program başlatırken kullanılacak ortam (dict).

    env verilmezse os.environ'un kopyası alınır. Windows'ta env olduğu gibi döner.
    Linux/macOS paketli uygulamada: LD_LIBRARY_PATH (macOS'ta DYLD_LIBRARY_PATH /
    DYLD_FRAMEWORK_PATH) <AD>_ORIG varsa ona geri konur; yoksa paketin klasörünü
    gösteren parçaları atılır (hepsi paketinse değişken silinir). Böylece işlev
    ikinci kez uygulansa da kullanıcının kendi ayarını silmez. macOS'ta ayrıca
    Homebrew klasörleri PATH'e eklenir ve paketin içine __pycache__ yazılmasın
    diye PYTHONDONTWRITEBYTECODE=1 konur (imzalı .app'in içi değişmemeli)."""
    ad = sistem_adi()
    if ad == "windows":
        return dict(os.environ) if env is None else env
    ortam = dict(os.environ if env is None else env)
    if paketli_mi():
        kokler = []
        for k in (kaynak_dizini(), backend_dizini()):
            try:
                kokler.append(os.path.realpath(k))
            except (OSError, ValueError):
                pass
        for degisken in _KUTUPHANE_DEGISKENLERI.get(ad, ()):
            eski = ortam.pop(degisken + "_ORIG", None)
            if eski:
                ortam[degisken] = eski
                continue
            kalan = [p for p in ortam.get(degisken, "").split(os.pathsep)
                     if p and not _paketin_icinde_mi(p, kokler)]
            if kalan:
                ortam[degisken] = os.pathsep.join(kalan)
            else:
                ortam.pop(degisken, None)
        if ad == "macos":
            ortam.setdefault("PYTHONDONTWRITEBYTECODE", "1")
    if ad == "macos":
        ortam["PATH"] = path_ekleri_uygula(ortam.get("PATH", ""), MACOS_PATH_EKLERI)
    return ortam
