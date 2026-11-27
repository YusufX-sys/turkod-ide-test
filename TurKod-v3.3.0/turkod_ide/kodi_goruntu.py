"""Kodi'ye mesajla birlikte giden ekran görüntüsü.

Ayarlar → Kodi → "Mesajla birlikte görüntü gönder" (kodi_goruntu):
- "kapali"  : görüntü gönderilmez (varsayılan),
- "pencere" : yalnızca TürKod penceresi,
- "ekran"   : bütün ekran(lar).

Görüntü JPEG olarak küçültülür (en uzun kenar 1600 px) ve yalnızca seçili
yapay zekâ modeli görsel görebiliyorsa gönderilir.
"""
import base64
import ctypes
import io
import sys

try:
    from . import platform_katmani
except ImportError:
    import platform_katmani

KIPLER = ("kapali", "pencere", "ekran")
EN_UZUN_KENAR = 1600
_PENCERE_OZELLIGI = "TurKod.Editor"  # flutter_window.h: kTurKodPencereOzelligi


def _turkod_penceresi():
    """TürKod ana penceresinin fiziksel piksel dikdörtgeni ya da None."""
    if not platform_katmani.windows_mu():
        return None
    import ctypes.wintypes as w
    u = ctypes.windll.user32
    try:
        u.SetThreadDpiAwarenessContext(ctypes.c_void_p(-4))
    except Exception:  # noqa: BLE001 (eski Windows)
        pass
    bulunan = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, w.HWND, w.LPARAM)
    def bak(h, _):
        if u.GetPropW(h, _PENCERE_OZELLIGI) and u.IsWindowVisible(h) and not u.IsIconic(h):
            r = w.RECT()
            if u.GetWindowRect(h, ctypes.byref(r)):
                bulunan.append((r.left, r.top, r.right, r.bottom))
                return False
        return True

    u.EnumWindows(bak, 0)
    return bulunan[0] if bulunan else None


def yakala(kip, hazir=None):
    """(base64 JPEG ya da None, açıklama). hazir: "pencere" kipinde arayüzün kendi
    penceresinden aldığı görüntü (base64 PNG); Linux/macOS'ta pencere böyle gelir."""
    if kip not in ("pencere", "ekran"):
        return None, "kapalı"
    try:
        from PIL import Image, ImageGrab
    except ImportError:
        return None, "görüntü kütüphanesi yok"
    try:
        if kip == "pencere" and hazir:
            resim = Image.open(io.BytesIO(base64.b64decode(hazir)))
            resim.load()
        elif kip == "pencere":
            if not platform_katmani.windows_mu():
                # TürKod penceresini bulmak Windows'a özgü; ekranın tamamı
                # gönderilmez (kullanıcı yalnızca TürKod penceresini seçmişti).
                return None, "TürKod penceresinin görüntüsü gelmedi"
            kutu = _turkod_penceresi()
            if kutu is None:
                return None, "TürKod penceresi görünmüyor"
            resim = ImageGrab.grab(bbox=kutu, all_screens=True)
        else:
            resim = ImageGrab.grab(all_screens=True)
    except Exception as e:  # noqa: BLE001
        return None, f"görüntü alınamadı: {e}"
    resim = resim.convert("RGB")
    resim.thumbnail((EN_UZUN_KENAR, EN_UZUN_KENAR), Image.LANCZOS)
    tampon = io.BytesIO()
    resim.save(tampon, "JPEG", quality=70, optimize=True)
    return base64.b64encode(tampon.getvalue()).decode("ascii"), f"{resim.width}x{resim.height}"
