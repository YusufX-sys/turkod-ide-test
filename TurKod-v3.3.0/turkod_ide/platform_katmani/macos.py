"""macOS uygulaması (yalnızca standart kütüphane).

Veri klasörü  : ~/Library/Application Support/TurKod
Terminal      : Terminal.app (osascript ile)
Kodi'nin sesi : `say` (Türkçe ses "Yelda" varsa o)
`turkod`      : ~/.local/bin/turkod bağlantısı
.trpy         : uygulama paketinin Info.plist'inden gelir (buradan değiştirilmez)
"""
import json
import os
import shlex
import shutil
import subprocess
import sys

from . import _posix
from ._ortak import (PlatformHatasi, alt_surec_ortami, backend_dizini, gomulu_python_dizini,
                     paketli_mi)
from ._posix import (  # noqa: F401  (ortak arayüzün parçası)
    GOMULU_PYTHON_GORELI, ebeveyni_izle, ekrani_temizle,
    gizli_surec_ayarlari, gizli_veri, gomulu_python, gomulu_python_yol_dizini, sistem_python,
    kabuk_kod_sayfasi, kendi_agacimi_oldur, path_ten_cikar, surec_yasiyor,
    sureci_agacla_oldur,
)

_SON_TERMINAL_HATASI = [None]


def son_terminal_hatasi():
    return _SON_TERMINAL_HATASI[0]


def veri_tabani(yedek=None):
    return os.path.join(os.path.expanduser("~"), "Library", "Application Support")


COP_KUTUSU_ADI = "Çöp Kutusu"


def cop_kutusu_klasoru():
    return os.path.join(os.path.expanduser("~"), ".Trash")


def cop_kutusu_var_mi(yol):
    return _posix.ayni_disk_mi(yol, cop_kutusu_klasoru())


# NSFileManager.trashItemAtURL: Finder'ın kullandığı yol. "Geri Koy" çalışır,
# başka disklerdeki öğeler o diskin çöp kutusuna gider. Yol betiğe GÖMÜLMEZ,
# argüman olarak verilir (tırnak / ters eğik çizgi sorunu olmasın).
COP_BETIGI = (
    "function run(argv) {\n"
    "  ObjC.import('Foundation');\n"
    "  var url = $.NSURL.fileURLWithPath(argv[0]);\n"
    "  var hata = Ref();\n"
    "  var tamam = $.NSFileManager.defaultManager"
    ".trashItemAtURLResultingItemURLError(url, null, hata);\n"
    "  if (!tamam) {\n"
    "    var h = hata[0];\n"
    "    throw new Error(h && !h.isNil() ? ObjC.unwrap(h.localizedDescription) : 'bilinmeyen hata');\n"
    "  }\n"
    "  return 'tamam';\n"
    "}\n"
)


def cop_komutu(yol):
    return ["osascript", "-l", "JavaScript", "-e", COP_BETIGI, os.path.abspath(yol)]


def cop_kutusuna_tasi(yol):
    """Öğeyi Finder gibi Çöp Kutusu'na taşır (NSFileManager.trashItemAtURL,
    osascript/JXA ile). Başarısız olursa OSError (Türkçe ileti)."""
    try:
        sonuc = subprocess.run(cop_komutu(yol), capture_output=True, text=True, timeout=30,
                               stdin=subprocess.DEVNULL, env=alt_surec_ortami())
    except (OSError, subprocess.SubprocessError) as e:
        raise OSError(f"Çöp Kutusu'na taşınamadı: {e}") from e
    if sonuc.returncode != 0:
        ayrinti = (sonuc.stderr or "").strip().splitlines()
        ayrinti = f" ({ayrinti[-1]})" if ayrinti else ""
        raise OSError(f"Çöp Kutusu'na taşınamadı{ayrinti}.")


def bellek_gb():
    """(toplam, kullanılabilir) GB. macOS'ta os.sysconf("SC_AVPHYS_PAGES") yoktur:
    toplam sysctl hw.memsize'dan, kullanılabilir vm_stat'tan (boş + etkin olmayan
    + temizlenebilir sayfalar) okunur."""
    try:
        toplam = int(subprocess.run(["sysctl", "-n", "hw.memsize"], capture_output=True,
                                    text=True, timeout=5,
                                    env=alt_surec_ortami()).stdout.strip())
    except (OSError, ValueError, subprocess.SubprocessError):
        return None
    bos = 0.0
    try:
        cikti = subprocess.run(["vm_stat"], capture_output=True, text=True, timeout=5,
                               env=alt_surec_ortami()).stdout
        import re
        sayfa = int((re.search(r"page size of (\d+)", cikti) or [0, 4096])[1])
        sayilar = {m.group(1): int(m.group(2))
                   for m in re.finditer(r"^Pages ([a-z ]+):\s+(\d+)", cikti, re.M)}
        bos = sum(sayilar.get(k, 0) for k in ("free", "inactive", "purgeable",
                                               "speculative")) * sayfa
    except (OSError, ValueError, subprocess.SubprocessError):
        pass
    return toplam / 2**30, bos / 2**30


# macOS'ta hazır bir komut satırı kayıt programı yoktur; SoX (`brew install sox`)
# kuruluysa kullanılır.
MIKROFON_PROGRAMLARI = (
    ("rec", lambda o: ["-q", "-t", "raw", "-b", "16", "-e", "signed-integer", "-c", "1",
                       "-r", str(o), "-"]),
    ("sox", lambda o: ["-q", "-d", "-t", "raw", "-b", "16", "-e", "signed-integer", "-c", "1",
                       "-r", str(o), "-"]),
)
MIKROFON_YOK = ("macOS'ta mikrofonu dinlemek için SoX gerekiyor. Terminalde "
                "'brew install sox' ile kurarsan Kodi'yle sesli konuşabilirsin.")


def mikrofon_komutu(ornekleme):
    return _posix.mikrofon_komutu(ornekleme, MIKROFON_PROGRAMLARI)


def editor_dosyasi(backend):
    """TurKod.app/Contents/MacOS/TurKod (sunucu Contents/Resources/backend içinde)."""
    return os.path.join(os.path.dirname(os.path.dirname(backend)), "MacOS", "TurKod")


def _uygulama_paketi(exe):
    """.../TurKod.app/Contents/MacOS/TurKod -> .../TurKod.app (paket değilse None)."""
    yol = os.path.abspath(exe)
    while True:
        if yol.endswith(".app") and os.path.isdir(yol):
            return yol
        ust = os.path.dirname(yol)
        if ust == yol:
            return None
        yol = ust


def editoru_ayri_baslat(exe, dosyalar=()):
    """Editörü LaunchServices ile ("open -a") başlatır: TürKod zaten açıksa
    dosyalar o pencereye gider (MainFlutterWindow.swift: DosyaAcmaKoprusu).
    Eskiden paketteki ikili doğrudan çalıştırılıyor, ikinci bir TürKod (ve
    ikinci sunucu) açılıyordu. Paket bulunamazsa (geliştirme) eski yol."""
    paket = _uygulama_paketi(exe)
    if paket is None:
        return _posix.editoru_ayri_baslat(exe, dosyalar)
    try:
        subprocess.Popen(["open", "-a", paket, *[os.path.abspath(d) for d in dosyalar]],
                         close_fds=True, start_new_session=True, stdin=subprocess.DEVNULL,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         env=alt_surec_ortami())
        return True
    except OSError:
        return False


def _applescript_metni(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def terminal_betigi(komut, cwd=None):
    """Terminal.app'te çalıştırılacak AppleScript."""
    kabuk = shlex.join(komut)
    if cwd:
        kabuk = f"cd {shlex.quote(cwd)} && {kabuk}"
    return (f"tell application \"Terminal\"\n"
            f"  do script {_applescript_metni(kabuk)}\n"
            f"  activate\n"
            f"end tell")


OTOMASYON_IZNI_YOK = ("Terminal'i açma izni verilmedi. Sistem Ayarları > Gizlilik ve "
                      "Güvenlik > Otomasyon'dan TürKod'a izin ver.")


def terminalde_ac(komut, cwd=None):
    """Terminal.app'te yeni pencerede çalıştırır. osascript beklenir: dönüş kodu
    0 değilse False (nedeni son_terminal_hatasi(); -1743 = Otomasyon izni yok)."""
    _SON_TERMINAL_HATASI[0] = None
    try:
        sonuc = subprocess.run(["osascript", "-e", terminal_betigi(komut, cwd)],
                               capture_output=True, text=True, timeout=20,
                               stdin=subprocess.DEVNULL, env=alt_surec_ortami())
    except subprocess.TimeoutExpired:
        # İlk seferde macOS izin sorar; soru yanıtlanana dek osascript bekler.
        _SON_TERMINAL_HATASI[0] = ("Terminal yanıt vermedi. macOS izin soruyorsa "
                                   "izin verip yeniden dene.")
        return False
    except (OSError, subprocess.SubprocessError) as e:
        _SON_TERMINAL_HATASI[0] = f"Terminal açılamadı: {e}"
        return False
    if sonuc.returncode != 0:
        hata = sonuc.stderr if isinstance(sonuc.stderr, str) else ""
        _SON_TERMINAL_HATASI[0] = (OTOMASYON_IZNI_YOK if "-1743" in hata
                                   else "Terminal açılamadı.")
        return False
    return True


TURKCE_SES = "Yelda"


def _turkce_ses_var_mi():
    try:
        cikti = subprocess.run(["say", "-v", "?"], capture_output=True, text=True,
                               timeout=10, env=alt_surec_ortami()).stdout
    except (OSError, subprocess.SubprocessError):
        return False
    return any(s.split()[:1] == [TURKCE_SES] for s in cikti.splitlines())


def konus(metin, dur=None):
    if not metin:
        return
    if not shutil.which("say"):
        raise PlatformHatasi("macOS'un konuşma komutu (say) bulunamadı.")
    komut = ["say"]
    if _turkce_ses_var_mi():
        komut += ["-v", TURKCE_SES]
    # say'in "--" desteği belgelenmemiş: "-" ile başlayan metin seçenek sanılmasın
    # diye başına boşluk konur (okunuşu değişmez).
    if metin.startswith("-"):
        metin = " " + metin
    _posix.sesli_oku([*komut, metin], dur)


# macOS'ta Tk bu süreçte AÇILMAZ: AppKit penceresi ana iş parçacığı dışında
# açılınca süreç çöker. Aileler ayrı bir Python sürecinde Tk'den okunur.
YAZI_TIPI_BETIGI = ("import tkinter,tkinter.font,json;r=tkinter.Tk();r.withdraw();"
                    "print(json.dumps(sorted(set(tkinter.font.families()))));r.destroy()")


def _yazi_tipi_pythonu():
    if paketli_mi():
        # Paketli uygulamada sys.executable PyInstaller ikilisidir: gömülü Python.
        aday = gomulu_python(gomulu_python_dizini())
        return aday if os.path.isfile(aday) else None
    return sys.executable or None


def yazi_tipi_aileleri():
    python = _yazi_tipi_pythonu()
    if not python:
        return None
    try:
        sonuc = subprocess.run([python, "-c", YAZI_TIPI_BETIGI], capture_output=True,
                               text=True, timeout=15, stdin=subprocess.DEVNULL,
                               env=alt_surec_ortami())
        if sonuc.returncode != 0:
            return None
        aileler = json.loads(sonuc.stdout.strip().splitlines()[-1])
    except (OSError, ValueError, IndexError, AttributeError, subprocess.SubprocessError):
        return None
    if not isinstance(aileler, list):
        return None
    return sorted({str(a) for a in aileler if str(a).strip()})


# Gatekeeper, indirilen ve yerinden taşınmamış uygulamayı rastgele, salt okunur
# bir yerden (App Translocation) çalıştırır; .dmg'den doğrudan açılan da
# /Volumes/ altındadır. Oraya kurulan bağlantılar bir sonraki açılışta bozulur.
TASI_UYARISI = ("TürKod'u önce Uygulamalar klasörüne taşı, sonra oradan açıp yeniden dene "
                "(şu an indirilen yerden ya da disk görüntüsünden çalışıyor).")


def gecici_konumda_mi(yol=None):
    yol = yol or backend_dizini()
    return "/AppTranslocation/" in yol or yol.startswith("/Volumes/")


def path_e_ekle():
    if gecici_konumda_mi():
        raise PlatformHatasi(TASI_UYARISI)
    _posix.path_e_ekle()


def dosya_iliskisi_kur():
    """macOS'ta .trpy ilişkisi uygulama paketinin Info.plist'indedir; yapılacak iş yok
    (yalnızca uygulama geçici bir yerden çalışıyorsa uyarılır)."""
    if gecici_konumda_mi():
        raise PlatformHatasi(TASI_UYARISI)


def dosya_iliskisi_kaldir():
    raise PlatformHatasi(".trpy dosyalarının hangi uygulamayla açılacağını Finder'da "
                         "'Bilgi Al > Birlikte Aç' bölümünden değiştirebilirsin.")


def entegrasyon_durumu():
    yok = _posix.entegrasyon_destegi_yok()
    if yok:
        return yok
    _, sistem_path = _posix.path_durumu()
    kullanici_path = _posix.kullanici_path_etkin()
    return {
        "destekleniyor": True,
        "path": kullanici_path or sistem_path,
        "path_sistemde": sistem_path,
        "iliskilendir": True,
        "iliski_kullanicida": False,
        "iliski_sistemde": True,
        "path_dizini": _posix.kullanici_bin_dizini(),
    }
