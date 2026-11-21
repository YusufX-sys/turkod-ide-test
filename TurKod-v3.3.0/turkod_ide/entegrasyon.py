"""Sistem entegrasyonu: PATH'teki `turkod` komutu ve .trpy dosya ilişkilendirmesi.

Kurulum sihirbazındaki iki seçeneğin (turkod.iss [Tasks] "path" / "iliskilendir")
uygulama içinden açılıp kapatılabilen karşılığı. Sürüm güncellemesiyle gelen
cihazlarda bu görevler hiç seçilmemiş olabiliyordu; Ayarlar sayfası buradan düzeltir.

Sisteme özgü iş (Windows kayıt defteri, Linux .desktop/MIME, macOS) platform
katmanındadır: turkod_ide/platform_katmani/.
"""
try:
    from . import platform_katmani
except ImportError:
    import platform_katmani


# --------------------------------------------------------------------------
# Dış arayüz (server.py komutları)
# --------------------------------------------------------------------------
def durum():
    return platform_katmani.entegrasyon_durumu()


def ayarla(path=None, iliskilendir=None):
    """Verilen seçenekleri uygular ve güncel durumu döndürür."""
    d = durum()
    if not d.get("destekleniyor"):
        raise RuntimeError(d.get("neden", "Desteklenmiyor"))
    if path is not None:
        if path:
            platform_katmani.path_e_ekle()
        else:
            platform_katmani.path_ten_cikar()
    if iliskilendir is not None:
        if iliskilendir:
            platform_katmani.dosya_iliskisi_kur()
        else:
            platform_katmani.dosya_iliskisi_kaldir()
    return durum()
