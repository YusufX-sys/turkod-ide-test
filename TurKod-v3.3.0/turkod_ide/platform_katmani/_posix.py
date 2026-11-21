"""Linux ve macOS'un paylaştığı POSIX uygulaması (yalnızca standart kütüphane)."""
import os
import shutil
import signal
import subprocess
import threading
import time

from ._ortak import PlatformHatasi, backend_dizini, paketli_mi

SIGKILL = getattr(signal, "SIGKILL", 9)   # Windows'ta (testlerde) tanımlı değil


# --------------------------------------------------------------------------
# Süreçler
# --------------------------------------------------------------------------
def gizli_surec_ayarlari():
    """Alt süreç kendi süreç grubunda başlasın: sureci_agacla_oldur onu
    alt süreçleriyle birlikte os.killpg ile kapatabilsin."""
    return {"start_new_session": True}


def _cocuklar(pid, zaman_asimi=5):
    """pid'in doğrudan alt süreçleri. Linux'ta /proc, diğerlerinde pgrep -P."""
    gorev = f"/proc/{pid}/task"
    if os.path.isdir(gorev):
        sonuc = []
        try:
            for tid in os.listdir(gorev):
                try:
                    with open(os.path.join(gorev, tid, "children"), encoding="ascii") as f:
                        sonuc += [int(x) for x in f.read().split()]
                except OSError:
                    pass
            return sonuc
        except OSError:
            pass
    try:
        cikti = subprocess.run(["pgrep", "-P", str(pid)], capture_output=True, text=True,
                               timeout=zaman_asimi).stdout
    except (OSError, subprocess.SubprocessError):
        return []
    return [int(x) for x in cikti.split() if x.isdigit()]


def _torunlar(pid, zaman_asimi=5):
    """pid'in tüm alt süreçleri (çocuklar, torunlar ...)."""
    sonuc, gorulen, sira = [], {pid}, [pid]
    while sira:
        for c in _cocuklar(sira.pop(), zaman_asimi):
            if c not in gorulen:
                gorulen.add(c)
                sonuc.append(c)
                sira.append(c)
    return sonuc


def _oldur(pid):
    """SIGKILL; süreç kendi grubunun lideriyse (start_new_session) grubu kapatır."""
    try:
        if os.getpgid(pid) == pid and pid != os.getpgrp():
            os.killpg(pid, SIGKILL)
            return
    except OSError:
        pass
    try:
        os.kill(pid, SIGKILL)
    except OSError:
        pass


def sureci_agacla_oldur(pid, zaman_asimi=5, sessiz=True):
    """Süreci ve tüm alt süreçlerini SIGKILL ile kapatır."""
    try:
        torunlar = _torunlar(pid, zaman_asimi)
        if pid != os.getpid():
            _oldur(pid)
        for t in torunlar:
            _oldur(t)
    except Exception:  # noqa: BLE001
        if not sessiz:
            raise


def kendi_agacimi_oldur():
    """Alt süreçleri kapatır (bu süreç ardından os._exit ile çıkar)."""
    sureci_agacla_oldur(os.getpid(), zaman_asimi=5, sessiz=True)


def surec_yasiyor(pid):
    try:
        os.kill(pid, 0)
        return True
    except PermissionError:
        return True   # süreç var ama başka kullanıcıya ait
    except OSError:
        return False


def ebeveyni_izle(pid, bitince, aralik=1.0):
    """pid'li süreç bitince bitince()'yi çağırır (saniyede bir yoklanır)."""
    if pid <= 0:
        return
    if not surec_yasiyor(pid):
        bitince()
        return

    def izle():
        while surec_yasiyor(pid):
            time.sleep(aralik)
        bitince()

    threading.Thread(target=izle, daemon=True, name="ebeveyn-izleyici").start()


def editoru_ayri_baslat(exe, dosyalar=()):
    """Editör bu sürecin alt süreci olarak kalmasın (ayrı oturum)."""
    try:
        subprocess.Popen([exe, *dosyalar], cwd=os.path.dirname(exe) or None, close_fds=True,
                         start_new_session=True, stdin=subprocess.DEVNULL,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except OSError:
        return False


def ekrani_temizle():
    os.system("clear")


# --------------------------------------------------------------------------
# Kullanıcı programlarını çalıştıran Python (python-build-standalone düzeni)
# --------------------------------------------------------------------------
GOMULU_PYTHON_GORELI = "_internal/python_embed/bin/python3"


def gomulu_python(dizin):
    return os.path.join(dizin, "bin", "python3")


def gomulu_python_yol_dizini(dizin):
    """PATH'e eklenecek klasör (python3 ve pip3 burada)."""
    return os.path.join(dizin, "bin")


def sistem_python():
    return shutil.which("python3") or shutil.which("python")


def kabuk_kod_sayfasi():
    return "utf-8"


def gizli_veri(veri, coz):
    """Kullanıcıya bağlı şifreleme bu sistemde yok: anahtarlar düz kalır."""
    return None


# --------------------------------------------------------------------------
# Kodi'nin sesi: dışarıdaki bir konuşma komutuyla
# --------------------------------------------------------------------------
def sesli_oku(komut, dur=None):
    """Konuşma komutunu çalıştırır; bitene ya da dur olayı gelene dek bekler."""
    try:
        surec = subprocess.Popen(komut, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                 stderr=subprocess.DEVNULL)
    except OSError as e:
        raise PlatformHatasi(f"Konuşma sesi başlatılamadı: {e}") from e
    while surec.poll() is None:
        if dur is not None and dur.is_set():
            surec.terminate()
            try:
                surec.wait(timeout=2)
            except subprocess.TimeoutExpired:
                surec.kill()
            return
        time.sleep(0.05)
    if surec.returncode not in (0, None):
        raise PlatformHatasi("Bu bilgisayarın konuşma sesi kullanılamadı.")


# --------------------------------------------------------------------------
# PATH'teki `turkod` komutu: ~/.local/bin/turkod bağlantısı
# --------------------------------------------------------------------------
KOMUT_ADI = "turkod"


def kullanici_bin_dizini():
    return os.path.join(os.path.expanduser("~"), ".local", "bin")


def turkod_komutu_hedefi():
    """Kurulum klasöründeki `turkod` (yoksa `turkod_backend`) çalıştırılabilir dosyası."""
    dizin = backend_dizini()
    for ad in (KOMUT_ADI, "turkod_backend"):
        yol = os.path.join(dizin, ad)
        if os.path.isfile(yol):
            return yol
    return os.path.join(dizin, "turkod_backend")


def appimage_yolu():
    """AppImage içinden çalışıyorsak AppImage DOSYASININ yolu, değilse None.

    AppImage her açılışta rastgele bir klasöre (/tmp/.mount_XXXX) bağlanır: oradaki
    dosyalara bağlantı kurmak bir sonraki açılışta bozulur. Kalıcı olan, AppImage
    çalışma ortamının $APPIMAGE ile bildirdiği dosyanın kendisidir."""
    yol = os.environ.get("APPIMAGE")
    return yol if yol and os.path.isfile(yol) else None


# AppImage'da `turkod` komutu bağlantı değil, AppImage'ı çağıran küçük bir betiktir.
SARMALAYICI_IZI = "# TurKod komut sarmalayicisi"


def _sarmalayici_metni(appimage):
    return ("#!/bin/sh\n"
            f"{SARMALAYICI_IZI}\n"
            f'exec "{appimage}" --turkod "$@"\n')


def _sarmalayici_mi(yol):
    try:
        if os.path.islink(yol) or not os.path.isfile(yol):
            return False
        with open(yol, encoding="utf-8", errors="replace") as f:
            return SARMALAYICI_IZI in f.read(4096)
    except OSError:
        return False


def _baglanti_bizim_mi(baglanti):
    if _sarmalayici_mi(baglanti):
        return True
    try:
        return (os.path.islink(baglanti)
                and os.path.dirname(os.path.realpath(baglanti))
                == os.path.realpath(backend_dizini()))
    except OSError:
        return False


def path_durumu():
    """(kullanıcıda, sistemde): ~/.local/bin ya da /usr/local/bin, /usr/bin'deki bağlantı."""
    kullanici = _baglanti_bizim_mi(os.path.join(kullanici_bin_dizini(), KOMUT_ADI))
    sistem = any(_baglanti_bizim_mi(os.path.join(d, KOMUT_ADI))
                 for d in ("/usr/local/bin", "/usr/bin"))
    return kullanici, sistem


def path_e_ekle():
    dizin = kullanici_bin_dizini()
    os.makedirs(dizin, exist_ok=True)
    baglanti = os.path.join(dizin, KOMUT_ADI)
    appimage = appimage_yolu()
    if os.path.lexists(baglanti):
        if _sarmalayici_mi(baglanti):
            os.remove(baglanti)   # AppImage taşınmış olabilir: yeniden yazılır
        elif _baglanti_bizim_mi(baglanti) and not appimage:
            return
        elif not os.path.islink(baglanti):
            raise PlatformHatasi(f"{baglanti} zaten var ve TürKod'a ait değil; değiştirilmedi.")
        else:
            os.remove(baglanti)   # eski bir kurulumu gösteren bağlantı
    if appimage:
        with open(baglanti, "w", encoding="utf-8") as f:
            f.write(_sarmalayici_metni(appimage))
        os.chmod(baglanti, 0o755)
    else:
        os.symlink(turkod_komutu_hedefi(), baglanti)


def path_ten_cikar():
    baglanti = os.path.join(kullanici_bin_dizini(), KOMUT_ADI)
    if _baglanti_bizim_mi(baglanti):
        os.remove(baglanti)


def entegrasyon_destegi_yok():
    if not paketli_mi():
        return {
            "destekleniyor": False,
            "neden": "Bu ayarlar yalnızca kurulmuş TürKod'da kullanılabilir.",
        }
    return None


def ilk_bulunan(adaylar):
    """[(komut, önek_argümanlar), ...] içinden PATH'te bulunan ilk komut."""
    for ad, onek in adaylar:
        yol = shutil.which(ad)
        if yol:
            return [yol, *onek]
    return None
