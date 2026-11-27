"""Kodi'nin yüz ifadesi / poz / hareket / efekt eylemi ("ifade") testleri."""
import contextlib
import io
import os
import sys
import unittest

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if KOK not in sys.path:
    sys.path.insert(0, KOK)

with contextlib.redirect_stdout(io.StringIO()):
    from turkod_ide import kodi  # noqa: E402


def blok(*satirlar):
    return "Merhaba!\n```eylem\n" + "\n".join(satirlar) + "\n```"


class IfadeEylemiTestleri(unittest.TestCase):
    def test_gecerli_ifade_korunur(self):
        metin, eylemler = kodi.eylemleri_ayir(blok(
            '{"eylem": "ifade", "yuz": "heyecanli", "poz": "zafer", '
            '"hareket": "zipla", "efekt": "konfeti"}', '{"eylem": "yok"}'))
        self.assertEqual(metin, "Merhaba!")
        self.assertIn({"eylem": "ifade", "yuz": "heyecanli", "poz": "zafer",
                       "hareket": "zipla", "efekt": "konfeti"}, eylemler)

    def test_turkce_harf_ve_bosluk_duzelir(self):
        _, eylemler = kodi.eylemleri_ayir(blok(
            '{"eylem": "ifade", "yuz": "Heyecanlı", "poz": "baş parmak", "hareket": "Dans"}'))
        self.assertEqual(eylemler, [{"eylem": "ifade", "yuz": "heyecanli",
                                     "poz": "basparmak", "hareket": "dans"}])

    def test_bilinmeyen_deger_atilir(self):
        _, eylemler = kodi.eylemleri_ayir(blok(
            '{"eylem": "ifade", "yuz": "ejderha", "efekt": "kalpler"}'))
        self.assertEqual(eylemler, [{"eylem": "ifade", "efekt": "kalpler"}])

    def test_hepsi_gecersizse_eylem_yok(self):
        _, eylemler = kodi.eylemleri_ayir(blok('{"eylem": "ifade", "yuz": "ejderha"}'))
        self.assertEqual(eylemler, [])

    def test_gecersiz_ifade_duzeltme_istemez(self):
        # Yanlış bir yüz adı yüzünden model ikinci kez çağrılmasın.
        self.assertEqual(kodi.gecersiz_eylemler(blok('{"eylem": "ifade", "yuz": "x"}')), [])

    def test_eylem_adi_unutulunca_tahmin(self):
        _, eylemler = kodi.eylemleri_ayir(blok('{"yuz": "saskin", "efekt": "unlem"}'))
        self.assertEqual(eylemler, [{"eylem": "ifade", "yuz": "saskin", "efekt": "unlem"}])

    def test_ifade_is_sayilmaz(self):
        self.assertFalse(kodi.is_eylemi({"eylem": "ifade", "yuz": "mutlu"}))
        self.assertTrue(kodi.is_eylemi({"eylem": "panel", "panel": "ai", "durum": "ac"}))

    def test_ifade_ayir(self):
        ifade, kalan = kodi.ifadeyi_ayir([
            {"eylem": "ifade", "yuz": "sevgi"},
            {"eylem": "panel", "panel": "ai", "durum": "ac"},
            {"eylem": "ifade", "poz": "alkis"},
        ])
        # Son ifade geçerlidir; diğer işler yerinde kalır.
        self.assertEqual(ifade, {"poz": "alkis"})
        self.assertEqual(kalan, [{"eylem": "panel", "panel": "ai", "durum": "ac"}])
        self.assertEqual(kodi.ifadeyi_ayir([]), (None, []))

    def test_sistem_mesajinda_ve_aracta_tanitilir(self):
        kurallar = kodi.eylem_kurallari()
        self.assertIn('"eylem": "ifade"', kurallar)
        for ad in ("heyecanli", "zafer", "zipla", "konfeti"):
            self.assertIn(ad, kurallar)
        ozellikler = kodi.ARACLAR[0]["function"]["parameters"]["properties"]
        self.assertIn("ifade", ozellikler["eylem"]["enum"])
        for alan in ("yuz", "poz", "hareket", "efekt"):
            self.assertIn(alan, ozellikler)

    def test_listeler_cesitli(self):
        self.assertGreaterEqual(len(kodi.KODI_YUZLERI), 12)
        self.assertGreaterEqual(len(kodi.KODI_POZLARI), 10)
        self.assertGreaterEqual(len(kodi.KODI_HAREKETLERI), 6)
        self.assertGreaterEqual(len(kodi.KODI_EFEKTLERI), 6)


class CekirdekIfadeTestleri(unittest.TestCase):
    def setUp(self):
        import tempfile
        from unittest import mock
        self.mock = mock
        self.dizin = tempfile.mkdtemp()
        with mock.patch("os.path.expanduser", return_value=self.dizin), \
                contextlib.redirect_stdout(io.StringIO()):
            from turkod_ide.ide_core import IDECore
            self.c = IDECore()
        self.c.ayarlar.ayarlar["ai_api_anahtarlari"] = {"deepseek": "k"}
        self.c.ayarlar.ayarlar["ai_gorev_atamalari"] = {
            "sohbet": {"saglayici": "deepseek", "model": "deepseek-chat"}}

    def tearDown(self):
        import shutil
        shutil.rmtree(self.dizin, ignore_errors=True)

    def sor(self, *cevaplar):
        yanitlar = [{"cevap": c, "dusunce": ""} for c in cevaplar]
        with self.mock.patch("turkod_ide.ai.sohbet_ayrintili", side_effect=yanitlar) as s, \
                contextlib.redirect_stdout(io.StringIO()):
            return self.c.kodi_sor("Kodum çalıştı!"), s

    def test_ifade_cevaba_ayri_alan_olarak_gelir(self):
        r, s = self.sor(blok('{"eylem": "ifade", "yuz": "heyecanli", "efekt": "konfeti"}',
                             '{"eylem": "yok"}'))
        self.assertTrue(r["ok"], r)
        self.assertEqual(r["ifade"], {"yuz": "heyecanli", "efekt": "konfeti"})
        self.assertEqual(r["eylemler"], [])
        self.assertEqual(r["cevap"], "Merhaba!")
        self.assertEqual(s.call_count, 1)

    def test_ifade_ve_is_birlikte(self):
        r, _ = self.sor(blok('{"eylem": "ifade", "poz": "basparmak"}',
                             '{"eylem": "panel", "panel": "terminal", "durum": "ac"}'))
        self.assertEqual(r["ifade"], {"poz": "basparmak"})
        self.assertEqual([e["eylem"] for e in r["eylemler"]], ["panel"])

    def test_ifadesiz_cevapta_alan_yok(self):
        r, _ = self.sor(blok('{"eylem": "yok"}'))
        self.assertNotIn("ifade", r)

    def test_yalniz_ifade_is_vaadine_bakilir(self):
        # Yalnızca ifade yazılmışsa şablon eksiktir: iş vaadi sorulur (2. çağrı).
        r, s = self.sor(blok('{"eylem": "ifade", "yuz": "mutlu"}'), "hayir",
                        blok('{"eylem": "yok"}'))
        self.assertGreaterEqual(s.call_count, 2)
        self.assertTrue(r["ok"], r)


if __name__ == "__main__":
    unittest.main()
