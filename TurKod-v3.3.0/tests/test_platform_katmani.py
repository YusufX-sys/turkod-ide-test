"""Platform katmanı (turkod_ide/platform_katmani) testleri.

Linux ve macOS kod yolları sys.platform ve sistem çağrıları taklit edilerek
(mock) denenir; gerçek bir Linux/macOS makinesi gerekmez. Hiçbir test gerçek
süreç öldürmez, terminal açmaz, ses çalmaz ya da kayıt defterine yazmaz.
"""
import contextlib
import io
import os
import shutil
import subprocess
import sys
import tempfile
import types
import threading
import unittest
from unittest import mock

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if KOK not in sys.path:
    sys.path.insert(0, KOK)

with contextlib.redirect_stdout(io.StringIO()):
    from turkod_ide import platform_katmani as pk  # noqa: E402
    from turkod_ide.platform_katmani import _posix, linux, macos, windows  # noqa: E402
    from turkod_ide import entegrasyon, kodi_ses, paths, surec_izleyici  # noqa: E402
    from turkod_ide import calistirici  # noqa: E402


def sistem(ad):
    """sys.platform'u taklit eder: 'win32', 'linux', 'darwin'."""
    return mock.patch.object(sys, "platform", ad)


class SecimTestleri(unittest.TestCase):
    def test_sys_platform_dogru_modulu_secer(self):
        for platform_adi, modul, ad in (("win32", windows, "windows"),
                                        ("linux", linux, "linux"),
                                        ("darwin", macos, "macos"),
                                        ("freebsd13", linux, "linux")):
            with sistem(platform_adi):
                self.assertIs(pk.secili(), modul)
                self.assertEqual(pk.windows_mu(), ad == "windows")
                self.assertEqual(pk.macos_mu(), ad == "macos")
                self.assertEqual(pk.linux_mu(), ad == "linux")

    def test_her_uygulama_ortak_arayuzu_sunar(self):
        islevler = ("veri_tabani", "gizli_surec_ayarlari", "sureci_agacla_oldur",
                    "kendi_agacimi_oldur", "surec_yasiyor", "ebeveyni_izle", "terminalde_ac",
                    "editoru_ayri_baslat", "ekrani_temizle", "konus", "gizli_veri",
                    "kabuk_kod_sayfasi", "entegrasyon_durumu", "path_e_ekle", "path_ten_cikar",
                    "dosya_iliskisi_kur", "dosya_iliskisi_kaldir")
        for modul in (windows, linux, macos):
            for ad in islevler:
                self.assertTrue(callable(getattr(modul, ad, None)), f"{modul.__name__}.{ad}")

    def test_paket_adi_standart_platform_modulunu_golgelemez(self):
        import platform
        self.assertTrue(hasattr(platform, "system"))
        self.assertFalse(os.path.isdir(os.path.join(KOK, "turkod_ide", "platform")))


class VeriKlasoruTestleri(unittest.TestCase):
    def test_windows_localappdata(self):
        with sistem("win32"), mock.patch.dict(os.environ, {"LOCALAPPDATA": r"C:\Veri"}):
            self.assertEqual(pk.veri_klasoru(), os.path.join(r"C:\Veri", "TurKod"))

    def test_windows_localappdata_yoksa_yedek(self):
        with sistem("win32"), mock.patch.dict(os.environ, {"LOCALAPPDATA": ""}):
            self.assertEqual(pk.veri_klasoru(yedek="YEDEK"), os.path.join("YEDEK", "TurKod"))
            self.assertEqual(pk.veri_tabani(), os.path.expanduser("~"))

    def test_linux_xdg_ve_varsayilan(self):
        with sistem("linux"):
            with mock.patch.dict(os.environ, {"XDG_DATA_HOME": os.path.abspath("xdg")}):
                self.assertEqual(pk.veri_klasoru(), os.path.join(os.path.abspath("xdg"), "TurKod"))
            with mock.patch.dict(os.environ, {"XDG_DATA_HOME": ""}):
                self.assertEqual(pk.veri_klasoru(), os.path.join(
                    os.path.expanduser("~"), ".local", "share", "TurKod"))
            # Göreli XDG yolu kurala aykırıdır: yok sayılır.
            with mock.patch.dict(os.environ, {"XDG_DATA_HOME": "goreli"}):
                self.assertEqual(pk.veri_tabani(), os.path.join(
                    os.path.expanduser("~"), ".local", "share"))

    def test_macos(self):
        with sistem("darwin"):
            self.assertEqual(pk.veri_klasoru(), os.path.join(
                os.path.expanduser("~"), "Library", "Application Support", "TurKod"))

    def test_paketli_calisma_yolu_platform_klasorunu_kullanir(self):
        kok = tempfile.mkdtemp(prefix="turkod_pk_")
        self.addCleanup(shutil.rmtree, kok, True)
        with sistem("linux"), mock.patch.object(sys, "frozen", True, create=True), \
                mock.patch.dict(os.environ, {"XDG_DATA_HOME": kok}):
            self.assertEqual(paths.calisma_yolu("a.json"), os.path.join(kok, "TurKod", "a.json"))


class SurecAyarlariTestleri(unittest.TestCase):
    def test_gizli_surec_ayarlari(self):
        with sistem("win32"):
            self.assertEqual(pk.gizli_surec_ayarlari(), {"creationflags": 0x08000000})
        for ad in ("linux", "darwin"):
            with sistem(ad):
                self.assertEqual(pk.gizli_surec_ayarlari(), {"start_new_session": True})

    def test_kabuk_kod_sayfasi_posix(self):
        for ad in ("linux", "darwin"):
            with sistem(ad):
                self.assertEqual(pk.kabuk_kod_sayfasi(), "utf-8")

    def test_ekrani_temizle(self):
        for ad, komut in (("win32", "cls"), ("linux", "clear"), ("darwin", "clear")):
            with sistem(ad), mock.patch.object(os, "system") as s:
                pk.ekrani_temizle()
            s.assert_called_once_with(komut)

    def test_gizli_veri_posix_yok(self):
        with sistem("linux"):
            self.assertIsNone(pk.gizli_veri(b"x", coz=False))


class WindowsSurecTestleri(unittest.TestCase):
    def test_taskkill_agacla(self):
        with mock.patch.object(subprocess, "run") as run:
            windows.sureci_agacla_oldur(1234, zaman_asimi=7)
        args, kw = run.call_args
        self.assertEqual(args[0], ["taskkill", "/F", "/T", "/PID", "1234"])
        self.assertEqual(kw["creationflags"], 0x08000000)
        self.assertEqual(kw["timeout"], 7)

    def test_sessiz_degilse_hata_iletilir(self):
        hata = subprocess.TimeoutExpired(["taskkill"], 10)
        with mock.patch.object(subprocess, "run", side_effect=hata):
            windows.sureci_agacla_oldur(1, sessiz=True)  # yutulur
            with self.assertRaises(subprocess.TimeoutExpired):
                windows.sureci_agacla_oldur(1, sessiz=False)

    def test_terminalde_ac_yeni_konsol(self):
        with mock.patch.object(subprocess, "Popen") as p:
            self.assertTrue(windows.terminalde_ac(["a", "b"], cwd="c"))
        self.assertEqual(p.call_args.kwargs["creationflags"], 0x00000010)

    def test_paketli_degilse_entegrasyon_desteklenmez(self):
        with sistem("win32"):
            d = entegrasyon.durum()
        self.assertFalse(d["destekleniyor"])
        self.assertIn("(Windows)", d["neden"])


class PosixSurecTestleri(unittest.TestCase):
    def test_cocuklar_pgrep_ile(self):
        sonuc = mock.Mock(stdout="11\n12\n")
        with mock.patch.object(_posix.os.path, "isdir", return_value=False), \
                mock.patch.object(subprocess, "run", return_value=sonuc) as run:
            self.assertEqual(_posix._cocuklar(10), [11, 12])
        self.assertEqual(run.call_args[0][0], ["pgrep", "-P", "10"])

    def test_torunlar_agaci_dolasir(self):
        agac = {1: [2, 3], 2: [4], 3: [], 4: [2]}   # döngü olsa da takılmaz
        with mock.patch.object(_posix, "_cocuklar", side_effect=lambda p, z=5: agac[p]):
            self.assertEqual(sorted(_posix._torunlar(1)), [2, 3, 4])

    def _oldur_taklitleri(self, gruplar):
        """os.getpgid/getpgrp/killpg/kill taklitleri (Windows'ta bazıları yok)."""
        olduruldu = []
        yamalar = [
            mock.patch.object(os, "getpgid", side_effect=lambda p: gruplar.get(p, 1),
                              create=True),
            mock.patch.object(os, "getpgrp", return_value=1, create=True),
            mock.patch.object(os, "killpg", side_effect=lambda p, s: olduruldu.append(("grup", p, s)),
                              create=True),
            mock.patch.object(os, "kill", side_effect=lambda p, s: olduruldu.append(("tek", p, s))),
        ]
        return yamalar, olduruldu

    def test_grup_lideri_killpg_digerleri_kill(self):
        yamalar, olduruldu = self._oldur_taklitleri({100: 100, 101: 1})
        with contextlib.ExitStack() as st:
            for y in yamalar:
                st.enter_context(y)
            st.enter_context(mock.patch.object(_posix, "_torunlar", return_value=[101]))
            _posix.sureci_agacla_oldur(100)
        self.assertEqual(olduruldu, [("grup", 100, _posix.SIGKILL), ("tek", 101, _posix.SIGKILL)])

    def test_kendi_agacimi_oldur_kendini_oldurmez(self):
        yamalar, olduruldu = self._oldur_taklitleri({})
        with contextlib.ExitStack() as st:
            for y in yamalar:
                st.enter_context(y)
            st.enter_context(mock.patch.object(_posix, "_torunlar", return_value=[55, 56]))
            _posix.kendi_agacimi_oldur()
        self.assertEqual([p for _, p, _ in olduruldu], [55, 56])
        self.assertNotIn(os.getpid(), [p for _, p, _ in olduruldu])

    def test_surec_yasiyor(self):
        for hata, beklenen in ((None, True), (PermissionError(), True),
                               (ProcessLookupError(), False)):
            with mock.patch.object(os, "kill", side_effect=hata):
                self.assertEqual(_posix.surec_yasiyor(5), beklenen)

    def test_ebeveyn_zaten_yoksa_hemen_kapanir(self):
        cagri = []
        with mock.patch.object(_posix, "surec_yasiyor", return_value=False):
            _posix.ebeveyni_izle(42, lambda: cagri.append(1))
        self.assertEqual(cagri, [1])

    def test_ebeveyn_kapaninca_haber_verir(self):
        bitti = threading.Event()
        durumlar = iter([True, True, True, False])
        with mock.patch.object(_posix, "surec_yasiyor", side_effect=lambda p: next(durumlar)):
            _posix.ebeveyni_izle(42, bitti.set, aralik=0.01)
            self.assertTrue(bitti.wait(5))

    def test_surec_izleyici_katmana_baglanir(self):
        with sistem("linux"), mock.patch.object(linux, "ebeveyni_izle") as izle:
            surec_izleyici.ebeveyni_izle(42)
        self.assertEqual(izle.call_args[0][0], 42)
        with sistem("linux"), mock.patch.object(linux, "ebeveyni_izle") as izle:
            surec_izleyici.ebeveyni_izle(0)
        izle.assert_not_called()

    def test_editor_ayri_oturumda(self):
        with mock.patch.object(subprocess, "Popen") as p:
            self.assertTrue(_posix.editoru_ayri_baslat("/opt/turkod/turkod_flutter", ["a.trpy"]))
        self.assertEqual(p.call_args[0][0], ["/opt/turkod/turkod_flutter", "a.trpy"])
        self.assertTrue(p.call_args.kwargs["start_new_session"])


class TerminalTestleri(unittest.TestCase):
    def test_linux_ilk_bulunan_terminal(self):
        bulunan = {"gnome-terminal": "/usr/bin/gnome-terminal"}
        with mock.patch.object(shutil, "which", side_effect=bulunan.get), \
                mock.patch.object(subprocess, "Popen") as p:
            self.assertTrue(linux.terminalde_ac(["turkod", "kabuk"], cwd="/ev"))
        self.assertEqual(p.call_args[0][0], ["/usr/bin/gnome-terminal", "--", "turkod", "kabuk"])
        self.assertEqual(p.call_args.kwargs["cwd"], "/ev")

    def test_linux_terminal_yoksa_false(self):
        with mock.patch.object(shutil, "which", return_value=None), \
                mock.patch.object(subprocess, "Popen") as p:
            self.assertFalse(linux.terminalde_ac(["turkod"]))
        p.assert_not_called()

    def test_macos_applescript_tirnaklari(self):
        betik = macos.terminal_betigi(["/Uygulamalar/Tür Kod/turkod", "kabuk"],
                                      cwd='/Users/a "b"')
        self.assertIn('tell application "Terminal"', betik)
        self.assertIn("do script \"cd '/Users/a \\\"b\\\"' && '/Uygulamalar/Tür Kod/turkod' kabuk\"",
                      betik)

    def test_macos_osascript_ile_acar(self):
        with mock.patch.object(subprocess, "run",
                               return_value=mock.Mock(returncode=0, stderr="")) as r:
            self.assertTrue(macos.terminalde_ac(["turkod"]))
        self.assertEqual(r.call_args[0][0][:2], ["osascript", "-e"])
        self.assertEqual(r.call_args.kwargs["timeout"], 20)
        self.assertIn("env", r.call_args.kwargs)
        self.assertIsNone(macos.son_terminal_hatasi())

    def test_kabuk_penceresi_katmandan_acilir(self):
        with sistem("linux"), mock.patch.object(linux, "terminalde_ac", return_value=True) as t:
            self.assertTrue(calistirici.kabuk_penceresi_ac())
        komut = t.call_args[0][0]
        self.assertIn("kabuk", komut)


class SesTestleri(unittest.TestCase):
    def test_linux_ses_motoru_yoksa_hata(self):
        with mock.patch.object(shutil, "which", return_value=None):
            with self.assertRaises(pk.PlatformHatasi):
                linux.konus("merhaba")

    def test_linux_espeak(self):
        bulunan = {"espeak-ng": "/usr/bin/espeak-ng"}
        with mock.patch.object(shutil, "which", side_effect=bulunan.get), \
                mock.patch.object(_posix, "sesli_oku") as oku:
            linux.konus("merhaba")
        self.assertEqual(oku.call_args[0][0], ["/usr/bin/espeak-ng", "-v", "tr", "--", "merhaba"])

    def test_macos_turkce_ses(self):
        sesler = mock.Mock(stdout="Alex  en_US # Hello\nYelda tr_TR # Merhaba\n")
        with mock.patch.object(shutil, "which", return_value="/usr/bin/say"), \
                mock.patch.object(subprocess, "run", return_value=sesler), \
                mock.patch.object(_posix, "sesli_oku") as oku:
            macos.konus("merhaba")
        self.assertEqual(oku.call_args[0][0], ["say", "-v", "Yelda", "merhaba"])

    def test_sesli_oku_dur_olayinda_keser(self):
        surec = mock.Mock()
        surec.poll.return_value = None
        dur = threading.Event()
        dur.set()
        with mock.patch.object(subprocess, "Popen", return_value=surec):
            _posix.sesli_oku(["say", "x"], dur)
        surec.terminate.assert_called_once()

    def test_kodi_ses_hatayi_sese_cevirir(self):
        with sistem("linux"), mock.patch.object(shutil, "which", return_value=None):
            with self.assertRaises(kodi_ses.SesHatasi):
                kodi_ses.seslendir("Merhaba")

    def test_bos_metin_okunmaz(self):
        with sistem("linux"), mock.patch.object(linux, "konus") as k:
            kodi_ses.seslendir("")
        k.assert_not_called()


class LinuxEntegrasyonTestleri(unittest.TestCase):
    def setUp(self):
        self.kok = tempfile.mkdtemp(prefix="turkod_pk_")
        self.addCleanup(shutil.rmtree, self.kok, True)
        self.backend = os.path.join(self.kok, "kurulum", "backend")
        os.makedirs(self.backend)
        for ad in ("turkod_backend", "turkod"):
            open(os.path.join(self.backend, ad), "w").close()
        self.ev = os.path.join(self.kok, "ev")
        st = contextlib.ExitStack()
        self.addCleanup(st.close)
        st.enter_context(sistem("linux"))
        st.enter_context(mock.patch.object(sys, "frozen", True, create=True))
        st.enter_context(mock.patch.object(sys, "executable",
                                           os.path.join(self.backend, "turkod_backend")))
        st.enter_context(mock.patch.dict(os.environ, {
            "XDG_DATA_HOME": os.path.join(self.ev, "veri"), "HOME": self.ev,
            "USERPROFILE": self.ev, "SHELL": "/bin/bash"}))
        self.run = st.enter_context(mock.patch.object(
            subprocess, "run", return_value=mock.Mock(returncode=0, stdout="")))

    def test_paketli_degilse_desteklenmez(self):
        with mock.patch.object(sys, "frozen", False):
            self.assertFalse(entegrasyon.durum()["destekleniyor"])

    def test_iliski_kur_ve_kaldir(self):
        d = entegrasyon.durum()
        self.assertTrue(d["destekleniyor"])
        self.assertFalse(d["iliskilendir"])
        d = entegrasyon.ayarla(iliskilendir=True)
        self.assertTrue(d["iliskilendir"])
        masaustu = os.path.join(self.ev, "veri", "applications", linux.MASAUSTU_DOSYASI)
        with open(masaustu, encoding="utf-8") as f:
            icerik = f.read()
        self.assertIn("--terminal %f", icerik)
        self.assertIn("MimeType=text/x-turkod;", icerik)
        with open(os.path.join(self.ev, "veri", "mime", "packages", "turkod-trpy.xml"),
                  encoding="utf-8") as f:
            self.assertIn('pattern="*.trpy"', f.read())
        komutlar = [c[0][0][0] for c in self.run.call_args_list]
        self.assertIn("xdg-mime", komutlar)
        self.assertFalse(entegrasyon.ayarla(iliskilendir=False)["iliskilendir"])
        self.assertFalse(os.path.exists(masaustu))

    def test_path_baglantisi(self):
        baglanti = os.path.join(self.ev, ".local", "bin", "turkod")
        with mock.patch.object(os, "symlink") as sym:
            entegrasyon.ayarla(path=True)
        sym.assert_called_once_with(os.path.join(self.backend, "turkod"), baglanti)
        with mock.patch.object(_posix, "_baglanti_bizim_mi", return_value=True), \
                mock.patch.object(os, "remove") as sil:
            entegrasyon.ayarla(path=False)
        sil.assert_called_once_with(baglanti)

    def test_yabanci_dosyanin_ustune_yazmaz(self):
        os.makedirs(os.path.join(self.ev, ".local", "bin"))
        with open(os.path.join(self.ev, ".local", "bin", "turkod"), "w") as f:
            f.write("baska")
        with self.assertRaises(pk.PlatformHatasi):
            entegrasyon.ayarla(path=True)


class GomuluPythonTestleri(unittest.TestCase):
    """Kullanıcı programlarını çalıştıran Python: paketli uygulamada python_embed."""

    def setUp(self):
        self.kok = tempfile.mkdtemp(prefix="turkod_pk_")
        self.addCleanup(shutil.rmtree, self.kok, True)
        self.backend = os.path.join(self.kok, "backend")
        self.embed = os.path.join(self.backend, "_internal", "python_embed")

    def _dosya(self, *parcalar):
        yol = os.path.join(self.embed, *parcalar)
        os.makedirs(os.path.dirname(yol), exist_ok=True)
        open(yol, "w").close()
        return yol

    def _paketli(self, ad):
        st = contextlib.ExitStack()
        st.enter_context(sistem(ad))
        st.enter_context(mock.patch.object(sys, "frozen", True, create=True))
        st.enter_context(mock.patch.object(
            sys, "executable", os.path.join(self.backend, "turkod_backend")))
        return st

    def test_windows_python_exe(self):
        beklenen = self._dosya("python.exe")
        with self._paketli("win32"):
            self.assertEqual(pk.kullanici_python_bul(), beklenen)
            self.assertEqual(pk.gomulu_python_yol_dizini(), self.embed)
            self.assertEqual(pk.gomulu_python_goreli(), "_internal/python_embed/python.exe")

    def test_posix_bin_python3(self):
        beklenen = self._dosya("bin", "python3")
        for ad in ("linux", "darwin"):
            with self._paketli(ad):
                self.assertEqual(pk.kullanici_python_bul(), beklenen)
                self.assertEqual(pk.gomulu_python_yol_dizini(), os.path.join(self.embed, "bin"))
                self.assertEqual(pk.gomulu_python_goreli(),
                                 "_internal/python_embed/bin/python3")

    def test_gomulu_yoksa_pathteki_python(self):
        bulunan = {"python3": "/usr/bin/python3", "python.exe": r"C:\Py\python.exe"}
        with mock.patch.object(shutil, "which", side_effect=bulunan.get):
            with self._paketli("linux"):
                self.assertEqual(pk.kullanici_python_bul(), "/usr/bin/python3")
            with self._paketli("win32"):
                self.assertEqual(pk.kullanici_python_bul(), r"C:\Py\python.exe")

    def test_paketliyken_hic_python_yoksa_none(self):
        with mock.patch.object(shutil, "which", return_value=None), self._paketli("linux"):
            self.assertIsNone(pk.kullanici_python_bul())

    def test_gelistirici_kipinde_bu_surecin_pythonu(self):
        with sistem("linux"), mock.patch.object(sys, "frozen", False, create=True), \
                mock.patch.object(shutil, "which", return_value=None):
            self.assertEqual(pk.kullanici_python_bul(), sys.executable)

    def test_pythonw_python_exeye_cevrilir(self):
        with sistem("win32"), mock.patch.object(sys, "frozen", False, create=True), \
                mock.patch.object(shutil, "which",
                                  side_effect=lambda ad: r"C:\Py\PythonW.exe" if ad == "python.exe" else None):
            self.assertEqual(pk.kullanici_python_bul(), r"C:\Py\python.exe")

    def test_ide_ve_calistirici_ayni_kurali_kullanir(self):
        beklenen = self._dosya("bin", "python3")
        with self._paketli("linux"):
            self.assertEqual(calistirici.python_exe_bul(), beklenen)

    def test_hazirlama_betigi_ayni_duzeni_uretir(self):
        with open(os.path.join(KOK, "platformlar", "python_embed_hazirla.sh"),
                  encoding="utf-8", newline="") as f:
            betik = f.read()
        self.assertNotIn("\r\n", betik)                     # bash CRLF ile çalışmaz
        self.assertIn('PY="$HEDEF/bin/python3"', betik)     # _posix.gomulu_python ile aynı
        self.assertIn("kullanici_kutuphaneleri.txt", betik)


class AppImageTestleri(unittest.TestCase):
    """AppImage her açılışta başka klasöre bağlanır: kalıcı yol $APPIMAGE dosyasıdır."""

    def setUp(self):
        self.kok = tempfile.mkdtemp(prefix="turkod_pk_")
        self.addCleanup(shutil.rmtree, self.kok, True)
        self.appimage = os.path.join(self.kok, "TurKod-3.3.0-x86_64.AppImage")
        open(self.appimage, "w").close()
        self.ev = os.path.join(self.kok, "ev")
        self.mount = os.path.join(self.kok, "mount_ABC", "usr", "lib", "turkod", "backend")
        os.makedirs(self.mount)
        st = contextlib.ExitStack()
        self.addCleanup(st.close)
        st.enter_context(sistem("linux"))
        st.enter_context(mock.patch.object(sys, "frozen", True, create=True))
        st.enter_context(mock.patch.object(sys, "executable",
                                           os.path.join(self.mount, "turkod_backend")))
        st.enter_context(mock.patch.dict(os.environ, {
            "APPIMAGE": self.appimage, "HOME": self.ev, "USERPROFILE": self.ev,
            "XDG_DATA_HOME": os.path.join(self.ev, "veri"), "SHELL": "/bin/bash"}))
        st.enter_context(mock.patch.object(subprocess, "run",
                                           return_value=mock.Mock(returncode=0, stdout="")))
        self.komut = os.path.join(self.ev, ".local", "bin", "turkod")

    def test_turkod_komutu_appimagei_cagiran_betik(self):
        with mock.patch.object(os, "symlink") as sym:
            d = entegrasyon.ayarla(path=True)
        sym.assert_not_called()
        with open(self.komut, encoding="utf-8") as f:
            betik = f.read()
        import shlex
        self.assertIn(f'exec {shlex.quote(self.appimage)} --turkod "$@"', betik)
        self.assertNotIn("mount_ABC", betik)
        self.assertTrue(d["path"])
        # AppImage taşındıysa betik yeniden yazılır; kaldırınca silinir.
        yeni = os.path.join(self.kok, "Uygulamalar", "TurKod.AppImage")
        os.makedirs(os.path.dirname(yeni))
        open(yeni, "w").close()
        with mock.patch.dict(os.environ, {"APPIMAGE": yeni}):
            entegrasyon.ayarla(path=True)
        with open(self.komut, encoding="utf-8") as f:
            self.assertIn(yeni, f.read())
        self.assertFalse(entegrasyon.ayarla(path=False)["path"])
        self.assertFalse(os.path.exists(self.komut))

    def test_trpy_iliskisi_appimage_dosyasini_cagirir(self):
        self.assertTrue(entegrasyon.ayarla(iliskilendir=True)["iliskilendir"])
        with open(os.path.join(self.ev, "veri", "applications", linux.MASAUSTU_DOSYASI),
                  encoding="utf-8") as f:
            icerik = f.read()
        self.assertIn(f"Exec={linux._exec_argumani(self.appimage)} --terminal %f", icerik)
        self.assertNotIn("mount_ABC", icerik)

    def test_apprun_ayni_argumanlari_tanir(self):
        with open(os.path.join(KOK, "platformlar", "linux", "AppRun"), encoding="utf-8",
                  newline="") as f:
            apprun = f.read()
        self.assertNotIn("\r\n", apprun)
        self.assertIn("--turkod)", apprun)
        self.assertIn('exec "$UYGULAMA/backend/turkod" "$@"', apprun)
        self.assertIn("--terminal)", apprun)
        self.assertIn('exec "$UYGULAMA/backend/turkod_backend" "$@"', apprun)


class EditorYoluTestleri(unittest.TestCase):
    def test_her_sistemde_editor_dosyasi(self):
        self.assertEqual(windows.editor_dosyasi(os.path.join("K", "backend")),
                         os.path.join("K", "turkod_flutter.exe"))
        self.assertEqual(linux.editor_dosyasi(os.path.join("K", "backend")),
                         os.path.join("K", "turkod_flutter"))
        b = os.path.join("TurKod.app", "Contents", "Resources", "backend")
        self.assertEqual(macos.editor_dosyasi(b),
                         os.path.join("TurKod.app", "Contents", "MacOS", "TurKod"))

    def test_calistirici_katmandan_bulur(self):
        kok = tempfile.mkdtemp(prefix="turkod_pk_")
        self.addCleanup(shutil.rmtree, kok, True)
        os.makedirs(os.path.join(kok, "backend"))
        editor = os.path.join(kok, "turkod_flutter")
        open(editor, "w").close()
        with sistem("linux"), mock.patch.object(sys, "frozen", True, create=True), \
                mock.patch.object(sys, "executable", os.path.join(kok, "backend", "turkod_backend")):
            self.assertEqual(calistirici.editor_exe_bul(), editor)


class TurkodKomutuTestleri(unittest.TestCase):
    """IDE terminalindeki `turkod ...` ve TürKod Kabuğu düğmesi kurulumdaki
    turkod komutunu bulmalı (Linux/macOS'ta adı .exe'siz; Codespaces'te
    "turkod: not found" hatası böyle bulundu)."""

    def setUp(self):
        self.kok = tempfile.mkdtemp(prefix="turkod_pk_")
        self.addCleanup(shutil.rmtree, self.kok, True)

    def _paketli(self, ad, dosya):
        open(os.path.join(self.kok, dosya), "w").close()
        st = contextlib.ExitStack()
        st.enter_context(sistem(ad))
        st.enter_context(mock.patch.object(sys, "frozen", True, create=True))
        st.enter_context(mock.patch.object(sys, "executable",
                                           os.path.join(self.kok, "turkod_backend")))
        return st

    def test_dosya_adi(self):
        with self._paketli("linux", "turkod"):
            self.assertEqual(pk.turkod_komutu_dosyasi(), os.path.join(self.kok, "turkod"))
        with self._paketli("darwin", "turkod"):
            self.assertEqual(pk.turkod_komutu_dosyasi(), os.path.join(self.kok, "turkod"))
        with self._paketli("win32", "turkod.exe"):
            self.assertEqual(pk.turkod_komutu_dosyasi(), os.path.join(self.kok, "turkod.exe"))

    def test_ide_terminali_linuxta_yonlendirir(self):
        from turkod_ide.ide_core import IDECore
        tirnak = getattr(IDECore, "_kabuk_tirnak", lambda y: f'"{y}"')
        sahte = types.SimpleNamespace(_TURKOD_KOMUTU=IDECore._TURKOD_KOMUTU,
                                      _kabuk_tirnak=tirnak)
        with self._paketli("linux", "turkod"):
            komut, ileti = IDECore._turkod_komutu(sahte, "turkod --surum")
            beklenen = f'{tirnak(os.path.join(self.kok, "turkod"))} --surum'
        self.assertIsNone(ileti)
        self.assertEqual(komut, beklenen)


class CopKutusuTestleri(unittest.TestCase):
    """Gezgin'de silme: Linux'ta freedesktop çöp kutusu, macOS'ta ~/.Trash
    (eskiden bu sistemlerde silme hiç çalışmıyordu)."""

    def setUp(self):
        self.kok = tempfile.mkdtemp(prefix="turkod_pk_")
        self.addCleanup(shutil.rmtree, self.kok, True)
        self.ev = os.path.join(self.kok, "ev")
        self.proje = os.path.join(self.ev, "proje")
        os.makedirs(self.proje)
        self.dosya = os.path.join(self.proje, "oyun.trpy")
        with open(self.dosya, "w", encoding="utf-8") as f:
            f.write('yazdır("x")\n')

    def test_linux_trashinfo_ile_tasir(self):
        veri = os.path.join(self.ev, "veri")
        with sistem("linux"), mock.patch.dict(os.environ, {"XDG_DATA_HOME": veri}):
            self.assertTrue(pk.cop_kutusu_var_mi(self.dosya))
            pk.cop_kutusuna_tasi(self.dosya)
            # Aynı adda ikinci dosya: "oyun 2.trpy"
            with open(self.dosya, "w", encoding="utf-8") as f:
                f.write("2")
            pk.cop_kutusuna_tasi(self.dosya)
        self.assertFalse(os.path.exists(self.dosya))
        dosyalar = sorted(os.listdir(os.path.join(veri, "Trash", "files")))
        self.assertEqual(dosyalar, ["oyun 2.trpy", "oyun.trpy"])
        with open(os.path.join(veri, "Trash", "info", "oyun.trpy.trashinfo"),
                  encoding="utf-8") as f:
            bilgi = f.read()
        self.assertTrue(bilgi.startswith("[Trash Info]\n"))
        self.assertIn("Path=", bilgi)
        self.assertIn("oyun.trpy", bilgi)
        self.assertIn("DeletionDate=", bilgi)

    def test_macos_nsfilemanager_ile_tasir(self):
        """macOS: Finder'ın yolu (NSFileManager.trashItemAtURL, JXA); yol betiğe
        gömülmez, argüman olarak verilir."""
        with sistem("darwin"), mock.patch.object(
                subprocess, "run", return_value=mock.Mock(returncode=0, stderr="")) as r:
            pk.cop_kutusuna_tasi(self.dosya)
        komut = r.call_args[0][0]
        self.assertEqual(komut[:5], ["osascript", "-l", "JavaScript", "-e", macos.COP_BETIGI])
        self.assertEqual(komut[5], os.path.abspath(self.dosya))
        self.assertEqual(len(komut), 6)
        self.assertIn("function run(argv)", macos.COP_BETIGI)
        self.assertIn("trashItemAtURLResultingItemURLError", macos.COP_BETIGI)
        self.assertNotIn("oyun.trpy", macos.COP_BETIGI)
        self.assertIn("env", r.call_args.kwargs)

    def test_macos_cop_hatasi_turkce_oserror(self):
        with sistem("darwin"), mock.patch.object(
                subprocess, "run", return_value=mock.Mock(
                    returncode=1, stderr="execution error: Error: izin yok (-1)")):
            with self.assertRaises(OSError) as h:
                pk.cop_kutusuna_tasi(self.dosya)
        self.assertIn("Çöp Kutusu'na taşınamadı", str(h.exception))
        self.assertTrue(os.path.exists(self.dosya))

    def test_linux_trashinfo_ayni_adi_ezmez(self):
        """.trashinfo O_EXCL ile açılır: yalnızca info'da kalmış eski bir kayıt
        varsa bile onun üstüne yazılmaz, sıradaki ad seçilir."""
        veri = os.path.join(self.ev, "veri")
        bilgi = os.path.join(veri, "Trash", "info")
        os.makedirs(bilgi)
        with open(os.path.join(bilgi, "oyun.trpy.trashinfo"), "w", encoding="utf-8") as f:
            f.write("ESKI")
        with sistem("linux"), mock.patch.dict(os.environ, {"XDG_DATA_HOME": veri}):
            pk.cop_kutusuna_tasi(self.dosya)
        with open(os.path.join(bilgi, "oyun.trpy.trashinfo"), encoding="utf-8") as f:
            self.assertEqual(f.read(), "ESKI")
        self.assertTrue(os.path.isfile(os.path.join(veri, "Trash", "files", "oyun 2.trpy")))
        self.assertTrue(os.path.isfile(os.path.join(bilgi, "oyun 2.trpy.trashinfo")))

    def test_cop_kutusu_adlari(self):
        for ad, beklenen in (("win32", "Geri Dönüşüm Kutusu"), ("darwin", "Çöp Kutusu"),
                             ("linux", "Çöp")):
            with sistem(ad):
                self.assertEqual(pk.cop_kutusu_adi(), beklenen)

    def test_ide_linuxta_siler(self):
        from turkod_ide.ide_core import IDECore
        veri = os.path.join(self.ev, "veri")
        with sistem("linux"), mock.patch.dict(os.environ, {"XDG_DATA_HOME": veri}):
            r = IDECore.oge_sil(types.SimpleNamespace(
                _cop_kutusu_var_mi=IDECore._cop_kutusu_var_mi,
                _kalici_silme_sorusu=IDECore._kalici_silme_sorusu), self.dosya)
        self.assertEqual(r, {"ok": True, "yol": self.dosya})
        self.assertTrue(os.path.isfile(os.path.join(veri, "Trash", "files", "oyun.trpy")))

    def test_baska_diskte_kalici_silme_sorulur(self):
        from turkod_ide.ide_core import IDECore
        with sistem("darwin"), mock.patch.object(pk, "cop_kutusu_var_mi", return_value=False):
            r = IDECore.oge_sil(types.SimpleNamespace(
                _cop_kutusu_var_mi=IDECore._cop_kutusu_var_mi,
                _kalici_silme_sorusu=IDECore._kalici_silme_sorusu), self.dosya)
        self.assertTrue(r["kalici_gerekir"])
        self.assertIn("Çöp Kutusu yok", r["hata"])
        self.assertTrue(os.path.exists(self.dosya))


class BellekOlcumuTestleri(unittest.TestCase):
    def test_linux_meminfo(self):
        meminfo = "MemTotal:       16384000 kB\nMemFree:  1000 kB\nMemAvailable:    8192000 kB\n"
        with sistem("linux"), mock.patch("builtins.open", mock.mock_open(read_data=meminfo)):
            toplam, bos = pk.bellek_gb()
        self.assertAlmostEqual(toplam, 16384000 / 2**20)
        self.assertAlmostEqual(bos, 8192000 / 2**20)

    def test_macos_sysctl_vm_stat(self):
        vm = ("Mach Virtual Memory Statistics: (page size of 16384 bytes)\n"
              "Pages free:                               1000.\n"
              "Pages active:                             5000.\n"
              "Pages inactive:                           2000.\n"
              "Pages speculative:                         500.\n"
              "Pages purgeable:                           100.\n")

        def calistir(komut, **k):
            return mock.Mock(stdout=str(8 * 2**30) if komut[0] == "sysctl" else vm)
        with sistem("darwin"), mock.patch.object(subprocess, "run", side_effect=calistir):
            toplam, bos = pk.bellek_gb()
        self.assertEqual(toplam, 8.0)
        self.assertAlmostEqual(bos, (1000 + 2000 + 500 + 100) * 16384 / 2**30)

    def test_yerel_modeller_macosta_sifir_degil(self):
        from turkod_ide import yerel_modeller
        with sistem("darwin"), mock.patch.object(pk, "bellek_gb", return_value=(8.0, 3.0)):
            self.assertEqual(yerel_modeller._ram_gb(), (8.0, 3.0))


class MikrofonTestleri(unittest.TestCase):
    def test_linux_arecord(self):
        with sistem("linux"), mock.patch.object(shutil, "which",
                                                side_effect=lambda a: "/usr/bin/arecord" if a == "arecord" else None):
            komut = pk.mikrofon_komutu(16000)
        self.assertEqual(komut[0], "/usr/bin/arecord")
        self.assertIn("S16_LE", komut)
        self.assertIn("16000", komut)

    def test_macos_sox_yoksa_aciklama(self):
        with sistem("darwin"), mock.patch.object(shutil, "which", return_value=None):
            self.assertIsNone(pk.mikrofon_komutu(16000))
            self.assertIn("brew install sox", pk.mikrofon_yok_mesaji())

    def test_kodi_ses_kayit_programindan_okur(self):
        boyut = int(kodi_ses.ORNEKLEME * 2 * kodi_ses.PARCA_SN)
        surec = mock.Mock()
        surec.stdout = io.BytesIO(b"\x01" * boyut * 2)
        surec.stderr = io.BytesIO(b"")
        with sistem("linux"), mock.patch.object(pk, "mikrofon_komutu", return_value=["arecord"]), \
                mock.patch.object(subprocess, "Popen", return_value=surec):
            uretec = kodi_ses._mikrofon_parcalari(None)
            self.assertEqual(len(next(uretec)), boyut)
            self.assertEqual(len(next(uretec)), boyut)
            with self.assertRaises(kodi_ses.SesHatasi):
                next(uretec)   # akış bitti: mikrofon yok sayılır
        surec.terminate.assert_called()

    def test_kayit_programi_yoksa_turkce_hata(self):
        with sistem("linux"), mock.patch.object(pk, "mikrofon_komutu", return_value=None):
            with self.assertRaises(kodi_ses.SesHatasi) as h:
                next(kodi_ses._mikrofon_parcalari(None))
        self.assertIn("alsa-utils", str(h.exception))


class WindowsaOzguOzellikTestleri(unittest.TestCase):
    def test_program_dosyasi_her_sistemde(self):
        """EXE'ye Dönüştür her sistemde kendi biçimini yapar (eskiden yalnızca Windows)."""
        from turkod_ide import exe_donusturucu as exe
        k = os.path.join("k")
        self.assertEqual(exe.cikti_yollari(k, "oyun", "turkod", False, "windows"),
                         (os.path.join(k, "oyun.exe"),) * 2)
        self.assertEqual(exe.cikti_yollari(k, "oyun", "turkod", False, "linux"),
                         (os.path.join(k, "oyun"),) * 2)
        self.assertEqual(exe.cikti_yollari(k, "oyun", "turkod", True, "linux"),
                         (os.path.join(k, "oyun"), os.path.join(k, "oyun", "oyun")))
        self.assertEqual(exe.cikti_yollari(k, "oyun", "yok", False, "macos"),
                         (os.path.join(k, "oyun.app"),
                          os.path.join(k, "oyun.app", "Contents", "MacOS", "oyun")))
        self.assertEqual(exe.cikti_yollari(k, "oyun", "konsol", False, "macos"),
                         (os.path.join(k, "oyun"),) * 2)
        with sistem("linux"):
            self.assertEqual(exe.hedef_sistem(), "linux")

    def test_kodi_pencere_goruntusu_linuxta_aciklama(self):
        """Arayüz pencere görüntüsünü göndermediyse ekranın tamamı gönderilmez."""
        from turkod_ide import kodi_goruntu
        with sistem("linux"):
            veri, aciklama = kodi_goruntu.yakala("pencere")
        self.assertIsNone(veri)
        self.assertIn("TürKod penceresi", aciklama)

    def test_kodi_pencere_goruntusu_arayuzden_gelir(self):
        """Linux/macOS: arayüzün kendi penceresinden aldığı PNG küçültülüp JPEG olur."""
        import base64
        try:
            from PIL import Image
        except ImportError:
            self.skipTest("PIL yok")
        from turkod_ide import kodi_goruntu
        tampon = io.BytesIO()
        Image.new("RGBA", (3200, 1800), (30, 60, 90, 255)).save(tampon, "PNG")
        png = base64.b64encode(tampon.getvalue()).decode("ascii")
        with sistem("linux"):
            veri, boyut = kodi_goruntu.yakala("pencere", hazir=png)
        self.assertEqual(boyut, "1600x900")
        self.assertTrue(base64.b64decode(veri).startswith(b"\xff\xd8"))   # JPEG


class PaketlemeBetikleriTestleri(unittest.TestCase):
    """Derleme betiklerindeki paket düzeni, kodun beklediği yollarla aynı mı?"""

    def _oku(self, *yol):
        with open(os.path.join(KOK, *yol), encoding="utf-8", newline="") as f:
            metin = f.read()
        self.assertNotIn("\r\n", metin, yol)   # bash/plist CRLF ile bozulur
        return metin

    def test_linux_duzeni(self):
        b = self._oku("platformlar", "linux", "build_linux.sh")
        self.assertIn('cp -a "$DIST/backend" "$CIKIS/backend"', b)
        self.assertIn("turkod_flutter", b)
        self.assertIn('"$CIKIS" "$APPDIR/usr/lib/turkod"', b)     # AppRun'ın UYGULAMA'sı
        self.assertIn('--haric "_internal/python_embed/*"', b)     # Windows ile aynı
        self.assertIn('bash "$KOK/platformlar/python_embed_hazirla.sh"', b)
        masaustu = self._oku("platformlar", "linux", "turkod.desktop")
        self.assertIn("MimeType=text/x-turkod;", masaustu)
        self.assertEqual(linux.MIME_TURU, "text/x-turkod")

    def test_macos_duzeni(self):
        b = self._oku("platformlar", "macos", "build_macos.sh")
        self.assertIn('KAYNAK="$APP/Contents/Resources"', b)
        self.assertIn('cp -R "$DIST/backend" "$KAYNAK/backend"', b)
        self.assertIn('cp -R "$KOK/belgeler" "$KAYNAK/belgeler"', b)   # yardim.dart Resources'a bakar
        self.assertIn("Contents/MacOS/TurKod", b)
        self.assertIn('--haric "_internal/python_embed/*"', b)
        import plistlib
        izin = plistlib.loads(self._oku("platformlar", "macos",
                                        "backend.entitlements").encode("utf-8"))
        self.assertTrue(izin["com.apple.security.cs.allow-unsigned-executable-memory"])
        self.assertTrue(izin["com.apple.security.cs.disable-library-validation"])

    def test_dart_tarafi_ayni_yollari_kullanir(self):
        dart = self._oku("turkod_flutter", "lib", "platform_ayarlari.dart")
        self.assertIn("'backend', 'turkod_backend.exe'", dart)
        self.assertIn("'backend', 'turkod_backend'", dart)
        self.assertIn("'Resources', 'backend', 'turkod_backend'", dart)


class SembolikKlasorTestleri(unittest.TestCase):
    """macOS'ta geçici klasör /var/... ama Python içe aktarılan modülü
    /private/var/... yolundan görür (sembolik bağlantı). Hata ayıklayıcı ve hata
    mesajları kullanıcının .trpy modülünü yine tanımalı (runner._yerel_modul_adi)."""

    def _islevler(self):
        from turkod_ide import runner
        kod = runner.RUNNER_ORTAK
        bas = kod.index("_TK_YEREL_MODUL_ONBELLEK = {}")
        son = kod.index("\n\n\n", kod.index("def _yerel_modul_adi"))
        ns = {"os": os}
        exec(kod[bas:son], ns)
        return ns["_yerel_modul_adi"]

    def test_ayni_klasorun_iki_yolu(self):
        # realpath: macOS'un kendi geçici klasörü de /var -> /private/var bağlantısıdır;
        # testin taklit ettiği bağlantı onunla karışmasın.
        kok = os.path.realpath(tempfile.mkdtemp(prefix="turkod_pk_"))
        self.addCleanup(shutil.rmtree, kok, True)
        gercek = os.path.join(kok, "private", "var", "tmp")
        takma = os.path.join(kok, "var", "tmp")
        gercek_realpath = os.path.realpath

        def sahte_realpath(p, *a, **k):
            p = gercek_realpath(p, *a, **k)
            return p.replace(takma, gercek) if p.startswith(takma) else p

        yerel_modul_adi = self._islevler()
        ana = os.path.join(takma, "turkce_kod_calisma.py")       # ana dosya: takma yol
        modul = os.path.join(gercek, "yardimci.py")              # modül: gerçek yol
        self.assertIsNone(yerel_modul_adi(modul, ana))           # çözülmeden: tanınmaz
        yerel_modul_adi = self._islevler()                        # temiz önbellek
        with mock.patch.object(os.path, "realpath", side_effect=sahte_realpath):
            self.assertEqual(yerel_modul_adi(modul, ana), "yardimci.trpy")
            self.assertIsNone(yerel_modul_adi(ana, ana))          # ana dosyanın kendisi değil
            self.assertIsNone(yerel_modul_adi(os.path.join(kok, "baska", "x.py"), ana))


class MacosEntegrasyonTestleri(unittest.TestCase):
    def test_iliski_paketten_gelir(self):
        with sistem("darwin"), mock.patch.object(sys, "frozen", True, create=True), \
                mock.patch.object(_posix, "path_durumu", return_value=(False, False)):
            d = entegrasyon.durum()
            self.assertTrue(d["destekleniyor"])
            self.assertTrue(d["iliski_sistemde"])
            with self.assertRaises(pk.PlatformHatasi):
                entegrasyon.ayarla(iliskilendir=False)


class AltSurecOrtamiTestleri(unittest.TestCase):
    """alt_surec_ortami: PyInstaller'ın LD_LIBRARY_PATH / DYLD_* ayarı dış
    programlara geçmez; macOS'ta Homebrew klasörleri PATH'e eklenir."""

    def setUp(self):
        self.kok = tempfile.mkdtemp(prefix="turkod_pk_")
        self.addCleanup(shutil.rmtree, self.kok, True)
        self.backend = os.path.join(self.kok, "backend")
        self.internal = os.path.join(self.backend, "_internal")
        os.makedirs(self.internal)

    def _paketli(self, ad, paketli=True):
        st = contextlib.ExitStack()
        st.enter_context(sistem(ad))
        st.enter_context(mock.patch.object(sys, "frozen", paketli, create=True))
        st.enter_context(mock.patch.object(sys, "_MEIPASS", self.internal, create=True))
        st.enter_context(mock.patch.object(sys, "executable",
                                           os.path.join(self.backend, "turkod_backend")))
        return st

    def test_linux_orig_geri_konur(self):
        env = {"LD_LIBRARY_PATH": self.internal, "LD_LIBRARY_PATH_ORIG": "/opt/kendi/lib",
               "PATH": "/usr/bin"}
        with self._paketli("linux"):
            ortam = pk.alt_surec_ortami(env)
        self.assertEqual(ortam["LD_LIBRARY_PATH"], "/opt/kendi/lib")
        self.assertNotIn("LD_LIBRARY_PATH_ORIG", ortam)
        self.assertEqual(env["LD_LIBRARY_PATH"], self.internal)   # verilen sözlük bozulmaz

    def test_linux_orig_yoksa_paket_yolu_atilir(self):
        with self._paketli("linux"):
            self.assertNotIn("LD_LIBRARY_PATH",
                             pk.alt_surec_ortami({"LD_LIBRARY_PATH": self.internal}))
            # Kullanıcının kendi yolu kalır; işlev ikinci kez uygulanınca da silinmez.
            karisik = {"LD_LIBRARY_PATH": os.pathsep.join([self.internal, "/opt/kendi"])}
            bir = pk.alt_surec_ortami(karisik)
            self.assertEqual(bir["LD_LIBRARY_PATH"], "/opt/kendi")
            self.assertEqual(pk.alt_surec_ortami(bir)["LD_LIBRARY_PATH"], "/opt/kendi")

    def test_paketli_degilse_dokunulmaz(self):
        with self._paketli("linux", paketli=False):
            ortam = pk.alt_surec_ortami({"LD_LIBRARY_PATH": "/x"})
        self.assertEqual(ortam, {"LD_LIBRARY_PATH": "/x"})

    def test_varsayilan_os_environ_kopyasi(self):
        with self._paketli("linux", paketli=False), \
                mock.patch.dict(os.environ, {"TURKOD_DENEME_DEGISKENI": "1"}):
            ortam = pk.alt_surec_ortami()
            self.assertEqual(ortam["TURKOD_DENEME_DEGISKENI"], "1")
            self.assertIsNot(ortam, os.environ)

    def test_macos_dyld_ve_homebrew(self):
        env = {"DYLD_LIBRARY_PATH": self.internal, "DYLD_FRAMEWORK_PATH_ORIG": "/F",
               "DYLD_FRAMEWORK_PATH": self.internal,
               "PATH": os.pathsep.join(["/usr/bin", "/bin", "/usr/local/bin"])}
        with self._paketli("darwin"):
            ortam = pk.alt_surec_ortami(env)
        self.assertNotIn("DYLD_LIBRARY_PATH", ortam)
        self.assertEqual(ortam["DYLD_FRAMEWORK_PATH"], "/F")
        self.assertEqual(ortam["PYTHONDONTWRITEBYTECODE"], "1")
        self.assertEqual(ortam["PATH"].split(os.pathsep),
                         ["/usr/bin", "/bin", "/usr/local/bin", "/opt/homebrew/bin",
                          "/opt/homebrew/sbin"])

    def test_windows_oldugu_gibi(self):
        env = {"PATH": r"C:\x", "LD_LIBRARY_PATH": "y"}
        with self._paketli("win32"):
            self.assertIs(pk.alt_surec_ortami(env), env)


class PathTamamlaTestleri(unittest.TestCase):
    def test_macos_homebrew_sona_eklenir(self):
        ev = os.path.join(os.sep, "ev")
        with sistem("darwin"), mock.patch.dict(os.environ, {
                "PATH": os.pathsep.join(["/usr/bin", "/bin"]), "HOME": ev, "USERPROFILE": ev}):
            pk.path_tamamla()
            parcalar = os.environ["PATH"].split(os.pathsep)
            pk.path_tamamla()   # ikinci kez: değişmez
            self.assertEqual(os.environ["PATH"].split(os.pathsep), parcalar)
        self.assertEqual(parcalar[:2], ["/usr/bin", "/bin"])
        self.assertEqual(parcalar[2:5], ["/opt/homebrew/bin", "/opt/homebrew/sbin",
                                         "/usr/local/bin"])
        self.assertEqual(parcalar[5], os.path.join(ev, ".local", "bin"))

    def test_mikrofon_homebrew_soxu_bulur(self):
        """Finder'dan açılınca PATH'te Homebrew yoktu: sox bulunamıyordu."""
        def which(ad):
            for d in os.environ["PATH"].split(os.pathsep):
                if d == "/opt/homebrew/bin" and ad == "rec":
                    return "/opt/homebrew/bin/rec"
            return None
        with sistem("darwin"), mock.patch.dict(os.environ, {"PATH": "/usr/bin"}), \
                mock.patch.object(shutil, "which", side_effect=which):
            self.assertIsNone(pk.mikrofon_komutu(16000))
            pk.path_tamamla()
            self.assertEqual(pk.mikrofon_komutu(16000)[0], "/opt/homebrew/bin/rec")

    def test_windows_degismez(self):
        with sistem("win32"), mock.patch.dict(os.environ, {"PATH": r"C:\a"}):
            pk.path_tamamla()
            self.assertEqual(os.environ["PATH"], r"C:\a")

    def test_linux_yerel_bin(self):
        ev = os.path.join(os.sep, "ev")
        with sistem("linux"), mock.patch.dict(os.environ, {
                "PATH": "/usr/bin", "HOME": ev, "USERPROFILE": ev}):
            pk.path_tamamla()
            self.assertEqual(os.environ["PATH"].split(os.pathsep),
                             ["/usr/bin", os.path.join(ev, ".local", "bin")])

    def test_backend_main_acilista_cagirir(self):
        with open(os.path.join(KOK, "backend_main.py"), encoding="utf-8") as f:
            kaynak = f.read()
        self.assertIn("_pk.path_tamamla()", kaynak)
        self.assertIn("_pk.alt_surec_ortami()", kaynak)


class YaziTipiTestleri(unittest.TestCase):
    def test_linux_fc_list(self):
        cikti = ("DejaVu Sans,DejaVu Sans Condensed\nNoto Sans\nDejaVu Sans\n"
                 "Ubuntu Mono\\-Bold,Ubuntu\n\n")
        with sistem("linux"), mock.patch.object(
                subprocess, "run", return_value=mock.Mock(returncode=0, stdout=cikti)) as r:
            aileler = pk.yazi_tipi_aileleri()
        self.assertEqual(r.call_args[0][0], ["fc-list", ":", "family"])
        self.assertEqual(aileler, ["DejaVu Sans", "DejaVu Sans Condensed", "Noto Sans",
                                   "Ubuntu", "Ubuntu Mono-Bold"])

    def test_linux_fc_list_yoksa_none(self):
        with sistem("linux"), mock.patch.object(subprocess, "run",
                                                side_effect=FileNotFoundError()):
            self.assertIsNone(pk.yazi_tipi_aileleri())

    def test_macos_ayri_surecte_tk(self):
        """macOS'ta Tk bu süreçte açılmaz (AppKit ana iş parçacığı dışında çöker):
        aileler ayrı bir Python sürecinden JSON olarak gelir."""
        with sistem("darwin"), mock.patch.object(sys, "frozen", False, create=True), \
                mock.patch.object(subprocess, "run", return_value=mock.Mock(
                    returncode=0, stdout='["Menlo", "Arial", "Menlo"]\n')) as r:
            aileler = pk.yazi_tipi_aileleri()
        komut = r.call_args[0][0]
        self.assertEqual(komut[:2], [sys.executable, "-c"])
        self.assertIn("r.withdraw()", komut[2])
        self.assertIn("json.dumps", komut[2])
        self.assertEqual(r.call_args.kwargs["timeout"], 15)
        self.assertEqual(aileler, ["Arial", "Menlo"])

    def test_macos_paketli_gomulu_python(self):
        kok = tempfile.mkdtemp(prefix="turkod_pk_")
        self.addCleanup(shutil.rmtree, kok, True)
        backend = os.path.join(kok, "backend")
        st = contextlib.ExitStack()
        self.addCleanup(st.close)
        st.enter_context(sistem("darwin"))
        st.enter_context(mock.patch.object(sys, "frozen", True, create=True))
        st.enter_context(mock.patch.object(sys, "executable",
                                           os.path.join(backend, "turkod_backend")))
        run = st.enter_context(mock.patch.object(subprocess, "run", return_value=mock.Mock(
            returncode=0, stdout='["Menlo"]')))
        # Gömülü Python yoksa PyInstaller ikilisi çalıştırılmaz: None.
        self.assertIsNone(pk.yazi_tipi_aileleri())
        run.assert_not_called()
        python = os.path.join(backend, "_internal", "python_embed", "bin", "python3")
        os.makedirs(os.path.dirname(python))
        open(python, "w").close()
        self.assertEqual(pk.yazi_tipi_aileleri(), ["Menlo"])
        self.assertEqual(run.call_args[0][0][0], python)

    def test_macos_hata_none(self):
        with sistem("darwin"), mock.patch.object(sys, "frozen", False, create=True), \
                mock.patch.object(subprocess, "run", side_effect=subprocess.TimeoutExpired("x", 15)):
            self.assertIsNone(pk.yazi_tipi_aileleri())

    def test_windows_none(self):
        with sistem("win32"):
            self.assertIsNone(pk.yazi_tipi_aileleri())


class TerminalAdaylariTestleri(unittest.TestCase):
    def test_sira(self):
        adlar = [ad for ad, _ in linux.TERMINALLER]
        self.assertEqual(adlar[0], "xdg-terminal-exec")
        self.assertEqual(adlar[-1], "x-terminal-emulator")
        for ad in ("ptyxis", "kgx", "gnome-terminal", "konsole", "xfce4-terminal",
                   "mate-terminal", "tilix", "foot", "wezterm", "alacritty", "kitty", "xterm"):
            self.assertIn(ad, adlar)
        onek = dict(linux.TERMINALLER)
        self.assertEqual(onek["wezterm"], ("start", "--"))
        self.assertEqual(onek["xdg-terminal-exec"], ())
        self.assertEqual(onek["kgx"], ("--",))

    def test_xdg_terminal_exec_once(self):
        bulunan = {"xdg-terminal-exec": "/usr/bin/xdg-terminal-exec",
                   "x-terminal-emulator": "/usr/bin/x-terminal-emulator"}
        with mock.patch.object(shutil, "which", side_effect=bulunan.get), \
                mock.patch.object(subprocess, "Popen") as p:
            self.assertTrue(linux.terminalde_ac(["turkod", "kabuk"]))
        self.assertEqual(p.call_args[0][0], ["/usr/bin/xdg-terminal-exec", "turkod", "kabuk"])
        self.assertIn("env", p.call_args.kwargs)

    def test_terminal_yoksa_turkce_neden(self):
        with sistem("linux"), mock.patch.object(shutil, "which", return_value=None):
            self.assertFalse(pk.terminalde_ac(["turkod"]))
            self.assertIn("Terminal programı bulunamadı", pk.son_terminal_hatasi())

    def test_terminal_paket_kutuphanesini_almaz(self):
        kok = tempfile.mkdtemp(prefix="turkod_pk_")
        self.addCleanup(shutil.rmtree, kok, True)
        internal = os.path.join(kok, "_internal")
        with sistem("linux"), mock.patch.object(sys, "frozen", True, create=True), \
                mock.patch.object(sys, "_MEIPASS", internal, create=True), \
                mock.patch.dict(os.environ, {"LD_LIBRARY_PATH": internal}), \
                mock.patch.object(shutil, "which", side_effect={"xterm": "/usr/bin/xterm"}.get), \
                mock.patch.object(subprocess, "Popen") as p:
            linux.terminalde_ac(["turkod"])
        self.assertNotIn("LD_LIBRARY_PATH", p.call_args.kwargs["env"])

    def test_macos_otomasyon_izni_yok(self):
        hata = "execution error: Not authorized to send Apple events to Terminal. (-1743)"
        with sistem("darwin"), mock.patch.object(
                subprocess, "run", return_value=mock.Mock(returncode=1, stderr=hata)):
            self.assertFalse(pk.terminalde_ac(["turkod"]))
            self.assertIn("Otomasyon", pk.son_terminal_hatasi())

    def test_macos_baska_hata_false(self):
        with sistem("darwin"), mock.patch.object(
                subprocess, "run", return_value=mock.Mock(returncode=1, stderr="x")):
            self.assertFalse(pk.terminalde_ac(["turkod"]))
            self.assertEqual(pk.son_terminal_hatasi(), "Terminal açılamadı.")

    def test_macos_zaman_asimi_false(self):
        with sistem("darwin"), mock.patch.object(
                subprocess, "run", side_effect=subprocess.TimeoutExpired("osascript", 20)):
            self.assertFalse(pk.terminalde_ac(["turkod"]))
            self.assertIn("izin", pk.son_terminal_hatasi())


class KabukPathTestleri(unittest.TestCase):
    """path_e_ekle: ~/.local/bin kabuğun PATH'inde değilse kabuğun açılış dosyasına
    işaretli satır eklenir; path_ten_cikar geri alır. Gerçek ev klasörüne YAZILMAZ."""

    def setUp(self):
        self.kok = tempfile.mkdtemp(prefix="turkod_pk_")
        self.addCleanup(shutil.rmtree, self.kok, True)
        self.backend = os.path.join(self.kok, "kurulum", "backend")
        os.makedirs(self.backend)
        open(os.path.join(self.backend, "turkod"), "w").close()
        self.ev = os.path.join(self.kok, "ev")
        os.makedirs(self.ev)
        self.st = contextlib.ExitStack()
        self.addCleanup(self.st.close)
        self.st.enter_context(sistem("linux"))
        self.st.enter_context(mock.patch.object(sys, "frozen", True, create=True))
        self.st.enter_context(mock.patch.object(sys, "executable",
                                                os.path.join(self.backend, "turkod_backend")))
        self.st.enter_context(mock.patch.dict(os.environ, {
            "HOME": self.ev, "USERPROFILE": self.ev,
            "XDG_DATA_HOME": os.path.join(self.ev, "veri")}))
        os.environ.pop("APPIMAGE", None)
        self.st.enter_context(mock.patch.object(os, "symlink"))
        self.kabuk_path = ""   # giriş kabuğunun bildirdiği PATH
        self.run = self.st.enter_context(mock.patch.object(
            subprocess, "run", side_effect=lambda *a, **k: mock.Mock(
                returncode=0, stdout=self.kabuk_path)))

    def _kabuk(self, ad):
        self.st.enter_context(mock.patch.dict(os.environ, {"SHELL": f"/bin/{ad}"}))

    def _oku(self, *yol):
        with open(os.path.join(self.ev, *yol), encoding="utf-8") as f:
            return f.read()

    def test_zsh_zprofile(self):
        self._kabuk("zsh")
        self.kabuk_path = "/usr/bin:/bin"
        pk.path_e_ekle()
        pk.path_e_ekle()   # ikinci kez: satır yinelenmez
        icerik = self._oku(".zprofile")
        self.assertEqual(icerik.count(_posix.KABUK_IZI), 1)
        self.assertIn('export PATH="$HOME/.local/bin:$PATH"', icerik)
        # Giriş kabuğu temiz bir PATH ile sorulur (bu sürecin PATH'i karışmaz).
        komut = self.run.call_args[0][0]
        self.assertEqual(komut[:3], ["/bin/zsh", "-l", "-c"])
        self.assertEqual(self.run.call_args.kwargs["env"]["PATH"], "/usr/bin:/bin:/usr/sbin:/sbin")
        pk.path_ten_cikar()
        self.assertNotIn(_posix.KABUK_IZI, self._oku(".zprofile"))
        self.assertNotIn(".local/bin", self._oku(".zprofile"))

    def test_bash_bashrc_ve_profile_var_olan_icerik_korunur(self):
        self._kabuk("bash")
        with open(os.path.join(self.ev, ".bashrc"), "w", encoding="utf-8") as f:
            f.write("alias ll='ls -l'")   # sonunda satır sonu yok
        pk.path_e_ekle()
        bashrc = self._oku(".bashrc")
        self.assertTrue(bashrc.startswith("alias ll='ls -l'\n" + _posix.KABUK_IZI))
        self.assertIn(_posix.KABUK_IZI, self._oku(".profile"))
        pk.path_ten_cikar()
        self.assertEqual(self._oku(".bashrc"), "alias ll='ls -l'\n")

    def test_fish_conf_d(self):
        self._kabuk("fish")
        pk.path_e_ekle()
        yol = (".config", "fish", "conf.d", "turkod.fish")
        self.assertIn("fish_add_path -g $HOME/.local/bin", self._oku(*yol))
        self.assertEqual(self.run.call_args[0][0][-1], "string join : $PATH")
        pk.path_ten_cikar()
        self.assertFalse(os.path.exists(os.path.join(self.ev, *yol)))

    def test_kabuk_pathi_cozumlenir(self):
        self._kabuk("bash")
        self.kabuk_path = "giriş iletisi\n/usr/bin:/ev/.local/bin:/bin"
        self.assertTrue(_posix.kabuk_pathinde_mi("/ev/.local/bin"))
        self.kabuk_path = "/usr/bin:/bin"
        self.assertFalse(_posix.kabuk_pathinde_mi("/ev/.local/bin"))
        self.kabuk_path = ""
        self.assertIsNone(_posix.kabuk_pathinde_mi("/ev/.local/bin"))   # bilinmiyor

    def test_zaten_pathteyse_dokunulmaz(self):
        self._kabuk("bash")
        # (Windows'ta sürücü harfindeki ":" PATH'i bölerdi: çözümleme ayrı sınanır.)
        self.st.enter_context(mock.patch.object(_posix, "kabuk_pathinde_mi", return_value=True))
        pk.path_e_ekle()
        self.assertFalse(os.path.exists(os.path.join(self.ev, ".bashrc")))
        self.assertFalse(os.path.exists(os.path.join(self.ev, ".profile")))

    def test_durum_pathte_degilse_kapali(self):
        self._kabuk("bash")
        self.kabuk_path = "/usr/bin:/bin"
        with mock.patch.object(_posix, "path_durumu", return_value=(True, False)):
            self.assertFalse(entegrasyon.durum()["path"])     # bağlantı var, PATH'te yok
            pk.path_e_ekle()
            self.assertTrue(entegrasyon.durum()["path"])      # satır yazıldı


class LinuxIliskiHatalariTestleri(unittest.TestCase):
    def setUp(self):
        self.kok = tempfile.mkdtemp(prefix="turkod_pk_")
        self.addCleanup(shutil.rmtree, self.kok, True)
        st = contextlib.ExitStack()
        self.addCleanup(st.close)
        st.enter_context(sistem("linux"))
        st.enter_context(mock.patch.object(sys, "frozen", True, create=True))
        st.enter_context(mock.patch.object(sys, "executable",
                                           os.path.join(self.kok, "b", "turkod_backend")))
        st.enter_context(mock.patch.dict(os.environ, {
            "XDG_DATA_HOME": os.path.join(self.kok, "veri")}))
        os.environ.pop("APPIMAGE", None)

    def test_xdg_utils_yoksa_turkce_hata(self):
        def calistir(komut, **k):
            if komut[0] == "xdg-mime":
                raise FileNotFoundError(komut[0])
            return mock.Mock(returncode=0)
        with mock.patch.object(subprocess, "run", side_effect=calistir):
            with self.assertRaises(pk.PlatformHatasi) as h:
                pk.dosya_iliskisi_kur()
        self.assertIn("'xdg-utils' paketi kurulu olmalı", str(h.exception))

    def test_basarisiz_arac_listelenir(self):
        with mock.patch.object(subprocess, "run", return_value=mock.Mock(returncode=1)):
            with self.assertRaises(pk.PlatformHatasi) as h:
                pk.dosya_iliskisi_kur()
        for paket in ("shared-mime-info", "desktop-file-utils", "xdg-utils"):
            self.assertIn(paket, str(h.exception))

    def test_calistir_basariyi_dondurur(self):
        with mock.patch.object(subprocess, "run", return_value=mock.Mock(returncode=0)):
            self.assertTrue(linux._calistir(["x"]))
        with mock.patch.object(subprocess, "run", side_effect=OSError()):
            self.assertFalse(linux._calistir(["x"]))

    def test_exec_kacislari(self):
        self.assertEqual(linux._exec_argumani("/opt/TurKod/turkod_backend"),
                         '"/opt/TurKod/turkod_backend"')
        self.assertEqual(linux._exec_argumani('/a b/%x"$`'),
                         '"/a b/%%x\\\\"\\\\$\\\\`"')
        self.assertEqual(linux._exec_argumani("/a\\b"), '"/a\\\\\\\\b"')


class PosixEkTestleri(unittest.TestCase):
    def test_children_dosyasi_yoksa_pgrep(self):
        """/proc/<pid>/task var ama children dosyası yok (CONFIG_PROC_CHILDREN):
        eskiden alt süreçler hiç bulunmuyordu."""
        with mock.patch.object(_posix.os.path, "isdir", return_value=True), \
                mock.patch.object(_posix.os, "listdir", return_value=["10"]), \
                mock.patch("builtins.open", side_effect=FileNotFoundError()), \
                mock.patch.object(subprocess, "run", return_value=mock.Mock(stdout="11\n")) as r:
            self.assertEqual(_posix._cocuklar(10), [11])
        self.assertEqual(r.call_args[0][0], ["pgrep", "-P", "10"])

    def test_children_dosyasi_varsa_pgrep_yok(self):
        with mock.patch.object(_posix.os.path, "isdir", return_value=True), \
                mock.patch.object(_posix.os, "listdir", return_value=["10"]), \
                mock.patch("builtins.open", mock.mock_open(read_data="12 13")), \
                mock.patch.object(subprocess, "run") as r:
            self.assertEqual(_posix._cocuklar(10), [12, 13])
        r.assert_not_called()

    def test_ebeveyn_degisince_biter(self):
        """Ebeveyn ölüp süreç init'e geçince (getppid değişir) pid yaşıyor görünse
        de (numara başka sürece verilmiş olabilir) bitince çağrılır."""
        bitti = threading.Event()
        ebeveynler = iter([42, 42, 1])
        with mock.patch.object(_posix, "surec_yasiyor", return_value=True), \
                mock.patch.object(os, "getppid", side_effect=lambda: next(ebeveynler, 1)):
            _posix.ebeveyni_izle(42, bitti.set, aralik=0.01)
            self.assertTrue(bitti.wait(5))

    def test_ebeveyn_degilse_getppid_bakilmaz(self):
        bitti = threading.Event()
        durumlar = iter([True, True, False])
        with mock.patch.object(_posix, "surec_yasiyor", side_effect=lambda p: next(durumlar, False)), \
                mock.patch.object(os, "getppid", return_value=7):
            _posix.ebeveyni_izle(42, bitti.set, aralik=0.01)
            self.assertTrue(bitti.wait(5))

    def test_sarmalayici_yolu_tirnaklanir(self):
        metin = _posix._sarmalayici_metni("/home/a b/$x`y`/T.AppImage")
        self.assertIn("exec '/home/a b/$x`y`/T.AppImage' --turkod \"$@\"", metin)


class AppImageEditorTestleri(unittest.TestCase):
    def test_editor_appimage_ile_baslar(self):
        kok = tempfile.mkdtemp(prefix="turkod_pk_")
        self.addCleanup(shutil.rmtree, kok, True)
        appimage = os.path.join(kok, "TurKod.AppImage")
        open(appimage, "w").close()
        with sistem("linux"), mock.patch.dict(os.environ, {"APPIMAGE": appimage}), \
                mock.patch.object(subprocess, "Popen") as p:
            self.assertEqual(linux.editor_dosyasi(os.path.join(kok, "mount", "backend")),
                             appimage)
            self.assertTrue(pk.editoru_ayri_baslat(
                os.path.join(kok, "mount", "turkod_flutter"), ["a.trpy"]))
        self.assertEqual(p.call_args[0][0], [appimage, os.path.abspath("a.trpy")])
        self.assertTrue(p.call_args.kwargs["start_new_session"])

    def test_apprun_dosya_argumaniyla_editor_acar(self):
        with open(os.path.join(KOK, "platformlar", "linux", "AppRun"), encoding="utf-8") as f:
            apprun = f.read()
        self.assertIn('exec "$UYGULAMA/turkod_flutter" "$@"', apprun)

    def test_appimage_yoksa_eski_yol(self):
        with sistem("linux"), mock.patch.dict(os.environ, {"APPIMAGE": ""}), \
                mock.patch.object(subprocess, "Popen") as p:
            pk.editoru_ayri_baslat("/opt/turkod/turkod_flutter", [])
        self.assertEqual(p.call_args[0][0], ["/opt/turkod/turkod_flutter"])


class MacosEkTestleri(unittest.TestCase):
    def test_editor_open_a_ile(self):
        kok = tempfile.mkdtemp(prefix="turkod_pk_")
        self.addCleanup(shutil.rmtree, kok, True)
        paket = os.path.join(kok, "TurKod.app")
        exe = os.path.join(paket, "Contents", "MacOS", "TurKod")
        os.makedirs(os.path.dirname(exe))
        with sistem("darwin"), mock.patch.object(subprocess, "Popen") as p:
            self.assertTrue(pk.editoru_ayri_baslat(exe, ["a.trpy"]))
        self.assertEqual(p.call_args[0][0], ["open", "-a", paket, os.path.abspath("a.trpy")])

    def test_say_tire_ile_baslayan_metin(self):
        with mock.patch.object(shutil, "which", return_value="/usr/bin/say"), \
                mock.patch.object(macos, "_turkce_ses_var_mi", return_value=False), \
                mock.patch.object(_posix, "sesli_oku") as oku:
            macos.konus("-5 derece")
        self.assertEqual(oku.call_args[0][0], ["say", " -5 derece"])

    def test_gecici_konumda_uyari(self):
        for yol in ("/private/var/folders/x/AppTranslocation/ABC/d/TurKod.app/Contents/"
                    "Resources/backend", "/Volumes/TürKod/TurKod.app/Contents/Resources/backend"):
            with sistem("darwin"), mock.patch.object(macos, "backend_dizini", return_value=yol):
                with self.assertRaises(pk.PlatformHatasi) as h:
                    pk.path_e_ekle()
                self.assertIn("Uygulamalar klasörüne taşı", str(h.exception))
                with self.assertRaises(pk.PlatformHatasi):
                    pk.dosya_iliskisi_kur()
        with sistem("darwin"), mock.patch.object(
                macos, "backend_dizini",
                return_value="/Applications/TurKod.app/Contents/Resources/backend"):
            self.assertIsNone(pk.dosya_iliskisi_kur())


class PaketIzinleriTestleri(unittest.TestCase):
    def _plist(self, *yol):
        import plistlib
        with open(os.path.join(KOK, *yol), "rb") as f:
            return plistlib.load(f)

    def test_info_plist_izin_metinleri(self):
        info = self._plist("turkod_flutter", "macos", "Runner", "Info.plist")
        self.assertIn("mikrofon", info["NSMicrophoneUsageDescription"])
        self.assertIn("Terminal", info["NSAppleEventsUsageDescription"])

    def test_entitlements(self):
        for yol in (("turkod_flutter", "macos", "Runner", "Release.entitlements"),
                    ("turkod_flutter", "macos", "Runner", "DebugProfile.entitlements"),
                    ("platformlar", "macos", "backend.entitlements")):
            izin = self._plist(*yol)
            self.assertTrue(izin.get("com.apple.security.device.audio-input"), yol)
            self.assertTrue(izin.get("com.apple.security.automation.apple-events"), yol)

    def test_linux_masaustu_kimligi(self):
        with open(os.path.join(KOK, "platformlar", "linux", "turkod.desktop"),
                  encoding="utf-8") as f:
            self.assertIn("StartupWMClass=org.turkod.TurKod\n", f.read())
        with open(os.path.join(KOK, "platformlar", "linux", "build_linux.sh"),
                  encoding="utf-8") as f:
            self.assertIn("org.turkod.TurKod.desktop", f.read())
        with open(os.path.join(KOK, "turkod_flutter", "linux", "CMakeLists.txt"),
                  encoding="utf-8") as f:
            self.assertIn('set(APPLICATION_ID "org.turkod.TurKod")', f.read())

    def test_ic_belge_pakete_girmez(self):
        for yol in (("platformlar", "linux", "build_linux.sh"),
                    ("platformlar", "macos", "build_macos.sh"), ("build_release.ps1",)):
            with open(os.path.join(KOK, *yol), encoding="utf-8-sig") as f:
                self.assertIn("KITAP_BAKIM.md", f.read(), yol)


if __name__ == "__main__":
    unittest.main()
