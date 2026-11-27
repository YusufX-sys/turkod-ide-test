"""Yapay zekânın yazdığı kodda olmayan komut denetimi (kod_adlari).

Kodi'ye yıldız yağmuru istendi; AI Asistan `turtle.save()` ve
`turtle.restore()` yazdı (turtle'da böyle komutlar yok). Kod yalnızca
sözdizimiyle denetlendiği için editöre yazıldı, çalışınca AttributeError
verdi."""
import contextlib
import io
import os
import sys
import unittest
from unittest import mock

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if KOK not in sys.path:
    sys.path.insert(0, KOK)

from turkod_ide import kod_adlari  # noqa: E402

YILDIZ = """import turtle
import random

turtle.speed(0)
turtle.penup()
for _ in range(random.randint(15, 20)):
    size = random.randint(10, 40)
    turtle.save()
    turtle.goto(1, 2)
    for _ in range(5):
        turtle.forward(size)
        turtle.right(144)
    turtle.restore()
turtle.done()
"""


class OlmayanAdTestleri(unittest.TestCase):
    def test_turtle_save_restore_bulunur(self):
        self.assertEqual(kod_adlari.olmayan_adlar(YILDIZ, sys.executable),
                         [(8, "turtle.save"), (13, "turtle.restore")])

    def test_dogru_kod_temiz(self):
        kod = ("import turtle as t\nimport math\nfrom random import randint, choice\n"
               "t.forward(math.pi)\nprint(randint(1, 2), choice([1]))\nt.done()\n")
        self.assertEqual(kod_adlari.olmayan_adlar(kod, sys.executable), [])

    def test_takma_ad_ve_from_import(self):
        kod = "import random as r\nfrom math import kokal\nr.zar_at()\n"
        self.assertEqual(kod_adlari.olmayan_adlar(kod, sys.executable),
                         [(2, "math.kokal"), (3, "random.zar_at")])

    def test_ustune_yazilan_ad_denetlenmez(self):
        # `turtle` sonradan başka bir nesneye bağlanırsa onun adları bilinemez.
        kod = "import turtle\nturtle = turtle.Turtle()\nturtle.save()\n"
        self.assertEqual(kod_adlari.olmayan_adlar(kod, sys.executable), [])

    def test_kurulu_olmayan_modul_ve_atanan_ad_atlanir(self):
        kod = ("import yok_boyle_bir_modul_xyz\nimport math\n"
               "yok_boyle_bir_modul_xyz.x()\nmath.yeni = 1\nprint(math.yeni)\n")
        self.assertEqual(kod_adlari.olmayan_adlar(kod, sys.executable), [])

    def test_tehlikeli_modul_yuklenmez(self):
        self.assertEqual(kod_adlari.olmayan_adlar("import antigravity\nantigravity.x\n",
                                                  sys.executable), [])

    def test_python_yoksa_ya_da_bozuksa_bos(self):
        self.assertEqual(kod_adlari.olmayan_adlar(YILDIZ, None), [])
        self.assertEqual(kod_adlari.olmayan_adlar("import (", sys.executable), [])
        with mock.patch("subprocess.run", side_effect=OSError("yok")):
            self.assertEqual(kod_adlari.olmayan_adlar(YILDIZ, sys.executable), [])


class KodiKodDenetimiTestleri(unittest.TestCase):
    def setUp(self):
        import tempfile
        self.dizin = tempfile.mkdtemp()
        with mock.patch("os.path.expanduser", return_value=self.dizin), \
                contextlib.redirect_stdout(io.StringIO()):
            from turkod_ide.ide_core import IDECore
            self.c = IDECore()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.dizin, ignore_errors=True)

    def test_olmayan_komut_duzelttirilir(self):
        with mock.patch("turkod_ide.platform_katmani.kullanici_python_bul",
                        return_value=sys.executable), \
                contextlib.redirect_stdout(io.StringIO()):
            hata = self.c._kod_denetle(YILDIZ)
            self.assertIn("turtle.save", hata)
            self.assertIn("turtle.restore", hata)
            self.assertEqual(self.c._kod_denetle(YILDIZ.replace("    turtle.save()\n", "")
                                                 .replace("    turtle.restore()\n", "")), "")


if __name__ == "__main__":
    unittest.main()
