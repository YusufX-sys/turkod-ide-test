"""Yerel AI sunucusunun erişim denetimi, hata iletileri, hata ayıklayıcının
bağlantı kabulü ve Kodi köprüsü testleri (ağa çıkılmaz, model yüklenmez)."""
import asyncio
import contextlib
import http.client
import io
import json
import os
import socket
import sys
import threading
import time
import unittest
from http.server import ThreadingHTTPServer
from unittest import mock

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if KOK not in sys.path:
    sys.path.insert(0, KOK)

from turkod_ide import debugger, yerel_sunucu  # noqa: E402


class _SahteModel:
    def __init__(self):
        self.cagrilar = []

    def create_chat_completion(self, **kw):
        self.cagrilar.append(kw)
        return {"choices": [{"message": {"role": "assistant", "content": "tamam"}}]}

    def create_completion(self, **kw):
        self.cagrilar.append(kw)
        return {"choices": [{"text": "tamam"}]}


class YerelSunucuTestleri(unittest.TestCase):
    def setUp(self):
        self.model = _SahteModel()
        yamalar = [
            mock.patch.object(yerel_sunucu, "model_al", lambda ad: self.model),
            mock.patch.object(yerel_sunucu, "model_listesi", lambda: ["a.gguf"]),
        ]
        for y in yamalar:
            y.start()
            self.addCleanup(y.stop)
        self.sunucu = ThreadingHTTPServer(("127.0.0.1", 0), yerel_sunucu.Isleyici)
        self.port = self.sunucu.server_address[1]
        threading.Thread(target=self.sunucu.serve_forever, daemon=True).start()
        self.addCleanup(self.sunucu.server_close)
        self.addCleanup(self.sunucu.shutdown)

    def istek(self, yontem, yol, govde=None, basliklar=None, ham=None):
        b = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        try:
            h = {"Host": f"127.0.0.1:{self.port}"}
            veri = None
            if govde is not None:
                veri = json.dumps(govde).encode("utf-8")
                h["Content-Type"] = "application/json"
            if ham is not None:
                veri = ham
            h.update(basliklar or {})
            b.putrequest(yontem, yol, skip_host=True, skip_accept_encoding=True)
            for k, v in h.items():
                if v is not None:
                    b.putheader(k, v)
            if veri is not None:
                b.putheader("Content-Length", str(len(veri)))
            b.endheaders(veri)
            y = b.getresponse()
            return y.status, json.loads(y.read() or b"{}")
        finally:
            b.close()

    def sohbet(self, **ek):
        return self.istek("POST", "/v1/chat/completions",
                          {"model": "a.gguf", "messages": [{"role": "user", "content": "x"}], **ek})

    # --- 1. Host / Origin / Content-Type -------------------------------
    def test_yerel_host_kabul_edilir(self):
        for host in ("127.0.0.1", f"127.0.0.1:{self.port}", "localhost",
                     f"localhost:{self.port}", "[::1]", f"[::1]:{self.port}", "LOCALHOST"):
            kod, _ = self.istek("GET", "/v1/models", basliklar={"Host": host})
            self.assertEqual(kod, 200, host)

    def test_yabanci_host_403(self):
        for host in ("evil.example", "evil.example:80", "127.0.0.1.evil.example",
                     "localhost.evil", "127.0.0.1:abc", ""):
            kod, veri = self.istek("GET", "/v1/models", basliklar={"Host": host})
            self.assertEqual(kod, 403, host)
            kod, _ = self.istek(
                "POST", "/v1/chat/completions", {"model": "a.gguf"}, {"Host": host})
            self.assertEqual(kod, 403, host)
        self.assertEqual(self.model.cagrilar, [])

    def test_yabanci_origin_403(self):
        for origin in ("http://evil.example", "null", "https://localhost.evil",
                       "file://"):
            kod, _ = self.istek(
                "POST", "/v1/chat/completions", {"model": "a.gguf"}, {"Origin": origin})
            self.assertEqual(kod, 403, origin)
        self.assertEqual(self.model.cagrilar, [])
        kod, _ = self.istek("POST", "/v1/chat/completions", {"model": "a.gguf"},
                            {"Origin": f"http://127.0.0.1:{self.port}"})
        self.assertEqual(kod, 200)

    def test_json_olmayan_post_415(self):
        govde = json.dumps({"model": "a.gguf", "messages": []}).encode()
        for tur in ("text/plain", "application/x-www-form-urlencoded",
                    "multipart/form-data; boundary=x", None):
            kod, _ = self.istek("POST", "/v1/chat/completions", ham=govde,
                                basliklar={"Content-Type": tur})
            self.assertEqual(kod, 415, tur)
        self.assertEqual(self.model.cagrilar, [])
        kod, _ = self.istek("POST", "/v1/chat/completions", ham=govde,
                            basliklar={"Content-Type": "application/json; charset=utf-8"})
        self.assertEqual(kod, 200)

    def test_turkod_istemcisi_gecer(self):
        # Meşru istemci (ai.py, yerel_modeller.py) requests.post(json=...) kullanır.
        import requests
        y = requests.post(f"http://127.0.0.1:{self.port}/v1/completions",
                          json={"model": "a.gguf", "prompt": "x"}, timeout=5)
        self.assertEqual(y.status_code, 200)
        self.assertTrue(requests.get(f"http://127.0.0.1:{self.port}/v1/models",
                                     timeout=5).ok)

    # --- 2. Hata iletileri ---------------------------------------------
    def test_gecersiz_parametre_400(self):
        for ek in ({"max_tokens": "abc"}, {"temperature": "sıcak"},
                   {"max_tokens": [1]}, {"max_tokens": -5}, {"stop": 5}):
            kod, veri = self.sohbet(**ek)
            self.assertEqual(kod, 400, ek)
            ileti = veri["error"]["message"]
            self.assertIn("invalid parameter", ileti)
            self.assertNotIn("context length", ileti)
        self.assertEqual(self.model.cagrilar, [])

    def test_baglam_tasmasi_bildirilir(self):
        def tasan(**kw):
            raise ValueError("Requested tokens (9000) exceed context window of 8192")
        self.model.create_chat_completion = tasan
        kod, veri = self.sohbet()
        self.assertEqual(kod, 400)
        self.assertIn("context length exceeded", veri["error"]["message"])

    def test_baska_valueerror_baglam_sayilmaz(self):
        def bozuk(**kw):
            raise ValueError("messages must be a list")
        self.model.create_chat_completion = bozuk
        kod, veri = self.sohbet()
        self.assertEqual(kod, 400)
        self.assertNotIn("context length", veri["error"]["message"])
        self.assertIn("messages must be a list", veri["error"]["message"])

    def test_nesne_olmayan_json_400(self):
        kod, _ = self.istek("POST", "/v1/chat/completions", [1, 2])
        self.assertEqual(kod, 400)


class YerelHostIslevleri(unittest.TestCase):
    def test_host_ve_origin(self):
        self.assertTrue(yerel_sunucu._yerel_host_mu("127.0.0.1:8765"))
        self.assertTrue(yerel_sunucu._yerel_host_mu("[::1]"))
        self.assertFalse(yerel_sunucu._yerel_host_mu("127.0.0.1:99999"))
        self.assertFalse(yerel_sunucu._yerel_host_mu(None))
        self.assertTrue(yerel_sunucu._yerel_origin_mi("http://localhost:3000"))
        self.assertFalse(yerel_sunucu._yerel_origin_mi("null"))
        self.assertFalse(yerel_sunucu._yerel_origin_mi("http://attacker.test"))


# --- 3. Hata ayıklayıcının bağlantı kabulü -----------------------------
class DebugKabulTestleri(unittest.TestCase):
    def oturum(self, genel=4.0, merhaba=0.4):
        o = object.__new__(debugger.DebugOturumu)
        o.BAGLANTI_ZAMAN_ASIMI = genel
        o.MERHABA_ZAMAN_ASIMI = merhaba
        o.on_olay = None
        o.durdu = False
        o.bitti = False
        o.mevcut_satir = 0
        o._baglanti = None
        o._yazici = None
        o._bekleyenler = {}
        o._token = "dogru-jeton"
        o._sunucu = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        o._sunucu.bind(("127.0.0.1", 0))
        o._sunucu.listen(1)
        self.port = o._sunucu.getsockname()[1]
        self.addCleanup(o._sunucu.close)
        return o

    def baglan(self):
        s = socket.create_connection(("127.0.0.1", self.port), timeout=5)
        self.addCleanup(s.close)
        return s

    def bekle(self, kosul, sure=5.0):
        son = time.monotonic() + sure
        while time.monotonic() < son:
            if kosul():
                return True
            time.sleep(0.02)
        return False

    def test_sessiz_ve_bozuk_baglanti_donguyu_bitirmez(self):
        o = self.oturum()
        t = threading.Thread(target=o._kabul_et, daemon=True)
        t.start()
        sessiz = self.baglan()          # hiçbir şey göndermez
        time.sleep(o.MERHABA_ZAMAN_ASIMI + 0.3)
        self.assertTrue(t.is_alive(), "sessiz bağlantı kabul döngüsünü bitirdi")
        bozuk = self.baglan()
        bozuk.sendall(b"\xff\xfe bozuk\n")
        yanlis = self.baglan()
        yanlis.sendall(b'{"tip": "merhaba", "token": "yanlis"}\n')
        dogru = self.baglan()
        dogru.sendall(b'{"tip": "merhaba", "token": "dogru-jeton"}\n')
        self.assertTrue(self.bekle(lambda: o._baglanti is not None))
        # Yabancı bağlantılar kapatılmış olmalı.
        sessiz.settimeout(2)
        self.assertEqual(sessiz.recv(10), b"")
        dogru.sendall(b'{"tip": "durdu", "satir": 3}\n')
        self.assertTrue(self.bekle(lambda: o.mevcut_satir == 3))
        dogru.close()
        self.assertTrue(self.bekle(lambda: o.bitti))
        t.join(3)
        o._yazici.close()
        o._baglanti.close()

    def test_genel_sure_dolunca_biter(self):
        o = self.oturum(genel=0.6, merhaba=5)
        t = threading.Thread(target=o._kabul_et, daemon=True)
        baslangic = time.monotonic()
        t.start()
        self.baglan()                   # sessiz: genel süreyi aşmamalı
        t.join(3)
        self.assertFalse(t.is_alive())
        self.assertLess(time.monotonic() - baslangic, 2.5)
        self.assertIsNone(o._baglanti)


# --- 4-6. Sunucu: Kodi köprüsü, komut tabloları ------------------------
class _SahteWS:
    def __init__(self, hata=False):
        self.hata = hata
        self.gonderilen = []

    async def send_json(self, veri):
        if self.hata:
            raise RuntimeError("websocket kapalı")
        self.gonderilen.append(veri)


class SunucuTestleri(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with contextlib.redirect_stdout(io.StringIO()):
            from turkod_ide import server
        cls.server = server

    def setUp(self):
        self.loop = asyncio.new_event_loop()
        t = threading.Thread(target=self.loop.run_forever, daemon=True)
        t.start()

        def kapat():
            self.loop.call_soon_threadsafe(self.loop.stop)
            t.join(2)
            self.loop.close()
        self.addCleanup(kapat)
        self.server._KODI_KOPRU.clear()
        self.addCleanup(self.server._KODI_KOPRU.clear)

    def test_kopru_iletir(self):
        ws = _SahteWS()
        self.server._KODI_KOPRU["kodi"] = self.server._kodi_kopru_gonderici(ws, self.loop)
        r = self.server._cmd_kodi_kopru_gonder({"rol": "kodi", "veri": {"tur": "don"}})
        self.assertTrue(r["ok"])
        self.assertEqual(ws.gonderilen, [{"event": "kodi_kopru", "data": {"tur": "don"}}])

    def test_kapali_pencereye_gonderim_basarisiz(self):
        ws = _SahteWS(hata=True)
        self.server._KODI_KOPRU["ana"] = self.server._kodi_kopru_gonderici(ws, self.loop)
        r = self.server._cmd_kodi_kopru_gonder({"rol": "ana", "veri": {}})
        self.assertFalse(r["ok"])
        self.assertEqual(r["hata"], "Karşı pencere bağlı değil.")
        self.assertNotIn("ana", self.server._KODI_KOPRU)

    def test_baglanti_kapaninca_kayit_silinir(self):
        ws1, ws2 = _SahteWS(), _SahteWS()
        self.server._KODI_KOPRU["kodi"] = self.server._kodi_kopru_gonderici(ws1, self.loop)
        self.server._KODI_KOPRU["ana"] = self.server._kodi_kopru_gonderici(ws2, self.loop)
        self.server._kodi_kopru_temizle(ws1)
        self.assertNotIn("kodi", self.server._KODI_KOPRU)
        self.assertIn("ana", self.server._KODI_KOPRU)
        r = self.server._cmd_kodi_kopru_gonder({"rol": "kodi", "veri": {}})
        self.assertFalse(r["ok"])

    def test_yeni_kayit_eski_baglantinin_temizliginde_silinmez(self):
        eski, yeni = _SahteWS(), _SahteWS()
        self.server._KODI_KOPRU["kodi"] = self.server._kodi_kopru_gonderici(eski, self.loop)
        self.server._KODI_KOPRU["kodi"] = self.server._kodi_kopru_gonderici(yeni, self.loop)
        self.server._kodi_kopru_temizle(eski)
        self.assertIn("kodi", self.server._KODI_KOPRU)

    def test_motor_kurulumu_uzun_havuzda(self):
        for k in ("yerel_ai_motor_kur", "yerel_ai_motor_kaldir"):
            self.assertIn(k, self.server._UZUN_KOMUTLAR)
        # Uzun listedeki her komut gerçekten tanımlı olmalı.
        self.assertLessEqual(self.server._UZUN_KOMUTLAR, set(self.server.SYNC_COMMANDS))

    def test_komut_listeleri_tam(self):
        liste = self.server.index()["komutlar"]
        tablo = self.server.komutlar()
        for k in ("kodi_kopru_kayit", "kabuk_baslat", "calistir", "ping"):
            self.assertIn(k, liste)
        self.assertIn("kodi_kopru_kayit", tablo["async"])
        self.assertEqual(sorted(liste), sorted(set(tablo["sync"]) | set(tablo["async"])))

    def test_olu_komutlar_kaldirildi(self):
        for k in ("ai_model_dogrula", "ai_tamamla", "breakpoint_toggle", "breakpoint_list",
                  "kod_tanimlari", "tokenize", "kodi_durum", "kodi_goruntu_dene",
                  "yerel_ai_gorev_ata", "yerel_ai_depolama", "guncelleme_indir"):
            self.assertNotIn(k, self.server.SYNC_COMMANDS, k)
        self.assertIn("ping", self.server.SYNC_COMMANDS)


if __name__ == "__main__":
    unittest.main()
