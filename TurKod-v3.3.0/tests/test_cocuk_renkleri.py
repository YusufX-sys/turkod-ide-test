"""Yeni kütüphanelerde Türkçe renkler: Python -> TürKod çevirisinde (Kütüphane Rehberi
örnekleri) "orange" -> "turuncu" olur; çalışırken de "turuncu" kütüphanenin kendi adına
çevrilir (Terminal Renkleri, Zengin Yazı, Etkileşimli Harita, customtkinter)."""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from turkod_ide import runner  # noqa: E402
from turkod_ide.converter import (python_kodu_turkceye_cevir,  # noqa: E402
                                  turkce_kodu_donustur)


def tr(kod):
    return python_kodu_turkceye_cevir(kod)


class TersCeviri(unittest.TestCase):
    def test_kolay_oyun(self):
        t = tr("import pgzrun\n\ndef draw():\n"
               "    screen.fill('white')\n"
               "    screen.draw.filled_circle((1, 2), 20, 'orange')\n"
               "    screen.draw.text('red', (10, 10), color='white')\n\npgzrun.go()\n")
        self.assertIn("'beyaz'", t)
        self.assertIn("'turuncu'", t)
        # draw.text'in ilk argümanı ekrana yazılan metindir, renk değil.
        self.assertIn("'red'", t)

    def test_terminal_renkleri(self):
        t = tr("from termcolor import colored, cprint\n"
               "renk = 'green'\n"
               "print(colored('a', 'cyan', 'on_red', attrs=['bold']))\n"
               "cprint('b', color='white', on_color='on_light_blue')\n")
        for beklenen in ("'yeşil'", "'camgöbeği'", "'on_kırmızı'", "'kalın'", "'beyaz'",
                         "'on_açık_mavi'"):
            self.assertIn(beklenen, t)

    def test_zengin_yazi(self):
        t = tr("from rich.console import Console\nc = Console()\n"
               "c.print('[bold red]Kazanan:[/bold red] Kodi [1]', style='cyan')\n"
               "c.print('[link=https://a.b]x[/link]')\n")
        self.assertIn("[kalın kırmızı]Kazanan:[/kalın kırmızı] Kodi [1]", t)
        self.assertIn("'camgöbeği'", t)
        self.assertIn("[link=https://a.b]x[/link]", t)

    def test_harita_karekod_ctk(self):
        self.assertIn("'kırmızı'", tr("import folium\nfolium.Icon(color='red')\n"))
        self.assertIn("'koyu_mavi'", tr("import qrcode\nq = qrcode.QRCode()\n"
                                        "q.make_image(fill_color='darkblue')\n"))
        t = tr("import customtkinter as ctk\nctk.set_appearance_mode('dark')\n"
               "ctk.set_default_color_theme('green')\n")
        self.assertIn("'koyu'", t)
        self.assertIn("'yeşil'", t)

    def test_renk_listesi(self):
        t = tr("import turtle\nrenkler = ['red', 'orange', 'gold']\nadlar = ['red', 'Ali']\n")
        self.assertIn("['kırmızı', 'turuncu', 'altın']", t)
        # Hepsi renk olmayan liste olduğu gibi kalır.
        self.assertIn("['red', 'Ali']", t)

    def test_kutuphane_yoksa_dokunulmaz(self):
        self.assertIn("'orange'", tr("renk = 'orange'\nprint(['red', 'blue'])\n"))


def py(kod):
    return turkce_kodu_donustur(kod)


class IleriCeviri(unittest.TestCase):
    """TürKod -> Python: "turuncu" -> "orange"; çevrilen kod TürKod dışında da çalışır."""

    def test_kolay_oyun(self):
        p = py("içe_aktar pgzrun\n\nfonksiyon draw():\n"
               "    screen.fill('beyaz')\n"
               "    screen.draw.filled_circle((1, 2), 20, 'turuncu')\n"
               "    screen.draw.text('kırmızı', (10, 10), color='Açık Mavi')\n\npgzrun.go()\n")
        self.assertIn("'white'", p)
        self.assertIn("'orange'", p)
        self.assertIn("'lightblue'", p)
        # draw.text'in ilk argümanı ekrana yazılan metindir, renk değil.
        self.assertIn("'kırmızı'", p)

    def test_terminal_renkleri(self):
        p = py("den termcolor içe_aktar colored, cprint\n"
               "renk = 'yeşil'\n"
               "yazdır(colored('a', 'camgöbeği', 'on_kırmızı', attrs=['kalın']))\n"
               "cprint('b', color='beyaz', on_color='on_açık_mavi')\n")
        for beklenen in ("'green'", "'cyan'", "'on_red'", "'bold'", "'white'",
                         "'on_light_blue'"):
            self.assertIn(beklenen, p)

    def test_zengin_yazi(self):
        p = py("den rich.console içe_aktar Console\nc = Console()\n"
               "c.print('[kalın turuncu]Kazanan:[/kalın turuncu] Kodi [1]', style='camgöbeği')\n"
               "c.print('[Ali] [link=https://a.b]x[/link]')\n")
        self.assertIn("[bold orange1]Kazanan:[/bold orange1] Kodi [1]", p)
        self.assertIn("'cyan'", p)
        self.assertIn("[Ali] [link=https://a.b]x[/link]", p)

    def test_harita_karekod_ctk_liste(self):
        self.assertIn("'red'", py("içe_aktar folium\nfolium.Icon(color='kırmızı')\n"))
        self.assertIn("'darkblue'", py("içe_aktar qrcode\nq = qrcode.QRCode()\n"
                                       "q.make_image(fill_color='koyu_mavi')\n"))
        p = py("içe_aktar customtkinter\ncustomtkinter.set_appearance_mode('koyu')\n"
               "customtkinter.set_default_color_theme('koyu_mavi')\n")
        self.assertIn("'dark'", p)
        self.assertIn("'dark-blue'", p)
        self.assertIn("['red', 'orange', 'gold']",
                      py("içe_aktar turtle\nrenkler = ['kırmızı', 'turuncu', 'altın']\n"))

    def test_kutuphane_yoksa_ve_fstring_dokunulmaz(self):
        self.assertIn("'turuncu'", py("renk = 'turuncu'\nyazdır(['kırmızı', 'mavi'])\n"))
        p = py("den termcolor içe_aktar colored\n"
               "yazdır(colored(f'{1} kırmızı', 'kırmızı'))\n")
        self.assertIn("f'{1} kırmızı', 'red'", p)

    def test_gidis_donus(self):
        kod = ("from termcolor import colored\nprint(colored('a', 'light_blue', 'on_red'))\n"
               "from rich import print as p\np('[bold orange1]x[/bold orange1]')\n")
        self.assertEqual(py(tr(kod)), kod)


class CalismaAni(unittest.TestCase):
    """Kütüphanelerin sahte (küçük) kopyalarıyla çalıştırıcı yamaları denenir."""

    def calistir(self, ek):
        kod = runner.oneri_tablolarini_yerlestir(runner.RUNNER_ORTAK).replace(
            "_TK_PROGRAM_IKONU = ", "_TK_PROGRAM_IKONU = None and ", 1)
        klasor = tempfile.mkdtemp(prefix="turkod_renk_")
        self.addCleanup(shutil.rmtree, klasor, True)
        yol = os.path.join(klasor, "s.py")
        with open(yol, "w", encoding="utf-8") as f:
            f.write(kod + "\nimport sys, types\n" + ek)
        r = subprocess.run([sys.executable, "-X", "utf8", yol], capture_output=True, timeout=60)
        return r.stdout.decode("utf-8").strip().splitlines()[-1:], r.stderr.decode("utf-8", "replace")

    def test_terminal_renkleri(self):
        cikti, hata = self.calistir(
            "m = types.SimpleNamespace(COLORS={'red': 31, 'light_blue': 94, 'white': 97},\n"
            "    HIGHLIGHTS={'on_red': 41}, ATTRIBUTES={'bold': 1})\n"
            "_tk_termcolor_yamala(m)\n"
            "sys.__stdout__.write(str([m.COLORS.get('kırmızı'), m.COLORS.get('açık_mavi'),\n"
            "    m.COLORS.get('beyaz'), m.HIGHLIGHTS.get('on_kırmızı'), m.ATTRIBUTES.get('kalın')]) + '\\n')\n")
        self.assertEqual(cikti, ["[31, 94, 97, 41, 1]"], hata)

    def test_zengin_yazi(self):
        cikti, hata = self.calistir(
            "c = types.SimpleNamespace(ANSI_COLOR_NAMES={'red': 1, 'orange1': 214, 'dark_orange': 208})\n"
            "class Style:\n    STYLE_ATTRIBUTES = {'bold': 'bold'}\n"
            "_tk_rich_renk_yamala(c)\n_tk_rich_stil_yamala(types.SimpleNamespace(Style=Style))\n"
            "n = c.ANSI_COLOR_NAMES\n"
            "sys.__stdout__.write(str([n.get('kırmızı'), n.get('turuncu'), n.get('koyu_turuncu'),\n"
            "    Style.STYLE_ATTRIBUTES.get('kalın')]) + '\\n')\n")
        self.assertEqual(cikti, ["[1, 214, 208, 'bold']"], hata)

    def test_harita_ve_ctk(self):
        cikti, hata = self.calistir(
            "v = types.SimpleNamespace(path_options=lambda **k: k)\n_tk_folium_cizgi_yamala(v)\n"
            "class Icon:\n"
            "    def __init__(self, color='blue', icon_color='white', icon='x'):\n"
            "        self.r = (color, icon_color, icon)\n"
            "_tk_folium_simge_yamala(types.SimpleNamespace(Icon=Icon))\n"
            "ctk = types.SimpleNamespace(set_default_color_theme=lambda t: t,\n"
            "    set_appearance_mode=lambda m: m)\n_tk_ctk_yamala(ctk)\n"
            "sys.__stdout__.write(str([v.path_options(line=True, color='mavi')['color'],\n"
            "    Icon('kırmızı', icon='y').r, ctk.set_default_color_theme('koyu_mavi'),\n"
            "    ctk.set_appearance_mode('koyu')]) + '\\n')\n")
        self.assertEqual(cikti, ["['blue', ('red', 'white', 'y'), 'dark-blue', 'dark']"], hata)


if __name__ == "__main__":
    unittest.main()
