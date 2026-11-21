"""Güncelleyicinin Windows, Linux ve macOS yolları (ağ kullanılmaz).

latest.json tek dosyadır; "platforms" alanında her sistemin paketi bulunur. Üst
düzey url/sha256/size alanları Windows kurulumudur (3.3.0 ve öncesi bunları okur).
sys.platform ve ağ taklit edilir; gerçek indirme ya da kurulum yapılmaz.
"""
import contextlib
import hashlib
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if KOK not in sys.path:
    sys.path.insert(0, KOK)

with contextlib.redirect_stdout(io.StringIO()):
    from turkod_ide import updater  # noqa: E402
    import surum_imzala  # noqa: E402

SHA_W, SHA_L, SHA_M = "a" * 64, "b" * 64, "c" * 64


def latest(**ek):
    m = {"version": "9.0.0", "url": "https://x/TurKod-Setup-9.0.0.exe", "sha256": SHA_W,
         "size": 10, "notes": "yeni",
         "platforms": {
             "windows": {"url": "https://x/TurKod-Setup-9.0.0.exe", "sha256": SHA_W, "size": 10},
             "linux-x86_64": {"url": "https://x/TurKod-9.0.0-x86_64.AppImage",
                              "sha256": SHA_L, "size": 20},
             "macos-arm64": {"url": "https://x/TurKod-9.0.0-macos-arm64.dmg",
                             "sha256": SHA_M, "size": 30}}}
    m.update(ek)
    return m


class _Yanit(io.BytesIO):
    def __init__(self, veri):
        super().__init__(veri)
        self.headers = {"Content-Length": str(len(veri))}

    def geturl(self):
        return "https://x"


def sunucu(bildirim):
    """_https_ac taklidi: latest.json ve imzası (imza her zaman 'doğru')."""
    veri = json.dumps(bildirim).encode("utf-8")

    def ac(url):
        return _Yanit(b"imza" if url.endswith(".sig") else veri)
    return contextlib.ExitStack(), ac


class _Taban(unittest.TestCase):
    def setUp(self):
        self.st = contextlib.ExitStack()
        self.addCleanup(self.st.close)
        self.st.enter_context(mock.patch.object(updater, "_imza_dogru_mu", return_value=True))
        self.st.enter_context(mock.patch.object(updater, "mevcut_surum", return_value="3.3.0"))
        self.kok = tempfile.mkdtemp(prefix="turkod_gnc_")
        self.addCleanup(shutil.rmtree, self.kok, True)

    def sistem(self, ad, makine="x86_64", appimage=None):
        st = contextlib.ExitStack()
        st.enter_context(mock.patch.object(sys, "platform", ad))
        st.enter_context(mock.patch.object(updater.platform, "machine", return_value=makine))
        ortam = {"APPIMAGE": appimage} if appimage else {}
        st.enter_context(mock.patch.dict(os.environ, ortam))
        if not appimage:
            os.environ.pop("APPIMAGE", None)
        return st

    def kontrol(self, bildirim):
        _, ac = sunucu(bildirim)
        with mock.patch.object(updater, "_https_ac", side_effect=ac):
            return updater.kontrol_et()


class PaketSecimiTestleri(_Taban):
    def test_paket_anahtari(self):
        for ad, makine, beklenen in (("win32", "AMD64", "windows"),
                                     ("linux", "x86_64", "linux-x86_64"),
                                     ("linux", "aarch64", "linux-aarch64"),
                                     ("darwin", "arm64", "macos-arm64"),
                                     ("darwin", "x86_64", "macos-x86_64")):
            with self.sistem(ad, makine):
                self.assertEqual(updater.paket_anahtari(), beklenen)

    def test_kurulum_turu(self):
        appimage = os.path.join(self.kok, "TurKod.AppImage")
        open(appimage, "w").close()
        with self.sistem("win32"):
            self.assertEqual(updater.kurulum_turu(), "setup")
        with self.sistem("darwin"):
            self.assertEqual(updater.kurulum_turu(), "dmg")
        with self.sistem("linux", appimage=appimage):
            self.assertEqual(updater.kurulum_turu(), "appimage")
        with self.sistem("linux"):
            self.assertIsNone(updater.kurulum_turu())   # .tar.gz kendini güncelleyemez

    def test_windows_eski_bicim_de_okunur(self):
        eski = {"version": "9.0.0", "url": "https://x/s.exe", "sha256": SHA_W, "size": 1}
        with self.sistem("win32"):
            r = self.kontrol(eski)
        self.assertTrue(r["ok"] and r["guncelleme_var"] and r["kurulabilir"])
        self.assertEqual(r["kurulum_turu"], "setup")
        self.assertEqual(updater._son_bildirim["url"], "https://x/s.exe")

    def test_linux_appimage_paketini_secer(self):
        appimage = os.path.join(self.kok, "TurKod.AppImage")
        open(appimage, "w").close()
        with self.sistem("linux", appimage=appimage):
            r = self.kontrol(latest())
        self.assertTrue(r["kurulabilir"])
        self.assertEqual(r["kurulum_turu"], "appimage")
        self.assertEqual(updater._son_bildirim["sha256"], SHA_L)
        self.assertEqual(updater._son_bildirim["tur"], "appimage")

    def test_macos_dmg_paketini_secer(self):
        with self.sistem("darwin", "arm64"):
            r = self.kontrol(latest())
        self.assertTrue(r["kurulabilir"])
        self.assertEqual(updater._son_bildirim["url"], "https://x/TurKod-9.0.0-macos-arm64.dmg")

    def test_paket_yoksa_yeni_surum_var_ama_kurulamaz(self):
        with self.sistem("darwin", "x86_64"):            # macos-x86_64 paketi yok
            r = self.kontrol(latest())
        self.assertTrue(r["ok"] and r["guncelleme_var"])
        self.assertFalse(r["kurulabilir"])
        self.assertEqual(updater._son_bildirim, {})

    def test_tar_gz_kurulumu_kurulamaz(self):
        with self.sistem("linux"):
            r = self.kontrol(latest())
        self.assertTrue(r["guncelleme_var"])
        self.assertFalse(r["kurulabilir"])

    def test_gecersiz_paket_reddedilir(self):
        bozuk = latest()
        bozuk["platforms"]["macos-arm64"]["url"] = "http://x/duz.dmg"
        with self.sistem("darwin", "arm64"):
            self.assertFalse(self.kontrol(bozuk)["ok"])


class IndirmeVeUygulamaTestleri(_Taban):
    def _indir(self, tur, icerik=b"YENI-TURKOD"):
        m = {"version": "9.0.0", "url": "https://x/p", "sha256": hashlib.sha256(icerik).hexdigest(),
             "size": len(icerik), "tur": tur}
        with mock.patch.object(updater.tempfile, "gettempdir", return_value=self.kok), \
                mock.patch.object(updater, "_https_ac", return_value=_Yanit(icerik)):
            return updater._indir(m)

    def test_dosya_adi_kurulum_turune_gore(self):
        for tur, ad in (("setup", "TurKod-Setup-9.0.0.exe"), ("appimage", "TurKod-9.0.0.AppImage"),
                        ("dmg", "TurKod-9.0.0.dmg")):
            r = self._indir(tur)
            self.assertTrue(r["ok"], r)
            self.assertEqual(os.path.basename(r["yol"]), ad)
            self.assertEqual(r["tur"], tur)

    def _hazir(self, tur):
        r = self._indir(tur)
        updater._indirme.update(durum="bitti", yol=r["yol"], sha256=r["sha256"], tur=tur)
        self.addCleanup(updater._indirme.update, durum="yok", yol="", sha256="", tur="")
        return r["yol"]

    def test_appimage_yerinde_yenilenir(self):
        eski = os.path.join(self.kok, "Uygulamalar", "TurKod.AppImage")
        os.makedirs(os.path.dirname(eski))
        with open(eski, "wb") as f:
            f.write(b"ESKI")
        yol = self._hazir("appimage")
        with self.sistem("linux", appimage=eski):
            r = updater.uygula(yol)
        self.assertEqual(r, {"ok": True, "baslat": eski})
        with open(eski, "rb") as f:
            self.assertEqual(f.read(), b"YENI-TURKOD")
        self.assertFalse(os.path.exists(eski + ".yeni"))

    def test_degistirilen_appimage_uygulanmaz(self):
        eski = os.path.join(self.kok, "TurKod.AppImage")
        with open(eski, "wb") as f:
            f.write(b"ESKI")
        yol = self._hazir("appimage")
        with open(yol, "ab") as f:
            f.write(b"!")                              # indirildikten sonra değiştirildi
        with self.sistem("linux", appimage=eski):
            self.assertFalse(updater.uygula(yol)["ok"])
        with open(eski, "rb") as f:
            self.assertEqual(f.read(), b"ESKI")

    def test_appimage_disinda_uygulanmaz(self):
        yol = self._hazir("dmg")
        with self.sistem("darwin"):
            self.assertFalse(updater.uygula(yol)["ok"])


class LatestJsonUretimTestleri(unittest.TestCase):
    def test_windows_ust_duzey_alanlari_doldurur(self):
        b = surum_imzala.bildirim_olustur("9.0.0", "windows", "https://x/s.exe", SHA_W, 10, "not")
        self.assertEqual((b["url"], b["sha256"], b["size"]), ("https://x/s.exe", SHA_W, 10))
        self.assertEqual(b["platforms"]["windows"]["url"], "https://x/s.exe")

    def test_diger_sistemler_eklenir_windows_korunur(self):
        w = surum_imzala.bildirim_olustur("9.0.0", "windows", "https://x/s.exe", SHA_W, 10, "not")
        l = surum_imzala.bildirim_olustur("9.0.0", "linux-x86_64", "https://x/t.AppImage",
                                          SHA_L, 20, "", w)
        m = surum_imzala.bildirim_olustur("9.0.0", "macos-arm64", "https://x/t.dmg",
                                          SHA_M, 30, "", l)
        self.assertEqual(sorted(m["platforms"]), ["linux-x86_64", "macos-arm64", "windows"])
        self.assertEqual(m["url"], "https://x/s.exe")       # eski Windows sürümleri bunu okur
        self.assertEqual(m["notes"], "not")

    def test_linux_tek_basina_ust_duzey_yazmaz(self):
        b = surum_imzala.bildirim_olustur("9.0.0", "linux-x86_64", "https://x/t.AppImage", SHA_L, 1)
        self.assertNotIn("url", b)

    def test_eski_bicimli_mevcut_windows_paketine_donusur(self):
        eski = {"version": "9.0.0", "url": "https://x/s.exe", "sha256": SHA_W, "size": 10}
        b = surum_imzala.bildirim_olustur("9.0.0", "macos-arm64", "https://x/t.dmg", SHA_M, 3,
                                          "", eski)
        self.assertEqual(b["platforms"]["windows"]["url"], "https://x/s.exe")

    def test_baska_surumun_dosyasina_eklenmez(self):
        w = surum_imzala.bildirim_olustur("8.0.0", "windows", "https://x/s.exe", SHA_W, 10)
        with self.assertRaises(ValueError):
            surum_imzala.bildirim_olustur("9.0.0", "linux-x86_64", "https://x/t", SHA_L, 1, "", w)

    def test_uretilen_dosyayi_guncelleyici_okur(self):
        w = surum_imzala.bildirim_olustur("9.0.0", "windows", "https://x/s.exe", SHA_W, 10)
        tam = surum_imzala.bildirim_olustur("9.0.0", "macos-arm64", "https://x/t.dmg", SHA_M, 3,
                                            "", w)
        _, ac = sunucu(tam)
        with mock.patch.object(updater, "_imza_dogru_mu", return_value=True), \
                mock.patch.object(updater, "mevcut_surum", return_value="3.3.0"), \
                mock.patch.object(updater, "_https_ac", side_effect=ac), \
                mock.patch.object(sys, "platform", "darwin"), \
                mock.patch.object(updater.platform, "machine", return_value="arm64"):
            r = updater.kontrol_et()
        self.assertTrue(r["kurulabilir"])
        self.assertEqual(updater._son_bildirim["sha256"], SHA_M)


if __name__ == "__main__":
    unittest.main()
