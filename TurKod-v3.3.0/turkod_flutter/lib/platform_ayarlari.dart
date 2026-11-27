/// İşletim sistemine göre değişen her şey burada (Windows, Linux, macOS).
///
/// Python tarafındaki turkod_ide/platform_katmani'nın Flutter karşılığı. Her
/// işlev isteğe bağlı bir [Isletim] alır; verilmezse çalışılan sistem kullanılır
/// (testlerde Linux/macOS yolları Windows'ta da denenebilir).
library;

import 'dart:io';

import 'package:flutter/services.dart' show HardwareKeyboard, LogicalKeyboardKey;
import 'package:flutter/widgets.dart' show CharacterActivator, SingleActivator;
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
/// "Kabuk penceresi açılamadı" iletisi; sunucu nedenini bildirdiyse (terminal
/// programı yok, macOS'ta Otomasyon izni verilmedi ...) onu da ekler.
String kabukPenceresiHataMetni(Object? neden) {
  final n = (neden ?? '').toString().trim();
  return n.isEmpty ? 'Kabuk penceresi açılamadı.' : 'Kabuk penceresi açılamadı. $n';
}

/// Sunucunun portunu yazdığı dosya (turkod_ide/paths.py port_dosyasi_yolu ile
/// aynı): Windows'ta %TEMP%\turkod_backend_port, Linux/macOS'ta
/// <veri klasörü>/backend_port.
String portDosyasiYolu({Isletim? isletim, Map<String, String>? ortam, String? gecici}) {
  final i = isletim ?? suankiIsletim;
  if (i == Isletim.windows) {
    return p.windows.join(gecici ?? Directory.systemTemp.path, 'turkod_backend_port');
  }
  return p.posix.join(veriKlasoru(isletim: i, ortam: ortam), 'backend_port');
}

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

/// Açılış hata ekranında gösterilen günlük dosyası yeri. Linux'ta
/// XDG_DATA_HOME verilmişse orası gösterilir ([veriKlasoru] ile aynı kural).
String sunucuGunluguAciklamasi([Isletim? isletim, Map<String, String>? ortam]) {
  switch (isletim ?? suankiIsletim) {
    case Isletim.windows:
      return r'%LOCALAPPDATA%\TurKod\backend.log';
    case Isletim.macos:
      return '~/Library/Application Support/TurKod/backend.log';
    case Isletim.linux:
      final xdg = (ortam ?? Platform.environment)['XDG_DATA_HOME'];
      if (xdg != null && p.posix.isAbsolute(xdg)) {
        return p.posix.join(xdg, 'TurKod', 'backend.log');
      }
      return '~/.local/share/TurKod/backend.log';
  }
}

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

/// Ekran metinlerinde sabit yazılmış kısayolları sisteme uydurur: macOS'ta
/// "Ctrl+Shift+P" -> "Cmd+Shift+P" (cümle içinde de).
String kisayolluMetin(String metin, [Isletim? isletim]) =>
    (isletim ?? suankiIsletim) == Isletim.macos ? metin.replaceAll('Ctrl+', 'Cmd+') : metin;

/// Kısayolların ana değiştirici tuşunun adı: macOS'ta "Cmd", diğerlerinde "Ctrl".
String kisayolTusuAdi([Isletim? isletim]) =>
    (isletim ?? suankiIsletim) == Isletim.macos ? 'Cmd' : 'Ctrl';

/// Kısayolların ana değiştirici tuşu (macOS'ta Cmd, diğerlerinde Ctrl) basılı mı?
/// Editörün kendi tuşları (Ctrl+Enter, Ctrl+tekerlek ...) bununla denetlenir.
bool kisayolTusuBasili([Isletim? isletim]) {
  final k = HardwareKeyboard.instance;
  return (isletim ?? suankiIsletim) == Isletim.macos ? k.isMetaPressed : k.isControlPressed;
}

/// Hayalet öneriyi kelime kelime kabul eden tuş (→ ile birlikte) basılı mı?
/// Windows/Linux'ta Ctrl; macOS'ta Ctrl+→ masaüstünü değiştirdiğinden Option.
bool kelimeKabulTusuBasili([Isletim? isletim]) {
  final k = HardwareKeyboard.instance;
  return (isletim ?? suankiIsletim) == Isletim.macos
      ? k.isAltPressed && !k.isMetaPressed && !k.isControlPressed
      : k.isControlPressed;
}

/// [kelimeKabulTusuBasili] kısayolunun ekrandaki adı.
String kelimeKabulKisayolMetni([Isletim? isletim]) =>
    (isletim ?? suankiIsletim) == Isletim.macos ? 'Option+→' : 'Ctrl+→';

/// Karakterle tanımlanan kısayol (ör. Türkçe klavyede Shift+7 ile yazılan "/"):
/// macOS'ta Ctrl yerine Cmd.
CharacterActivator platformKarakterKisayolu(String karakter,
    {bool alt = false, Isletim? isletim}) {
  final mac = (isletim ?? suankiIsletim) == Isletim.macos;
  return CharacterActivator(karakter, control: !mac, meta: mac, alt: alt);
}

/// Sisteme göre varsayılanı farklı olan kısayollar (eylem kimliğine göre);
/// null ise [platformKisayolu] ile çevrilen varsayılan geçerlidir.
///  - macOS'ta Yinele, editörün kendisinde (re_editor) Cmd+Shift+Z'dir.
///  - macOS'ta Cmd+H uygulamayı gizler (TürKod menüsündeki "Gizle"); Bul /
///    Değiştir orada Cmd+Option+F olur (Xcode ve VS Code'daki gibi).
({SingleActivator? activator, String shortcut})? sistemKisayolIstisnasi(String eylemId,
    [Isletim? isletim]) {
  if ((isletim ?? suankiIsletim) != Isletim.macos) return null;
  return switch (eylemId) {
    'edit.redo' => (activator: null, shortcut: 'Cmd+Shift+Z'),
    'edit.find_replace' => (
        activator: const SingleActivator(LogicalKeyboardKey.keyF, meta: true, alt: true),
        shortcut: 'Cmd+Alt+F',
      ),
    _ => null,
  };
}

/// Ekranın üstündeki sistem menü çubuğu (PlatformMenuBar) yalnızca macOS'ta var.
bool sistemMenuCubuguVar([Isletim? isletim]) =>
    (isletim ?? suankiIsletim) == Isletim.macos;

// ---------------------------------------------------------------------------
// Çöp kutusu (Gezgin'de silme)
// ---------------------------------------------------------------------------

/// Çöp kutusunun adı yönelme ekiyle: "Geri Dönüşüm Kutusu'na" (Windows),
/// "Çöp Kutusu'na" (macOS), "Çöp'e" (Linux).
String copKutusunaMetni([Isletim? isletim]) => switch (isletim ?? suankiIsletim) {
      Isletim.windows => "Geri Dönüşüm Kutusu'na",
      Isletim.macos => "Çöp Kutusu'na",
      Isletim.linux => "Çöp'e",
    };

// ---------------------------------------------------------------------------
// Sisteme göre adı ya da çıktısı değişen özellikler
// ---------------------------------------------------------------------------

/// "EXE'ye Dönüştür" her sistemde var; ürettiği dosya o sistemin programıdır:
/// Windows'ta .exe, Linux'ta uzantısız program dosyası, macOS'ta .app.
bool exeDonusturmeVar([Isletim? isletim]) => true;

/// Menüdeki adı: Windows'ta "EXE'ye Dönüştür…", diğerlerinde "Uygulamaya Dönüştür…".
String exeDonusturEtiketi([Isletim? isletim]) =>
    (isletim ?? suankiIsletim) == Isletim.windows ? "EXE'ye Dönüştür…" : 'Uygulamaya Dönüştür…';

/// "EXE'nin Kaynak Kodunu Aç…" komutunun sisteme göre adı.
String exeKaynakEtiketi([Isletim? isletim]) => (isletim ?? suankiIsletim) == Isletim.windows
    ? "EXE'nin Kaynak Kodunu Aç…"
    : 'Uygulamanın Kaynak Kodunu Aç…';

/// Metinlerde üretilen dosyanın adı: "EXE" ya da "uygulama".
String programDosyasiAdi([Isletim? isletim]) =>
    (isletim ?? suankiIsletim) == Isletim.windows ? 'EXE' : 'uygulama';

/// Üretilen dosyanın uzantısı (exe_donusturucu.cikti_yollari ile aynı):
/// Windows .exe; macOS'ta pencereli program .app, konsol kipinde uzantısız;
/// Linux'ta uzantısız.
String programUzantisi(String pencere, [Isletim? isletim]) =>
    switch (isletim ?? suankiIsletim) {
      Isletim.windows => '.exe',
      Isletim.macos => pencere == 'konsol' ? '' : '.app',
      Isletim.linux => '',
    };

// ---------------------------------------------------------------------------
// Gömülü tarayıcı
// ---------------------------------------------------------------------------

/// IDE içindeki tarayıcı: Windows'ta WebView2, macOS'ta WKWebView. Linux'ta
/// gömülebilen bir bileşen yok; sayfalar bilgisayarın kendi tarayıcısında açılır.
bool gomuluTarayiciVar([Isletim? isletim]) =>
    (isletim ?? suankiIsletim) != Isletim.linux;

// ---------------------------------------------------------------------------
// Dışarıda açma, dosya penceresi, yollar
// ---------------------------------------------------------------------------

/// Bağlantıyı / dosyayı sistemin varsayılan uygulamasıyla açan komut:
/// Windows'ta rundll32 (cmd "start" yerine: & ve boşluk içeren yollar
/// bölünmez), macOS'ta open, Linux'ta xdg-open.
({String komut, List<String> argumanlar}) disaridaAcKomutu(String hedef,
        [Isletim? isletim]) =>
    switch (isletim ?? suankiIsletim) {
      Isletim.windows => (
          komut: 'rundll32',
          argumanlar: ['url.dll,FileProtocolHandler', hedef],
        ),
      Isletim.macos => (komut: 'open', argumanlar: [hedef]),
      Isletim.linux => (komut: 'xdg-open', argumanlar: [hedef]),
    };

/// Dosya / klasör seçme penceresi açılamadığında gösterilen ileti. Linux'ta
/// pencereyi zenity (ya da kdialog / qarma) çizer; kurulu değilse açılmaz.
String dosyaPenceresiHataMetni([Isletim? isletim]) =>
    (isletim ?? suankiIsletim) == Isletim.linux
        ? "Dosya penceresi açılamadı. Linux'ta zenity kurulu olmalı: sudo apt install zenity"
        : 'Dosya penceresi açılamadı.';

/// Dosya seçme penceresini (file_picker) açar. Açılamazsa (Linux'ta zenity
/// yoksa istisna atar) [hataBildir] Türkçe bir iletiyle çağrılır ve null döner.
Future<T?> dosyaSecicisiyle<T>(
    Future<T?> Function() sec, void Function(String ileti) hataBildir,
    [Isletim? isletim]) async {
  try {
    return await sec();
  } catch (_) {
    hataBildir(dosyaPenceresiHataMetni(isletim));
    return null;
  }
}

/// İki dosya yolu aynı dosya mı? Windows ve macOS'ta (varsayılan disk biçimi)
/// büyük/küçük harf farkı aynı dosyadır; Linux'ta farklı dosyalardır.
bool yollarAyniMi(String a, String b, [Isletim? isletim]) =>
    switch (isletim ?? suankiIsletim) {
      Isletim.windows => p.windows.equals(a, b),
      Isletim.macos => p.posix.equals(a.toLowerCase(), b.toLowerCase()),
      Isletim.linux => p.posix.equals(a, b),
    };

/// Komut satırı için tırnaklama (EXE'ye Dönüştür komutu; Python'daki
/// exe_donusturucu._tirnak ile aynı). Windows'ta tırnak içindeki sondaki "\"
/// ikilenir: `"C:\Oyun Klasörü\"` biçimindeki \" kapanış tırnağını kaçırıyordu.
/// Linux/macOS'ta (sh) çift tırnak içinde $ ` " \ kaçırılır; komut TürKod
/// Kabuğu'na da yazılabildiğinden (yalnızca çift tırnağı tanır) tek tırnak
/// kullanılmaz.
String komutSatiriTirnagi(String s, [Isletim? isletim]) {
  if ((isletim ?? suankiIsletim) == Isletim.windows) {
    if (s.isNotEmpty && !RegExp(r'[\s&|<>^]').hasMatch(s)) return s;
    final sondaki = s.length - s.replaceFirst(RegExp(r'\\+$'), '').length;
    return '"$s${'\\' * sondaki}"';
  }
  if (s.isNotEmpty && !RegExp(r'[^\p{L}\p{N}_@%+=:,./-]', unicode: true).hasMatch(s)) {
    return s;
  }
  return '"${s.replaceAllMapped(RegExp(r'["$`\\]'), (m) => '\\${m[0]}')}"';
}

// ---------------------------------------------------------------------------
// Ayarlardaki sisteme özgü açıklamalar
// ---------------------------------------------------------------------------

/// Ayarlar → ".trpy dosyalarını TürKod ile ilişkilendir" seçeneğinin açıklaması.
String dosyaIliskisiAciklamasi([Isletim? isletim]) => switch (isletim ?? suankiIsletim) {
      Isletim.windows => 'Çift tıklayınca çalıştır, sağ tıkta "Editör ile aç".',
      Isletim.macos => "Çift tıklayınca TürKod'da açılır.",
      Isletim.linux => 'Çift tıklayınca TürKod ile çalışır.',
    };

/// Kodi masaüstü görüntüsünde "yalnızca TürKod penceresi" kipi: Windows'ta
/// pencereyi arka uç bulur; Linux/macOS'ta arayüz kendi görüntüsünü gönderir.
bool pencereGoruntusuArayuzden([Isletim? isletim]) =>
    (isletim ?? suankiIsletim) != Isletim.windows;

// ---------------------------------------------------------------------------
// Yerel AI modelleri: diskler
// ---------------------------------------------------------------------------

/// Depolama listesindeki diskin adı: Windows'ta "D:", diğerlerinde diskin
/// bağlandığı klasör (ör. "/media/ali/Disk"), yoksa harf.
String surucuEtiketi(String harf, String? kok, [Isletim? isletim]) {
  if ((isletim ?? suankiIsletim) == Isletim.windows) return '$harf:';
  return (kok == null || kok.isEmpty) ? harf : kok;
}

/// Diskte modellere bırakılmayan pay: Windows'ta "Windows payı", diğerlerinde "sistem payı".
String sistemPayiAdi([Isletim? isletim]) =>
    (isletim ?? suankiIsletim) == Isletim.windows ? 'Windows' : 'sistem';

/// Model sığmadığında öneri: "başka bir sürücü seç" (Windows) /
/// "başka bir disk ya da klasör seç" (Linux, macOS).
String baskaSurucuOnerisi([Isletim? isletim]) =>
    (isletim ?? suankiIsletim) == Isletim.windows
        ? 'başka bir sürücü seç'
        : 'başka bir disk ya da klasör seç';

/// Daha çok yeri olan diske geçme düğmesi: "D: sürücüsüne geç" (Windows),
/// "Daha çok yeri olan diske geç" (Linux, macOS).
String onerilenSurucuyeGecMetni(String dizin, [Isletim? isletim]) =>
    (isletim ?? suankiIsletim) == Isletim.windows && dizin.isNotEmpty
        ? '${dizin.substring(0, 1)}: sürücüsüne geç'
        : 'Daha çok yeri olan diske geç';
