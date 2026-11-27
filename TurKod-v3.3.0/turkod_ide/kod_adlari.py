"""Yapay zekânın yazdığı Python kodunda, modüllerde olmayan adlar.

Kodi kod isteyince kodu AI Asistan yazar; kod editöre yazılmadan önce
denetlenir (ide_core._kod_denetle). Eskiden yalnızca sözdizimine bakılıyordu:
model `turtle.save()` / `turtle.restore()` gibi hiç olmayan komutlar
uydurunca kod denetimden geçiyor, çalışınca AttributeError veriyordu.

Burada kodun içe aktardığı modüllerde kullanılan her ad (`turtle.save`,
`from math import kokal`) kullanıcı programlarını çalıştıran Python'da ayrı
bir süreçte aranır: modüllerin yüklenirken yaptığı işler (çıktı, pencere ...)
TürKod'u etkilemez. Denetim yapılamazsa (Python yok, süre doldu) sessizce
boş liste döner; kod yine sözdizimiyle denetlenmiş olur.
"""
import ast
import json
import os
import subprocess
import tempfile

try:
    from . import platform_katmani
except ImportError:
    import platform_katmani

# Yüklenince iş yapan (tarayıcı açan, yazı basan, pencere açan) modüller
# denetlenmez.
YUKLENMEYECEK = {"antigravity", "this", "__hello__", "__phello__", "__future__",
                 "idlelib", "turtledemo"}
ZAMAN_ASIMI = 20
_ISARET = "@@KOD_ADLARI@@"

# Ayrı süreçte çalışan denetçi: {modül: [adlar]} okur, olmayanları yazar.
# Yüklenemeyen modül atlanır (kurulu değilse "modül yok" hatası ayrı konudur).
_DENETCI = r'''
import importlib, json, sys
istek = json.loads(sys.stdin.read())
sonuc = {}
for modul, adlar in istek.items():
    try:
        m = importlib.import_module(modul)
    except BaseException:
        continue
    eksik = []
    for ad in adlar:
        if hasattr(m, ad):
            continue
        try:
            importlib.import_module(modul + "." + ad)  # alt modül (xml.dom gibi)
            continue
        except BaseException:
            pass
        eksik.append(ad)
    sonuc[modul] = eksik
sys.stdout = sys.__stdout__
print("@@KOD_ADLARI@@" + json.dumps(sonuc), flush=True)
'''


def _kullanilan_adlar(agac):
    """[(satır, modül, ad)]: içe aktarılan modüllerde kullanılan adlar."""
    takma = {}  # koddaki ad -> modül
    cakisan = set()
    from_adlari = []
    for d in ast.walk(agac):
        if isinstance(d, ast.Import):
            for a in d.names:
                ad = a.asname or a.name.split(".")[0]
                modul = a.name if a.asname else a.name.split(".")[0]
                if takma.get(ad, modul) != modul:
                    cakisan.add(ad)
                takma[ad] = modul
        elif isinstance(d, ast.ImportFrom) and d.level == 0 and d.module:
            for a in d.names:
                if a.name != "*":
                    from_adlari.append((d.lineno, d.module, a.name))

    # Sonradan başka bir şeye bağlanan ad denetlenmez (`turtle = turtle.Turtle()`).
    atanan = set(cakisan)
    atanan_oznitelik = set()
    for d in ast.walk(agac):
        if isinstance(d, ast.Name) and isinstance(d.ctx, (ast.Store, ast.Del)):
            atanan.add(d.id)
        elif isinstance(d, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            atanan.add(d.name)
        elif isinstance(d, ast.arg):
            atanan.add(d.arg)
        elif isinstance(d, ast.ExceptHandler) and d.name:
            atanan.add(d.name)
        elif (isinstance(d, ast.Attribute) and isinstance(d.ctx, (ast.Store, ast.Del))
              and isinstance(d.value, ast.Name)):
            atanan_oznitelik.add((d.value.id, d.attr))  # `math.yeni = 1`

    sonuc = list(from_adlari)
    for d in ast.walk(agac):
        if (isinstance(d, ast.Attribute) and isinstance(d.ctx, ast.Load)
                and isinstance(d.value, ast.Name) and d.value.id in takma
                and d.value.id not in atanan
                and (d.value.id, d.attr) not in atanan_oznitelik):
            sonuc.append((d.lineno, takma[d.value.id], d.attr))
    return [(s, m, a) for s, m, a in sonuc if m.split(".")[0] not in YUKLENMEYECEK]


def olmayan_adlar(py, python_exe):
    """[(satır, "modül.ad")]: kodda kullanılan ama modülde olmayan adlar
    (satır sırasıyla, her ad bir kez). Denetlenemezse []."""
    if not python_exe:
        return []
    try:
        kullanilan = _kullanilan_adlar(ast.parse(py))
    except (SyntaxError, ValueError):
        return []
    if not kullanilan:
        return []
    istek = {}
    for _, modul, ad in kullanilan:
        if ad not in istek.setdefault(modul, []):
            istek[modul].append(ad)
    ortam = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONDONTWRITEBYTECODE="1")
    try:
        # Boş bir klasörde çalışır: o klasördeki `random.py` gibi dosyalar
        # gerçek modülün yerine geçmesin.
        with tempfile.TemporaryDirectory(prefix="turkod_adlar_") as klasor:
            r = subprocess.run(
                [python_exe, "-c", _DENETCI], input=json.dumps(istek), capture_output=True,
                text=True, encoding="utf-8", errors="replace", timeout=ZAMAN_ASIMI,
                cwd=klasor, env=ortam, **platform_katmani.gizli_surec_ayarlari())
    except (OSError, subprocess.SubprocessError, ValueError):
        return []
    satir = next((s for s in reversed((r.stdout or "").splitlines())
                  if s.startswith(_ISARET)), None)
    if satir is None:
        return []
    try:
        eksikler = json.loads(satir[len(_ISARET):])
    except ValueError:
        return []
    sonuc, gorulen = [], set()
    for s, modul, ad in sorted(kullanilan):
        ad_tam = f"{modul}.{ad}"
        if ad in (eksikler.get(modul) or []) and ad_tam not in gorulen:
            gorulen.add(ad_tam)
            sonuc.append((s, ad_tam))
    return sonuc
