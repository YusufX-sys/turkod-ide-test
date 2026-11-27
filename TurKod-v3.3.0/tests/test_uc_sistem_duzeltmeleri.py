"""Üç sistem uyumluluk denetiminde bulunan sorunların düzeltmeleri.

Linux / macOS dalları bu Windows bilgisayarında sys.platform taklit edilerek
sınanır (platform_katmani çağrıldığı anda sys.platform'a bakar).
"""
import hashlib
import os
import re
import shlex
import shutil
import signal
import sys
import tempfile
import types
import unittest
from unittest import mock

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if KOK not in sys.path:
    sys.path.insert(0, KOK)

from turkod_ide import (akilli_duzeltici, calistirici, exe_donusturucu as exe,  # noqa: E402
                        exe_terminali, kabuk, kodi, paths, platform_katmani, settings,
                        updater, yerel_modeller, yerel_sunucu)
from turkod_ide.ide_core import IDECore  # noqa: E402


def sistem(ad):
    return mock.patch.object(sys, "platform", ad)


def _gecici(test):
    klasor = tempfile.mkdtemp(prefix="turkod_uc_sistem_")
    test.addCleanup(shutil.rmtree, klasor, True)
    return klasor


# ----------------------------------------------------------------------
# 1. Yazı tipleri: Windows dışında bu süreçte Tk açılmaz
# ----------------------------------------------------------------------
class SistemFontlariTestleri(unittest.TestCase):
    def _cagir(self, aileler):
        c = IDECore.__new__(IDECore)
        import tkinter
        with mock.patch.object(platform_katmani, "yazi_tipi_aileleri",
                               return_value=aileler) as yt, \
                mock.patch.object(tkinter, "Tk",
                                  side_effect=AssertionError("Tk açılmamalı")):
            sonuc = c.sistem_fontlari()
        yt.assert_called_once()
        return sonuc

    def test_macosta_tk_acilmaz_sistem_listesi(self):
        with sistem("darwin"):
            s = self._cagir(["Menlo", "Helvetica", "@Gizli"])
        self.assertEqual(s["kaynak"], "sistem")
        self.assertEqual(s["fontlar"], ["Helvetica", "Menlo"])

    def test_bos_ise_yedek_liste(self):
        with sistem("linux"):
            s = self._cagir(None)
        self.assertEqual(s["kaynak"], "yedek_liste")
        self.assertIn("DejaVu Sans Mono", s["fontlar"])


# ----------------------------------------------------------------------
# 2. Konsol kipinde Ctrl+C
# ----------------------------------------------------------------------
class SigintTestleri(unittest.TestCase):
    def test_posixte_bos_isleyici(self):
        for ad in ("linux", "darwin"):
            with sistem(ad):
                isleyici = calistirici._sigint_isleyicisi()
            self.assertIsNot(isleyici, signal.SIG_IGN)
            self.assertTrue(callable(isleyici))
            self.assertIsNone(isleyici(signal.SIGINT, None))

    def test_windowsta_yok_sayilir(self):
        with sistem("win32"):
            self.assertIs(calistirici._sigint_isleyicisi(), signal.SIG_IGN)

    def test_create_no_window_windowsta(self):
        self.assertEqual(calistirici.CREATE_NO_WINDOW,
                         0x08000000 if os.name == "nt" else 0)


# ----------------------------------------------------------------------
# 3. Alt süreç ortamı platform katmanından
# ----------------------------------------------------------------------
class AltSurecOrtamiTestleri(unittest.TestCase):
    def _taklit(self):
        return mock.patch.object(platform_katmani, "alt_surec_ortami",
                                 side_effect=lambda env=None: {"KATMAN": "1", "PATH": "x"})

    def test_ide_core_ortami(self):
        c = IDECore.__new__(IDECore)
        c._kullanici_paket_yolu = lambda: "PAKET"
        with self._taklit() as k:
            env = c._subprocess_env()
        k.assert_called_once()
        self.assertEqual(env["KATMAN"], "1")
        self.assertTrue(env["PYTHONPATH"].startswith("PAKET"))
        self.assertEqual(env["PYTHONIOENCODING"], "utf-8")

    def test_terminal_ortami_da_katmandan(self):
        c = IDECore.__new__(IDECore)
        c._kullanici_paket_yolu = lambda: "PAKET"
        c._terminal_boyutlari = {"t": (100, 30)}
        with self._taklit():
            env = c._terminal_ortami("t")
        self.assertEqual((env["KATMAN"], env["COLUMNS"]), ("1", "100"))

    def test_calistirici_ve_exe_ortami(self):
        with self._taklit():
            env = calistirici._ortam()
            env2 = exe._ortam()
        self.assertEqual(env["KATMAN"], "1")
        self.assertIn("PYTHONPATH", env)
        self.assertEqual((env2["KATMAN"], env2["PYTHONUTF8"]), ("1", "1"))

    def test_yerel_modeller_ortami(self):
        with self._taklit():
            env = yerel_modeller._ortam(PYTHONIOENCODING="utf-8")
        self.assertEqual(env, {"KATMAN": "1", "PATH": "x", "PYTHONIOENCODING": "utf-8"})


# ----------------------------------------------------------------------
# 4. Yerel sunucu: Linux'ta CUDA .so dosyaları
# ----------------------------------------------------------------------
class CudaKitapliklariTestleri(unittest.TestCase):
    def test_linuxta_so_dosyalari_sirayla_yuklenir(self):
        paket = _gecici(self)
        dosyalar = {"cuda_runtime": ["libcudart.so.12"],
                    "cublas": ["libcublas.so.12", "libcublasLt.so.12", "libnvblas.so.12"]}
        for alt, adlar in dosyalar.items():
            lib = os.path.join(paket, "nvidia", alt, "lib")
            os.makedirs(lib)
            for ad in adlar:
                open(os.path.join(lib, ad), "wb").close()
        yuklenen = []

        def cdll(yol, mode=None):
            yuklenen.append((os.path.basename(yol), mode))
            return object()

        import ctypes
        with mock.patch.object(os, "name", "posix"), \
                mock.patch.dict(os.environ, {"CUDA_PATH": ""}), \
                mock.patch.object(ctypes, "CDLL", side_effect=cdll), \
                mock.patch.object(ctypes, "RTLD_GLOBAL", 256, create=True), \
                mock.patch.object(yerel_sunucu, "_DLL_TUTAMACLARI", []):
            dizinler = yerel_sunucu.dll_dizinlerini_ekle(paket)
        self.assertEqual(len(dizinler), 2)
        self.assertEqual(yuklenen, [("libcudart.so.12", 256), ("libcublasLt.so.12", 256),
                                    ("libcublas.so.12", 256)])

    def test_posixte_cuda_path_lib64(self):
        cuda = _gecici(self)
        os.makedirs(os.path.join(cuda, "lib64"))
        os.makedirs(os.path.join(cuda, "bin"))
        with mock.patch.object(os, "name", "posix"), \
                mock.patch.dict(os.environ, {"CUDA_PATH": cuda}):
            self.assertEqual(yerel_sunucu.cuda_dll_dizinleri(_gecici(self)),
                             [os.path.join(cuda, "lib64")])

    def test_hata_iletisinde_dll_sozcugu_yalnizca_windowsta(self):
        for ad, dll in (("linux", False), ("darwin", False), ("win32", True)):
            with sistem(ad), mock.patch.dict(yerel_modeller._KURULUM, {}):
                yerel_modeller._motor_hatasi("libcudart.so.12: cannot open shared object")
                metin = yerel_modeller._KURULUM["son_hata"]
            self.assertIn("CUDA kitaplıkları", metin)
            self.assertEqual("DLL" in metin, dll)


# ----------------------------------------------------------------------
# 5. EXE / uygulama komutunda tırnaklar
# ----------------------------------------------------------------------
class TirnakTestleri(unittest.TestCase):
    def test_posixte_shlex(self):
        with sistem("linux"):
            for metin in ("oyun.trpy", "Uzay Oyunu", "a$b`c'd", "/ev/k\\l/"):
                t = exe._tirnak(metin)
                self.assertEqual(shlex.split(t), [metin])
            komut = exe.komut_metni("/ev/Oyunlar ım/oyun.trpy", {"ad": "Uzay $Oyun"})
        self.assertEqual(shlex.split(komut)[2:5],
                         ["/ev/Oyunlar ım/oyun.trpy", "--ad", "Uzay $Oyun"])

    def test_windowsta_eski_davranis(self):
        with sistem("win32"):
            self.assertEqual(exe._tirnak("C:\\Oyun Klasörü\\"), '"C:\\Oyun Klasörü\\\\"')
            self.assertEqual(exe._tirnak("oyun.trpy"), "oyun.trpy")


# ----------------------------------------------------------------------
# 6-7. Kaydetme izni ve büyük/küçük harf ad değişikliği
# ----------------------------------------------------------------------
class DosyaTestleri(unittest.TestCase):
    def setUp(self):
        self.klasor = _gecici(self)
        self.c = IDECore.__new__(IDECore)

    def test_yeni_dosya_posixte_umaska_gore_izin(self):
        yol = os.path.join(self.klasor, "yeni.trpy")
        gercek_chmod = os.chmod
        verilen = []

        def chmod(p, mod, *a, **k):
            verilen.append((os.path.basename(p), mod))
            return gercek_chmod(p, mod, *a, **k)

        with mock.patch.object(os, "name", "posix"), \
                mock.patch("turkod_ide.ide_core._umask", return_value=0o022), \
                mock.patch.object(os, "chmod", side_effect=chmod):
            sonuc = self.c.dosya_kaydet(yol, "yazdır(1)\n")
        self.assertTrue(sonuc["ok"], sonuc)
        self.assertEqual(len(verilen), 1)
        self.assertEqual(verilen[0][1], 0o644)

    def test_var_olan_dosyada_chmod_yok(self):
        yol = os.path.join(self.klasor, "var.trpy")
        open(yol, "w").close()
        # Var olan dosyanın izni copymode ile korunur; umask'a göre yeniden verilmez.
        with mock.patch.object(os, "name", "posix"), \
                mock.patch("turkod_ide.ide_core._umask") as umask:
            self.assertTrue(self.c.dosya_kaydet(yol, "x\n")["ok"])
        umask.assert_not_called()

    def test_yalnizca_harf_degisikligi_izinli(self):
        yol = os.path.join(self.klasor, "oyun.trpy")
        open(yol, "w").close()
        # macOS (büyük/küçük harf duyarsız) gibi: hedef "var" ama aynı dosya.
        with mock.patch.object(os.path, "samefile", return_value=True):
            sonuc = self.c.oge_yeniden_adlandir(yol, "Oyun.trpy")
        self.assertTrue(sonuc["ok"], sonuc)

    def test_baska_dosyanin_uzerine_yazmaz(self):
        a = os.path.join(self.klasor, "a.trpy")
        b = os.path.join(self.klasor, "b.trpy")
        open(a, "w").close()
        open(b, "w").close()
        sonuc = self.c.oge_yeniden_adlandir(a, "b.trpy")
        self.assertFalse(sonuc["ok"])
        self.assertIn("zaten var", sonuc["hata"])

    def test_samefile_hatasinda_eski_kural(self):
        with mock.patch.object(os.path, "samefile", side_effect=OSError):
            self.assertTrue(IDECore._ayni_oge_mi("C:\\A\\x", "C:\\A\\x"))

    def test_model_dizini_ev_klasorune_acilir(self):
        c = self.c
        c.ayarlar = mock.Mock()
        hedef = os.path.join(self.klasor, "Modeller")
        with mock.patch.object(os.path, "expanduser",
                               side_effect=lambda p: p.replace("~", self.klasor)), \
                mock.patch.object(yerel_modeller, "model_dizini_ayarla") as ayarla, \
                mock.patch.object(yerel_modeller, "depolama_analizi", return_value={}):
            sonuc = c.yerel_ai_model_dizini_ayarla("~" + os.sep + "Modeller")
        self.assertTrue(sonuc["ok"])
        ayarla.assert_called_once_with(hedef)
        self.assertTrue(os.path.isdir(hedef))


# ----------------------------------------------------------------------
# 8. macOS .app çalışma klasörü (EXE giriş şablonu)
# ----------------------------------------------------------------------
class MacCalismaDiziniTestleri(unittest.TestCase):
    def _islev(self, platform_adi):
        m = re.search(r"\ndef _tk_mac_calisma_dizini\(exe_yolu\):.*?\n(?=\n\n)",
                      exe.GIRIS_BASI, re.S)
        self.assertIsNotNone(m)
        alan = {"_tk_os": os, "_tk_sys": types.SimpleNamespace(platform=platform_adi)}
        exec(m.group(0), alan)
        return alan["_tk_mac_calisma_dizini"]

    def test_app_yaninda_calisir(self):
        kok = _gecici(self)
        exe_yolu = os.path.join(kok, "Oyun.app", "Contents", "MacOS", "Oyun")
        self.assertEqual(self._islev("darwin")(exe_yolu), kok)

    def test_yazilamazsa_belgeler(self):
        kok = _gecici(self)
        exe_yolu = os.path.join(kok, "Oyun.app", "Contents", "MacOS", "Oyun")
        with mock.patch.object(os, "access", return_value=False):
            sonuc = self._islev("darwin")(exe_yolu)
        self.assertIn(sonuc, (os.path.join(os.path.expanduser("~"), "Documents"),
                              os.path.expanduser("~")))

    def test_mac_ya_da_app_degilse_yok(self):
        kok = _gecici(self)
        self.assertIsNone(self._islev("linux")(os.path.join(kok, "Oyun.app", "Contents",
                                                            "MacOS", "Oyun")))
        self.assertIsNone(self._islev("darwin")(os.path.join(kok, "Oyun")))

    def test_sablon_derlenir(self):
        compile(exe.giris_kodu_uret({"ad": "a", "pencere": "turkod", "veri": False,
                                     "sonda_bekle": False, "kaynak_acik": False}),
                "_tk_ana.py", "exec")


# ----------------------------------------------------------------------
# 9. Uygulamaya Dönüştür: binutils, çeviriler, metinler, boyut
# ----------------------------------------------------------------------
class UygulamaYapmaTestleri(unittest.TestCase):
    def test_linuxta_binutils_yoksa_durur(self):
        with mock.patch.object(shutil, "which", return_value=None):
            self.assertIn("sudo apt install binutils", exe._eksik_derleme_araci("linux"))
            self.assertIsNone(exe._eksik_derleme_araci("macos"))
        with mock.patch.object(shutil, "which", return_value="/usr/bin/x"):
            self.assertIsNone(exe._eksik_derleme_araci("linux"))

    def test_exe_yap_binutils_iletisi(self):
        kok = _gecici(self)
        dosya = os.path.join(kok, "oyun.trpy")
        with open(dosya, "w", encoding="utf-8") as f:
            f.write('yazdır("merhaba")\n')
        satirlar = []
        with mock.patch.object(exe, "hedef_sistem", return_value="linux"), \
                mock.patch.object(shutil, "which", return_value=None), \
                mock.patch.object(exe, "pyinstaller_hazirla") as hazirla:
            self.assertIsNone(exe.exe_yap(dosya, exe.varsayilan_ayarlar(), satirlar.append))
        hazirla.assert_not_called()
        self.assertTrue(any("binutils" in s for s in satirlar), satirlar)

    def test_izin_ve_salt_okunur_cevirileri(self):
        metin, tamam = exe.arac_satiri_cevir(
            "PermissionError: [Errno 13] Permission denied: '/opt/x'")
        self.assertTrue(tamam)
        self.assertIn("Erişim engellendi", metin)
        metin, tamam = exe.arac_satiri_cevir("OSError: [Errno 30] Read-only file system: '/x'")
        self.assertTrue(tamam)
        self.assertIn("salt okunur", metin)

    def test_bundle_adimi(self):
        self.assertIn("Building BUNDLE", dict(exe._ADIMLAR))

    def test_konsol_metni_sisteme_gore(self):
        with sistem("darwin"):
            mac = exe.yardim_metni()
        with sistem("linux"):
            linux = exe.yardim_metni()
        with sistem("win32"):
            win = exe.yardim_metni()
        self.assertNotIn("Windows konsolu", mac)
        self.assertIn("Terminal'de çalışır", mac)
        self.assertIn("sistem konsolunda çalışır", linux)
        self.assertIn("Windows konsolunda çalışır", win)
        self.assertIn("Windows konsolu, program bitince", win)
        self.assertNotIn("{KONSOL", mac + linux + win)

    def test_girdi_yok_iletisi_sisteme_gore(self):
        self.assertIn("_tk_sys.platform == \"darwin\"", exe.GIRIS_BASI)
        self.assertIn("'Windows konsolunda'", exe.GIRIS_BASI)

    def test_app_boyutu_paketin_toplami(self):
        kok = _gecici(self)
        app = os.path.join(kok, "Oyun.app", "Contents")
        os.makedirs(os.path.join(app, "MacOS"))
        os.makedirs(os.path.join(app, "Frameworks"))
        with open(os.path.join(app, "MacOS", "Oyun"), "wb") as f:
            f.write(b"\0" * 1024 * 1024)
        with open(os.path.join(app, "Frameworks", "lib"), "wb") as f:
            f.write(b"\0" * 2 * 1024 * 1024)
        self.assertAlmostEqual(exe._boyut_mb(os.path.join(kok, "Oyun.app")), 3.0)
        self.assertAlmostEqual(exe._boyut_mb(os.path.join(app, "MacOS", "Oyun")), 1.0)

    def test_hedef_sistem_katmandan(self):
        for ad, beklenen in (("win32", "windows"), ("darwin", "macos"), ("linux", "linux")):
            with sistem(ad):
                self.assertEqual(exe.hedef_sistem(), beklenen)


# ----------------------------------------------------------------------
# 10. Kodi'nin sistem iletisi
# ----------------------------------------------------------------------
class KodiSistemTestleri(unittest.TestCase):
    def _mesaj(self, ad, veri):
        with sistem(ad), mock.patch.object(platform_katmani, "veri_klasoru", return_value=veri):
            return kodi.sabit_sistem_mesaji("4.0")

    def test_macos(self):
        veri = os.path.join(os.path.expanduser("~"), "Library", "Application Support", "TurKod")
        m = self._mesaj("darwin", veri)
        self.assertIn("Kullanıcı macOS kullanıyor", m)
        self.assertIn("Cmd", m)
        self.assertIn("`Cmd+R`", m)
        self.assertIn("Uygulamaya Dönüştür", m)
        self.assertIn("~/Library/Application Support/TurKod", m)

    def test_linux(self):
        veri = os.path.join(os.path.expanduser("~"), ".local", "share", "TurKod")
        m = self._mesaj("linux", veri)
        self.assertIn("Kullanıcı Linux kullanıyor", m)
        self.assertIn("`Ctrl+R`", m)
        self.assertIn("~/.local/share/TurKod", m)

    def test_windows(self):
        m = self._mesaj("win32", "C:\\Users\\x\\AppData\\Local\\TurKod")
        self.assertIn("Kullanıcı Windows kullanıyor", m)
        self.assertIn("**Çalıştır → EXE'ye Dönüştür…**, `Ctrl+R`", m)
        self.assertNotIn("{", m.split("EYLEM")[0].replace("{\"", ""))


# ----------------------------------------------------------------------
# 11. Kabukta satır düzenleme (readline)
# ----------------------------------------------------------------------
class _Tty:
    def isatty(self):
        return True

    def write(self, _m):
        pass

    def flush(self):
        pass


class KabukReadlineTestleri(unittest.TestCase):
    def _kabuk(self, giris, cikis):
        k = kabuk.TurKodKabugu.__new__(kabuk.TurKodKabugu)
        k.giris, k.cikis = giris, cikis
        return k

    def test_posix_ttyde_readline(self):
        giris, cikis = _Tty(), _Tty()
        with sistem("linux"), mock.patch.object(sys, "stdin", giris), \
                mock.patch.object(sys, "stdout", cikis), \
                mock.patch.dict(sys.modules, {"readline": types.ModuleType("readline")}):
            k = self._kabuk(giris, cikis)
            self.assertTrue(k._satir_duzenleme_kur())
            k._satir_duzenleme = True
            with mock.patch.object(kabuk, "_ASIL_INPUT", return_value="yazdır(1)") as girdi:
                self.assertEqual(k._satir_oku("TürKod> "), "yazdır(1)")
            girdi.assert_called_once_with("TürKod> ")

    def test_readline_yoksa_sessiz(self):
        giris, cikis = _Tty(), _Tty()
        with sistem("darwin"), mock.patch.object(sys, "stdin", giris), \
                mock.patch.object(sys, "stdout", cikis), \
                mock.patch.dict(sys.modules, {"readline": None}):
            self.assertFalse(self._kabuk(giris, cikis)._satir_duzenleme_kur())

    def test_windowsta_ve_boruda_yok(self):
        giris, cikis = _Tty(), _Tty()
        with sistem("win32"), mock.patch.object(sys, "stdin", giris), \
                mock.patch.object(sys, "stdout", cikis):
            self.assertFalse(self._kabuk(giris, cikis)._satir_duzenleme_kur())
        with sistem("linux"):
            import io
            self.assertFalse(self._kabuk(io.StringIO(), io.StringIO())._satir_duzenleme_kur())


# ----------------------------------------------------------------------
# 12. Düşük öncelikliler
# ----------------------------------------------------------------------
class PosixTerminalTestleri(unittest.TestCase):
    def setUp(self):
        self.klasor = _gecici(self)
        os.makedirs(os.path.join(self.klasor, "alt klasör"))
        self.c = IDECore.__new__(IDECore)
        self.c.proje_dizini = self.klasor
        self.c._terminal_dizini = None
        self.c._terminal_dizinleri = {}

    def test_posix_cd(self):
        c = self.c
        with sistem("linux"):
            self.assertEqual(c._terminal_cd("cd 'alt klasör'")["dizin"],
                             os.path.join(self.klasor, "alt klasör"))
            self.assertEqual(c._terminal_cd("cd ..")["dizin"], self.klasor)
            self.assertEqual(c._terminal_cd("cd alt\\ klasör")["dizin"],
                             os.path.join(self.klasor, "alt klasör"))
            with mock.patch.object(os.path, "expanduser",
                                   side_effect=lambda p: self.klasor if p == "~" else p):
                self.assertEqual(c._terminal_cd("cd")["dizin"], self.klasor)
            self.assertIsNone(c._terminal_cd("D:"))
            self.assertIsNone(c._terminal_cd("cd /d x"))
            self.assertIsNone(c._terminal_cd("cd a; ls"))
            self.assertIsNone(c._terminal_cd("cd -"))
            self.assertFalse(c._terminal_cd("cd olmayan")["ok"])

    def test_turkod_komutu_posix_tirnaklari(self):
        with sistem("linux"):
            self.assertEqual(IDECore._kabuk_tirnak('/ev/a b/$x`y"z'),
                             '"/ev/a b/\\$x\\`y\\"z"')
        with sistem("win32"):
            self.assertEqual(IDECore._kabuk_tirnak("C:\\a b\\t.exe"), '"C:\\a b\\t.exe"')

    def test_python_python3e_yonlendirilir(self):
        c = self.c
        with sistem("linux"), mock.patch.object(shutil, "which",
                                                side_effect=lambda ad, path=None: None):
            self.assertEqual(c._python_komutunu_yonlendir("python oyun.py", "/opt/py/python3"),
                             '"/opt/py/python3" oyun.py')
            self.assertEqual(c._python_komutunu_yonlendir("python", "/opt/py/python3"),
                             '"/opt/py/python3"')
            self.assertEqual(c._python_komutunu_yonlendir("python3 a.py", "/x"), "python3 a.py")
        with sistem("linux"), mock.patch.object(shutil, "which", return_value="/usr/bin/python"):
            self.assertEqual(c._python_komutunu_yonlendir("python a.py", "/x"), "python a.py")
        with sistem("win32"):
            self.assertEqual(c._python_komutunu_yonlendir("python a.py", "/x"), "python a.py")


class AyarYaziTipiTestleri(unittest.TestCase):
    def test_sisteme_gore(self):
        for ad, beklenen in (("win32", "Consolas"), ("darwin", "Menlo"),
                             ("linux", "DejaVu Sans Mono")):
            with sistem(ad):
                self.assertEqual(settings.varsayilan_yazi_tipi(), beklenen)


class _Kok:
    def __init__(self, dpi):
        self.dpi = dpi

    def winfo_fpixels(self, _):
        return self.dpi


class TkPencereTestleri(unittest.TestCase):
    def test_olcek(self):
        for ad, dpi, beklenen in (("darwin", 72, 1.0), ("linux", 72, 1.0),
                                  ("linux", 144, 1.5), ("win32", 144, 1.5)):
            # exe_terminali tek başına çalışır: os.name / sys.platform'a bakar.
            with sistem(ad), mock.patch.object(os, "name", "nt" if ad == "win32" else "posix"):
                self.assertEqual(calistirici._tk_olcegi(_Kok(dpi)), beklenen)
                self.assertEqual(exe_terminali._olcek(_Kok(dpi)), beklenen)

    def test_kisayol_metni(self):
        with sistem("darwin"):
            self.assertEqual(calistirici._kisayol("E"), "⌘E")
        with sistem("linux"):
            self.assertEqual(calistirici._kisayol("E"), "Ctrl+E")

    def test_png_simgesi(self):
        kok = _gecici(self)
        ico = os.path.join(kok, "editor-logo.ico")
        self.assertIsNone(calistirici._png_karsiligi(ico))
        open(os.path.join(kok, "program-logo.png"), "w").close()
        self.assertEqual(calistirici._png_karsiligi(ico), os.path.join(kok, "program-logo.png"))
        open(os.path.join(kok, "editor-logo.png"), "w").close()
        self.assertEqual(calistirici._png_karsiligi(ico), os.path.join(kok, "editor-logo.png"))

    def test_posixte_iconphoto(self):
        kok = _gecici(self)
        open(os.path.join(kok, "program-logo.png"), "w").close()
        pencere = mock.Mock()
        import tkinter
        with sistem("linux"), mock.patch.object(tkinter, "PhotoImage") as resim:
            calistirici._pencere_simgesi_kur(pencere, os.path.join(kok, "editor-logo.ico"))
        pencere.iconbitmap.assert_not_called()
        pencere.iconphoto.assert_called_once_with(True, resim.return_value)

    def test_windows_islevleri_posixte_cagrilmaz(self):
        with sistem("linux"):
            calistirici._dpi_farkinda_ol()
            calistirici._uygulama_kimligi()
            calistirici._koyu_baslik_cubugu(mock.Mock())
            g = akilli_duzeltici._PencereGizleyici(1234)
            self.assertIsNone(g._is)
            g.durdur()


class YerelModelSistemTestleri(unittest.TestCase):
    def test_isletim_ve_paketler(self):
        with sistem("darwin"):
            self.assertEqual(yerel_modeller._isletim(), "darwin")
            self.assertEqual(yerel_modeller.cpu_paketi(makine="arm64"), "metal")
            self.assertFalse(yerel_modeller.vulkan_paketi_var(makine="x86_64"))
        with sistem("linux"):
            self.assertEqual(yerel_modeller._isletim(), "linux")
            self.assertTrue(yerel_modeller.vulkan_paketi_var(makine="x86_64"))
        with sistem("win32"):
            self.assertEqual(yerel_modeller._gpu_linux(), [])

    def test_proc_mounts(self):
        kok = _gecici(self)
        mounts = os.path.join(kok, "mounts")
        with open(mounts, "w", encoding="utf-8") as f:
            f.write("/dev/sda2 / ext4 rw 0 0\n"
                    "/dev/sda1 /boot/efi vfat rw 0 0\n"
                    "proc /proc proc rw 0 0\n"
                    "/dev/loop3 /snap/core/1 squashfs ro 0 0\n"
                    "/dev/sdb1 /media/ali/USB\\040Bellek vfat rw 0 0\n")
        with sistem("linux"):
            self.assertEqual(yerel_modeller._posix_diskleri(mounts),
                             ["/", "/media/ali/USB Bellek"])

    def test_disk_etiketi_ve_ayni_disk(self):
        kok = _gecici(self)
        with sistem("linux"):
            self.assertEqual(yerel_modeller._surucu_etiketi("/media/usb"), "/media/usb diskinde")
            self.assertTrue(yerel_modeller._ayni_disk(kok, os.path.join(kok, "yok", "alt")))
        with sistem("win32"):
            self.assertEqual(yerel_modeller._surucu_etiketi("D"), "D: sürücüsünde")

    def test_posix_depolama_alanlari(self):
        kok = _gecici(self)
        model = os.path.join(kok, "modeller")
        with sistem("linux"), \
                mock.patch.object(yerel_modeller, "_sabit_suruculer", return_value=[kok]), \
                mock.patch.object(yerel_modeller, "_sistem_yolu", return_value=kok), \
                mock.patch.object(yerel_modeller, "model_dizini", return_value=model), \
                mock.patch.object(yerel_modeller, "yuklu_modeller", return_value=[]):
            d = yerel_modeller.depolama_analizi()
        s = d["suruculer"][0]
        self.assertEqual((s["kok"], s["harf"], s["sistem"], s["model_surucusu"]),
                         (kok, kok, True, True))


class GuncellemeTestleri(unittest.TestCase):
    def test_posixte_kullanici_klasoru(self):
        with sistem("linux"), mock.patch.object(platform_katmani, "veri_klasoru",
                                                return_value="/ev/ali/.local/share/TurKod"):
            self.assertEqual(str(updater.indirme_klasoru()).replace("\\", "/"),
                             "/ev/ali/.local/share/TurKod/guncelleme")
        with sistem("win32"):
            self.assertEqual(updater.indirme_klasoru().name, "turkod_guncelleme")

    def _hazirla(self, icerik, beklenen_icerik=None):
        kok = _gecici(self)
        indirilen = os.path.join(kok, "TurKod-4.1.AppImage")
        with open(indirilen, "wb") as f:
            f.write(icerik)
        hedef = os.path.join(kok, "TurKod.AppImage")
        with open(hedef, "wb") as f:
            f.write(b"eski")
        sha = hashlib.sha256(beklenen_icerik or icerik).hexdigest()
        durum = {"durum": "bitti", "yol": indirilen, "sha256": sha, "tur": "appimage"}
        self.addCleanup(updater._indirme.update, dict(updater._indirme))
        updater._indirme.update(durum)
        return kok, indirilen, hedef

    def test_dogrulanan_kopya_yerine_konur(self):
        kok, indirilen, hedef = self._hazirla(b"yeni surum")
        with mock.patch.object(updater._posix, "appimage_yolu", return_value=hedef):
            sonuc = updater.uygula(indirilen)
        self.assertTrue(sonuc["ok"], sonuc)
        with open(hedef, "rb") as f:
            self.assertEqual(f.read(), b"yeni surum")
        self.assertEqual(sorted(os.listdir(kok)), ["TurKod-4.1.AppImage", "TurKod.AppImage"])

    def test_degistirilmis_dosya_kurulmaz(self):
        kok, indirilen, hedef = self._hazirla(b"kotu", beklenen_icerik=b"iyi")
        with mock.patch.object(updater._posix, "appimage_yolu", return_value=hedef):
            sonuc = updater.uygula(indirilen)
        self.assertFalse(sonuc["ok"])
        with open(hedef, "rb") as f:
            self.assertEqual(f.read(), b"eski")
        self.assertEqual(sorted(os.listdir(kok)), ["TurKod-4.1.AppImage", "TurKod.AppImage"])

    def test_bilinmeyen_dosya_reddedilir(self):
        kok, _indirilen, hedef = self._hazirla(b"x")
        with mock.patch.object(updater._posix, "appimage_yolu", return_value=hedef):
            self.assertFalse(updater.uygula(os.path.join(kok, "baska"))["ok"])


class KullaniciyaOzelAdTestleri(unittest.TestCase):
    def test_posixte_uid_eki(self):
        with sistem("linux"), mock.patch.object(os, "getuid", return_value=1000, create=True):
            self.assertEqual(paths.port_dosyasi_adi(), "turkod_backend_port-1000")
            # Port dosyası Linux/macOS'ta kullanıcının veri klasöründe (arayüz
            # main.dart AppConfig ile aynı kural); gerçek ev klasörüne yazılmaz.
            with tempfile.TemporaryDirectory() as d, \
                    mock.patch.object(paths.platform_katmani, "veri_klasoru",
                                      return_value=d):
                self.assertEqual(paths.port_dosyasi_yolu(),
                                 os.path.join(d, "backend_port"))
            self.assertEqual(paths.gecici_klasor_adi(), "TurKod-1000")
        with sistem("win32"):
            self.assertEqual(paths.port_dosyasi_adi(), "turkod_backend_port")
            self.assertEqual(paths.gecici_klasor_adi(), "TurKod")


if __name__ == "__main__":
    unittest.main()
