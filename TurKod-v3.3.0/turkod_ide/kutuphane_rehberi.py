"""Kütüphane Rehberi: TürKod'un tanıdığı bütün kütüphanelerin ayrıntılı açıklaması.

Metinler kutuphane_aciklamalari.py içindedir. Bu modül onları TürKod'un
çeviri tablolarıyla (converter.MODUL_CEVIRILERI / MODUL_METOTLARI) birleştirir:
her kütüphanenin Türkçe içe aktarma adları, bütün üye çevirileri ve örnek kodun
TürKod hâli buradan gelir. Arayüz (Öğren → Kütüphane Rehberi) iki komut kullanır:
"kutuphane_listesi" ve "kutuphane_ayrintisi".
"""

import ast
import builtins
import io
import re
import tokenize
import warnings

try:
    from .converter import (MODUL_CEVIRILERI, MODUL_METOTLARI, python_kodu_turkceye_cevir,
                            turkce_kodu_donustur)
    from .dictionary import TERS_SOZLUK
    from .kutuphane_aciklamalari import ACIKLAMALAR, NESNE_METOTLARI
except ImportError:  # pragma: no cover - paket dışı çalıştırma
    from converter import (MODUL_CEVIRILERI, MODUL_METOTLARI, python_kodu_turkceye_cevir,
                           turkce_kodu_donustur)
    from dictionary import TERS_SOZLUK
    from kutuphane_aciklamalari import ACIKLAMALAR, NESNE_METOTLARI

KATEGORI_SIRASI = [
    "Temel araçlar", "Matematik ve bilim", "Dosya ve sistem",
    "Metin ve veri biçimleri", "Veri bilimi", "Yapay zekâ", "Grafik ve çizim",
    "Oyun", "Arayüz", "Görüntü işleme", "Ağ ve web", "Ofis belgeleri",
    "Eşzamanlılık", "Test ve hata ayıklama", "Güvenlik",
]

# Aynı Python modülüne giden ikinci kopya (fitz = pymupdf) ve iç modüller
# rehberde ayrı kart almaz. pgzero, Pygame Zero'nun iç paketidir; çocuklar
# pgzrun (kolay_oyun) kartını görür.
_GIZLI = {"fitz", "_tkinter", "pgzero"}


def _ascii_mi(ad):
    return all(ord(h) < 128 for h in ad)


def _turkce_adlar(py):
    """Python modülüne giden TürKod adları: kütüphanenin asıl Türkçe adı
    (turkce_ad) en başta, Python'daki adı en sonda. Türkçe harfli bir eşi
    olan ASCII takma adlar (veri_tablolari) atlanır."""
    adlar = [t for t, p in MODUL_CEVIRILERI.items() if p == py]
    turkce = [a for a in adlar if not _ascii_mi(a)]
    sonuc = []
    for a in adlar:
        if _ascii_mi(a) and a != py and turkce and any(
                _katla(t) == a for t in turkce):
            continue
        sonuc.append(a)
    asil = ACIKLAMALAR.get(py, {}).get("turkce_ad")
    if asil in sonuc:
        sonuc.remove(asil)
        sonuc.insert(0, asil)
    if py in sonuc and len(sonuc) > 1:
        sonuc.remove(py)
        sonuc.append(py)
    return sonuc


def turkce_ad(py):
    """Kütüphanenin asıl Türkçe adı (içe_aktar ve pip yükle için)."""
    return (ACIKLAMALAR.get(py, {}).get("turkce_ad")
            or (_turkce_adlar(py) or [py])[0])


_KATLA = str.maketrans("çğıöşüÇĞİÖŞÜâÂîÎûÛ", "cgiosuCGIOSUaAiIuU")


def _katla(ad):
    return ad.translate(_KATLA)


def _uye_tablosu(py):
    """[(türkçe, python)] — modülün bütün üye çevirileri, ASCII takma adlar ve
    aynı Python adına giden eski adlar ayıklanmış olarak."""
    tablo = {}
    for t in _turkce_adlar(py):
        tablo = MODUL_METOTLARI.get(t) or tablo
        if tablo:
            break
    goruldu = set()
    cift = []
    for tr, p in tablo.items():
        # Türkçesi Python adıyla aynı olanlar (satrançtaki A1 kareleri) çeviri
        # değildir; aynı Python adına giden ikinci ad ise takma addır (ters
        # çeviride ilk yazılan kazanır).
        if tr == p or p in goruldu:
            continue
        goruldu.add(p)
        cift.append((tr, p))
    cift.sort(key=lambda c: c[1].lower())
    return cift


def _metot_tablosu(py):
    cift = []
    for p in NESNE_METOTLARI.get(py, ()):
        tr = TERS_SOZLUK.get(p)
        if isinstance(tr, str) and tr.isidentifier() and tr != p:
            cift.append((tr, p))
    return cift


def _moduller():
    sira = []
    for py in dict.fromkeys(MODUL_CEVIRILERI.values()):
        if py not in _GIZLI:
            sira.append(py)
    for py in ACIKLAMALAR:
        if py not in sira:
            sira.append(py)
    return sira


def _turkce_modul_adiyla(kod, py):
    """Ters çevirinin seçtiği modül adını (içe_aktar chess) kütüphanenin
    Türkçe adıyla (içe_aktar satranç) değiştirir. Yalnızca ad belirteçleri
    değişir; metinler, yorumlar ve öznitelikler (x.chess) olduğu gibi kalır."""
    yeni = turkce_ad(py)
    if not kod or not yeni:
        return kod
    eskiler = [a for a in _turkce_adlar(py) if a != yeni]
    noktali = [a for a in eskiler if "." in a]
    for a in noktali:
        kod = re.sub(rf"(?<![\w.]){re.escape(a)}(?![\w])", yeni, kod)
    tekil = {a for a in eskiler if "." not in a}
    if not tekil:
        return kod
    try:
        belirtecler = list(tokenize.generate_tokens(io.StringIO(kod).readline))
    except (tokenize.TokenError, IndentationError, SyntaxError):
        return kod
    satirlar = kod.splitlines(keepends=True)
    anlamli = [b for b in belirtecler if b.type not in (tokenize.NL, tokenize.COMMENT)]
    degisim = []
    for i, b in enumerate(anlamli):
        if b.type != tokenize.NAME or b.string not in tekil:
            continue
        onceki = anlamli[i - 1].string if i else ""
        sonraki = anlamli[i + 1].string if i + 1 < len(anlamli) else ""
        if onceki == ".":
            continue  # x.chess: öznitelik
        if sonraki == "." and onceki in ("içe_aktar", "den", "import", "from"):
            continue  # içe_aktar matplotlib.pyplot: alt modülün yolu
        degisim.append(b)
    for b in reversed(degisim):
        (sat, sut), (_, son) = b.start, b.end
        s = satirlar[sat - 1]
        satirlar[sat - 1] = s[:sut] + yeni + s[son:]
    return "".join(satirlar)


_KOD_PARCASI = re.compile(r"`([^`\n]+)`")
_ACIKLAMA_ONBELLEK = {}


def _ice_aktarma_baglami(py):
    """Kütüphanenin örneğindeki içe aktarma satırları ("from torch import
    nn", "import pandas as pd"): açıklamadaki `nn.Linear`, `pd.read_csv`
    gibi takma adlı parçalar bu bağlamla çevrilir."""
    satirlar = []
    for satir in (ACIKLAMALAR.get(py, {}).get("ornek") or "").splitlines():
        if re.match(r"(?:import|from)\s", satir):
            satirlar.append(satir)
    return satirlar


def _serbest_adlar(parca, baglam):
    """Parçada tanımı olmayan adlar (`print(tahta)` -> tahta): açıklamada
    bunlar okuyucunun kendi değişkenleridir; çeviride kullanıcı tanımı gibi
    korunmaları için bağlama "ad = None" olarak eklenir."""
    agac = ast.parse(parca)
    baglam_agaci = ast.parse("\n".join(baglam)) if baglam else None
    bilinen = set(dir(builtins))
    if baglam_agaci is not None:
        for d in ast.walk(baglam_agaci):
            if isinstance(d, (ast.Import, ast.ImportFrom)):
                bilinen.update((a.asname or a.name).split(".")[0] for a in d.names)
    bilinen.update(MODUL_CEVIRILERI.values())
    return sorted({d.id for d in ast.walk(agac)
                   if isinstance(d, ast.Name) and d.id not in bilinen})


def _tek_parca_cevir(baglam, parca, py):
    """(baglam + parça)yı çevirir; parçanın TürKod hâlini ya da None döner."""
    baglam = baglam + [f"{ad} = None" for ad in _serbest_adlar(parca, baglam)]
    kaynak = "\n".join(baglam + [parca])
    asil = ast.dump(ast.parse(kaynak))
    tr = python_kodu_turkceye_cevir(kaynak).strip("\n")
    if "\x00" in tr:
        return None
    tr = _turkce_modul_adiyla(tr, py)
    satirlar = tr.split("\n")
    if len(satirlar) != len(baglam) + 1:
        return None
    # Geri çevrilince aynı Python kodu çıkmıyorsa (bağlamsız parçada ad
    # karışabilir) yanlış bir şey öğretmemek için Python hâli kalır.
    if ast.dump(ast.parse(turkce_kodu_donustur(tr))) != asil:
        return None
    return satirlar[-1].strip()


def _kod_parcasini_cevir(parca, py):
    """Açıklamadaki `chess.Board()` gibi bir kod parçasının TürKod hâli
    (`satranç.Tahta()`). Python olarak ayrıştırılamayan parçalar (`pip
    install x`, `"e4"` gibi yazılar, dosya adları) olduğu gibi kalır."""
    # Açıklamadaki `\d+` gibi düzenli ifade parçaları ayrıştırılırken
    # SyntaxWarning basılıp arka uç günlüğünü kirletmesin.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            ast.parse(parca)
        except (SyntaxError, ValueError):
            return parca
        baglam = _ice_aktarma_baglami(py)
        for denenen in ((baglam, []) if baglam else ([],)):
            try:
                tr = _tek_parca_cevir(denenen, parca, py)
            except Exception:
                tr = None
            if tr:
                return tr
    return parca


def _aciklamayi_turkcelestir(metin, py):
    """Açıklamadaki ters tırnaklı kod parçalarını TürKod'a çevirir."""
    if not metin:
        return metin
    anahtar = (py, metin)
    if anahtar not in _ACIKLAMA_ONBELLEK:
        _ACIKLAMA_ONBELLEK[anahtar] = _KOD_PARCASI.sub(
            lambda m: "`" + _kod_parcasini_cevir(m.group(1), py) + "`", metin)
    return _ACIKLAMA_ONBELLEK[anahtar]


def kutuphane_listesi():
    ogeler = []
    for py in _moduller():
        bilgi = ACIKLAMALAR.get(py, {})
        ogeler.append({
            "py": py,
            "ad": bilgi.get("ad") or py,
            "turkce_ad": turkce_ad(py),
            "kategori": bilgi.get("kategori") or "Temel araçlar",
            "standart": bool(bilgi.get("standart", False)),
            "pip_adi": bilgi.get("pip_adi"),
            "ozet": bilgi.get("ozet", ""),
            "turkce_adlar": _turkce_adlar(py),
            "ceviri_sayisi": len(_uye_tablosu(py)) + len(_metot_tablosu(py)),
        })
    sira = {k: i for i, k in enumerate(KATEGORI_SIRASI)}
    ogeler.sort(key=lambda o: (sira.get(o["kategori"], 99), o["ad"].lower()))
    return {"ok": True, "kutuphaneler": ogeler, "kategoriler": KATEGORI_SIRASI}


def kutuphane_ayrintisi(py):
    py = str(py or "")
    if py not in _moduller():
        return {"ok": False, "hata": f"'{py}' adlı bir kütüphane rehberde yok."}
    bilgi = ACIKLAMALAR.get(py, {})
    ornek = bilgi.get("ornek", "")
    try:
        ornek_turkod = python_kodu_turkceye_cevir(ornek) if ornek else ""
        ornek_turkod = _turkce_modul_adiyla(ornek_turkod, py)
    except Exception:
        ornek_turkod = ""
    turkce = _turkce_adlar(py)
    pip_adi = bilgi.get("pip_adi")
    return {
        "ok": True,
        "py": py,
        "ad": bilgi.get("ad") or py,
        "turkce_ad": turkce_ad(py),
        "kategori": bilgi.get("kategori") or "Temel araçlar",
        "standart": bool(bilgi.get("standart", False)),
        "pip_adi": pip_adi,
        # "pip yükle" Türkçe adı tanır (pip_tr.paket_adini_cevir).
        "kurulum": (None if bilgi.get("standart") or not pip_adi
                    else f"pip yükle {turkce_ad(py)}"),
        "ozet": bilgi.get("ozet", ""),
        "aciklama": bilgi.get("aciklama", ""),
        "aciklama_turkod": _aciklamayi_turkcelestir(bilgi.get("aciklama", ""), py),
        "ornek_python": ornek,
        "ornek_turkod": ornek_turkod,
        "turkce_adlar": turkce,
        "uyeler": [list(c) for c in _uye_tablosu(py)],
        "metotlar": [list(c) for c in _metot_tablosu(py)],
    }
