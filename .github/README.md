<div align="center">

# TürKod IDE · Platform deneme deposu

**Bu depo, TürKod IDE'nin Windows, Linux ve macOS'ta otomatik olarak denendiği test deposudur.**

TürKod'u indirmek, kullanmak, hata bildirmek ya da katkıda bulunmak için asıl depoya git:

[**Asıl depo: YusufX-sys/turkod-ide**](https://github.com/YusufX-sys/turkod-ide) · [**Proje sitesi**](https://turkod.pages.dev/) · [**İndir**](https://github.com/YusufX-sys/turkod-ide/releases/latest)

</div>

---

## Bu depoda ne var?

Buradaki kod, asıl depodaki TürKod'un **geliştirilmekte olan** hâlidir. Her değişiklikten sonra
buraya gönderilir ve GitHub Actions'ta gerçek Windows, Linux ve macOS makinelerinde denenir.
Buradan sürüm yayımlanmaz; buradaki kod kararsız olabilir.

## Denemeler

Denemeler elle başlatılır: **Actions → Platform denemesi → Run workflow** ve bir "hedef" seçilir.
İş akışı: [`.github/workflows/platform-denemesi.yml`](workflows/platform-denemesi.yml)

| Hedef | Ne yapar? |
|---|---|
| `testler` | Python testleri Ubuntu, macOS ve Windows'ta; Flutter analyze ve test |
| `linux` | AppImage derlenir, açılış ve duman testi, ekran görüntüsü |
| `macos` | TurKod.app ve .dmg derlenir, açılış ve duman testi, ekran görüntüsü |
| `hepsi` | Üçü birden |
| `arayuz-linux` | Arayüz testleri Linux'ta: uygulama açılır, menülere tıklanır, kod yazılır, kitap üstüne çizilir |
| `arayuz-macos` | Aynı arayüz testleri macOS'ta |
| `arayuz-windows` | Aynı arayüz testleri Windows'ta |

## Hata bildirimi ve katkı

Lütfen sorunları ve önerileri **asıl depoda** aç:
[Hata bildir / öneri gönder](https://github.com/YusufX-sys/turkod-ide/issues/new/choose).
Lisans: MIT (asıl depodaki [LICENSE](https://github.com/YusufX-sys/turkod-ide/blob/main/LICENSE)).
