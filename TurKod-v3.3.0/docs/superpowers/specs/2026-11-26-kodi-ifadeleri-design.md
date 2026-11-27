# Kodi'nin yüz ifadeleri, pozları ve hareketleri — tasarım

## Amaç
Kodi daha canlı ve çeşitli görünsün; hangi yüzle, hangi pozda, hangi hareketle
konuşacağına çoğunlukla yapay zekâ karar versin.

## Kapsam
- **Yüzler (`KodiYuzu`)**: mutlu, konusuyor, dusunceli, uzgun, dinliyor (eski) +
  heyecanli (yıldız göz), saskin, kahkaha, goz_kirp, sevgi (kalp göz), utangac,
  merakli, endiseli, uykulu.
- **Pozlar (`KodiPozu`)**: normal, el_salla, dusun, zafer (iki kol havada),
  basparmak, sola_goster, saga_goster, omuz_silk, alkis, eller_belde, yuz_kapa.
- **Hareketler (`KodiHareketi`)**: yok, zipla, dans, don, titre, selam (eğilme),
  salla (yana sallanma).
- **Efektler (`KodiEfekti`)**: yok, konfeti, kalpler, yildizlar, soru, unlem, zzz.

## Yapay zekâ denetimi
- Yeni eylem: `{"eylem": "ifade", "yuz": "...", "poz": "...", "hareket": "...", "efekt": "..."}`.
  Hepsi isteğe bağlı; bilinmeyen değer atılır, hiçbiri geçerli değilse eylem yok sayılır.
- Python (`kodi.py`) eylemi doğrular; `ide_core` onu eylem listesinden çıkarıp cevaba
  `ifade` alanı olarak koyar (balonda iş kartı olmaz, izin istemez, "iş vaadi" sayılmaz).
- Flutter: `KodiMesaji.ifade` olarak saklanır; Kodi o cevabı yazarken ve ardından
  ~6 sn o hâlde kalır, sonra normale döner. Konuşurken ağız yine oynar (yüz seçimi
  ağzı ezmez: konuşma sırasında ağız açılıp kapanır, gözler seçilen yüzden gelir).
- Öncelik: dinliyor > bekliyor(düşünme) > yapay zekânın seçtiği > hata (üzgün) > varsayılan.
- Programın kendisi: uzun süre (2 dk) etkileşim yoksa uykulu yüz + zzz.

## Kısıtlar
- Tek kod; yalnız Flutter CustomPainter. Yeni paket yok. Üç sistemde aynı.
- Kare hızı kuralları korunur (etkin 24 kare/sn, boşta 12; dinlenince durur).
- Yeni ayar yok.

## Seçilen yol ve diğerleri
- Seçilen: mevcut eylem şablonuna yeni "ifade" eylemi (ucuz, araç şemasıyla uyumlu).
- Elenen: duygu analizini programın kelimelerle yapması (yapay zekâ denetimi istenmişti);
  ayrı mini istekle duygu sordurmak (her cevapta fazladan istek, token).
