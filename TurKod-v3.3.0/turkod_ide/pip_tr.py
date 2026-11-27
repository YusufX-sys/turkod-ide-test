"""Türkçe pip komutları.

IDE terminalinde şunlar çalışır:
    pip yükle numpy          ->  python -m pip install --target <kullanıcı paketleri> numpy
    pip güncelle numpy       ->  pip install --upgrade (kullanıcı paketlerine)
    pip sil numpy            ->  python -m pip uninstall -y numpy
    pip listele              ->  python -m pip list
    pip eskiler              ->  python -m pip list --outdated
    pip bilgi numpy          ->  python -m pip show numpy
    pip ara numpy            ->  kurulu paketler içinde ada göre arama
    pip dondur / denetle / indir / önbellek / yardım
Eş anlamlılar (kaldır/sil, liste/listele, göster/bilgi ...) ve Türkçe
karaktersiz yazımlar (yukle, guncelle ...) da kabul edilir. Eski (İngilizce)
alt komutlar da çalışmaya devam eder.

`pip_komutu_cevir()` bir komut satırını (cmd.exe için) döndürür; komut pip ile
ilgili değilse None döndürür ve terminal komutu olduğu gibi çalıştırılır.
"""
import re
import shlex

try:
    from . import platform_katmani
except ImportError:  # pragma: no cover - paket dışı çalıştırma
    import platform_katmani

ALT_KOMUTLAR = {
    # kurulum
    "yükle": "install", "yukle": "install", "kur": "install", "install": "install",
    # güncelleme (install --upgrade)
    "güncelle": "upgrade", "guncelle": "upgrade", "yükselt": "upgrade",
    "yukselt": "upgrade", "upgrade": "upgrade",
    # kaldırma
    "kaldır": "uninstall", "kaldir": "uninstall", "sil": "uninstall",
    "uninstall": "uninstall",
    # listeleme
    "liste": "list", "listele": "list", "list": "list",
    # eskimiş paketler (list --outdated)
    "eskiler": "outdated", "eskimiş": "outdated", "eskimis": "outdated",
    "outdated": "outdated",
    # ayrıntı
    "göster": "show", "goster": "show", "bilgi": "show", "show": "show",
    # kurulu paketlerde arama (pip search kaldırıldı; yerel arama yapılır)
    "ara": "search", "bul": "search", "search": "search",
    # diğer
    "dondur": "freeze", "freeze": "freeze",
    "denetle": "check", "kontrol": "check", "check": "check",
    "indir": "download", "download": "download",
    "önbellek": "cache", "onbellek": "cache", "cache": "cache",
    "sürüm": "--version", "surum": "--version", "version": "--version",
    "yardım": "help", "yardim": "help", "help": "help",
}

BAYRAKLAR = {
    "--yükselt": "--upgrade", "--yukselt": "--upgrade",
    "--evet": "--yes",
    "--sessiz": "--quiet",
    "--ayrıntılı": "--verbose", "--ayrintili": "--verbose",
    "--eskiler": "--outdated",
    "--gereksinimler": "-r", "-g": "-r",
}

# Kullanıcı paketlerini (PYTHONPATH ile) görmesi gereken alt komutlar.
_PAKET_YOLU_GEREKLI = {"uninstall", "list", "show", "freeze", "check"}

_KOMUT_RE = re.compile(r"^\s*pip3?(?:\s+(.*))?$", re.IGNORECASE | re.DOTALL)
_ARGUMAN_RE = re.compile(r'"[^"]*"|\S+')
# Paket adı + sürüm kısıtı: numpy>=1.2, pandas==2.0, requests[socks]<3
_SURUM_KISITI_RE = re.compile(r"^[A-Za-z0-9_.\-\[\],]+(?:===|==|>=|<=|!=|~=|>|<)")


PIP_YARDIM = """TürKod pip komutları:
  pip yükle <paket>       Paket kurar            (kur)
  pip güncelle <paket>    Paketi günceller       (yükselt)
  pip sil <paket>         Paketi kaldırır        (kaldır)
  pip listele             Kurulu paketler        (liste)
  pip eskiler             Güncellenebilir paketler
  pip bilgi <paket>       Paket ayrıntıları      (göster)
  pip ara <metin>         Kurulu paketlerde arar (bul)
  pip dondur              requirements biçiminde liste
  pip denetle             Bağımlılık uyumluluğunu denetler
  pip indir <paket>       Kurmadan indirir
  pip sürüm               pip sürümü
  pip yardım              Bu yardım (pip'in kendi yardımı: pip help)
Bayraklar: --yükselt, --evet, --sessiz, --ayrıntılı, -g <dosya> (gereksinimler)
"""


_KATLA = str.maketrans("çğıöşüÇĞİÖŞÜâÂîÎûÛ", "cgiosuCGIOSUaAiIuU")
# Paket adından sonra gelen ek/sürüm kısmı: veri_tabloları[excel]==2.0
_PAKET_ADI_RE = re.compile(r"^([^\[\]=<>!~;@\s]+)(.*)$", re.S)
_PAKET_TABLOSU = None


def _anahtar(ad: str) -> str:
    return ad.translate(_KATLA).lower().replace("-", "_")


def _paket_tablosu():
    """Türkçe kütüphane adı (ve içe aktarma adı) -> (pip paketi | None, Python adı).

    Kaynak: çevirici (TürKod modül adları) ve Kütüphane Rehberi (pip paket
    adları). None: Python ile birlikte gelen standart kütüphane."""
    global _PAKET_TABLOSU
    if _PAKET_TABLOSU is not None:
        return _PAKET_TABLOSU
    tablo = {}
    try:
        try:
            from .converter import MODUL_CEVIRILERI
            from .kutuphane_aciklamalari import ACIKLAMALAR
        except ImportError:
            from converter import MODUL_CEVIRILERI
            from kutuphane_aciklamalari import ACIKLAMALAR
    except Exception:
        _PAKET_TABLOSU = tablo
        return tablo
    for tr, py in MODUL_CEVIRILERI.items():
        bilgi = ACIKLAMALAR.get(py)
        if bilgi is None:
            continue
        paket = None if bilgi.get("standart") else bilgi.get("pip_adi")
        if tr != py:
            tablo.setdefault(_anahtar(tr), (paket, py))
    # İçe aktarma adı pip paketinden farklı olanlar: "pip yükle cv2" eskiden
    # PyPI'de bulunamıyor ya da (docx, sklearn) yanlış/eski paketi kuruyordu.
    for py, bilgi in ACIKLAMALAR.items():
        paket = bilgi.get("pip_adi")
        if not bilgi.get("standart") and paket and _anahtar(paket) != _anahtar(py) \
                and "." not in py:
            tablo.setdefault(_anahtar(py), (paket, py))
    _PAKET_TABLOSU = tablo
    return tablo


def paket_adini_cevir(arguman: str):
    """Türkçe kütüphane adını pip paket adına çevirir; ek/sürüm kısmı korunur.

    "satranç" -> "chess", "veri_tabloları==2.2" -> "pandas==2.2",
    "görüntü_işleme" -> "opencv-python". Tanınmayan ad olduğu gibi döner.
    Standart kütüphaneyse (matematik) ("", python_adı) döner."""
    m = _PAKET_ADI_RE.match(arguman)
    if not m:
        return arguman, None
    ad, kalan = m.groups()
    karsilik = _paket_tablosu().get(_anahtar(ad))
    if karsilik is None:
        return arguman, None
    paket, py = karsilik
    if paket is None:
        return "", py
    return paket + kalan, None


def pip_yardim_mi(komut: str) -> bool:
    """`pip`, `pip yardım` ve `pip yardim`: Türkçe özet gösterilir."""
    m = _KOMUT_RE.match((komut or "").strip())
    if not m:
        return False
    kalan = (m.group(1) or "").strip().lower()
    return kalan in ("", "yardım", "yardim")


def _tirnakla(yol: str) -> str:
    return '"' + yol.replace('"', "") + '"'


def _paket_yolu_ile(paket_yolu, komut):
    if not paket_yolu:
        return komut
    if platform_katmani.windows_mu():
        return f'set "PYTHONPATH={paket_yolu.replace(chr(34), "")}" && {komut}'
    # Linux/macOS: kabuk /bin/sh. cmd.exe'nin "set" sözdizimi orada değişken
    # atamıyordu; "pip listele / sil / bilgi" kullanıcı paketlerini görmüyordu.
    return f"PYTHONPATH={shlex.quote(paket_yolu)} {komut}"


def pip_komutu_cevir(komut: str, python_exe, paket_yolu: str):
    """`pip ...` komutunu gömülü Python'un pip'ine çevirir; pip komutu değilse None."""
    if not komut or not python_exe:
        return None
    m = _KOMUT_RE.match(komut.strip())
    if not m:
        return None

    kalan = (m.group(1) or "").strip()
    py = _tirnakla(str(python_exe))
    if not kalan:
        return f"{py} -m pip"

    # Herhangi bir boşluk (sekme dahil) alt komutu ayırır.
    parcalar = kalan.split(None, 1)
    ilk = parcalar[0]
    geri = parcalar[1] if len(parcalar) > 1 else ""
    alt = ALT_KOMUTLAR.get(ilk.lower())
    if alt is None:
        # Bilinmeyen alt komut: olduğu gibi ilet (pip kendi hata iletisini verir).
        return f"{py} -m pip {kalan}"

    argumanlar = []
    # Tırnaklı argümanlar bölünmez ("pip ara "a b"" eskiden yalnızca "a"yı
    # arıyordu).
    for parca in _ARGUMAN_RE.findall(geri):
        # Türkçe uzun bayraklar büyük/küçük harf duyarsız; kısa bayraklar
        # duyarlı ("-G" eskiden sessizce "-r" oluyordu).
        karsilik = BAYRAKLAR.get(parca)
        if karsilik is None and parca.startswith("--"):
            karsilik = BAYRAKLAR.get(parca.lower())
        parca = karsilik or parca
        # "numpy>=1.2": cmd.exe'de tırnaksız ">" / "<" yönlendirme sayılır;
        # sürüm kısıtı kaybolup "=1.2" adlı bir dosyaya yazılıyordu.
        if not parca.startswith('"') and _SURUM_KISITI_RE.match(parca):
            parca = _tirnakla(parca)
        argumanlar.append(parca)

    # Türkçe kütüphane adları: "pip yükle satranç" -> chess. Yalnızca paket
    # adı alan alt komutlarda ve bayrak/dosya olmayan argümanlarda.
    if alt in ("install", "upgrade", "uninstall", "show", "download"):
        standartlar = []
        yeni = []
        onceki = ""
        for a in argumanlar:
            tirnaksiz = a.strip('"')
            if a.startswith("-") or onceki in ("-r", "--requirement", "-t", "--target",
                                               "-d", "--dest", "-c", "--constraint",
                                               "-i", "--index-url"):
                yeni.append(a)
            else:
                karsilik, standart = paket_adini_cevir(tirnaksiz)
                if standart:
                    standartlar.append((tirnaksiz, standart))
                elif karsilik != tirnaksiz:
                    # "qrcode[pil]": köşeli ayraç sh'de dosya deseni sayılır; tırnaklanır.
                    yeni.append(_tirnakla(karsilik) if a.startswith('"') or "[" in karsilik
                                or _SURUM_KISITI_RE.match(karsilik) else karsilik)
                else:
                    yeni.append(a)
            onceki = a
        argumanlar = yeni
        if standartlar and not [a for a in argumanlar if not a.startswith("-")]:
            adlar = ", ".join(f"{tr_ad} ({py_ad})" for tr_ad, py_ad in standartlar)
            ileti = (f"{adlar}: Python ile birlikte gelir, kurmana gerek yok. "
                     "Kodunda doğrudan içe aktarabilirsin.")
            # ascii(): Türkçe harfler \xe7 gibi kaçışlarla gider; komut satırı
            # kod sayfasından (cmd.exe) etkilenmez. Tırnak içermez.
            return f"{py} -c {_tirnakla('print(' + ascii(ileti) + ')')}"

    # "--yes" yalnızca kaldırmada geçerli bir pip seçeneğidir; diğerlerinde
    # pip "no such option" hatası veriyordu.
    if alt != "uninstall":
        argumanlar = [a for a in argumanlar if a != "--yes"]

    if alt == "--version":
        return f"{py} -m pip --version"

    if alt == "upgrade":
        alt = "install"
        if "--upgrade" not in argumanlar and "-U" not in argumanlar:
            argumanlar.insert(0, "--upgrade")

    if alt == "outdated":
        alt = "list"
        if "--outdated" not in argumanlar:
            argumanlar.insert(0, "--outdated")

    # Kaldırmada pip "Proceed (Y/n)?" diye sorar; IDE terminali etkileşimli
    # olmadığından komut takılı kalırdı. Onay otomatik verilir.
    if alt == "uninstall" and not any(a in ("-y", "--yes") for a in argumanlar):
        argumanlar.insert(0, "-y")

    args = " ".join(argumanlar)
    args = (" " + args) if args else ""

    if alt == "search":
        # `pip search` PyPI tarafından kapatıldı; kurulu paketlerde ada göre
        # arama yapılır (Windows findstr, büyük/küçük harf duyarsız).
        if not argumanlar:
            return _paket_yolu_ile(paket_yolu, f"{py} -m pip list")
        aranan = argumanlar[0].replace('"', "")
        if platform_katmani.windows_mu():
            suzgec = f'findstr /I /C:"{aranan}"'
        else:
            # findstr yalnızca Windows'ta var; Linux/macOS'ta "pip ara" hiç çalışmıyordu.
            suzgec = f"grep -i -F -- {shlex.quote(aranan)}"
        return _paket_yolu_ile(paket_yolu, f"{py} -m pip list | {suzgec}")

    if alt in ("install", "download"):
        # --user / --prefix / --root, --target ile birlikte kullanılamaz
        # (pip reddeder); kullanıcı kendi kurulum yerini seçmişse eklenmez.
        hedef_var = any(
            a in ("-t", "--target", "--user", "--prefix", "--root")
            or a.startswith(("--target=", "--prefix=", "--root="))
            for a in argumanlar)
        if alt == "install" and not hedef_var and paket_yolu:
            return f"{py} -m pip install --target {_tirnakla(paket_yolu)}{args}"
        return f"{py} -m pip {alt}{args}"

    if alt in _PAKET_YOLU_GEREKLI and paket_yolu:
        return _paket_yolu_ile(paket_yolu, f"{py} -m pip {alt}{args}")

    return f"{py} -m pip {alt}{args}"
