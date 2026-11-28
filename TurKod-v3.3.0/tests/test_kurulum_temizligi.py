"""Güncellemeden kalan kurulum dosyalarının silinmesi (updater.eski_kurulumlari_temizle)."""
import contextlib
import io
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if KOK not in sys.path:
    sys.path.insert(0, KOK)

with contextlib.redirect_stdout(io.StringIO()):
    from turkod_ide import updater  # noqa: E402


class KurulumTemizligiTesti(unittest.TestCase):
    def setUp(self):
        self._gecici = tempfile.TemporaryDirectory()
        self.dizin = Path(self._gecici.name) / "turkod_guncelleme"
        self.dizin.mkdir()
        self._yama = mock.patch.object(updater, "indirme_klasoru", return_value=self.dizin)
        self._yama.start()
        self._eski = dict(updater._indirme)
        updater._indirme.update(durum="yok", yol="")

    def tearDown(self):
        self._yama.stop()
        updater._indirme.clear()
        updater._indirme.update(self._eski)
        self._gecici.cleanup()

    def _dosya(self, ad, yas_sn=0):
        yol = self.dizin / ad
        yol.write_bytes(b"x")
        if yas_sn:
            t = time.time() - yas_sn
            os.utime(yol, (t, t))
        return yol

    def test_kurulmus_surumun_dosyasi_silinir(self):
        eski = self._dosya("TurKod-Setup-4.0.0.exe")
        daha_eski = self._dosya("TurKod-3.9.1.AppImage")
        self.assertEqual(updater.eski_kurulumlari_temizle("4.0.0"), 2)
        self.assertFalse(eski.exists())
        self.assertFalse(daha_eski.exists())
        # Boş kalan klasör de kaldırılır.
        self.assertFalse(self.dizin.exists())

    def test_daha_yeni_surum_korunur(self):
        yeni = self._dosya("TurKod-Setup-4.1.0.exe")
        self.assertEqual(updater.eski_kurulumlari_temizle("4.0.0"), 0)
        self.assertTrue(yeni.exists())

    def test_yarim_indirme_bir_saat_sonra_silinir(self):
        taze = self._dosya("TurKod-Setup-4.1.0.1234.part")
        bayat = self._dosya("TurKod-Setup-4.1.0.5678.part", yas_sn=7200)
        updater.eski_kurulumlari_temizle("4.0.0")
        self.assertTrue(taze.exists())
        self.assertFalse(bayat.exists())

    def test_baska_dosyalara_dokunulmaz(self):
        baska = self._dosya("notlar.txt")
        updater.eski_kurulumlari_temizle("4.0.0")
        self.assertTrue(baska.exists())

    def test_indirme_surerken_dokunulmaz(self):
        eski = self._dosya("TurKod-Setup-3.0.0.exe")
        updater._indirme["durum"] = "indiriyor"
        self.assertEqual(updater.eski_kurulumlari_temizle("4.0.0"), 0)
        self.assertTrue(eski.exists())

    def test_hazir_bekleyen_kurulum_korunur(self):
        hazir = self._dosya("TurKod-Setup-4.0.0.exe")
        updater._indirme.update(durum="bitti", yol=str(hazir))
        updater.eski_kurulumlari_temizle("4.0.0")
        self.assertTrue(hazir.exists())


if __name__ == "__main__":
    unittest.main()
