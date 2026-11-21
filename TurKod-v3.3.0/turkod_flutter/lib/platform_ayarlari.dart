/// İşletim sistemine göre değişen her şey burada (Windows, Linux, macOS).
///
/// Python tarafındaki turkod_ide/platform_katmani'nın Flutter karşılığı. Her
/// işlev isteğe bağlı bir [Isletim] alır; verilmezse çalışılan sistem kullanılır
/// (testlerde Linux/macOS yolları Windows'ta da denenebilir).
library;

import 'dart:io';

import 'package:flutter/widgets.dart' show SingleActivator;
import 'package:path/path.dart' as p;

enum Isletim { windows, linux, macos }

/// Çalışılan işletim sistemi (Linux dışındaki POSIX sistemler de linux sayılır).
Isletim get suankiIsletim => Platform.isWindows
    ? Isletim.windows
    : (Platform.isMacOS ? Isletim.macos : Isletim.linux);

// ---------------------------------------------------------------------------
// Kod yazı tipi
// ---------------------------------------------------------------------------

/// Sistemde hazır bulunan eş aralıklı (monospace) yazı tipi: Windows'ta
/// Consolas, macOS'ta Menlo, Linux'ta DejaVu Sans Mono.
String kodYaziTipi([Isletim? isletim]) => switch (isletim ?? suankiIsletim) {
      Isletim.windows => 'Consolas',
      Isletim.macos => 'Menlo',
      Isletim.linux => 'DejaVu Sans Mono',
    };

/// Seçilen yazı tipi bulunamazsa sırayla denenenler (her sistemden biri).
const List<String> kodYaziTipiYedekleri = [
  'Consolas',
  'Menlo',
  'DejaVu Sans Mono',
  'Liberation Mono',
  'Noto Sans Mono',
  'Courier New',
  'monospace',
];

// ---------------------------------------------------------------------------
// Paketli sunucu (turkod_backend)
// ---------------------------------------------------------------------------

/// Paketli sunucunun yolu, arayüzün çalıştırılabilir dosyasına göre:
///  - Windows: <uygulama>\backend\turkod_backend.exe
///  - Linux  : <uygulama>/backend/turkod_backend
///  - macOS  : TurKod.app/Contents/Resources/backend/turkod_backend
///             (arayüz TurKod.app/Contents/MacOS/ içindedir)
String paketliSunucuYolu(String arayuzDosyasi, [Isletim? isletim]) {
  final i = isletim ?? suankiIsletim;
  final yol = i == Isletim.windows ? p.windows : p.posix;
  final klasor = yol.dirname(arayuzDosyasi);
  return switch (i) {
    Isletim.windows => yol.join(klasor, 'backend', 'turkod_backend.exe'),
    Isletim.linux => yol.join(klasor, 'backend', 'turkod_backend'),
    Isletim.macos =>
      yol.join(yol.dirname(klasor), 'Resources', 'backend', 'turkod_backend'),
  };
}

/// Geliştirici kipinde sunucuyu çalıştıran Python komutu.
String pythonKomutu([Isletim? isletim]) =>
    (isletim ?? suankiIsletim) == Isletim.windows ? 'python' : 'python3';

// ---------------------------------------------------------------------------
// Veri klasörü (Python: platform_katmani.veri_klasoru ile aynı)
// ---------------------------------------------------------------------------

/// TürKod'un kullanıcı veri klasörü; ortam değişkenleri verilmezse süreçten okunur.
String veriKlasoru({Isletim? isletim, Map<String, String>? ortam}) {
  final i = isletim ?? suankiIsletim;
  final env = ortam ?? Platform.environment;
  final ev = env['HOME'] ?? env['USERPROFILE'] ?? Directory.systemTemp.path;
  switch (i) {
    case Isletim.windows:
      final taban = env['LOCALAPPDATA'];
      return p.windows.join(
          (taban == null || taban.isEmpty) ? Directory.systemTemp.path : taban, 'TurKod');
    case Isletim.macos:
      return p.posix.join(ev, 'Library', 'Application Support', 'TurKod');
    case Isletim.linux:
      final xdg = env['XDG_DATA_HOME'];
      final taban = (xdg != null && p.posix.isAbsolute(xdg))
          ? xdg
          : p.posix.join(ev, '.local', 'share');
      return p.posix.join(taban, 'TurKod');
  }
}

/// Açılış hata ekranında gösterilen günlük dosyası yeri.
String sunucuGunluguAciklamasi([Isletim? isletim]) =>
    switch (isletim ?? suankiIsletim) {
      Isletim.windows => r'%LOCALAPPDATA%\TurKod\backend.log',
      Isletim.macos => '~/Library/Application Support/TurKod/backend.log',
      Isletim.linux => '~/.local/share/TurKod/backend.log',
    };

// ---------------------------------------------------------------------------
// Süreç kapatma
// ---------------------------------------------------------------------------

/// Süreci alt süreçleriyle birlikte kapatır. Windows'ta taskkill /F /T; Linux
/// ve macOS'ta sunucu kendi alt süreçlerini kapatır (--parent-pid izleyicisi),
/// burada yalnızca SIGTERM gönderilir.
void sureciAgaclaKapat(Process surec) {
  if (Platform.isWindows) {
    Process.run('taskkill', ['/F', '/T', '/PID', '${surec.pid}']);
  } else {
    surec.kill(ProcessSignal.sigterm);
  }
}

// ---------------------------------------------------------------------------
// Kısayollar: macOS'ta Ctrl yerine Cmd (⌘)
// ---------------------------------------------------------------------------

/// Kısayol tanımları Ctrl ile yazılır; macOS'ta Ctrl, Cmd'ye çevrilir.
SingleActivator platformKisayolu(SingleActivator a, [Isletim? isletim]) {
  if ((isletim ?? suankiIsletim) != Isletim.macos || !a.control) return a;
  return SingleActivator(a.trigger,
      control: false,
      meta: true,
      shift: a.shift,
      alt: a.alt,
      numLock: a.numLock,
      includeRepeats: a.includeRepeats);
}

/// Kısayol metni: macOS'ta "Ctrl+S" -> "Cmd+S".
String platformKisayolMetni(String metin, [Isletim? isletim]) {
  if ((isletim ?? suankiIsletim) != Isletim.macos || metin.isEmpty) return metin;
  return metin.split('+').map((p) => p.trim() == 'Ctrl' ? 'Cmd' : p).join('+');
}

/// Meta (Windows/⌘) tuşunun kısayol metnindeki adı.
String metaTusAdi([Isletim? isletim]) =>
    (isletim ?? suankiIsletim) == Isletim.macos ? 'Cmd' : 'Win';

// ---------------------------------------------------------------------------
// Gömülü tarayıcı
// ---------------------------------------------------------------------------

/// IDE içindeki tarayıcı (WebView2) yalnızca Windows'ta var; diğer sistemlerde
/// sayfalar bilgisayarın kendi tarayıcısında açılır.
bool gomuluTarayiciVar([Isletim? isletim]) =>
    (isletim ?? suankiIsletim) == Isletim.windows;
