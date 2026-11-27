# Kodi İfadeleri Implementation Plan

**Goal:** Kodi'ye çeşitli yüz, poz, hareket ve efekt ekle; yapay zekâ "ifade" eylemiyle seçsin.

**Architecture:** Python `kodi.py` "ifade" eylemini doğrular; `ide_core._kodi_cevabi` onu
eylem listesinden çıkarıp cevaba `ifade` sözlüğü olarak koyar. Flutter `KodiMesaji.ifade`
saklar; `_KodiCanli` bunu `KodiRobotu`'na verir; `KodiRessami` çizer.

**Tech Stack:** Python 3 (unittest), Flutter (CustomPainter, flutter_test).

**Spec:** `docs/superpowers/specs/2026-11-26-kodi-ifadeleri-design.md`

## Global Constraints
- Yeni paket yok; sisteme özgü kod yok. Git komutu çalıştırılmaz (kullanıcı commit eder).
- Kare hızı kuralları korunur.

## Review Focus
- Model geçersiz/eksik değer yazarsa: değer atılır, Kodi bozulmaz (Python testi).
- `ifade` eylemi balonda iş kartı olarak görünmez, izin istemez (Python testi: eylemlerde yok).
- Eski kayıtlı sohbet (ifade alanı yok) yüklenince hata vermez (Dart testi).
- Masaüstü penceresi sohbeti json ile taşır: ifade json'da korunur (Dart testi).
- Bütün yüz × poz bileşimleri çizilirken hata atmaz (Dart widget testi).

### Task 1: Python ifade eylemi
- Files: `turkod_ide/kodi.py` (YUZLER, POZLAR, HAREKETLER, EFEKTLER sabitleri; `_dogrula` "ifade";
  EYLEM_GIRIS satırı; ARACLAR enum + alanlar), `turkod_ide/ide_core.py` (`_kodi_cevabi`:
  ifade eylemini ayır, sonuca `"ifade": {...}`), `tests/test_kodi_ifade.py`.
- Tests: geçerli eylem korunur; bilinmeyen değer atılır; hepsi geçersiz → None; `_tur_tahmini`
  "yuz" alanından "ifade" çıkarır.

### Task 2: Flutter çizim
- Files: `turkod_flutter/lib/kodi_ifade.dart` (yeni: enumlar, `KodiHali`, ad→enum çözümleme),
  `turkod_flutter/lib/kodi.dart` (`KodiRessami`/`KodiRobotu`: poz, hareket, efekt parametreleri).
- Tests: `test/kodi_test.dart` bütün yüz/poz/hareket/efekt çizimi.

### Task 3: Flutter bağlama
- `KodiMesaji.ifade` (json), cevaptan okuma, `_KodiCanli` önceliği, 6 sn sonra normale dönüş,
  2 dk boşta uykulu.
- Tests: json gidiş-dönüş; eski json.

### Task 4: Kitap + sürüm notları
- `belgeler/KITAP_BAKIM.md` adımlarıyla Kodi sayfasına kısa ekleme; `4.0 notlar.txt`.
