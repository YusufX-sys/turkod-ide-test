"""Windows uygulaması.

Buradaki kod, eskiden entegrasyon.py, calistirici.py, ide_core.py,
surec_izleyici.py, kodi_ses.py, settings.py ve diğer dosyalara dağılmış olan
Windows kodunun AYNISIDIR (winreg, taskkill /F /T, CREATE_NO_WINDOW,
kodi_ses.ps1, %LOCALAPPDATA%, DPAPI). Davranış değiştirilmedi; yalnızca
tek yerde toplandı.

Windows'a özgü modüller (winreg, ctypes.windll, winsound) işlevlerin içinde
içe aktarılır: bu dosya Linux/macOS'ta da hatasız içe aktarılabilir.
"""
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import wave

from ._ortak import PlatformHatasi, ayni_yol, paketli_mi

CREATE_NO_WINDOW = 0x08000000
CREATE_NEW_CONSOLE = 0x00000010


# --------------------------------------------------------------------------
# Klasörler
# --------------------------------------------------------------------------
def veri_tabani(yedek=None):
    """%LOCALAPPDATA%; tanımlı değilse yedek (verilmezse kullanıcı klasörü)."""
    return os.environ.get("LOCALAPPDATA") or (
        yedek if yedek is not None else os.path.expanduser("~"))


# --------------------------------------------------------------------------
# Süreçler
# --------------------------------------------------------------------------
def gizli_surec_ayarlari():
    """Alt süreç için konsol penceresi açılmasın."""
    return {"creationflags": CREATE_NO_WINDOW}


def sureci_agacla_oldur(pid, zaman_asimi=5, sessiz=True):
    """taskkill /F /T: süreci ve tüm alt süreçlerini kapatır.

    sessiz=False ise taskkill'in hatası (ör. zaman aşımı) çağırana iletilir."""
    try:
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)],
                       creationflags=CREATE_NO_WINDOW, timeout=zaman_asimi,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:  # noqa: BLE001
        if not sessiz:
            raise


def kendi_agacimi_oldur():
    """Bu süreci ve alt süreçlerini (kullanıcı programları, terminal) kapatır."""
    sureci_agacla_oldur(os.getpid(), zaman_asimi=5, sessiz=True)


def surec_yasiyor(pid):
    import ctypes
    k32 = ctypes.windll.kernel32
    h = k32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
    if not h:
        # Erişim engeli: süreç var ama sorgulanamıyor -> yaşıyor say.
        return ctypes.GetLastError() == 5
    try:
        kod = ctypes.c_ulong()
        if not k32.GetExitCodeProcess(h, ctypes.byref(kod)):
            return True
        return kod.value == 259  # STILL_ACTIVE
    finally:
        k32.CloseHandle(h)


def ebeveyni_izle(pid, bitince):
    """pid'li süreç bitince bitince()'yi çağırır (arka plan iş parçacığında)."""
    if pid <= 0:
        return
    import ctypes

    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.OpenProcess.argtypes = [ctypes.c_ulong, ctypes.c_int, ctypes.c_ulong]
    k32.OpenProcess.restype = ctypes.c_void_p
    k32.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
    k32.WaitForSingleObject.restype = ctypes.c_ulong

    SYNCHRONIZE = 0x00100000
    tutamak = k32.OpenProcess(SYNCHRONIZE, 0, pid)
    if not tutamak:
        # 87 = ERROR_INVALID_PARAMETER: böyle bir süreç yok (ebeveyn zaten kapanmış).
        # Başka bir hata (örn. erişim reddedildi) ise izlemeyi bırak.
        if ctypes.get_last_error() == 87:
            bitince()
        return

    def izle():
        while True:
            sonuc = k32.WaitForSingleObject(tutamak, 1000)
            if sonuc == 0:            # WAIT_OBJECT_0: ebeveyn sonlandı
                bitince()
            if sonuc != 0x102:        # WAIT_TIMEOUT dışındaki her şey = hata: izlemeyi bırak
                return

    threading.Thread(target=izle, daemon=True, name="ebeveyn-izleyici").start()


def terminalde_ac(komut, cwd=None):
    """Komutu yeni bir konsol penceresinde başlatır."""
    try:
        subprocess.Popen(komut, cwd=cwd, close_fds=True, creationflags=CREATE_NEW_CONSOLE)
        return True
    except OSError:
        return False


def editoru_ayri_baslat(exe, dosyalar=()):
    try:
        # Açık editör varsa yeni süreç dosyayı ona iletip onu öne getirir;
        # bunun için öne getirme izni bu (ön plandaki) süreçten devredilir.
        import ctypes
        ctypes.windll.user32.AllowSetForegroundWindow(-1)  # ASFW_ANY
    except Exception:  # noqa: BLE001
        pass
    try:
        # "cmd /c start" aracılığıyla: editör bu sürecin ALT süreci olmaz. Kurulum
        # / güncelleme 'taskkill /T /IM turkod_backend.exe' ile terminal
        # pencerelerini kapatırken açık editörü kaydetmeden öldürmesin.
        # Her yol tırnaklanır: '&' içeren klasör adları cmd'yi bölmesin.
        komut = 'cmd.exe /d /c start "" ' + " ".join(f'"{y}"' for y in (exe, *dosyalar))
        subprocess.Popen(komut, cwd=os.path.dirname(exe), close_fds=True,
                         creationflags=CREATE_NO_WINDOW)
        return True
    except OSError:
        return False


COP_KUTUSU_ADI = "Geri Dönüşüm Kutusu"
# Windows'ta çöp kutusu ve mikrofon kendi API'leriyle (ide_core.oge_sil,
# kodi_ses._mikrofon_parcalari); RAM yerel_modeller._ram_gb içinde.


def bellek_gb():
    return None


def mikrofon_komutu(ornekleme):
    return None


def editor_dosyasi(backend):
    """<kurulum>\\turkod_flutter.exe (backend\\ klasörünün bir üstü)."""
    return os.path.join(os.path.dirname(backend), "turkod_flutter.exe")


def ekrani_temizle():
    os.system("cls")


# --------------------------------------------------------------------------
# Kullanıcı programlarını çalıştıran Python
# --------------------------------------------------------------------------
GOMULU_PYTHON_GORELI = "_internal/python_embed/python.exe"


def gomulu_python(dizin):
    return os.path.join(dizin, "python.exe")


def gomulu_python_yol_dizini(dizin):
    """PATH'e eklenecek klasör (python.exe ve pip.cmd burada)."""
    return dizin


def sistem_python():
    return shutil.which("python.exe") or shutil.which("python")


def kabuk_kod_sayfasi():
    """cmd yerleşik komutlarının (dir, ipconfig …) çıktı kod sayfası."""
    try:
        import ctypes
        return f"cp{ctypes.windll.kernel32.GetOEMCP()}"
    except Exception:
        return "cp857"


# --------------------------------------------------------------------------
# Kodi'nin sesi (kodi_ses.ps1, WinRT Türkçe ses)
# --------------------------------------------------------------------------
def _ses_betigi():
    yol = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "kodi_ses.ps1")
    if not os.path.exists(yol) and getattr(sys, "_MEIPASS", None):
        yol = os.path.join(sys._MEIPASS, "kodi_ses.ps1")
    return yol


def konus(metin, dur=None):
    """Metni Windows'un Türkçe sesiyle okur; bitene ya da dur olayı gelene dek bekler."""
    import winsound
    if not metin:
        return
    klasor = tempfile.mkdtemp(prefix="kodi_ses_")
    girdi = os.path.join(klasor, "metin.txt")
    cikti = os.path.join(klasor, "ses.wav")
    try:
        with open(girdi, "w", encoding="utf-8") as f:
            f.write(metin)
        sonuc = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
             "-File", _ses_betigi(), girdi, cikti],
            capture_output=True, timeout=60,
            creationflags=CREATE_NO_WINDOW)
        if sonuc.returncode != 0 or not os.path.exists(cikti):
            raise PlatformHatasi("Windows'un konuşma sesi kullanılamadı.")
        if dur is not None and dur.is_set():
            return
        with wave.open(cikti) as w:
            sure = w.getnframes() / float(w.getframerate())
        winsound.PlaySound(cikti, winsound.SND_FILENAME | winsound.SND_ASYNC)
        bitis = time.time() + sure + 0.2
        while time.time() < bitis:
            if dur is not None and dur.is_set():
                winsound.PlaySound(None, 0)
                break
            time.sleep(0.05)
    finally:
        # Geçici klasör her durumda silinir. Eskiden ses dosyası üretilemeyince
        # os.remove(ses.wav) hata veriyor, klasör hiç silinmiyordu.
        shutil.rmtree(klasor, ignore_errors=True)


# --------------------------------------------------------------------------
# Gizli veri (DPAPI)
# --------------------------------------------------------------------------
def gizli_veri(veri, coz):
    """Windows DPAPI: veri yalnızca aynı Windows kullanıcısı tarafından
    çözülebilir. Hata olursa None."""
    try:
        import ctypes
        from ctypes import wintypes

        class _Blob(ctypes.Structure):
            _fields_ = [("cbData", wintypes.DWORD),
                        ("pbData", ctypes.POINTER(ctypes.c_char))]

        crypt32 = ctypes.windll.crypt32
        kernel32 = ctypes.windll.kernel32
        tampon = ctypes.create_string_buffer(veri, len(veri))
        giris = _Blob(len(veri), ctypes.cast(tampon, ctypes.POINTER(ctypes.c_char)))
        cikis = _Blob()
        islev = crypt32.CryptUnprotectData if coz else crypt32.CryptProtectData
        # 0x1 = CRYPTPROTECT_UI_FORBIDDEN
        if not islev(ctypes.byref(giris), None, None, None, None, 0x1,
                     ctypes.byref(cikis)):
            return None
        try:
            return ctypes.string_at(cikis.pbData, cikis.cbData)
        finally:
            kernel32.LocalFree(cikis.pbData)
    except Exception:
        return None


# --------------------------------------------------------------------------
# Sistem entegrasyonu: PATH'teki `turkod` komutu ve .trpy dosya ilişkilendirmesi
#
# Kurulum sihirbazındaki iki seçeneğin (turkod.iss [Tasks] "path" / "iliskilendir")
# uygulama içinden açılıp kapatılabilen karşılığı. Yönetici izni istemez: her şey
# kullanıcı kayıt defterine (HKCU) yazılır. HKCU\Software\Classes, HKLM'dekinin
# önüne geçer; kullanıcı PATH'i sistem PATH'ine eklenir. Yönetici kurulumunun
# HKLM'ye yazdığı girdiler buradan silinemez (durumda bildirilir). Kayıtların
# biçimi turkod.iss [Registry] / [Code] PATH bölümüyle aynıdır.
# --------------------------------------------------------------------------
_ORTAM_ANAHTARI = "Environment"
_SISTEM_ORTAM_ANAHTARI = r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment"
_SINIFLAR = r"Software\Classes"
_PROGID = "TurKod.Program"


def _winreg():
    try:
        import winreg
    except ImportError:  # Windows dışı (geliştirme)
        return None
    return winreg


def _yollar():
    """Kurulum klasöründeki dosyalar. Yalnızca paketli (kurulmuş) uygulamada anlamlı."""
    backend = os.path.dirname(os.path.abspath(sys.executable))
    uygulama = os.path.dirname(backend)
    ic = getattr(sys, "_MEIPASS", os.path.join(backend, "_internal"))
    return {
        "backend_dizini": backend,
        "editor_exe": os.path.join(uygulama, "turkod_flutter.exe"),
        "backend_exe": os.path.join(backend, "turkod_backend.exe"),
        "ikon": os.path.join(ic, "editor-logo.ico"),
    }


def _path_oku(kok, anahtar):
    """(değer, tür) döndürür; değer yoksa ("", REG_EXPAND_SZ)."""
    winreg = _winreg()
    try:
        with winreg.OpenKey(kok, anahtar, 0, winreg.KEY_READ) as k:
            deger, tur = winreg.QueryValueEx(k, "Path")
    except FileNotFoundError:
        return "", winreg.REG_EXPAND_SZ
    if tur not in (winreg.REG_SZ, winreg.REG_EXPAND_SZ) or not isinstance(deger, str):
        raise RuntimeError("PATH değeri beklenmeyen türde; değiştirilmedi.")
    return deger, tur


def _path_iceriyor(deger, dizin):
    return any(ayni_yol(p, dizin) for p in deger.split(";") if p.strip())


def _ortam_degisti_bildir():
    """Yeni açılan terminallerin güncel PATH'i görmesi için WM_SETTINGCHANGE yayını."""
    try:
        import ctypes
        from ctypes import wintypes
        sonuc = wintypes.DWORD()
        ctypes.windll.user32.SendMessageTimeoutW(
            0xFFFF, 0x001A, 0, "Environment", 0x0002, 3000, ctypes.byref(sonuc))
    except Exception:
        pass


def _path_ayarla(ekle):
    winreg = _winreg()
    dizin = _yollar()["backend_dizini"]
    eski, tur = _path_oku(winreg.HKEY_CURRENT_USER, _ORTAM_ANAHTARI)
    parcalar = [p for p in eski.split(";") if p.strip() and not ayni_yol(p, dizin)]
    if ekle:
        parcalar.append(dizin)
    yeni = ";".join(parcalar)
    if yeni == eski:
        return
    with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, _ORTAM_ANAHTARI, 0,
                            winreg.KEY_SET_VALUE) as k:
        if yeni:
            winreg.SetValueEx(k, "Path", 0, tur, yeni)
        else:
            try:
                winreg.DeleteValue(k, "Path")
            except FileNotFoundError:
                pass
    _ortam_degisti_bildir()


def _deger_oku(kok, anahtar, ad=""):
    winreg = _winreg()
    try:
        with winreg.OpenKey(kok, anahtar, 0, winreg.KEY_READ) as k:
            return winreg.QueryValueEx(k, ad)[0]
    except OSError:
        return None


def _yaz(anahtar, ad, deger):
    winreg = _winreg()
    with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, _SINIFLAR + "\\" + anahtar, 0,
                            winreg.KEY_SET_VALUE) as k:
        winreg.SetValueEx(k, ad, 0, winreg.REG_SZ, deger)


def _agac_sil(kok, anahtar):
    """Anahtarı alt anahtarlarıyla siler (yoksa sessizce geçer)."""
    winreg = _winreg()
    try:
        with winreg.OpenKey(kok, anahtar, 0, winreg.KEY_READ) as k:
            altlar = []
            i = 0
            while True:
                try:
                    altlar.append(winreg.EnumKey(k, i))
                except OSError:
                    break
                i += 1
        for alt in altlar:
            _agac_sil(kok, anahtar + "\\" + alt)
        winreg.DeleteKey(kok, anahtar)
    except FileNotFoundError:
        pass


def _bossa_sil(kok, anahtar):
    winreg = _winreg()
    try:
        winreg.DeleteKey(kok, anahtar)   # alt anahtarı varsa OSError: dokunma
    except OSError:
        pass


def _iliski_etkin_mi(kok, on_ek):
    """kok\\on_ek altında .trpy -> TurKod.Program ve çalıştırma komutu kayıtlı mı?"""
    if _deger_oku(kok, on_ek + ".trpy") != _PROGID:
        return False
    komut = _deger_oku(kok, on_ek + _PROGID + r"\shell\open\command")
    return bool(komut) and "turkod_backend.exe" in komut.lower()


def _dosya_turu_bildir():
    try:
        import ctypes
        ctypes.windll.shell32.SHChangeNotify(0x08000000, 0, None, None)  # SHCNE_ASSOCCHANGED
    except Exception:
        pass


def _iliskilendir(ac):
    winreg = _winreg()
    y = _yollar()
    hk = winreg.HKEY_CURRENT_USER
    if ac:
        ikon = y["ikon"] + ",0"
        _yaz(".trpy", "", _PROGID)
        _yaz(".trpy", "Content Type", "text/plain")
        _yaz(".trpy", "PerceivedType", "text")
        _yaz(r".trpy\OpenWithProgids", _PROGID, "")
        _yaz(_PROGID, "", "TürKod Programı")
        _yaz(_PROGID + r"\DefaultIcon", "", ikon)
        _yaz(_PROGID + r"\shell", "", "open")
        _yaz(_PROGID + r"\shell\open", "", "TürKod ile çalıştır")
        _yaz(_PROGID + r"\shell\open", "Icon", ikon)
        _yaz(_PROGID + r"\shell\open\command", "", f'"{y["backend_exe"]}" --terminal "%1"')
        _yaz(r"Applications\turkod_flutter.exe", "FriendlyAppName", "TürKod Editör")
        _yaz(r"Applications\turkod_flutter.exe\SupportedTypes", ".trpy", "")
        _yaz(r"Applications\turkod_flutter.exe\shell\open\command", "",
             f'"{y["editor_exe"]}" "%1"')
        _yaz(r"SystemFileAssociations\.trpy\shell\TurKod.Editor", "", "Editör ile aç")
        _yaz(r"SystemFileAssociations\.trpy\shell\TurKod.Editor", "Icon",
             y["editor_exe"] + ",0")
        _yaz(r"SystemFileAssociations\.trpy\shell\TurKod.Editor\command", "",
             f'"{y["editor_exe"]}" "%1"')
    else:
        s = _SINIFLAR + "\\"
        if _deger_oku(hk, s + ".trpy") == _PROGID:
            with winreg.OpenKey(hk, s + ".trpy", 0, winreg.KEY_SET_VALUE) as k:
                for ad in ("", "Content Type", "PerceivedType"):
                    try:
                        winreg.DeleteValue(k, ad)
                    except FileNotFoundError:
                        pass
        try:
            with winreg.OpenKey(hk, s + r".trpy\OpenWithProgids", 0, winreg.KEY_SET_VALUE) as k:
                winreg.DeleteValue(k, _PROGID)
        except FileNotFoundError:
            pass
        _bossa_sil(hk, s + r".trpy\OpenWithProgids")
        _agac_sil(hk, s + _PROGID)
        _agac_sil(hk, s + r"Applications\turkod_flutter.exe")
        _agac_sil(hk, s + r"SystemFileAssociations\.trpy\shell\TurKod.Editor")
        _bossa_sil(hk, s + r"SystemFileAssociations\.trpy\shell")
        _bossa_sil(hk, s + r"SystemFileAssociations\.trpy")
        # Değeri kalmamış boş .trpy anahtarı da gitsin.
        try:
            with winreg.OpenKey(hk, s + ".trpy", 0, winreg.KEY_READ) as k:
                bos = winreg.QueryInfoKey(k)[1] == 0
            if bos:
                _bossa_sil(hk, s + ".trpy")
        except FileNotFoundError:
            pass
    _dosya_turu_bildir()


def entegrasyon_durumu():
    winreg = _winreg()
    if winreg is None or not paketli_mi():
        return {
            "destekleniyor": False,
            "neden": "Bu ayarlar yalnızca kurulmuş TürKod'da (Windows) kullanılabilir.",
        }
    y = _yollar()
    dizin = y["backend_dizini"]
    try:
        kullanici_path = _path_iceriyor(_path_oku(winreg.HKEY_CURRENT_USER, _ORTAM_ANAHTARI)[0], dizin)
    except Exception:
        kullanici_path = False
    try:
        sistem_path = _path_iceriyor(
            _path_oku(winreg.HKEY_LOCAL_MACHINE, _SISTEM_ORTAM_ANAHTARI)[0], dizin)
    except Exception:
        sistem_path = False
    kullanici_iliski = _iliski_etkin_mi(winreg.HKEY_CURRENT_USER, _SINIFLAR + "\\")
    sistem_iliski = _iliski_etkin_mi(winreg.HKEY_LOCAL_MACHINE, _SINIFLAR + "\\")
    return {
        "destekleniyor": True,
        "path": kullanici_path or sistem_path,
        "path_sistemde": sistem_path,
        "iliskilendir": _iliski_etkin_mi(winreg.HKEY_CLASSES_ROOT, ""),
        "iliski_kullanicida": kullanici_iliski,
        "iliski_sistemde": sistem_iliski,
        "path_dizini": dizin,
    }


def path_e_ekle():
    _path_ayarla(True)


def path_ten_cikar():
    _path_ayarla(False)


def dosya_iliskisi_kur():
    _iliskilendir(True)


def dosya_iliskisi_kaldir():
    _iliskilendir(False)
