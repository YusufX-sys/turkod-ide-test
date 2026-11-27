"""Çocuklar için eklenen kütüphanelerin (Pygame Zero, Dear PyGui, Arduino, Ollama ...)
İngilizce hata iletileri çalıştırıcıda Türkçeye çevrilir; kurulu olmayan kütüphane için
Türkçe 'pip yükle' ipucu verilir; Dear PyGui bağlamsız çağrıda çökmez."""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from turkod_ide import runner  # noqa: E402

ILETILER = {
    "invalid color name": "bilinmeyen renk adı",
    "No 'images' directory found to load image 'uzayli'.": "'images' klasörü yok",
    "No image found like 'uzayli'. Are you sure the image exists?": "'uzayli' adında bir resim",
    "<built-in function add_button> returned a result with an exception set": "pencerenin içinde",
    "could not open port 'COM9': FileNotFoundError": "'COM9' portu açılamadı",
    "Could not find a serial port.": "Arduino bulunamadı",
    "Unable to load any default pin factory!": "GPIOZERO_PIN_FACTORY",
    "Failed to connect to Ollama. Please check": "Ollama'ya bağlanılamadı",
    "model 'llama3' not found": "ollama pull llama3",
    "Wikipedia.__init__() missing 1 required positional argument: 'user_agent'": "user_agent",
    "Code length overflow. Data size (3000) > size available (2953)": "karekoda sığmıyor",
    "unknown url type: 'turkod.org'": "https://",
    "HTTP Error 404: Not Found": "404",
    "process PID not found (pid=99999)": "99999 numaralı süreç",
    "Language not supported: xx": "lang=\"tr\"",
    "Invalid configuration for faker locale `zz_ZZ`": "tr_TR",
    "Dynamic bodies must have a mass > 0 and moment > 0": "kütlesi",
    "Stream has ended unexpectedly": "PDF dosyası bozuk",
}


def _sablonu_calistir(ek_kod):
    kod = runner.oneri_tablolarini_yerlestir(runner.RUNNER_ORTAK).replace(
        "_TK_PROGRAM_IKONU = ", "_TK_PROGRAM_IKONU = None and ", 1)
    klasor = tempfile.mkdtemp(prefix="turkod_cocuk_")
    try:
        yol = os.path.join(klasor, "sablon.py")
        with open(yol, "w", encoding="utf-8") as f:
            f.write(kod + "\n" + ek_kod)
        r = subprocess.run([sys.executable, "-X", "utf8", yol], capture_output=True, timeout=60)
        return r.stdout.decode("utf-8", "replace"), r.stderr.decode("utf-8", "replace")
    finally:
        shutil.rmtree(klasor, ignore_errors=True)


class CocukHataIletileri(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Şablondaki çeviri tabloları ayrı bir süreçte, şablonun kendi koduyla denenir.
        satirlar = "".join(
            f"_y = _tam_mesaj_cevir({m!r})\n"
            f"sys.__stdout__.write(repr(_y) + '\\n')\n" for m in ILETILER)
        cls.cikti, cls.hata = _sablonu_calistir("import sys\n" + satirlar)

    def test_iletiler_turkcelesir(self):
        sonuclar = self.cikti.strip().splitlines()[-len(ILETILER):]
        self.assertEqual(len(sonuclar), len(ILETILER), self.hata)
        for (ileti, beklenen), sonuc in zip(ILETILER.items(), sonuclar):
            with self.subTest(ileti=ileti):
                self.assertIn(beklenen, sonuc)

    def test_kurulum_adlari_turkce(self):
        adlar = runner._kurulum_adlari()
        # Python modül adı -> Türkçe pip adı (pip yükle <ad>)
        for py in ("pgzrun", "pgzero", "pyray", "pymunk", "dearpygui", "qrcode"):
            with self.subTest(py=py):
                self.assertIn(py, adlar)
                self.assertNotEqual(adlar[py], py)
        self.assertEqual(adlar["pgzero"], adlar["pgzrun"])
        govde = runner.oneri_tablolarini_yerlestir(runner.RUNNER_ORTAK)
        self.assertNotIn("_TK_KURULUM = {}", govde)
        compile(govde, "calistirici", "exec")


class DearPyGuiBaglami(unittest.TestCase):
    def test_baglamsiz_cagri_turkce_hata_verir(self):
        """Gerçek Dear PyGui bağlam olmadan çöker; sahte modülle yamanın
        bağlam açılana kadar Türkçe hata verdiği, sonra çağrıyı geçirdiği denenir."""
        cikti, hata = _sablonu_calistir(
            "import sys, types\n"
            "m = types.ModuleType('dearpygui.dearpygui')\n"
            "def _f(ad):\n"
            "    def f(*a, **k): return ad\n"
            "    f.__module__ = 'dearpygui.dearpygui'\n"
            "    return f\n"
            "for _ad in ('create_context', 'destroy_context', 'add_button', 'window'):\n"
            "    setattr(m, _ad, _f(_ad))\n"
            "_tk_dpg_yamala(m)\n"
            "try:\n"
            "    m.add_button()\n"
            "    sys.__stdout__.write('HATA YOK\\n')\n"
            "except RuntimeError as e:\n"
            "    sys.__stdout__.write(('bağlam_oluştur' in str(e)) and 'TÜRKÇE\\n' or 'BAŞKA\\n')\n"
            "m.create_context()\n"
            "sys.__stdout__.write(m.add_button() + '\\n')\n"
            "m.destroy_context()\n"
            "try:\n"
            "    m.window()\n"
            "except RuntimeError:\n"
            "    sys.__stdout__.write('YİNE KORUMALI\\n')\n")
        self.assertEqual(cikti.strip().splitlines()[-3:],
                         ["TÜRKÇE", "add_button", "YİNE KORUMALI"], hata)


class ExeToplama(unittest.TestCase):
    def test_veri_dosyali_kutuphaneler_toplanir(self):
        """Kolay Oyun, Dev Harfler ve Raspberry Pi pinleri veri dosyaları
        toplanmadan EXE'de açılır açılmaz çöküyordu."""
        from turkod_ide import converter, exe_donusturucu as e
        kod = converter.turkce_kodu_donustur(
            "içe_aktar kolay_oyun\niçe_aktar dev_harfler\niçe_aktar raspberry_pinleri\n")
        paketler = e._ice_aktarilan_paketler(kod)
        toplanan = {t for p in paketler for t in e._TOPLANACAK.get(p, ())}
        self.assertTrue({"pgzero", "pyfiglet", "gpiozero"} <= toplanan, (kod, toplanan))


if __name__ == "__main__":
    unittest.main()
