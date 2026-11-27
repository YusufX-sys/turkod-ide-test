"""Linux ve macOS'un paylaştığı POSIX uygulaması (yalnızca standart kütüphane)."""
import os
import shlex
import shutil
import signal
import subprocess
import sys
import threading
import time

from ._ortak import PlatformHatasi, alt_surec_ortami, backend_dizini, paketli_mi

SIGKILL = getattr(signal, "SIGKILL", 9)   # Windows'ta (testlerde) tanımlı değil


# --------------------------------------------------------------------------
# Süreçler
# --------------------------------------------------------------------------
def gizli_surec_ayarlari():
    """Alt süreç kendi süreç grubunda başlasın: sureci_agacla_oldur onu
    alt süreçleriyle birlikte os.killpg ile kapatabilsin."""
    return {"start_new_session": True}


def _cocuklar(pid, zaman_asimi=5):
    """pid'in doğrudan alt süreçleri. Linux'ta /proc/<pid>/task/*/children; bu
    dosyalar yoksa (çekirdek CONFIG_PROC_CHILDREN olmadan derlenmiş) ya da macOS'ta
    pgrep -P."""
    gorev = f"/proc/{pid}/task"
    if os.path.isdir(gorev):
        sonuc, okundu = [], False
        try:
            for tid in os.listdir(gorev):
                try:
                    with open(os.path.join(gorev, tid, "children"), encoding="ascii") as f:
                        sonuc += [int(x) for x in f.read().split()]
                    okundu = True
                except (OSError, ValueError):
                    pass
        except OSError:
            pass
        if okundu:
            return sonuc
    try:
        cikti = subprocess.run(["pgrep", "-P", str(pid)], capture_output=True, text=True,
                               timeout=zaman_asimi, env=alt_surec_ortami()).stdout
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
    """pid'li süreç bitince bitince()'yi çağırır (saniyede bir yoklanır).

    pid bu sürecin ebeveyniyse os.getppid()'nin değişmesi de "bitti" sayılır:
    ebeveyn ölünce süreç init'e (ya da bir alt-süreç toplayıcısına) geçer; pid
    numarası bu arada başka bir sürece verilmiş olsa bile kapanış kaçmaz."""
    if pid <= 0:
        return
    if not surec_yasiyor(pid):
        bitince()
        return
    try:
        ilk_ebeveyn = os.getppid()
    except (AttributeError, OSError):
        ilk_ebeveyn = None
    ebeveynim = ilk_ebeveyn == pid

    def ebeveyn_degisti():
        if not ebeveynim:
            return False
        try:
            return os.getppid() != ilk_ebeveyn
        except OSError:
            return False

    def izle():
        while surec_yasiyor(pid) and not ebeveyn_degisti():
            time.sleep(aralik)
        bitince()

    threading.Thread(target=izle, daemon=True, name="ebeveyn-izleyici").start()


def editoru_ayri_baslat(exe, dosyalar=()):
    """Editör bu sürecin alt süreci olarak kalmasın (ayrı oturum)."""
    try:
        subprocess.Popen([exe, *dosyalar], cwd=os.path.dirname(exe) or None, close_fds=True,
                         start_new_session=True, stdin=subprocess.DEVNULL,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         env=alt_surec_ortami())
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


# --------------------------------------------------------------------------
# Çöp kutusu (Gezgin'de "sil")
# --------------------------------------------------------------------------
def ayni_disk_mi(yol, klasor):
    """yol ile klasör aynı dosya sisteminde mi? Değilse taşımak kopyalamak demektir
    (USB bellek, ağ klasörü): o zaman çöp kutusu yok sayılır, kalıcı silme sorulur."""
    try:
        os.makedirs(klasor, exist_ok=True)
        return os.stat(os.path.abspath(yol)).st_dev == os.stat(klasor).st_dev
    except OSError:
        return False


def benzersiz_ad(klasor, ad):
    """klasor içinde boş bir ad: "ad", "ad 2", "ad 3" ... (uzantı korunur)."""
    kok, uzanti = os.path.splitext(ad)
    aday, n = ad, 1
    while os.path.lexists(os.path.join(klasor, aday)):
        n += 1
        aday = f"{kok} {n}{uzanti}"
    return aday


# --------------------------------------------------------------------------
# Mikrofon (Kodi ile sesli konuşma): dış kayıt programı ham ses akıtır
# --------------------------------------------------------------------------
def mikrofon_komutu(ornekleme, adaylar):
    """[(program, argümanlar(ornekleme))] içinden PATH'te bulunan ilk kayıt komutu
    (16 bit, tek kanal, ham PCM'i stdout'a yazar) ya da None."""
    for ad, argumanlar in adaylar:
        yol = shutil.which(ad)
        if yol:
            return [yol, *argumanlar(ornekleme)]
    return None


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
                                 stderr=subprocess.DEVNULL, env=alt_surec_ortami())
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
    # shlex.quote: yolda $, `, " ya da \ olsa da kabuk onu olduğu gibi alır.
    return ("#!/bin/sh\n"
            f"{SARMALAYICI_IZI}\n"
            f'exec {shlex.quote(appimage)} --turkod "$@"\n')


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


# --------------------------------------------------------------------------
# ~/.local/bin kullanıcının kabuğunun PATH'inde mi? Değilse kabuğun açılış
# dosyasına işaretli bir satır eklenir (path_ten_cikar geri alır).
# --------------------------------------------------------------------------
KABUK_IZI = "# TürKod: turkod komutu"
KABUK_SATIRI = 'export PATH="$HOME/.local/bin:$PATH"'
FISH_SATIRI = "fish_add_path -g $HOME/.local/bin"
# Giriş kabuğu bu PATH ile sorulur: bu sürecin PATH'i (path_tamamla ~/.local/bin'i
# eklemiş olabilir) sonuca karışmasın.
_TEMEL_PATH = "/usr/bin:/bin:/usr/sbin:/sbin"


def giris_kabugu():
    """Kullanıcının giriş kabuğu: $SHELL, yoksa parola veritabanı, yoksa
    macOS'ta zsh, Linux'ta bash."""
    kabuk = os.environ.get("SHELL")
    if not kabuk:
        try:
            import pwd
            kabuk = pwd.getpwuid(os.getuid()).pw_shell
        except (ImportError, KeyError, OSError, AttributeError):
            kabuk = None
    return kabuk or ("/bin/zsh" if sys.platform == "darwin" else "/bin/bash")


def _ev(*parcalar):
    return os.path.join(os.path.expanduser("~"), *parcalar)


def _fish_dosyasi():
    return _ev(".config", "fish", "conf.d", "turkod.fish")


def kabuk_dosyalari(kabuk=None):
    """Kabuğa göre PATH satırının yazılacağı açılış dosyaları."""
    ad = os.path.basename(kabuk or giris_kabugu())
    if ad == "zsh":
        return [_ev(".zprofile")]
    if ad == "bash":
        dosyalar = [_ev(".bashrc"), _ev(".profile")]
        # ~/.bash_profile varsa giriş kabuğu ~/.profile'ı okumaz (macOS Terminal'i hep
        # giriş kabuğu açar).
        if os.path.isfile(_ev(".bash_profile")):
            dosyalar.append(_ev(".bash_profile"))
        return dosyalar
    if ad == "fish":
        return [_fish_dosyasi()]
    return [_ev(".profile")]


def _tum_kabuk_dosyalari():
    return [_ev(".zprofile"), _ev(".bashrc"), _ev(".profile"), _ev(".bash_profile"),
            _fish_dosyasi()]


def _oku(yol):
    try:
        with open(yol, encoding="utf-8", errors="replace", newline="") as f:
            return f.read()
    except OSError:
        return None


def kabuk_ayari_var_mi():
    """Giriş kabuğunun açılış dosyalarından birinde TürKod'un işaretli satırı var mı?"""
    return any(KABUK_IZI in (_oku(d) or "") for d in kabuk_dosyalari())


def kabuk_pathinde_mi(dizin, zaman_asimi=10):
    """dizin, kullanıcının giriş kabuğunun PATH'inde mi? True / False; kabuk
    sorulamadıysa None."""
    kabuk = giris_kabugu()
    betik = ("string join : $PATH" if os.path.basename(kabuk) == "fish"
             else 'printf "%s" "$PATH"')
    ortam = alt_surec_ortami()
    ortam["PATH"] = _TEMEL_PATH
    try:
        sonuc = subprocess.run([kabuk, "-l", "-c", betik], capture_output=True, text=True,
                               timeout=zaman_asimi, stdin=subprocess.DEVNULL, env=ortam)
    except (OSError, ValueError, subprocess.SubprocessError):
        return None
    cikti = sonuc.stdout
    if sonuc.returncode != 0 or not isinstance(cikti, str) or not cikti.strip():
        return None
    hedef = os.path.normpath(dizin)
    return any(os.path.normpath(os.path.expanduser(p)) == hedef
               for p in cikti.strip().splitlines()[-1].split(":") if p)


def _satir_ekle(dosya):
    """Açılış dosyasına işaretli PATH satırını ekler (zaten varsa eklemez)."""
    icerik = _oku(dosya)
    if icerik is not None and KABUK_IZI in icerik:
        return
    satir = FISH_SATIRI if dosya == _fish_dosyasi() else KABUK_SATIRI
    os.makedirs(os.path.dirname(dosya), exist_ok=True)
    on = "" if not icerik or icerik.endswith("\n") else "\n"
    with open(dosya, "a", encoding="utf-8", newline="\n") as f:
        f.write(f"{on}{KABUK_IZI}\n{satir}\n")


def _satiri_kaldir(dosya):
    icerik = _oku(dosya)
    if icerik is None or KABUK_IZI not in icerik:
        return
    satirlar = icerik.splitlines(keepends=True)
    kalan, atla = [], False
    for s in satirlar:
        if atla:
            atla = False
            if s.strip() in (KABUK_SATIRI, FISH_SATIRI):
                continue
        if s.strip() == KABUK_IZI:
            atla = True
            continue
        kalan.append(s)
    yeni = "".join(kalan)
    if dosya == _fish_dosyasi() and not yeni.strip():
        os.remove(dosya)
        return
    with open(dosya, "w", encoding="utf-8", newline="") as f:
        f.write(yeni)


def kabuk_path_ayarla():
    """~/.local/bin giriş kabuğunun PATH'inde değilse açılış dosyalarına ekler."""
    if kabuk_ayari_var_mi():
        return
    if kabuk_pathinde_mi(kullanici_bin_dizini()):
        return
    for dosya in kabuk_dosyalari():
        _satir_ekle(dosya)


def kabuk_path_ayarini_kaldir():
    for dosya in _tum_kabuk_dosyalari():
        try:
            _satiri_kaldir(dosya)
        except OSError:
            pass


def kullanici_path_etkin():
    """~/.local/bin/turkod bizim VE ~/.local/bin kabuğun PATH'inde (ya da işaretli
    satır yazılmış; yeni açılan terminalde geçerli olur)."""
    kullanici, _ = path_durumu()
    if not kullanici:
        return False
    if kabuk_ayari_var_mi():
        return True
    return kabuk_pathinde_mi(kullanici_bin_dizini()) is not False


def _baglanti_kur():
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
        with open(baglanti, "w", encoding="utf-8", newline="\n") as f:
            f.write(_sarmalayici_metni(appimage))
        os.chmod(baglanti, 0o755)
    else:
        os.symlink(turkod_komutu_hedefi(), baglanti)


def path_e_ekle():
    """~/.local/bin/turkod'u kurar; ~/.local/bin kabuğun PATH'inde değilse kabuğun
    açılış dosyasına (zsh: ~/.zprofile, bash: ~/.bashrc + ~/.profile, fish:
    conf.d/turkod.fish) işaretli bir satır ekler."""
    _baglanti_kur()
    kabuk_path_ayarla()


def path_ten_cikar():
    baglanti = os.path.join(kullanici_bin_dizini(), KOMUT_ADI)
    if _baglanti_bizim_mi(baglanti):
        os.remove(baglanti)
    kabuk_path_ayarini_kaldir()


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
