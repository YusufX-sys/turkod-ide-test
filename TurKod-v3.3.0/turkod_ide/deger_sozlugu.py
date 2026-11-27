"""Tırnak içindeki seçenek DEĞERLERİNİN Türkçe karşılıkları.

Sözlük yalnızca adları çevirir; metinlerin içine (haklı olarak) dokunmaz.
Bu yüzden kaplumbağada kalem_rengi("mavi"), şekil("kaplumbağa"),
hız("en_hızlı"); tkinter'da arkaplan_rengi="mavi", kabartma="çökük" gibi
değerler kütüphaneye olduğu gibi gidip "bad color name" / "unknown shape"
hatası veriyordu. Ters yönde de (Python -> TürKod) pencolor("blue")
"kalem_rengi("blue")" olarak İngilizce kalıyordu.

Burada iki yön için TEK tablo tutulur:
  * calisma_tablolari(): çalıştırıcıya gömülür; kütüphane fonksiyonları
    Türkçe değeri İngilizcesine çevirerek çağrılır (runner.py yamaları).
  * ters_degerleri_cevir(): Python -> TürKod çevirisinde, bilinen çağrı
    bağlamlarındaki İngilizce değerleri Türkçeleştirir. Üretilen her Türkçe
    değer çalışma anında geri tanındığından çeviri gidiş-dönüş güvenlidir.
Her tabloda ilk yazılan Türkçe ad kanoniktir (ters çeviride o seçilir).
"""

import re

# Türkçe renk adı -> Tk / CSS / matplotlib / Pillow'da geçerli İngilizce ad.
RENKLER = {
    "kırmızı": "red",
    "yeşil": "green",
    "mavi": "blue",
    "beyaz": "white",
    "siyah": "black",
    "gri": "gray",
    "sarı": "yellow",
    "turuncu": "orange",
    "mor": "purple",
    "pembe": "pink",
    "kahverengi": "brown",
    "turkuaz": "turquoise",
    "lacivert": "navy",
    "altın": "gold",
    "gümüş": "silver",
    "bordo": "maroon",
    "eflatun": "violet",
    "menekşe": "violet",
    "camgöbeği": "cyan",
    "macenta": "magenta",
    "fuşya": "fuchsia",
    "açık_mavi": "lightblue",
    "koyu_mavi": "darkblue",
    "gök_mavisi": "skyblue",
    "gece_mavisi": "midnightblue",
    "kraliyet_mavisi": "royalblue",
    "çelik_mavisi": "steelblue",
    "açık_yeşil": "lightgreen",
    "koyu_yeşil": "darkgreen",
    "orman_yeşili": "forestgreen",
    "deniz_yeşili": "seagreen",
    "limon_yeşili": "lime",
    "çimen_yeşili": "lawngreen",
    "zeytin_yeşili": "olive",
    "açık_gri": "lightgray",
    "koyu_gri": "darkgray",
    "açık_pembe": "lightpink",
    "koyu_kırmızı": "darkred",
    "kızıl": "crimson",
    "koyu_turuncu": "darkorange",
    "koyu_mor": "darkviolet",
    "çivit": "indigo",
    "lila": "plum",
    "orkide": "orchid",
    "bej": "beige",
    "fildişi": "ivory",
    "haki": "khaki",
    "somon": "salmon",
    "mercan": "coral",
    "domates": "tomato",
    "çikolata": "chocolate",
    "şeftali": "peachpuff",
    "kar": "snow",
    "deniz_kabuğu": "seashell",
    "toprak": "sienna",
    "camgöbeği_mavisi": "teal",
    "gri_mavi": "slategray",
}

# İngilizce yazımın eş anlamlıları (ters çeviri bunları da tanır).
_INGILIZCE_ES_ADLAR = {
    "grey": "gray", "lightgrey": "lightgray", "darkgrey": "darkgray",
    "aqua": "cyan", "slategrey": "slategray",
}

# --- kaplumbağa (turtle) ---
SEKILLER = {
    "kaplumbağa": "turtle",
    "ok": "arrow",
    "daire": "circle",
    "çember": "circle",
    "kare": "square",
    "üçgen": "triangle",
    "klasik": "classic",
    "boş": "blank",
}

HIZLAR = {
    "en_hızlı": "fastest",
    "hızlı": "fast",
    "normal": "normal",
    "yavaş": "slow",
    "en_yavaş": "slowest",
}

# kaplumbağa yaz(..., hizala=...) ve tkinter justify.
HIZALAR = {
    "sol": "left",
    "orta": "center",
    "sağ": "right",
    "sola": "left",
    "ortada": "center",
    "ortala": "center",
    "merkez": "center",
    "sağa": "right",
}

# Yazı tipi biçimleri: ("Arial", 16, "kalın"), "Arial 12 kalın italik".
YAZI_BICIMLERI = {
    "normal": "normal",
    "kalın": "bold",
    "italik": "italic",
    "eğik": "italic",
    "altı_çizili": "underline",
    "üstü_çizili": "overstrike",
}

# Klavye tuşları: ekran.tuşa_basınca(fonksiyon, "yukarı").
TUSLAR = {
    "yukarı": "Up",
    "aşağı": "Down",
    "sol": "Left",
    "sağ": "Right",
    "boşluk": "space",
    "enter": "Return",
    "giriş": "Return",
    "esc": "Escape",
    "kaçış": "Escape",
    "geri_sil": "BackSpace",
    "sil": "Delete",
    "sekme": "Tab",
}

KIPLER = {
    "standart": "standard",
    "logo": "logo",
    "dünya": "world",
}

# --- tkinter seçenek değerleri (seçenek adı -> değer tablosu) ---
KABARTMALAR = {
    "düz": "flat",
    "kabarık": "raised",
    "çökük": "sunken",
    "oluklu": "groove",
    "sırtlı": "ridge",
    "katı": "solid",
    "çıkık": "raised",
    "gömük": "sunken",
}

DURUMLAR = {
    "normal": "normal",
    "devre_dışı": "disabled",
    "etkin": "active",
    "salt_okunur": "readonly",
    "gizli": "hidden",
    "pasif": "disabled",
    "aktif": "active",
}

YANLAR = {
    "üst": "top",
    "alt": "bottom",
    "sol": "left",
    "sağ": "right",
    "üstte": "top",
    "altta": "bottom",
    "solda": "left",
    "sağda": "right",
}

DOLGULAR = {
    "her_ikisi": "both",
    "yok": "none",
    "ikisi": "both",
}

YONLER = {
    "kuzey": "n",
    "güney": "s",
    "doğu": "e",
    "batı": "w",
    "kuzeydoğu": "ne",
    "kuzeybatı": "nw",
    "güneydoğu": "se",
    "güneybatı": "sw",
    "merkez": "center",
    "orta": "center",
}

SARMALAR = {
    "kelime": "word",
    "karakter": "char",
    "yok": "none",
    "harf": "char",
}

YONELIMLER = {
    "yatay": "horizontal",
    "dikey": "vertical",
}

SECIM_KIPLERI = {
    "tek": "single",
    "gözat": "browse",
    "çoklu": "multiple",
    "genişletilmiş": "extended",
}

BIRLESIKLER = {
    "üst": "top",
    "alt": "bottom",
    "sol": "left",
    "sağ": "right",
    "orta": "center",
    "yok": "none",
}

IMLECLER = {
    "el": "hand2",
    "ok": "arrow",
    "bekle": "watch",
    "artı": "crosshair",
    "metin": "xterm",
}

# Tk'de renk alan seçenekler.
TK_RENK_SECENEKLERI = (
    "bg", "fg", "background", "foreground",
    "activebackground", "activeforeground", "disabledforeground",
    "disabledbackground", "readonlybackground",
    "highlightbackground", "highlightcolor", "insertbackground",
    "selectbackground", "selectforeground", "selectcolor", "troughcolor",
    "outline", "activefill", "activeoutline", "disabledfill", "disabledoutline",
)

# "fill": tuvalde renk, pack()'te x/y/both/none; ikisi birlikte aranır.
TK_SECENEKLERI = {
    "relief": KABARTMALAR,
    "overrelief": KABARTMALAR,
    "state": DURUMLAR,
    "side": YANLAR,
    "fill": {**DOLGULAR, **RENKLER},
    "anchor": YONLER,
    "justify": HIZALAR,
    "wrap": SARMALAR,
    "orient": YONELIMLER,
    "selectmode": SECIM_KIPLERI,
    "compound": BIRLESIKLER,
    "cursor": IMLECLER,
}
for _secenek in TK_RENK_SECENEKLERI:
    TK_SECENEKLERI[_secenek] = RENKLER

# matplotlib renk anahtar kelimeleri (ters çeviri için).
MPL_RENK_SECENEKLERI = (
    "color", "c", "facecolor", "edgecolor", "fc", "ec", "ecolor",
    "markerfacecolor", "markeredgecolor", "mfc", "mec",
)

# --- Çocuklar için eklenen kütüphaneler ---
# Terminal Renkleri (termcolor) ve Zengin Yazı (rich) yalnızca kendi renk
# adlarını tanır ("orange" ikisinde de yok). Türkçe ad, çalışma anında
# kütüphanenin adına eşlenir (runner: _tk_renk_esle); ters çeviride de
# yalnızca kütüphanenin tanıdığı adlar Türkçeleşir. Listeler kütüphanenin
# RENKLER'le eşleşen adlarıdır (termcolor 3.3, rich 15).
TERMCOLOR_RENKLERI = (
    "black", "blue", "cyan", "dark_grey", "green", "grey", "light_blue",
    "light_green", "light_grey", "magenta", "red", "white", "yellow",
)
RICH_RENKLERI = (
    "black", "blue", "cyan", "dark_blue", "dark_green", "dark_orange", "dark_red",
    "dark_violet", "green", "light_green", "magenta", "orchid", "purple", "red",
    "steel_blue", "violet", "white", "yellow",
    # rich bu renkleri sonuna 1 ekleyerek adlandırır ("orange" yok, "orange1" var).
    "gold1", "khaki1", "light_pink1", "orange1", "pink1", "plum1", "royal_blue1",
    "salmon1", "sea_green1", "sky_blue1",
)

# Zengin Yazı stilleri: "[kalın kırmızı]", style="altı_çizili mavi".
YAZI_STILLERI = {
    "kalın": "bold",
    "italik": "italic",
    "eğik": "italic",
    "altı_çizili": "underline",
    "üstü_çizili": "strike",
    "sönük": "dim",
    "yanıp_sönen": "blink",
    "ters_renk": "reverse",
    "gizli": "conceal",
}
# Terminal Renkleri: renkli("a", "yeşil", attrs=["kalın"]).
TERMCOLOR_STILLERI = {
    "kalın": "bold",
    "italik": "italic",
    "eğik": "italic",
    "altı_çizili": "underline",
    "üstü_çizili": "strike",
    "sönük": "dark",
    "yanıp_sönen": "blink",
    "ters_renk": "reverse",
    "gizli": "concealed",
}

# customtkinter: set_default_color_theme("yeşil"), set_appearance_mode("koyu").
CTK_TEMALARI = {
    "mavi": "blue",
    "yeşil": "green",
    "koyu_mavi": "dark-blue",
}
CTK_GORUNUMLERI = {
    "koyu": "dark",
    "karanlık": "dark",
    "açık": "light",
    "aydınlık": "light",
    "sistem": "system",
}

# Kolay Oyun (Pygame Zero) çizim komutlarında renk alan anahtar kelimeler.
PGZERO_RENK_SECENEKLERI = ("color", "gcolor", "ocolor", "scolor", "background")
# Etkileşimli Harita (folium) simge ve çizgi renkleri.
FOLIUM_RENK_SECENEKLERI = ("color", "fill_color", "fillColor", "icon_color")

_TR_KUCUK = str.maketrans({"İ": "i", "I": "ı"})
_ASCII = str.maketrans({
    "ç": "c", "ğ": "g", "ı": "i", "ö": "o", "ş": "s", "ü": "u",
})


def ad_normallestir(yazi):
    """'Açık Mavi', 'açık-mavi', 'AÇIK MAVİ' -> 'açık_mavi'."""
    yazi = yazi.strip().translate(_TR_KUCUK).lower()
    return re.sub(r"[\s\-]+", "_", yazi)


def _genislet(tablo):
    """Normalleştirilmiş adla birlikte ASCII ('acik_mavi') ve bitişik
    ('açıkmavi') yazımları da ekler; kanonik yazımlar ezilmez."""
    sonuc = dict(tablo)
    for tr, en in tablo.items():
        for takma in (tr.translate(_ASCII), tr.replace("_", ""),
                      tr.translate(_ASCII).replace("_", "")):
            sonuc.setdefault(takma, en)
    return sonuc


def calisma_tablolari():
    """Çalıştırıcıya gömülecek tablolar (yalnızca düz dict/str/tuple)."""
    return {
        "renk": _genislet(RENKLER),
        "sekil": _genislet(SEKILLER),
        "hiz": _genislet(HIZLAR),
        "hiza": _genislet(HIZALAR),
        "bicim": _genislet(YAZI_BICIMLERI),
        "tus": _genislet(TUSLAR),
        "kip": _genislet(KIPLER),
        "tk": {ad: _genislet(t) for ad, t in TK_SECENEKLERI.items()},
        "stil": _genislet(YAZI_STILLERI),
        "tc_stil": _genislet(TERMCOLOR_STILLERI),
        "ctk_tema": _genislet(CTK_TEMALARI),
        "ctk_gorunum": _genislet(CTK_GORUNUMLERI),
    }


# ---------------------------------------------------------------------
# Ters yön: Python -> TürKod
# ---------------------------------------------------------------------

def _ters(tablo, es_adlar=None):
    ters = {}
    for tr, en in tablo.items():
        ters.setdefault(en, tr)
    for es, asil in (es_adlar or {}).items():
        if asil in ters:
            ters.setdefault(es, ters[asil])
    return ters


_TERS_RENK = _ters(RENKLER, _INGILIZCE_ES_ADLAR)
_TERS_SEKIL = _ters(SEKILLER)
_TERS_HIZ = _ters(HIZLAR)
_TERS_HIZA = _ters(HIZALAR)
_TERS_BICIM = _ters(YAZI_BICIMLERI)
_TERS_TUS = _ters(TUSLAR)
_TERS_KIP = _ters(KIPLER)
_TERS_TK = {ad: _ters(t, _INGILIZCE_ES_ADLAR if t is RENKLER else None)
            for ad, t in TK_SECENEKLERI.items()}
_TERS_TK["fill"] = {**_TERS_RENK, **_ters(DOLGULAR)}


def _renk_anahtari(yazi):
    return yazi.strip().lower().replace(" ", "").replace("_", "")


def _kutuphane_renk_anahtari(ad):
    """'light_grey', 'dark-blue', 'orange1' -> 'lightgray', 'darkblue', 'orange'
    (RENKLER yazımı; Zengin Yazı bazı renkleri sonuna 1 ekleyerek adlandırır)."""
    return re.sub(r"[\s_\-]+", "", ad.strip().lower()).replace("grey", "gray").rstrip("1")


def _kutuphane_ters_renk(adlar):
    """Kütüphanenin renk adı -> Türkçe (yalnızca RENKLER'de karşılığı olanlar)."""
    sonuc = {}
    for ad in adlar:
        tr = _TERS_RENK.get(_kutuphane_renk_anahtari(ad))
        if tr is not None:
            sonuc[_renk_anahtari(ad)] = tr
    return sonuc


def _kutuphane_ileri_renk(adlar):
    """Türkçe renk -> kütüphanenin kendi adı ('açık_mavi' -> 'light_blue')."""
    normal = {}
    for ad in adlar:
        normal.setdefault(_kutuphane_renk_anahtari(ad), ad)
    sonuc = {}
    for tr, en in RENKLER.items():
        ad = normal.get(_kutuphane_renk_anahtari(en))
        if ad is not None:
            sonuc.setdefault(tr, ad)
    return _genislet(sonuc)


class _Yon:
    """Çeviri yönünün tabloları. Ters yön (Python -> TürKod) İngilizce adı
    çağrıya özgü anahtarla arar; ileri yön (TürKod -> Python) Türkçe adı
    ad_normallestir ile arar ('Açık Mavi', 'acik_mavi' de bulunur)."""

    def __init__(self, ileri, **tablolar):
        self.ileri = ileri
        self.__dict__.update(tablolar)

    def anahtar(self, ters_anahtar):
        return ad_normallestir if self.ileri else ters_anahtar


_TERS = _Yon(
    False,
    renk=_TERS_RENK, sekil=_TERS_SEKIL, hiz=_TERS_HIZ, hiza=_TERS_HIZA,
    bicim=_TERS_BICIM, tus=_TERS_TUS, kip=_TERS_KIP, tk=_TERS_TK,
    tc_renk=_kutuphane_ters_renk(TERMCOLOR_RENKLERI),
    tc_stil=_ters(TERMCOLOR_STILLERI),
    rich_renk=_kutuphane_ters_renk(RICH_RENKLERI),
    rich_stil=_ters(YAZI_STILLERI),
    ctk_tema=_ters(CTK_TEMALARI),
    ctk_gorunum=_ters(CTK_GORUNUMLERI),
)
_TERS.tc_zemin = {"on" + en: "on_" + tr for en, tr in _TERS.tc_renk.items()}

_ILERI = _Yon(
    True,
    renk=_genislet(RENKLER), sekil=_genislet(SEKILLER), hiz=_genislet(HIZLAR),
    hiza=_genislet(HIZALAR), bicim=_genislet(YAZI_BICIMLERI), tus=_genislet(TUSLAR),
    kip=_genislet(KIPLER), tk={ad: _genislet(t) for ad, t in TK_SECENEKLERI.items()},
    tc_renk=_kutuphane_ileri_renk(TERMCOLOR_RENKLERI),
    tc_stil=_genislet(TERMCOLOR_STILLERI),
    rich_renk=_kutuphane_ileri_renk(RICH_RENKLERI),
    rich_stil=_genislet(YAZI_STILLERI),
    ctk_tema=_genislet(CTK_TEMALARI),
    ctk_gorunum=_genislet(CTK_GORUNUMLERI),
)
_ILERI.tc_zemin = {"on_" + tr: "on_" + ad for tr, ad in _ILERI.tc_renk.items()}


def _rich_stili_cevir(stil, yon=_TERS):
    """'bold red on white' <-> 'kalın kırmızı on beyaz'. Tanınmayan bir kelime
    (renk kodu, bağlantı ...) varsa stil olduğu gibi bırakılır."""
    kelimeler = stil.split()
    if not kelimeler:
        return None
    sonuc = []
    for k in kelimeler:
        kucuk = k.lower()
        stil_anahtari = ad_normallestir(k) if yon.ileri else kucuk
        renk_anahtari = ad_normallestir(k) if yon.ileri else _renk_anahtari(kucuk)
        if kucuk in ("on", "not"):
            sonuc.append(k)
        elif stil_anahtari in yon.rich_stil:
            sonuc.append(yon.rich_stil[stil_anahtari])
        elif renk_anahtari in yon.rich_renk:
            sonuc.append(yon.rich_renk[renk_anahtari])
        else:
            return None
    return " ".join(sonuc)


_RICH_ETIKET = re.compile(r"(?<!\\)\[(/?)([a-z][a-z0-9_ ]*)\]")
_RICH_ETIKET_TR = re.compile(r"(?<!\\)\[(/?)([^\W\d_][\w ]*)\]")


def _rich_isaretlerini_cevir(metin, yon=_TERS):
    """'[bold red]Uyarı[/bold red]' <-> '[kalın kırmızı]Uyarı[/kalın kırmızı]'.
    rich etiketin ilk harfini a-z ile tanır; Türkçe hâli ç/ö/ü ile başlayacaksa
    (üstü_çizili) ters çeviride etiket İngilizce kalır."""
    def degistir(m):
        cevrilmis = _rich_stili_cevir(m.group(2), yon)
        if cevrilmis is None or (not yon.ileri and not re.match(r"[a-z]", cevrilmis)):
            return m.group(0)
        return f"[{m.group(1)}{cevrilmis}]"
    return (_RICH_ETIKET_TR if yon.ileri else _RICH_ETIKET).sub(degistir, metin)


def _arguman_listesi(kod, bas):
    """kod[bas] açılan parantezin hemen sonrası: üst düzey argümanlar,
    [(anahtar ya da None, metin)]. Metinler yer tutucuda olduğundan tırnak
    içindeki parantez/virgül karışmaz."""
    derinlik, parca_bas, parcalar = 0, bas, []
    for i in range(bas, len(kod)):
        ch = kod[i]
        if ch in "([{":
            derinlik += 1
        elif ch in ")]}":
            if derinlik == 0:
                parcalar.append(kod[parca_bas:i])
                break
            derinlik -= 1
        elif ch == "," and derinlik == 0:
            parcalar.append(kod[parca_bas:i])
            parca_bas = i + 1
    else:
        return []
    sonuc = []
    for p in parcalar:
        m = re.match(r"\s*([A-Za-z_]\w*)\s*=(?!=)\s*(.*?)\s*$", p, re.S)
        sonuc.append((m.group(1), m.group(2)) if m else (None, p.strip()))
    return sonuc


_YT = r"\x00METIN_(\d+)\x00"
_YT_LISTESI = rf"({_YT}(?:\s*,\s*{_YT})*)"
_DUZ_METIN = re.compile(r"""^([rRuU]?)(['"])(.*)\2$""", re.S)
_KUTUPHANE = re.compile(
    r"^[ \t]*(?:import|from)[ \t]+(turtle|tkinter|matplotlib|PIL|pygame|pgzrun|pgzero|"
    r"termcolor|rich|folium|qrcode|customtkinter)\b", re.M)


def ters_degerleri_cevir(gecici_kod, metinler):
    """Python kodunda (metinler yer tutucuya alınmışken) bilinen çağrıların
    İngilizce değerlerini Türkçeleştirir. metinler: {uid: kaynak_metin};
    yerinde güncellenir. Yalnızca ilgili kütüphane içe aktarılmışsa çalışır;
    başka bir kütüphanenin color="blue" değeri Türkçeleşip bozulmaz."""
    _degerleri_cevir(gecici_kod, metinler, _TERS)


def ileri_degerleri_cevir(kod):
    """TürKod'dan çevrilmiş Python kodunda aynı çağrıların Türkçe değerlerini
    kütüphanenin İngilizce adına çevirir: screen.fill("turuncu") ->
    screen.fill("orange"). Böylece "Kodu Çevir" ile alınan Python kodu TürKod
    dışında da çalışır (çalıştırıcının yamaları ayrıca Türkçe adları tanır).
    Kod ayrıştırılamazsa (yarım satır ...) olduğu gibi döner."""
    if "import" not in kod or not _KUTUPHANE.search(kod):
        return kod
    import io
    import tokenize
    try:
        jetonlar = list(tokenize.generate_tokens(io.StringIO(kod).readline))
    except (tokenize.TokenError, SyntaxError, ValueError):
        return kod
    satir_basi = [0]
    for m in re.finditer("\n", kod):
        satir_basi.append(m.end())

    def konum(satir_sutun):
        return satir_basi[satir_sutun[0] - 1] + satir_sutun[1]

    f_bas = getattr(tokenize, "FSTRING_START", None)
    f_son = getattr(tokenize, "FSTRING_END", None)
    araliklar, derinlik, f_konum = [], 0, None
    for j in jetonlar:
        if f_bas is not None and j.type == f_bas:
            if derinlik == 0:
                f_konum = j.start
            derinlik += 1
        elif f_son is not None and j.type == f_son:
            derinlik -= 1
            if derinlik == 0:
                araliklar.append((konum(f_konum), konum(j.end)))
        elif j.type == tokenize.STRING and derinlik == 0:
            araliklar.append((konum(j.start), konum(j.end)))
    if not araliklar:
        return kod

    parcalar, metinler, onceki = [], {}, 0
    for uid, (bas, son) in enumerate(araliklar):
        parcalar.append(kod[onceki:bas])
        parcalar.append(f"\x00METIN_{uid}\x00")
        metinler[uid] = kod[bas:son]
        onceki = son
    parcalar.append(kod[onceki:])
    asil = dict(metinler)
    _degerleri_cevir("".join(parcalar), metinler, _ILERI)
    if metinler == asil:
        return kod

    sonuc, onceki = [], 0
    for uid, (bas, son) in enumerate(araliklar):
        sonuc.append(kod[onceki:bas])
        sonuc.append(metinler[uid])
        onceki = son
    sonuc.append(kod[onceki:])
    return "".join(sonuc)


def _degerleri_cevir(gecici_kod, metinler, yon):
    kutuphaneler = set(_KUTUPHANE.findall(gecici_kod))
    if not kutuphaneler:
        return

    def cevir(uid, tablo, anahtar=str.strip):
        uid = int(uid)
        kaynak = metinler.get(uid)
        if kaynak is None:
            return
        m = _DUZ_METIN.match(kaynak)
        if not m or "\\" in m.group(3) or m.group(2) * 3 in kaynak:
            return
        karsilik = tablo.get(yon.anahtar(anahtar)(m.group(3)))
        if karsilik is not None:
            metinler[uid] = f"{m.group(1)}{m.group(2)}{karsilik}{m.group(2)}"

    def konumsal(desen, tablo, anahtar=str.strip):
        for m in re.finditer(desen + r"\(\s*" + _YT_LISTESI + r"\s*[,)]", gecici_kod):
            for uid in re.findall(_YT, m.group(1)):
                cevir(uid, tablo, anahtar)

    def anahtar_kelime(adlar, tablolar, anahtar=str.strip):
        desen = r"(?<![\w.])(" + "|".join(adlar) + r")\s*=\s*" + _YT + r"(?=\s*[,)\n])"
        for m in re.finditer(desen, gecici_kod):
            cevir(m.group(2), tablolar[m.group(1)], anahtar)

    def yazi_tipi_bicimi():
        # font=("Arial", 16, "bold") <-> ("Arial", 16, "kalın")
        desen = r"\bfont\s*=\s*\(\s*" + _YT + r"\s*,\s*[^,()]+,\s*" + _YT
        for m in re.finditer(desen, gecici_kod):
            cevir(m.group(2), yon.bicim)

    if "turtle" in kutuphaneler:
        konumsal(r"\b(?:pencolor|fillcolor|bgcolor|color)", yon.renk, _renk_anahtari)
        konumsal(r"\bshape", yon.sekil)
        konumsal(r"\bspeed", yon.hiz)
        konumsal(r"\bmode", yon.kip)
        anahtar_kelime(["shape"], {"shape": yon.sekil})
        anahtar_kelime(["align"], {"align": yon.hiza})
        for m in re.finditer(
                r"\bonkey(?:press|release)?\(\s*[^,()]+,\s*" + _YT, gecici_kod):
            cevir(m.group(1), yon.tus, lambda y: y)
        yazi_tipi_bicimi()
    if "tkinter" in kutuphaneler:
        renkli = [ad for ad, t in TK_SECENEKLERI.items() if t is RENKLER] + ["fill"]
        anahtar_kelime(renkli, yon.tk, _renk_anahtari)
        anahtar_kelime([ad for ad in TK_SECENEKLERI if ad not in renkli], yon.tk)
        yazi_tipi_bicimi()
    if "matplotlib" in kutuphaneler:
        anahtar_kelime(MPL_RENK_SECENEKLERI,
                       dict.fromkeys(MPL_RENK_SECENEKLERI, yon.renk), _renk_anahtari)
    if "PIL" in kutuphaneler:
        anahtar_kelime(["fill", "outline"],
                       {"fill": yon.renk, "outline": yon.renk}, _renk_anahtari)
        for m in re.finditer(r"\bImage\.new\(\s*[^,()]+,\s*(?:\([^()]*\)|[\w.]+)\s*,\s*"
                             + _YT, gecici_kod):
            cevir(m.group(1), yon.renk, _renk_anahtari)
    if "pygame" in kutuphaneler:
        konumsal(r"(?:\.fill|\bColor)", yon.renk, _renk_anahtari)
        for m in re.finditer(r"\bdraw\.\w+\(\s*[\w.]+\s*,\s*" + _YT, gecici_kod):
            cevir(m.group(1), yon.renk, _renk_anahtari)

    def yer_tutucu(deger):
        m = re.fullmatch(_YT, deger.strip())
        return m.group(1) if m else None

    def metni_degistir(uid, donustur):
        uid = int(uid)
        kaynak = metinler.get(uid)
        m = _DUZ_METIN.match(kaynak or "")
        if not m or "\\" in m.group(3) or m.group(2) * 3 in kaynak:
            return
        yeni = donustur(m.group(3))
        if yeni is not None and yeni != m.group(3):
            metinler[uid] = f"{m.group(1)}{m.group(2)}{yeni}{m.group(2)}"

    renk_bul = yon.anahtar(_renk_anahtari)

    def renk_listeleri(tablo):
        # renkler = ["red", "orange", "gold"]: hepsi renkse çevrilir.
        desen = r"[\[(]\s*(" + _YT + r"(?:\s*,\s*" + _YT + r")+)\s*,?\s*[\])]"
        for m in re.finditer(desen, gecici_kod):
            uidler = re.findall(_YT, m.group(1))
            degerler = [_DUZ_METIN.match(metinler.get(int(u), "")) for u in uidler]
            if all(d and renk_bul(d.group(3)) in tablo for d in degerler):
                for u in uidler:
                    cevir(u, tablo, _renk_anahtari)

    def atamalar(donustur):
        # renk = "green" (sonra renkli(metin, renk) ile kullanılır).
        for m in re.finditer(r"(?m)^[ \t]*[A-Za-z_]\w*[ \t]*=[ \t]*" + _YT + r"[ \t]*$",
                             gecici_kod):
            metni_degistir(m.group(1), donustur)

    def tablodan(tablo):
        return lambda y: tablo.get(renk_bul(y))

    def rich_stili(stil):
        return _rich_stili_cevir(stil, yon)

    for ad in ("turtle", "tkinter", "matplotlib", "PIL", "pygame", "pgzrun", "pgzero",
               "folium"):
        if ad in kutuphaneler:
            renk_listeleri(yon.renk)
            break

    if kutuphaneler & {"pgzrun", "pgzero"}:
        # screen.fill("orange"), screen.draw.filled_circle(konum, 20, "orange"),
        # screen.draw.text("Merhaba", (10, 10), color="white")
        for m in re.finditer(r"\bscreen\.(?:fill|draw\.(\w+))\(|\bColor\(", gecici_kod):
            metin_cagrisi = m.group(1) in ("text", "textbox")
            for i, (anahtar, deger) in enumerate(_arguman_listesi(gecici_kod, m.end())):
                if anahtar is None and (i == 0 and metin_cagrisi):
                    continue
                if anahtar is not None and anahtar not in PGZERO_RENK_SECENEKLERI:
                    continue
                uid = yer_tutucu(deger)
                if uid is not None:
                    cevir(uid, yon.renk, _renk_anahtari)
    if "folium" in kutuphaneler:
        anahtar_kelime(FOLIUM_RENK_SECENEKLERI,
                       dict.fromkeys(FOLIUM_RENK_SECENEKLERI, yon.renk), _renk_anahtari)
    if "qrcode" in kutuphaneler:
        anahtar_kelime(["fill_color", "back_color"],
                       {"fill_color": yon.renk, "back_color": yon.renk}, _renk_anahtari)
    if "customtkinter" in kutuphaneler:
        konumsal(r"\bset_default_color_theme", yon.ctk_tema)
        konumsal(r"\bset_appearance_mode", yon.ctk_gorunum)
        anahtar_kelime(["mode"], {"mode": yon.ctk_gorunum})
    if "termcolor" in kutuphaneler:
        # renkli(metin, "green", "on_red", attrs=["bold"])
        for m in re.finditer(r"\b(?:colored|cprint)\(", gecici_kod):
            for i, (anahtar, deger) in enumerate(_arguman_listesi(gecici_kod, m.end())):
                if anahtar == "color" or (anahtar is None and i == 1):
                    tablo = yon.tc_renk
                elif anahtar == "on_color" or (anahtar is None and i == 2):
                    tablo = yon.tc_zemin
                elif anahtar == "attrs" or (anahtar is None and i == 3):
                    for uid in re.findall(_YT, deger):
                        cevir(uid, yon.tc_stil)
                    continue
                else:
                    continue
                uid = yer_tutucu(deger)
                if uid is not None:
                    cevir(uid, tablo, _renk_anahtari)
        renk_listeleri(yon.tc_renk)
        atamalar(tablodan({**yon.tc_renk, **yon.tc_zemin}))
    if "rich" in kutuphaneler:
        # style="bold cyan", "[bold red]Uyarı[/bold red]"
        for m in re.finditer(r"(?<![\w.])(?:style|header_style|border_style|title_style)\s*=\s*"
                             + _YT, gecici_kod):
            metni_degistir(m.group(1), rich_stili)
        for uid, kaynak in list(metinler.items()):
            if "[" in kaynak:
                metni_degistir(uid, lambda s: _rich_isaretlerini_cevir(s, yon))
        renk_listeleri(yon.rich_renk)
        atamalar(rich_stili)
