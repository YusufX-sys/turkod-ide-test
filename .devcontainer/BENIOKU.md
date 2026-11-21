# TürKod'u tarayıcıda Linux'ta denemek (GitHub Codespaces)

Bu klasör, TürKod'un Linux sürümünü bir Linux bilgisayarı olmadan, tarayıcıdan
**arayüzüyle** denemek içindir. Codespaces, GitHub'ın tarayıcıda açılan Linux
bilgisayarıdır; buna bir masaüstü eklenmiştir.

## Önce

Actions'ta **Platform denemesi** iş akışını `linux` hedefiyle bir kez çalıştır.
Codespace, o çalıştırmanın ürettiği AppImage paketini kullanır. Paketler 3 gün
saklanır; süresi geçtiyse iş akışını yeniden çalıştır.

## Açmak

1. Depoda **Code → Codespaces → Create codespace on main**.
2. İlk açılışta kütüphaneler kurulur (birkaç dakika). Bitince terminalde
   "Hazır" yazar.
3. Terminale yaz:

   ```bash
   bash .devcontainer/turkod_ac.sh
   ```

4. Alttaki **PORTS** sekmesinde **TürKod masaüstü (6080)** satırındaki küre simgesine
   tıkla. Açılan sayfada **Connect** de; parola: `vscode`.
5. TürKod masaüstünde açılır: kod yaz, **Çalıştır**'a bas, kaplumbağa çizimini gör,
   menüleri, Kodi'yi ve ayarları dene.

## Arayüzsüz denemeler (terminalde)

```bash
bash .devcontainer/turkod_ac.sh kabuk              # TürKod Kabuğu (satır satır kod)
bash .devcontainer/turkod_ac.sh ornek.trpy         # bir .trpy dosyasını çalıştırır
bash .devcontainer/turkod_ac.sh --yenile           # en son paketi yeniden indirir
```

## Sorun çıkarsa

- **"GitHub'a erişilemedi"**: Codespace'in kendi izni yetmiyor olabilir. Terminalde
  `unset GITHUB_TOKEN`, sonra `gh auth login --web` ile kendi hesabınla gir ve
  `bash .devcontainer/turkod_ac.sh --yenile` çalıştır.
- **Pencere açılmadı**: `~/turkod/arayuz.log` ve `~/.local/share/TurKod/backend.log`
  dosyalarına bak.
- Masaüstü yavaş olabilir: ekran kartı yoktur, her şey işlemcide çizilir.

## Bitirince

Sol alttaki **Codespaces** menüsünden **Stop Current Codespace** de. Açık kaldıkça
aylık ücretsiz süreden düşer. İşin tamamen bittiyse github.com/codespaces sayfasından
sil (diskte yer tutar).

## Sınırlar

- Bu bir **Linux** denemesidir; macOS Codespaces'te yoktur.
- AppImage'ın kendi güncelleme özelliği burada denenemez (paket açılarak çalışır).
- Ses (Kodi'nin okuması) tarayıcıya gelmez.
