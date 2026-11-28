import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:path/path.dart' as p;

import 'platform_ayarlari.dart';

/// backend.call ile aynı imza (main.dart'ı import etmemek için).
typedef BackendCagri = Future<Map<String, dynamic>> Function(String command,
    [Map<String, dynamic> params]);

const Color _yesil = Color(0xFF2ECC71);

/// Güncelleme denetimi.
///
/// * Açılışta (sessiz: true): yeni sürüm varsa "Yeni sürüm yayınlandı" paneli çıkar.
///   Daha önce "Atla" denen sürüm için tekrar sorulmaz.
/// * "Güncelleştirmeler > Güncelleştirmeleri Denetle" (sessiz: false): yeni sürüm
///   varsa aynı panel, yoksa "Programınız Güncel" paneli çıkar.
/// * [kaydet]: Yükle'ye basılınca, uygulama kapanmadan ÖNCE çağrılır. false dönerse
///   (bir dosya yazılamadıysa) güncelleme iptal edilir.
Future<void> guncellemeKontrolEt(
  BuildContext context,
  BackendCagri cagir, {
  Future<bool> Function()? kaydet,
  bool sessiz = true,
}) async {
  Map<String, dynamic> r;
  try {
    r = await cagir('guncelleme_kontrol');
  } catch (e) {
    if (!sessiz && context.mounted) {
      await _bilgiPaneli(
        context,
        ikon: Icons.error_outline,
        ikonRenk: Colors.orange,
        baslik: 'Güncelleme denetlenemedi',
        metin: _hataMetni(e),
      );
    }
    return;
  }
  if (!context.mounted) return;

  final mevcut = (r['mevcut'] ?? '').toString();
  if (r['guncelleme_var'] != true) {
    if (!sessiz) {
      await _bilgiPaneli(
        context,
        ikon: Icons.check_circle_outline,
        ikonRenk: _yesil,
        baslik: 'Programın Güncel',
        metin: mevcut.isEmpty ? '' : 'Kurulu sürüm: $mevcut',
      );
    }
    return;
  }

  final yeni = (r['yeni'] ?? '').toString();
  if (sessiz && yeni.isNotEmpty && yeni == _atlananOku()) return;

  final yukle = await _yeniSurumPaneli(
      context, mevcut, yeni, (r['notlar'] ?? '').toString());
  if (!yukle) {
    // Yalnızca açılıştaki otomatik denetimde "Atla" o sürümü kalıcı olarak
    // atlar. Menüden elle denetlerken "Atla" "şimdi değil" demektir; eskiden
    // o sürüm bir daha açılışta hiç sorulmuyordu.
    if (sessiz) _atlananYaz(yeni);
    return;
  }
  if (!context.mounted) return;
  // Sunucu bu kurulumun kendini güncelleyip güncelleyemeyeceğini ve nasıl
  // (setup / appimage / dmg) güncelleyeceğini söyler (updater.kurulum_turu).
  await _guncelle(context, cagir, kaydet,
      kurulabilir: r['kurulabilir'] is bool ? r['kurulabilir'] as bool : suankiIsletim == Isletim.windows,
      tur: (r['kurulum_turu'] ?? '').toString().isEmpty
          ? 'setup'
          : r['kurulum_turu'].toString());
}

// ---------------------------------------------------------------------------
// Atlanan sürüm
// ---------------------------------------------------------------------------
File _atlananDosya() => File(p.join(veriKlasoru(), 'atlanan_surum.txt'));

String _atlananOku() {
  try {
    final f = _atlananDosya();
    return f.existsSync() ? f.readAsStringSync().trim() : '';
  } catch (_) {
    return '';
  }
}

void _atlananYaz(String surum) {
  try {
    final f = _atlananDosya();
    f.parent.createSync(recursive: true);
    f.writeAsStringSync(surum);
  } catch (_) {}
}

String _hataMetni(Object e) {
  try {
    final m = (e as dynamic).message;
    if (m is String && m.isNotEmpty) return m;
  } catch (_) {}
  return e.toString();
}

// ---------------------------------------------------------------------------
// Güncelleme akışı: indir + doğrula -> kaydet -> kurulumu başlat -> çık
// ---------------------------------------------------------------------------
Future<void> _guncelle(BuildContext context, BackendCagri cagir,
    Future<bool> Function()? kaydet,
    {required bool kurulabilir, required String tur}) async {
  if (!kurulabilir) {
    // Bu sistem için paket yok ya da bu kurulum (Linux .tar.gz) kendini
    // güncelleyemiyor: yeni sürüm elle kurulur.
    await _bilgiPaneli(
      context,
      ikon: Icons.system_update_alt,
      ikonRenk: Colors.blue,
      baslik: 'Yeni sürüm var',
      metin: 'Bu bilgisayarda TürKod kendini güncelleyemiyor. Yeni sürümü '
          "TürKod'un indirme sayfasından indirip kurabilirsin.",
    );
    return;
  }
  // Kurulum penceresi programın temasıyla açılır (context, async boşluklardan önce okunur).
  final renkler = GuncellemeRenkleri.temadan(Theme.of(context));
  final ilerleme = ValueNotifier<double?>(0);
  final metin = ValueNotifier<String>('Güncelleme indiriliyor...');

  // İlerleme penceresinin KENDİ rotası: kapatırken en üstteki rota değil bu
  // pencere kapatılır (araya başka bir pencere girerse yanlışı kapanıp
  // kapatılamayan dönen gösterge ekranda kalıyordu).
  Route<dynamic>? panelRotasi;
  unawaited(showDialog<void>(
    context: context,
    barrierDismissible: false,
    builder: (dc) {
      panelRotasi ??= ModalRoute.of(dc);
      return _IlerlemePaneli(ilerleme: ilerleme, metin: metin);
    },
  ));

  void kapat() {
    final r = panelRotasi;
    if (r != null && r.isActive && r.navigator != null) {
      r.navigator!.removeRoute(r);
    } else if (r == null && context.mounted) {
      Navigator.of(context, rootNavigator: true).pop();
    }
  }

  String? yol;
  String? hata;
  // İndirme hiç ilerlemezse (takılan bağlantı) pencere sonsuza kadar
  // kapanmaz kalıyordu; 90 sn ilerleme olmazsa vazgeçilir.
  const ilerlemesizSinir = Duration(seconds: 90);
  var sonIlerleme = DateTime.now();
  var sonIndirilen = -1.0;
  try {
    await cagir('guncelleme_indir_baslat');
    while (true) {
      await Future<void>.delayed(const Duration(milliseconds: 300));
      final d = await cagir('guncelleme_indir_durum');
      final durum = (d['durum'] ?? '').toString();
      final toplam = d['toplam'] is num ? (d['toplam'] as num).toDouble() : 0.0;
      final indirilen =
          d['indirilen'] is num ? (d['indirilen'] as num).toDouble() : 0.0;
      if (indirilen != sonIndirilen) {
        sonIndirilen = indirilen;
        sonIlerleme = DateTime.now();
      } else if (durum == 'indiriyor' &&
          DateTime.now().difference(sonIlerleme) > ilerlemesizSinir) {
        hata = 'İndirme ${ilerlemesizSinir.inSeconds} saniyedir ilerlemiyor; '
            'internet bağlantını kontrol edip yeniden dene.';
        break;
      }
      if (toplam > 0) {
        ilerleme.value = (indirilen / toplam).clamp(0.0, 1.0).toDouble();
        metin.value =
            'Güncelleme indiriliyor... %${(indirilen / toplam * 100).floor()}';
      } else {
        ilerleme.value = null;
      }
      if (durum == 'bitti') {
        yol = (d['yol'] ?? '').toString();
        break;
      }
      if (durum == 'hata') {
        hata = (d['hata'] ?? 'Bilinmeyen hata').toString();
        break;
      }
      if (durum == 'yok') {
        hata = 'İndirme başlatılamadı.';
        break;
      }
    }
  } catch (e) {
    hata = _hataMetni(e);
  }

  if (hata != null || yol == null || yol.isEmpty) {
    kapat();
    if (context.mounted) {
      await _bilgiPaneli(
        context,
        ikon: Icons.error_outline,
        ikonRenk: Colors.orange,
        baslik: 'Güncelleme indirilemedi',
        metin: hata ?? 'Kurulum dosyası bulunamadı.',
      );
    }
    return;
  }

  // Sekmeler ve kodlar KAYDEDİLMEDEN uygulama kapatılmaz.
  ilerleme.value = null;
  metin.value = 'Dosyaların kaydediliyor...';
  if (kaydet != null) {
    bool kaydedildi;
    try {
      kaydedildi = await kaydet();
    } catch (_) {
      kaydedildi = false;
    }
    if (!kaydedildi) {
      kapat();
      if (context.mounted) {
        await _bilgiPaneli(
          context,
          ikon: Icons.error_outline,
          ikonRenk: Colors.orange,
          baslik: 'Güncelleme iptal edildi',
          metin: 'Açık dosyaların kaydedilemedi. Dosyaları kaydedip '
              'güncellemeyi tekrar dene.',
        );
      }
      return;
    }
  }

  metin.value = 'Güncelleme başlatılıyor...';
  try {
    // Kayıt sırasında beklenirken %TEMP%'teki dosya değiştirilmiş olabilir:
    // çalıştırmadan hemen önce SHA-256 yeniden doğrulanır (ok:false -> hata).
    switch (tur) {
      case 'appimage':
        // Linux: yeni AppImage çalışanın yerine konur (sunucu SHA-256'yı yeniden
        // doğrular), sonra yeni sürüm başlatılıp bu süreç kapanır.
        final r = await cagir('guncelleme_uygula', {'yol': yol});
        final baslat = (r['baslat'] ?? '').toString();
        if (baslat.isEmpty) throw StateError('Yeni TürKod dosyası bulunamadı.');
        await Process.start(baslat, const [], mode: ProcessStartMode.detached);
      case 'dmg':
        // macOS: yeni .dmg açılır; kullanıcı TürKod'u Uygulamalar klasörüne
        // sürükler. Uygulama açıkken değiştirilemeyeceği için TürKod kapanır.
        await cagir('guncelleme_kurulum_dogrula', {'yol': yol});
        await Process.start('open', [yol], mode: ProcessStartMode.detached);
        metin.value = "Açılan pencerede TürKod'u Uygulamalar klasörüne sürükle.";
        await Future<void>.delayed(const Duration(seconds: 3));
      default:
        await cagir('guncelleme_kurulum_dogrula', {'yol': yol});
        await _kurulumuBaslat(yol, renkler, metin: metin);
    }
  } catch (e) {
    kapat();
    if (context.mounted) {
      await _bilgiPaneli(
        context,
        ikon: Icons.error_outline,
        ikonRenk: Colors.orange,
        baslik: 'Güncelleme başlatılamadı',
        metin: _hataMetni(e),
      );
    }
    return;
  }

  // Kurulum ayrı süreçte sürüyor; uygulama kapanır.
  exit(0);
}

/// Güncelleme penceresinin renkleri: programın o anki temasından alınır
/// (açık / koyu, vurgu rengi), böylece pencere TürKod'un bir parçası gibi görünür.
class GuncellemeRenkleri {
  final Color zemin, yazi, soluk, vurgu, iz;
  const GuncellemeRenkleri(
      {required this.zemin,
      required this.yazi,
      required this.soluk,
      required this.vurgu,
      required this.iz});

  factory GuncellemeRenkleri.temadan(ThemeData t) {
    final cs = t.colorScheme;
    return GuncellemeRenkleri(
      zemin: cs.surface,
      yazi: cs.onSurface,
      soluk: Color.alphaBlend(cs.onSurface.withValues(alpha: 0.62), cs.surface),
      vurgu: cs.primary,
      iz: Color.alphaBlend(cs.onSurface.withValues(alpha: 0.12), cs.surface),
    );
  }

  static String hex(Color c) {
    String b(double v) => (v * 255).round().clamp(0, 255).toRadixString(16).padLeft(2, '0');
    return '#${b(c.r)}${b(c.g)}${b(c.b)}';
  }
}

/// Kurulumu sessiz modda başlatır. Sıra önemlidir: önce temaya uygun ilerleme
/// penceresi açılır ve hazır olduğunu bildirir, SONRA kurulum başlar ve TürKod
/// kapanır. Eskiden önce program kapanıyor, pencere birkaç saniye sonra (bazen
/// hiç) geliyordu; kullanıcı ne olduğunu anlamadan bekliyordu.
///
/// Kurulum her aşamayı (eski sürüm kaldırılıyor, yeni sürüm kuruluyor %NN, son
/// ayarlar, bitti) /DURUM dosyasına yazar (turkod.iss); pencere gerçek durumu
/// gösterir. İş bitince pencere kurulum dosyasını siler.
///
/// Kurulumu bu (Flutter) süreç başlatır: backend'in alt süreci olsaydı, uygulama
/// kapanırken onunla birlikte sonlandırılırdı.
Future<void> _kurulumuBaslat(String kurulumYolu, GuncellemeRenkleri renk,
    {ValueNotifier<String>? metin}) async {
  final dizin = p.dirname(kurulumYolu);
  final durum = File(p.join(dizin, 'kurulum_durumu.txt'));
  final hazir = File(p.join(dizin, 'pencere_hazir.txt'));
  for (final f in [durum, hazir]) {
    try {
      if (f.existsSync()) f.deleteSync();
    } catch (_) {}
  }

  // Pencere açılamazsa (örn. PowerShell kısıtlıysa) güncelleme yine de sürer;
  // kalan kurulum dosyasını TürKod bir sonraki açılışta siler.
  try {
    final betik = File(p.join(dizin, 'turkod_guncelleme_penceresi.ps1'));
    // UTF-8 BOM: Windows PowerShell 5.1 Türkçe karakterleri doğru okusun.
    await betik.writeAsBytes([0xEF, 0xBB, 0xBF, ...utf8.encode(_arayuzBetigi)]);
    final sistem = Platform.environment['SystemRoot'] ?? r'C:\Windows';
    await Process.start(
      p.join(sistem, 'System32', 'WindowsPowerShell', 'v1.0', 'powershell.exe'),
      [
        '-NoProfile',
        '-ExecutionPolicy',
        'Bypass',
        '-WindowStyle',
        'Hidden',
        '-File',
        betik.path,
        '-KurulumYolu',
        kurulumYolu,
        '-DurumDosyasi',
        durum.path,
        '-HazirDosyasi',
        hazir.path,
        '-UygulamaExe',
        Platform.resolvedExecutable,
        '-Zemin',
        GuncellemeRenkleri.hex(renk.zemin),
        '-Yazi',
        GuncellemeRenkleri.hex(renk.yazi),
        '-Soluk',
        GuncellemeRenkleri.hex(renk.soluk),
        '-Vurgu',
        GuncellemeRenkleri.hex(renk.vurgu),
        '-Iz',
        GuncellemeRenkleri.hex(renk.iz),
      ],
      mode: ProcessStartMode.detached,
    );
    metin?.value = 'Güncelleme penceresi açılıyor...';
    // Pencere ekranda görünene dek (en çok 10 sn) TürKod açık kalır.
    final son = DateTime.now().add(const Duration(seconds: 10));
    while (!hazir.existsSync() && DateTime.now().isBefore(son)) {
      await Future<void>.delayed(const Duration(milliseconds: 100));
    }
  } catch (_) {}

  await Process.start(
    kurulumYolu,
    [
      '/VERYSILENT',
      '/SUPPRESSMSGBOXES',
      '/NORESTART',
      '/CLOSEAPPLICATIONS',
      '/DURUM=${durum.path}',
    ],
    mode: ProcessStartMode.detached,
  );
}

// ---------------------------------------------------------------------------
// Paneller
// ---------------------------------------------------------------------------
Widget _panel(
  BuildContext ctx, {
  required IconData ikon,
  required Color ikonRenk,
  required String baslik,
  String altMetin = '',
  String notlar = '',
  String ipucu = '',
  required List<Widget> butonlar,
}) {
  final tema = Theme.of(ctx);
  final soluk = tema.colorScheme.onSurface.withValues(alpha: 0.7);
  return Dialog(
    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
    child: ConstrainedBox(
      constraints: const BoxConstraints(maxWidth: 420),
      child: Padding(
        padding: const EdgeInsets.fromLTRB(24, 24, 24, 20),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(ikon, size: 42, color: ikonRenk),
            const SizedBox(height: 12),
            Text(
              baslik,
              textAlign: TextAlign.center,
              style: tema.textTheme.titleLarge
                  ?.copyWith(fontWeight: FontWeight.w700),
            ),
            if (altMetin.isNotEmpty) ...[
              const SizedBox(height: 6),
              Text(altMetin,
                  textAlign: TextAlign.center, style: tema.textTheme.bodyMedium),
            ],
            if (notlar.trim().isNotEmpty) ...[
              const SizedBox(height: 12),
              ConstrainedBox(
                constraints: const BoxConstraints(maxHeight: 140),
                child: SingleChildScrollView(
                  child: Text(notlar.trim(),
                      textAlign: TextAlign.center,
                      style: tema.textTheme.bodySmall),
                ),
              ),
            ],
            if (ipucu.isNotEmpty) ...[
              const SizedBox(height: 16),
              Text(ipucu,
                  textAlign: TextAlign.center,
                  style: tema.textTheme.bodySmall?.copyWith(color: soluk)),
            ],
            const SizedBox(height: 20),
            Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: butonlar,
            ),
          ],
        ),
      ),
    ),
  );
}

Future<bool> _yeniSurumPaneli(
    BuildContext context, String mevcut, String yeni, String notlar) async {
  final r = await showDialog<bool>(
    context: context,
    barrierDismissible: false,
    builder: (ctx) => _panel(
      ctx,
      ikon: Icons.system_update_alt,
      ikonRenk: Theme.of(ctx).colorScheme.primary,
      baslik: 'Yeni sürüm yayınlandı',
      altMetin: mevcut.isEmpty
          ? 'TürKod $yeni'
          : 'TürKod $yeni  (kurulu sürüm: $mevcut)',
      notlar: notlar,
      ipucu:
          'Sonrasında da "Güncelleştirmeler" menüsünden güncelleyebilirsin.',
      butonlar: [
        FilledButton(
          onPressed: () => Navigator.pop(ctx, true),
          child: const Text('Yükle'),
        ),
        const SizedBox(width: 12),
        OutlinedButton(
          onPressed: () => Navigator.pop(ctx, false),
          child: const Text('Atla'),
        ),
      ],
    ),
  );
  return r == true;
}

Future<void> _bilgiPaneli(
  BuildContext context, {
  required IconData ikon,
  required Color ikonRenk,
  required String baslik,
  String metin = '',
}) {
  return showDialog<void>(
    context: context,
    builder: (ctx) => _panel(
      ctx,
      ikon: ikon,
      ikonRenk: ikonRenk,
      baslik: baslik,
      altMetin: metin,
      butonlar: [
        FilledButton(
          onPressed: () => Navigator.pop(ctx),
          child: const Text('Tamam'),
        ),
      ],
    ),
  );
}

class _IlerlemePaneli extends StatelessWidget {
  final ValueNotifier<double?> ilerleme;
  final ValueNotifier<String> metin;
  const _IlerlemePaneli({required this.ilerleme, required this.metin});

  @override
  Widget build(BuildContext context) {
    final tema = Theme.of(context);
    return PopScope(
      canPop: false,
      child: Dialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 380),
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                ValueListenableBuilder<String>(
                  valueListenable: metin,
                  builder: (_, t, __) => Text(
                    t,
                    textAlign: TextAlign.center,
                    style: tema.textTheme.titleMedium,
                  ),
                ),
                const SizedBox(height: 18),
                ValueListenableBuilder<double?>(
                  valueListenable: ilerleme,
                  builder: (_, v, __) => ClipRRect(
                    borderRadius: BorderRadius.circular(4),
                    child: LinearProgressIndicator(
                      value: v,
                      minHeight: 10,
                      color: _yesil,
                      backgroundColor:
                          tema.colorScheme.onSurface.withValues(alpha: 0.12),
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// ---------------------------------------------------------------------------
// Güncelleme penceresi (TürKod kapandıktan sonra da ekranda kalır).
// Windows PowerShell + WinForms: ek kurulum gerektirmez. Renkler programın
// temasından gelir; kenarsız, yuvarlak köşeli, soldan sağa akan çubuklu.
// Kurulumun yazdığı durum dosyasını okur (turkod.iss DurumYaz):
//   kapat -> kaldir -> kur|NN -> ayar -> temizle -> bitti   (geri: yarıda kaldı)
// İş bitince kurulum dosyasını siler.
// ---------------------------------------------------------------------------
const String _arayuzBetigi = r'''
param(
    [Parameter(Mandatory = $true)][string]$KurulumYolu,
    [Parameter(Mandatory = $true)][string]$DurumDosyasi,
    [string]$HazirDosyasi = "",
    [string]$UygulamaExe = "",
    [string]$Zemin = "#FFFFFF",
    [string]$Yazi = "#1F2937",
    [string]$Soluk = "#6B7280",
    [string]$Vurgu = "#2ECC71",
    [string]$Iz = "#E5E7EB"
)

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
# Yüksek DPI ekranda bulanık görünmesin.
try {
    Add-Type -Namespace TurKod -Name Dpi -MemberDefinition '[DllImport("user32.dll")] public static extern bool SetProcessDPIAware();'
    [void][TurKod.Dpi]::SetProcessDPIAware()
} catch {}
[System.Windows.Forms.Application]::EnableVisualStyles()

function Renk([string]$h) {
    try { return [System.Drawing.ColorTranslator]::FromHtml($h) } catch { return [System.Drawing.Color]::Gray }
}
$cZemin = Renk $Zemin; $cYazi = Renk $Yazi; $cSoluk = Renk $Soluk
$cVurgu = Renk $Vurgu; $cIz = Renk $Iz

$form = New-Object System.Windows.Forms.Form
$g = $form.CreateGraphics(); $k = $g.DpiX / 96.0; $g.Dispose()
function O([double]$v) { return [int][Math]::Round($v * $k) }

$form.Text = "TürKod"
$form.FormBorderStyle = [System.Windows.Forms.FormBorderStyle]::None
$form.StartPosition = [System.Windows.Forms.FormStartPosition]::CenterScreen
$form.ClientSize = New-Object System.Drawing.Size((O 440), (O 150))
$form.BackColor = $cZemin
$form.TopMost = $true
$form.ShowInTaskbar = $true
try { $form.Icon = [System.Drawing.Icon]::ExtractAssociatedIcon($UygulamaExe) } catch {}

# Yuvarlak köşeler.
$r = O 14
$yol = New-Object System.Drawing.Drawing2D.GraphicsPath
$w = $form.ClientSize.Width; $h = $form.ClientSize.Height
$yol.AddArc(0, 0, $r * 2, $r * 2, 180, 90)
$yol.AddArc($w - $r * 2, 0, $r * 2, $r * 2, 270, 90)
$yol.AddArc($w - $r * 2, $h - $r * 2, $r * 2, $r * 2, 0, 90)
$yol.AddArc(0, $h - $r * 2, $r * 2, $r * 2, 90, 90)
$yol.CloseFigure()
$form.Region = New-Object System.Drawing.Region($yol)
$form.Add_Paint({
    param($s, $e)
    $e.Graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
    $kalem = New-Object System.Drawing.Pen($cIz, [single](O 2))
    $e.Graphics.DrawPath($kalem, $yol)
    $kalem.Dispose()
})

# Pencere sürüklenebilir (kenarlık yok).
$script:surukle = $null
$form.Add_MouseDown({ param($s, $e) $script:surukle = $e.Location })
$form.Add_MouseUp({ $script:surukle = $null })
$form.Add_MouseMove({
    param($s, $e)
    if ($script:surukle -ne $null) {
        $form.Left += $e.X - $script:surukle.X
        $form.Top += $e.Y - $script:surukle.Y
    }
})

$baslik = New-Object System.Windows.Forms.Label
$baslik.Text = "TürKod güncelleniyor"
$baslik.Font = New-Object System.Drawing.Font("Segoe UI Semibold", 13)
$baslik.ForeColor = $cYazi
$baslik.BackColor = [System.Drawing.Color]::Transparent
$baslik.SetBounds((O 28), (O 22), (O 384), (O 30))
$form.Controls.Add($baslik)

$asama = New-Object System.Windows.Forms.Label
$asama.Text = "TürKod kapatılıyor..."
$asama.Font = New-Object System.Drawing.Font("Segoe UI", 9.5)
$asama.ForeColor = $cSoluk
$asama.BackColor = [System.Drawing.Color]::Transparent
$asama.SetBounds((O 28), (O 56), (O 300), (O 22))
$form.Controls.Add($asama)

$yuzdeEtiket = New-Object System.Windows.Forms.Label
$yuzdeEtiket.Text = "%0"
$yuzdeEtiket.Font = New-Object System.Drawing.Font("Segoe UI Semibold", 9.5)
$yuzdeEtiket.ForeColor = $cYazi
$yuzdeEtiket.BackColor = [System.Drawing.Color]::Transparent
$yuzdeEtiket.TextAlign = [System.Drawing.ContentAlignment]::MiddleRight
$yuzdeEtiket.SetBounds((O 332), (O 56), (O 80), (O 22))
$form.Controls.Add($yuzdeEtiket)

$not = New-Object System.Windows.Forms.Label
$not.Text = "Lütfen bilgisayarı kapatma. Bitince TürKod kendiliğinden açılacak."
$not.Font = New-Object System.Drawing.Font("Segoe UI", 8.5)
$not.ForeColor = $cSoluk
$not.BackColor = [System.Drawing.Color]::Transparent
$not.SetBounds((O 28), (O 112), (O 384), (O 20))
$form.Controls.Add($not)

# Çubuk: dolu kısım vurgu renginde, içinde soldan sağa akan parlak bir şerit.
$cubuk = New-Object System.Windows.Forms.PictureBox
$cubuk.SetBounds((O 28), (O 86), (O 384), (O 10))
$cubuk.BackColor = $cZemin
$form.Controls.Add($cubuk)

$script:goster = 0.0     # ekrandaki yüzde (yumuşak)
$script:hedef = 2.0      # durumdan gelen yüzde
$script:akis = 0.0       # şeridin yeri
$script:durum = ""
$script:bitti = $false
$script:hata = $false
$script:bitisZamani = $null
$script:baslangic = Get-Date
$script:sonDegisim = Get-Date

function Yuvarlak($gr, $firca, [single]$x, [single]$y, [single]$en, [single]$boy) {
    if ($en -le 0) { return }
    $d = [Math]::Min($boy, $en)
    $p = New-Object System.Drawing.Drawing2D.GraphicsPath
    $p.AddArc($x, $y, $d, $boy, 90, 180)
    $p.AddArc($x + $en - $d, $y, $d, $boy, 270, 180)
    $p.CloseFigure()
    $gr.FillPath($firca, $p)
    $p.Dispose()
}

$cubuk.Add_Paint({
    param($s, $e)
    $gr = $e.Graphics
    $gr.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
    $en = [single]$cubuk.Width; $boy = [single]$cubuk.Height
    $f1 = New-Object System.Drawing.SolidBrush($cIz)
    Yuvarlak $gr $f1 0 0 $en $boy
    $f1.Dispose()
    $dolu = [single]($en * $script:goster / 100.0)
    if ($dolu -lt $boy) { $dolu = [Math]::Min($boy, $en) }
    $f2 = New-Object System.Drawing.SolidBrush($cVurgu)
    Yuvarlak $gr $f2 0 0 $dolu $boy
    $f2.Dispose()
    # Akan parlaklık (yalnızca dolu kısmın içinde).
    $genislik = [single](O 90)
    $x = [single](($script:akis % ($dolu + $genislik)) - $genislik)
    $acik = [System.Drawing.Color]::FromArgb(110, 255, 255, 255)
    $saydam = [System.Drawing.Color]::FromArgb(0, 255, 255, 255)
    $dik = New-Object System.Drawing.RectangleF($x, 0, $genislik, $boy)
    $parlak = New-Object System.Drawing.Drawing2D.LinearGradientBrush($dik, $saydam, $acik, [single]0)
    $bl = New-Object System.Drawing.Drawing2D.Blend
    $bl.Factors = [single[]](0, 1, 0)
    $bl.Positions = [single[]](0, 0.5, 1)
    $parlak.Blend = $bl
    $gr.SetClip((New-Object System.Drawing.RectangleF(0, 0, $dolu, $boy)))
    $gr.FillRectangle($parlak, $dik)
    $gr.ResetClip()
    $parlak.Dispose()
})

function DurumOku {
    try {
        if (Test-Path -LiteralPath $DurumDosyasi) {
            return ([System.IO.File]::ReadAllText($DurumDosyasi)).Trim()
        }
    } catch {}
    return ""
}

# Kurulum dosyası hâlâ çalışıyor mu? (Çalışan programın dosyası kilitlidir.)
function KurulumCalisiyor {
    if (-not (Test-Path -LiteralPath $KurulumYolu)) { return $false }
    try {
        $fs = [System.IO.File]::Open($KurulumYolu, 'Open', 'ReadWrite', 'None')
        $fs.Close()
        return $false
    } catch { return $true }
}

function Bitir([bool]$basarili) {
    $script:bitti = $true
    $script:hata = -not $basarili
    $script:bitisZamani = Get-Date
    if ($basarili) {
        $script:hedef = 100.0
        $asama.Text = "Güncelleme tamamlandı"
        $not.Text = "TürKod açılıyor..."
    }
}

$zaman = New-Object System.Windows.Forms.Timer
$zaman.Interval = 30
$zaman.Add_Tick({
    $simdi = Get-Date
    if (-not $script:bitti) {
        $d = DurumOku
        if ($d -ne $script:durum) { $script:durum = $d; $script:sonDegisim = $simdi }
        $parca = $d.Split('|')
        switch ($parca[0]) {
            "kapat"   { $asama.Text = "TürKod kapatılıyor..."; $script:hedef = 5 }
            "kaldir"  { $asama.Text = "Eski sürüm kaldırılıyor..."; $script:hedef = 10 }
            "kur"     {
                $n = 0; [void][int]::TryParse($parca[1], [ref]$n)
                $asama.Text = "Yeni sürüm kuruluyor..."
                $script:hedef = 12 + $n * 0.78
            }
            "ayar"    { $asama.Text = "Son ayarlar yapılıyor..."; $script:hedef = 93 }
            "temizle" { $asama.Text = "Eski sürümün dosyaları siliniyor..."; $script:hedef = 97 }
            "bitti"   { Bitir $true }
            "geri"    { Bitir $false }
        }
        $gecen = ($simdi - $script:baslangic).TotalSeconds
        # Kurulum hiç durum yazmadan kapandıysa (başlayamadı / çöktü) ya da
        # 20 dakikayı aştıysa iş biter.
        if (-not $script:bitti -and $gecen -gt 12 -and -not (KurulumCalisiyor)) {
            if ($script:durum -eq "") { Bitir $false } else { Start-Sleep -Milliseconds 300; if ((DurumOku) -eq "bitti") { Bitir $true } else { Bitir $false } }
        }
        if (-not $script:bitti -and $gecen -gt 1200) { Bitir $false }
    }
    $script:goster = $script:goster + ($script:hedef - $script:goster) * 0.08
    $yuzdeEtiket.Text = "%" + [int][Math]::Floor($script:goster + 0.3)
    $script:akis += (O 6)
    $cubuk.Invalidate()
    if ($script:bitti -and (($simdi - $script:bitisZamani).TotalSeconds -gt 1.6 -or $script:hata)) {
        $zaman.Stop()
        $form.Close()
    }
})

$form.Add_Shown({
    $form.Activate()
    if ($HazirDosyasi) { try { Set-Content -LiteralPath $HazirDosyasi -Value "1" } catch {} }
    $zaman.Start()
})

[void]$form.ShowDialog()

if ($script:hata) {
    [void][System.Windows.Forms.MessageBox]::Show(
        "Güncelleme tamamlanamadı. TürKod'un önceki sürümü yerinde duruyor ve yeniden açılıyor.`nDaha sonra Güncelleştirmeler menüsünden yeniden deneyebilirsin.",
        "TürKod",
        [System.Windows.Forms.MessageBoxButtons]::OK,
        [System.Windows.Forms.MessageBoxIcon]::Warning)
    if ($UygulamaExe -and (Test-Path -LiteralPath $UygulamaExe)) {
        Start-Process -FilePath $UygulamaExe
    }
}

# Kurulum dosyası artık gereksiz: kurulum programı kapanınca silinir (en çok 2 dk).
$son = (Get-Date).AddMinutes(2)
while ((Get-Date) -lt $son) {
    try {
        if (Test-Path -LiteralPath $KurulumYolu) { Remove-Item -LiteralPath $KurulumYolu -Force -ErrorAction Stop }
        break
    } catch { Start-Sleep -Milliseconds 500 }
}
foreach ($f in @($DurumDosyasi, $HazirDosyasi)) {
    if ($f) { try { Remove-Item -LiteralPath $f -Force -ErrorAction SilentlyContinue } catch {} }
}
# Betiğin kendisi de silinir.
try { Remove-Item -LiteralPath $PSCommandPath -Force -ErrorAction SilentlyContinue } catch {}
''';
