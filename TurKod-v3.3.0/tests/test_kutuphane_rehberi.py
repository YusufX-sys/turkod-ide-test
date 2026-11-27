"""Kütüphane Rehberi ve yeni kütüphane çevirileri (chess, llama_cpp, pandas,
customtkinter, torch, transformers)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from turkod_ide import kutuphane_rehberi as rehber  # noqa: E402
from turkod_ide.converter import (MODUL_CEVIRILERI, python_kodu_turkceye_cevir,  # noqa: E402
                                  turkce_kodu_donustur)
from turkod_ide.kutuphane_aciklamalari import ACIKLAMALAR  # noqa: E402


class RehberIcerigi(unittest.TestCase):
    def test_her_kutuphanenin_aciklamasi_var(self):
        eksik = [o["py"] for o in rehber.kutuphane_listesi()["kutuphaneler"]
                 if o["py"] not in ACIKLAMALAR]
        self.assertEqual(eksik, [])

    def test_alanlar_dolu_ve_kategori_bilinen(self):
        for py, v in ACIKLAMALAR.items():
            with self.subTest(py=py):
                for alan in ("ad", "ozet", "aciklama", "ornek"):
                    self.assertTrue(str(v.get(alan) or "").strip(), alan)
                self.assertIn(v["kategori"], rehber.KATEGORI_SIRASI)
                self.assertGreaterEqual(v["aciklama"].count("\n\n"), 2)
                if not v["standart"]:
                    self.assertTrue(v["pip_adi"])

    def test_ornekler_derlenir(self):
        for py, v in ACIKLAMALAR.items():
            with self.subTest(py=py):
                compile(v["ornek"], py, "exec")

    def test_ornegin_turkod_hali_python_a_geri_doner(self):
        for py in ("math", "pandas", "chess", "torch", "customtkinter", "llama_cpp"):
            with self.subTest(py=py):
                a = rehber.kutuphane_ayrintisi(py)
                self.assertTrue(a["ok"])
                self.assertTrue(a["ornek_turkod"])
                compile(turkce_kodu_donustur(a["ornek_turkod"]), py, "exec")

    def test_ayrinti_uyeler_ve_metotlar(self):
        a = rehber.kutuphane_ayrintisi("chess")
        self.assertIn("satranç", a["turkce_adlar"])
        self.assertEqual(a["kurulum"], "pip yükle satranç")
        self.assertIn(["Tahta", "Board"], a["uyeler"])
        self.assertTrue(any(p == "push" for _, p in a["metotlar"]))
        self.assertIsNone(rehber.kutuphane_ayrintisi("math")["kurulum"])

    def test_bilinmeyen_kutuphane(self):
        self.assertFalse(rehber.kutuphane_ayrintisi("yok_boyle_bir_sey")["ok"])


class YeniCeviriler(unittest.TestCase):
    def test_modul_adlari(self):
        self.assertEqual(MODUL_CEVIRILERI["satranç"], "chess")
        self.assertEqual(MODUL_CEVIRILERI["llama_kütüphanesi"], "llama_cpp")

    def test_satranc_kodu(self):
        kod = turkce_kodu_donustur(
            "içe_aktar satranç\n"
            "tahta = satranç.Tahta()\n"
            "tahta.hamle_oyna(satranç.Hamle.uciden(\"e2e4\"))\n")
        self.assertIn("import chess", kod)
        self.assertIn("chess.Board()", kod)
        self.assertIn(".push(", kod)

    def test_satranc_ters_ceviri(self):
        tr = python_kodu_turkceye_cevir("import chess\nb = chess.Board()\nb.push_san('e4')\n")
        self.assertIn("Tahta()", tr)
        self.assertNotIn("push_san", tr)

    def test_pandas_metotlari_geri_doner(self):
        py = ("import pandas as pd\n"
              "df = pd.DataFrame({'a': [1, 2, 2]})\n"
              "print(df.drop_duplicates().value_counts().to_dict())\n")
        tr = python_kodu_turkceye_cevir(py)
        self.assertNotIn("drop_duplicates", tr)
        self.assertEqual(turkce_kodu_donustur(tr).strip(), py.strip())

    def test_torch_tensor_metotlari_geri_doner(self):
        py = ("import torch\n"
              "x = torch.ones(2, requires_grad=True)\n"
              "y = (x * 3).sum()\n"
              "y.backward()\n"
              "print(x.grad.detach().numpy())\n")
        tr = python_kodu_turkceye_cevir(py)
        self.assertNotIn("detach", tr)
        self.assertEqual(turkce_kodu_donustur(tr).strip(), py.strip())

    def test_llama_cpp_geri_doner(self):
        py = ("from llama_cpp import Llama\n"
              "m = Llama(model_path='a.gguf', n_ctx=2048)\n"
              "c = m.create_chat_completion(messages=[])\n")
        tr = python_kodu_turkceye_cevir(py)
        self.assertNotIn("create_chat_completion", tr)
        self.assertEqual(turkce_kodu_donustur(tr).strip(), py.strip())


class GidisDonusDuzeltmeleri(unittest.TestCase):
    """Python -> TürKod -> Python çevirisinde yanlış üyeye giden adlar
    (modül tablosu ile düz sözlük aynı Türkçe adı farklı üyelere bağlıyordu)."""

    def gidis_donus(self, py):
        self.assertEqual(turkce_kodu_donustur(python_kodu_turkceye_cevir(py)).strip(),
                         py.strip())

    def test_gecici_dizin(self):
        self.gidis_donus("import tempfile\nwith tempfile.TemporaryDirectory() as k:\n"
                         "    print(k, tempfile.tempdir)\n")

    def test_shutil_copy2(self):
        self.gidis_donus("import shutil\nshutil.copy2('a', 'b')\nshutil.copyfile('a', 'b')\n")

    def test_pyplot_draw_takma_adla(self):
        self.gidis_donus("import matplotlib.pyplot as plt\nplt.plot([1])\nplt.draw()\n")

    def test_pygame_color_modulu(self):
        self.gidis_donus("import pygame\nc = pygame.Color(1, 2, 3)\nprint(pygame.color)\n")

    def test_renk_rgb_her_nesnede(self):
        self.gidis_donus("import docx\nx.font.color.rgb = 1\n")

    def test_numpy_takma_adi_bozulmaz(self):
        self.gidis_donus("import numpy as np\na = np.array([1])\nb = np.arange(3)\n"
                         "c = np.zeros(2, dtype=np.uint8)\n")

    def test_rehber_ornekleri_gidis_donus(self):
        # Kullanıcı adlarının tutarlı yeniden adlandırılması (sinif -> sinif_) ve
        # çalışma anında tanınan renk adları dışında fark olmamalı.
        import ast
        import re
        from turkod_ide.deger_sozlugu import calisma_tablolari
        bilinen = {"collections", "pyglet", "timeit", "trace", "PIL", "pygame",
                   "matplotlib.pyplot", "string"}
        # Renk / stil / tema değerleri bilerek Türkçeleşir ("orange" -> "turuncu");
        # çalışma anında İngilizcesine döner. Karşılaştırmada ikisi de aynı yazıma iner.
        t = calisma_tablolari()
        degerler = {**t["renk"], **t["stil"], **t["tc_stil"], **t["ctk_tema"],
                    **t["ctk_gorunum"]}

        def kelime(k):
            on = k[:3] if k.lower().startswith("on_") else ""
            k = degerler.get(k[len(on):], k[len(on):])
            return on + re.sub(r"[_\-]", "", k.lower()).replace("grey", "gray")

        class Normal(ast.NodeTransformer):
            def visit_Constant(self, d):
                if isinstance(d.value, str):
                    d.value = re.sub(r"\w+", lambda m: kelime(m.group(0)), d.value)
                return d

        def dok(kod):
            return ast.dump(Normal().visit(ast.parse(kod)))

        for py, v in ACIKLAMALAR.items():
            if py in bilinen:
                continue
            with self.subTest(py=py):
                geri = turkce_kodu_donustur(python_kodu_turkceye_cevir(v["ornek"]))
                self.assertEqual(dok(geri), dok(v["ornek"]))


class TurkceKutuphaneAdlari(unittest.TestCase):
    def test_turkce_adla_ice_aktarma(self):
        for tr, beklenen in (("veri_tabloları", "import pandas"),
                             ("derin_öğrenme", "import torch"),
                             ("yerel_dil_modeli", "import llama_cpp"),
                             ("veri_tablolari", "import pandas")):
            with self.subTest(tr=tr):
                self.assertIn(beklenen, turkce_kodu_donustur(f"içe_aktar {tr}\n"))
        kod = turkce_kodu_donustur("den derin_öğrenme içe_aktar sinir_ağı\n"
                                   "içe_aktar web_istekleri\n"
                                   "x = web_istekleri.RequestException\n")
        self.assertIn("from torch import nn", kod)
        self.assertIn("requests.RequestException", kod)

    def test_ters_ceviri_python_adini_korur(self):
        # Kitap ve var olan kodlar için: Python -> TürKod eskisi gibi.
        tr = python_kodu_turkceye_cevir("import pandas as pd\nimport numpy as np\n")
        self.assertIn("içe_aktar pandas olarak pd", tr)
        self.assertIn("içe_aktar numpy olarak np", tr)

    def test_turkce_adla_nesne_metotlari(self):
        kod = turkce_kodu_donustur("içe_aktar pdf_belgeleri\nbelge = pdf_belgeleri.aç()\n"
                                   "sayfa = belge.yeni_sayfa()\n")
        self.assertIn("belge.new_page()", kod)

    def test_rehber_turkce_ad_ve_kurulum(self):
        a = rehber.kutuphane_ayrintisi("pandas")
        self.assertEqual(a["turkce_ad"], "veri_tabloları")
        self.assertEqual(a["turkce_adlar"][0], "veri_tabloları")
        self.assertEqual(a["turkce_adlar"][-1], "pandas")
        self.assertEqual(a["kurulum"], "pip yükle veri_tabloları")
        self.assertIn("içe_aktar veri_tabloları", a["ornek_turkod"])
        self.assertTrue(a["ad"].startswith("Veri Tabloları"))


    def test_aciklamanin_kod_parcalari_turkcelesir(self):
        import ast
        import re
        a = rehber.kutuphane_ayrintisi("chess")
        self.assertIn("`satranç.Tahta()`", a["aciklama_turkod"])
        self.assertIn("`chess.Board()`", a["aciklama"])
        # Her çevrilen parça geri çevrilince aslına döner (yanlış öğretmez).
        desen = re.compile(r"`([^`\n]+)`")
        for py in ("chess", "pandas", "torch", "llama_cpp"):
            d = rehber.kutuphane_ayrintisi(py)
            for asil, tr in zip(desen.findall(d["aciklama"]),
                                desen.findall(d["aciklama_turkod"])):
                if asil == tr:
                    continue
                with self.subTest(py=py, parca=asil):
                    # Parça, okuyucunun programındaki gibi (içe aktarmalar ve
                    # kendi değişkenleri tanımlıyken) TürKod'dan geri
                    # çevrilince aslına dönmeli.
                    gecti = False
                    for baglam in (rehber._ice_aktarma_baglami(py), []):
                        baglam = baglam + [f"{ad} = None"
                                           for ad in rehber._serbest_adlar(asil, baglam)]
                        tr_baglam = rehber._turkce_modul_adiyla(
                            python_kodu_turkceye_cevir("\n".join(baglam)), py).strip("\n")
                        kod = (tr_baglam + "\n" if baglam else "") + tr
                        try:
                            geri = turkce_kodu_donustur(kod)
                            if ast.dump(ast.parse(geri)) == ast.dump(
                                    ast.parse("\n".join(baglam + [asil]))):
                                gecti = True
                                break
                        except SyntaxError:
                            pass
                    self.assertTrue(gecti, f"{asil} -> {tr}")


class CocukKutuphaneleri(unittest.TestCase):
    """2026-11'de eklenen çocuk kütüphaneleri (Pygame Zero, raylib, gpiozero ...)."""

    def test_pygame_zero_turkce_programi(self):
        kod = turkce_kodu_donustur(
            "içe_aktar kolay_oyun\n"
            "GENİŞLİK = 400\n"
            "BAŞLIK = \"Top\"\n"
            "fonksiyon çiz():\n"
            "    ekran.temizle()\n"
            "fonksiyon güncelle():\n"
            "    eğer klavye.sol_ok:\n"
            "        geç\n"
            "fonksiyon tuşa_basılınca(tuş):\n"
            "    eğer tuş == tuşlar.BOŞLUK:\n"
            "        müzik.durdur()\n"
            "fonksiyon fare_basılınca(konum):\n"
            "    oyun_saati.aralıklı_zamanla(güncelle, 1.0)\n"
            "kolay_oyun.oyunu_başlat()\n")
        for parca in ("import pgzrun", "WIDTH = 400", "TITLE = ", "def draw():",
                      "screen.clear()", "def update():", "keyboard.left",
                      "def on_key_down(", "keys.SPACE", "music.stop()",
                      "def on_mouse_down(", "clock.schedule_interval(update", "pgzrun.go()"):
            self.assertIn(parca, kod)

    def test_pygame_zero_olay_parametreleri(self):
        # Pygame Zero parametreleri ADLARINA göre doldurur: "tuş" -> "key" olmalı.
        kod = turkce_kodu_donustur(
            "içe_aktar kolay_oyun\n"
            "fonksiyon tuşa_basılınca(tuş):\n"
            "    yazdır(\"tuş\", tuş)\n"
            "fonksiyon fare_basılınca(konum, düğme):\n"
            "    yazdır(konum, düğme)\n"
            "fonksiyon başka(tuş):\n"
            "    yazdır(tuş)\n")
        self.assertIn("def on_key_down(key):", kod)
        self.assertIn('print("tuş", key)', kod)
        self.assertIn("def on_mouse_down(pos, button):", kod)
        self.assertIn("print(pos, button)", kod)
        self.assertIn("def başka(tuş):", kod)
        # Pygame Zero içe aktarılmamışsa dokunulmaz
        self.assertIn("(tuş)", turkce_kodu_donustur("fonksiyon tuşa_basılınca(tuş):\n    geç\n"))

    def test_ok_tusu_adlari_degiskenleri_bozmaz(self):
        # "sol" / "yukarı" değişken adı olarak kalmalı: kaplumbağanın left/up
        # işlevlerini ezmesin (klavye için sol_ok, yukarı_ok kullanılır).
        kod = turkce_kodu_donustur("sol = 5\nyukarı = 3\nyazdır(sol + yukarı)\n")
        self.assertIn("sol = 5", kod)
        self.assertIn("yukarı = 3", kod)

    def test_yeni_turkce_modul_adlari(self):
        for tr, py in (("içe_aktar hızlı_grafik", "import pyray"),
                       ("içe_aktar fizik_motoru", "import pymunk"),
                       ("içe_aktar etkileşimli_harita", "import folium"),
                       ("içe_aktar hızlı_arayüz olarak dpg", "import dearpygui.dearpygui as dpg"),
                       ("içe_aktar raspberry_pinleri", "import gpiozero"),
                       ("içe_aktar renk_dönüşümleri", "import colorsys")):
            with self.subTest(tr=tr):
                self.assertIn(py, turkce_kodu_donustur(tr + "\n"))

    def test_raylib_yildizli_ice_aktarma_gidis_donus(self):
        # Modül tablosundaki Türkçe ad ortak sözlükte başka anlama gelmemeli
        # (eskiden draw_text -> yazı_yaz -> text oluyordu).
        py = ("from pyray import *\n"
              "init_window(400, 300, \"a\")\n"
              "draw_text(\"b\", 1, 2, 20, RED)\n"
              "wait_time(1)\n")
        self.assertEqual(turkce_kodu_donustur(python_kodu_turkceye_cevir(py)).strip(),
                         py.strip())

    def test_pymupdf_nesne_tablosu_yalnizca_pymupdf_ile(self):
        py = ("from pypdf import PdfReader\nr = PdfReader(\"a.pdf\")\n"
              "for sayfa in r.pages:\n    print(sayfa.rotation)\n")
        self.assertEqual(turkce_kodu_donustur(python_kodu_turkceye_cevir(py)).strip(),
                         py.strip())

    def test_pgzero_ic_paketi_rehberde_gizli(self):
        adlar = {o["py"] for o in rehber.kutuphane_listesi()["kutuphaneler"]}
        self.assertIn("pgzrun", adlar)
        self.assertNotIn("pgzero", adlar)
        self.assertEqual(rehber.kutuphane_ayrintisi("pgzrun")["kurulum"], "pip yükle kolay_oyun")


class TurkcePip(unittest.TestCase):
    def setUp(self):
        from turkod_ide import pip_tr
        self.pip = pip_tr

    def cevir(self, komut):
        return self.pip.pip_komutu_cevir(komut, "python", "PAKET")

    def test_turkce_ad_pip_paketine_cevrilir(self):
        self.assertTrue(self.cevir("pip yükle satranç").endswith(" chess"))
        self.assertTrue(self.cevir("pip yukle veri_tablolari").endswith(" pandas"))
        self.assertIn('"pandas==2.2"', self.cevir("pip yükle veri_tabloları==2.2"))
        self.assertIn("uninstall -y torch", self.cevir("pip sil derin_öğrenme"))
        self.assertTrue(self.cevir("pip yükle cv2").endswith(" opencv-python"))
        self.assertTrue(self.cevir("pip yükle docx").endswith(" python-docx"))
        self.assertTrue(self.cevir("pip yükle requests").endswith(" requests"))
        # Çocuk kütüphaneleri; "serial" PyPI'de başka (yanlış) bir paket.
        self.assertTrue(self.cevir("pip yükle kolay_oyun").endswith(" pgzero"))
        self.assertTrue(self.cevir("pip yükle hızlı_grafik").endswith(" raylib"))
        self.assertTrue(self.cevir("pip yükle serial").endswith(" pyserial"))
        self.assertTrue(self.cevir("pip yükle karekod").endswith(' "qrcode[pil]"'))
        self.assertNotIn("install", self.cevir("pip yükle renk_dönüşümleri"))
        self.assertTrue(self.cevir("pip yükle -r gereksinimler.txt").endswith(
            "-r gereksinimler.txt"))

    def test_standart_kutuphane_kurulmaz(self):
        komut = self.cevir("pip yükle matematik")
        self.assertNotIn("install", komut)
        self.assertIn("print(", komut)
        self.assertTrue(komut.isascii())

    def test_linux_macos_kabuk_sozdizimi(self):
        from unittest import mock
        for ad in ("linux", "darwin"):
            with self.subTest(ad=ad), mock.patch.object(sys, "platform", ad):
                liste = self.cevir("pip listele")
                self.assertTrue(liste.startswith("PYTHONPATH=PAKET "), liste)
                self.assertNotIn("set ", liste)
                self.assertIn("grep -i", self.cevir("pip ara numpy"))
        with mock.patch.object(sys, "platform", "win32"):
            self.assertTrue(self.cevir("pip listele").startswith('set "PYTHONPATH=PAKET"'))
            self.assertIn("findstr", self.cevir("pip ara numpy"))


if __name__ == "__main__":
    unittest.main()
