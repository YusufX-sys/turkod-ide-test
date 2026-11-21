"""Backend'in arayüz (Flutter) sürecine bağlı yaşamasını sağlar.

--parent-pid ile verilen süreç (arayüz) HANGİ yolla kapanırsa kapansın (X düğmesi,
çökme, Görev Yöneticisi, uygulama içi güncelleme) backend kendini ve çalıştırdığı
tüm alt süreçleri (kullanıcı programları, terminal) kapatır. Hem paketli exe
(backend_main.py) hem geliştirici kipi (python -m turkod_ide.server) kullanır.
"""
import os

try:
    from . import platform_katmani
except ImportError:
    import platform_katmani


def kendini_kapat(temizle=None):
    """Kendini ve alt süreçlerini (kullanıcı programları, terminal) sonlandırır."""
    if temizle:
        try:
            temizle()
        except Exception:
            pass
    try:
        platform_katmani.kendi_agacimi_oldur()
    except Exception:
        pass
    os._exit(0)


def ebeveyni_izle(pid: int, temizle=None):
    """Ebeveyn (Flutter arayüzü) süreci bitince backend'i kapatır."""
    if pid <= 0:
        return
    platform_katmani.ebeveyni_izle(pid, lambda: kendini_kapat(temizle))
