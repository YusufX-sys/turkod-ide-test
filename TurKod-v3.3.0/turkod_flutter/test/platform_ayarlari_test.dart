// Platform ayarları: Windows, Linux ve macOS yolları, her sistemde taklit
// edilerek (Isletim parametresiyle) denenir.
import 'package:flutter/services.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:turkod_ide/platform_ayarlari.dart';

void main() {
  group('Kod yazı tipi', () {
    test('her sistemde hazır bulunan eş aralıklı yazı tipi', () {
      expect(kodYaziTipi(Isletim.windows), 'Consolas');
      expect(kodYaziTipi(Isletim.macos), 'Menlo');
      expect(kodYaziTipi(Isletim.linux), 'DejaVu Sans Mono');
    });

    test('yedekler her sistemin yazı tipini içerir', () {
      for (final i in Isletim.values) {
        expect(kodYaziTipiYedekleri, contains(kodYaziTipi(i)));
      }
      expect(kodYaziTipiYedekleri.last, 'monospace');
    });
  });

  group('Paketli sunucu yolu', () {
    test('Windows: backend\\turkod_backend.exe', () {
      expect(paketliSunucuYolu(r'C:\Program Files\TurKod\turkod_flutter.exe', Isletim.windows),
          r'C:\Program Files\TurKod\backend\turkod_backend.exe');
    });

    test('Linux: backend/turkod_backend (.exe yok)', () {
      expect(paketliSunucuYolu('/opt/turkod/turkod_flutter', Isletim.linux),
          '/opt/turkod/backend/turkod_backend');
    });

    test('macOS: uygulama paketinin Resources klasörü', () {
      expect(
          paketliSunucuYolu('/Applications/TurKod.app/Contents/MacOS/TurKod', Isletim.macos),
          '/Applications/TurKod.app/Contents/Resources/backend/turkod_backend');
    });

    test('Python komutu', () {
      expect(pythonKomutu(Isletim.windows), 'python');
      expect(pythonKomutu(Isletim.linux), 'python3');
      expect(pythonKomutu(Isletim.macos), 'python3');
    });
  });

  test('Port dosyası (Python paths.port_dosyasi_yolu ile aynı)', () {
    expect(portDosyasiYolu(isletim: Isletim.windows, gecici: r'C:\Temp'),
        r'C:\Temp\turkod_backend_port');
    expect(portDosyasiYolu(isletim: Isletim.linux, ortam: {'HOME': '/home/a'}),
        '/home/a/.local/share/TurKod/backend_port');
    expect(portDosyasiYolu(isletim: Isletim.macos, ortam: {'HOME': '/Users/a'}),
        '/Users/a/Library/Application Support/TurKod/backend_port');
  });

  group('Veri klasörü (Python platform_katmani ile aynı)', () {
    test('Windows: LOCALAPPDATA', () {
      expect(
          veriKlasoru(isletim: Isletim.windows, ortam: {'LOCALAPPDATA': r'C:\Users\a\AppData\Local'}),
          r'C:\Users\a\AppData\Local\TurKod');
    });

    test('Linux: XDG_DATA_HOME, yoksa ~/.local/share', () {
      expect(veriKlasoru(isletim: Isletim.linux, ortam: {'HOME': '/home/a', 'XDG_DATA_HOME': '/veri'}),
          '/veri/TurKod');
      expect(veriKlasoru(isletim: Isletim.linux, ortam: {'HOME': '/home/a'}),
          '/home/a/.local/share/TurKod');
      expect(veriKlasoru(isletim: Isletim.linux, ortam: {'HOME': '/home/a', 'XDG_DATA_HOME': 'goreli'}),
          '/home/a/.local/share/TurKod');
    });

    test('macOS: Library/Application Support', () {
      expect(veriKlasoru(isletim: Isletim.macos, ortam: {'HOME': '/Users/a'}),
          '/Users/a/Library/Application Support/TurKod');
    });

    test('günlük dosyası açıklaması', () {
      expect(sunucuGunluguAciklamasi(Isletim.windows), r'%LOCALAPPDATA%\TurKod\backend.log');
      expect(sunucuGunluguAciklamasi(Isletim.linux), contains('.local/share/TurKod'));
      expect(sunucuGunluguAciklamasi(Isletim.macos), contains('Application Support'));
    });
  });

  group('Kısayollar', () {
    const ctrlS = SingleActivator(LogicalKeyboardKey.keyS, control: true);
    const ctrlShiftF = SingleActivator(LogicalKeyboardKey.keyF, control: true, shift: true);
    const f5 = SingleActivator(LogicalKeyboardKey.f5);

    test('Windows ve Linux: değişmez', () {
      for (final i in [Isletim.windows, Isletim.linux]) {
        expect(identical(platformKisayolu(ctrlS, i), ctrlS), isTrue);
        expect(platformKisayolMetni('Ctrl+S', i), 'Ctrl+S');
      }
    });

    test('macOS: Ctrl yerine Cmd', () {
      final a = platformKisayolu(ctrlShiftF, Isletim.macos);
      expect(a.meta, isTrue);
      expect(a.control, isFalse);
      expect(a.shift, isTrue);
      expect(a.trigger, LogicalKeyboardKey.keyF);
      expect(identical(platformKisayolu(f5, Isletim.macos), f5), isTrue);
      expect(platformKisayolMetni('Ctrl+Shift+F', Isletim.macos), 'Cmd+Shift+F');
      expect(platformKisayolMetni('F5', Isletim.macos), 'F5');
      expect(platformKisayolMetni('', Isletim.macos), '');
    });

    test('meta tuşunun adı', () {
      expect(metaTusAdi(Isletim.windows), 'Win');
      expect(metaTusAdi(Isletim.macos), 'Cmd');
    });
  });

  test('ekran metinlerinde kısayol: macOS\'ta Cmd', () {
    const metin = 'Ctrl+Shift+P ile Komut Paleti\'ni aç, Ctrl+R ile çalıştır.';
    expect(kisayolluMetin(metin, Isletim.windows), metin);
    expect(kisayolluMetin(metin, Isletim.linux), metin);
    expect(kisayolluMetin(metin, Isletim.macos),
        'Cmd+Shift+P ile Komut Paleti\'ni aç, Cmd+R ile çalıştır.');
  });

  test('çöp kutusu adı ve EXE özelliği', () {
    expect(copKutusunaMetni(Isletim.windows), "Geri Dönüşüm Kutusu'na");
    expect(copKutusunaMetni(Isletim.macos), "Çöp Kutusu'na");
    expect(copKutusunaMetni(Isletim.linux), "Çöp'e");
    for (final i in Isletim.values) {
      expect(exeDonusturmeVar(i), isTrue);
    }
  });

  test('program dosyasının adı ve uzantısı (exe_donusturucu.cikti_yollari)', () {
    expect(exeDonusturEtiketi(Isletim.windows), "EXE'ye Dönüştür…");
    expect(exeDonusturEtiketi(Isletim.linux), 'Uygulamaya Dönüştür…');
    expect(exeKaynakEtiketi(Isletim.macos), 'Uygulamanın Kaynak Kodunu Aç…');
    expect(programUzantisi('turkod', Isletim.windows), '.exe');
    expect(programUzantisi('konsol', Isletim.windows), '.exe');
    expect(programUzantisi('yok', Isletim.macos), '.app');
    expect(programUzantisi('konsol', Isletim.macos), '');
    expect(programUzantisi('turkod', Isletim.linux), '');
  });

  test('gömülü tarayıcı Windows ve macOS\'ta (Linux\'ta yok)', () {
    expect(gomuluTarayiciVar(Isletim.windows), isTrue);
    expect(gomuluTarayiciVar(Isletim.linux), isFalse);
    expect(gomuluTarayiciVar(Isletim.macos), isTrue);
  });

  test('günlük dosyası: Linux\'ta XDG_DATA_HOME', () {
    expect(sunucuGunluguAciklamasi(Isletim.linux, {'XDG_DATA_HOME': '/veri'}),
        '/veri/TurKod/backend.log');
    expect(sunucuGunluguAciklamasi(Isletim.linux, {'XDG_DATA_HOME': 'goreli'}),
        '~/.local/share/TurKod/backend.log');
    expect(sunucuGunluguAciklamasi(Isletim.linux, const {}), '~/.local/share/TurKod/backend.log');
    expect(sunucuGunluguAciklamasi(Isletim.macos, {'XDG_DATA_HOME': '/veri'}),
        contains('Application Support'));
  });

  group('Editörün kendi tuşları', () {
    test('tuş adları', () {
      expect(kisayolTusuAdi(Isletim.windows), 'Ctrl');
      expect(kisayolTusuAdi(Isletim.linux), 'Ctrl');
      expect(kisayolTusuAdi(Isletim.macos), 'Cmd');
      expect(kelimeKabulKisayolMetni(Isletim.windows), 'Ctrl+→');
      expect(kelimeKabulKisayolMetni(Isletim.linux), 'Ctrl+→');
      expect(kelimeKabulKisayolMetni(Isletim.macos), 'Option+→');
    });

    testWidgets('Ctrl basılı: Windows/Linux\'ta kısayol tuşu, macOS\'ta değil',
        (t) async {
      await simulateKeyDownEvent(LogicalKeyboardKey.controlLeft);
      expect(kisayolTusuBasili(Isletim.windows), isTrue);
      expect(kisayolTusuBasili(Isletim.linux), isTrue);
      expect(kisayolTusuBasili(Isletim.macos), isFalse);
      expect(kelimeKabulTusuBasili(Isletim.windows), isTrue);
      expect(kelimeKabulTusuBasili(Isletim.macos), isFalse);
      await simulateKeyUpEvent(LogicalKeyboardKey.controlLeft);
      expect(kisayolTusuBasili(Isletim.windows), isFalse);
    });

    testWidgets('Cmd basılı: yalnızca macOS\'ta kısayol tuşu', (t) async {
      await simulateKeyDownEvent(LogicalKeyboardKey.metaLeft);
      expect(kisayolTusuBasili(Isletim.macos), isTrue);
      expect(kisayolTusuBasili(Isletim.windows), isFalse);
      expect(kisayolTusuBasili(Isletim.linux), isFalse);
      await simulateKeyUpEvent(LogicalKeyboardKey.metaLeft);
    });

    testWidgets('Option (Alt) basılı: macOS\'ta kelime kelime kabul', (t) async {
      await simulateKeyDownEvent(LogicalKeyboardKey.altLeft);
      expect(kelimeKabulTusuBasili(Isletim.macos), isTrue);
      expect(kelimeKabulTusuBasili(Isletim.windows), isFalse);
      expect(kelimeKabulTusuBasili(Isletim.linux), isFalse);
      await simulateKeyUpEvent(LogicalKeyboardKey.altLeft);
    });
  });

  group('Sisteme özgü kısayollar', () {
    test('karakter kısayolu macOS\'ta Cmd ile', () {
      final w = platformKarakterKisayolu('/', isletim: Isletim.windows);
      expect(w.control, isTrue);
      expect(w.meta, isFalse);
      final m = platformKarakterKisayolu('\\', alt: true, isletim: Isletim.macos);
      expect(m.control, isFalse);
      expect(m.meta, isTrue);
      expect(m.alt, isTrue);
      expect(m.character, '\\');
    });

    test('Windows ve Linux\'ta istisna yok', () {
      for (final i in [Isletim.windows, Isletim.linux]) {
        expect(sistemKisayolIstisnasi('edit.redo', i), isNull);
        expect(sistemKisayolIstisnasi('edit.find_replace', i), isNull);
      }
    });

    test('macOS: Yinele Cmd+Shift+Z, Bul / Değiştir Cmd+Option+F (Cmd+H Gizle)', () {
      final yinele = sistemKisayolIstisnasi('edit.redo', Isletim.macos)!;
      expect(yinele.shortcut, 'Cmd+Shift+Z');
      expect(yinele.activator, isNull);
      final bul = sistemKisayolIstisnasi('edit.find_replace', Isletim.macos)!;
      expect(bul.shortcut, 'Cmd+Alt+F');
      expect(bul.activator!.trigger, LogicalKeyboardKey.keyF);
      expect(bul.activator!.meta, isTrue);
      expect(bul.activator!.alt, isTrue);
      expect(bul.activator!.control, isFalse);
      expect(sistemKisayolIstisnasi('file.save', Isletim.macos), isNull);
    });

    test('sistem menü çubuğu yalnızca macOS\'ta', () {
      expect(sistemMenuCubuguVar(Isletim.macos), isTrue);
      expect(sistemMenuCubuguVar(Isletim.windows), isFalse);
      expect(sistemMenuCubuguVar(Isletim.linux), isFalse);
    });
  });

  test('dışarıda açma komutu', () {
    final w = disaridaAcKomutu('https://a.b/?x=1&y=2', Isletim.windows);
    expect(w.komut, 'rundll32');
    expect(w.argumanlar, ['url.dll,FileProtocolHandler', 'https://a.b/?x=1&y=2']);
    expect(disaridaAcKomutu('x', Isletim.macos).komut, 'open');
    expect(disaridaAcKomutu('x', Isletim.linux).komut, 'xdg-open');
    expect(disaridaAcKomutu('x', Isletim.linux).argumanlar, ['x']);
  });

  group('Dosya penceresi', () {
    test('Linux\'ta zenity önerilir', () {
      expect(dosyaPenceresiHataMetni(Isletim.linux), contains('sudo apt install zenity'));
      expect(dosyaPenceresiHataMetni(Isletim.windows), isNot(contains('zenity')));
      expect(dosyaPenceresiHataMetni(Isletim.macos), isNot(contains('zenity')));
    });

    test('pencere açılamazsa ileti verilir, null döner', () async {
      final iletiler = <String>[];
      final r = await dosyaSecicisiyle<String>(
          () async => throw Exception('zenity yok'), iletiler.add, Isletim.linux);
      expect(r, isNull);
      expect(iletiler, [dosyaPenceresiHataMetni(Isletim.linux)]);
    });

    test('pencere açılırsa sonucu döner, ileti yok', () async {
      final iletiler = <String>[];
      expect(await dosyaSecicisiyle<String>(() async => '/a/b', iletiler.add), '/a/b');
      expect(await dosyaSecicisiyle<String>(() async => null, iletiler.add), isNull);
      expect(iletiler, isEmpty);
    });
  });

  test('yol karşılaştırma: Windows ve macOS\'ta harf duyarsız', () {
    expect(yollarAyniMi(r'C:\Kod\A.trpy', r'c:\kod\a.TRPY', Isletim.windows), isTrue);
    expect(yollarAyniMi(r'C:\Kod\a.trpy', 'C:/Kod/a.trpy', Isletim.windows), isTrue);
    expect(yollarAyniMi('/Users/a/Kod.trpy', '/users/a/kod.trpy', Isletim.macos), isTrue);
    expect(yollarAyniMi('/home/a/Kod.trpy', '/home/a/kod.trpy', Isletim.linux), isFalse);
    expect(yollarAyniMi('/home/a/./kod.trpy', '/home/a/kod.trpy', Isletim.linux), isTrue);
    expect(yollarAyniMi('/home/a/b.trpy', '/home/a/c.trpy', Isletim.macos), isFalse);
  });

  group('Komut satırı tırnakları (EXE\'ye Dönüştür)', () {
    test('Windows: değişmedi', () {
      expect(komutSatiriTirnagi(r'C:\oyun.trpy', Isletim.windows), r'C:\oyun.trpy');
      expect(komutSatiriTirnagi(r'C:\Oyun Klasörü\', Isletim.windows), r'"C:\Oyun Klasörü\\"');
      expect(komutSatiriTirnagi('', Isletim.windows), '""');
    });

    test('Linux/macOS: sh için güvenli', () {
      for (final i in [Isletim.linux, Isletim.macos]) {
        expect(komutSatiriTirnagi('/home/ali/oyun.trpy', i), '/home/ali/oyun.trpy');
        expect(komutSatiriTirnagi('/home/ali/Çalışma/oyun.trpy', i), '/home/ali/Çalışma/oyun.trpy');
        expect(komutSatiriTirnagi('/home/ali/Oyun Klasörü', i), '"/home/ali/Oyun Klasörü"');
        expect(komutSatiriTirnagi(r'/tmp/$HOME `x` "a" \b', i), r'"/tmp/\$HOME \`x\` \"a\" \\b"');
        expect(komutSatiriTirnagi("Ali'nin Oyunu", i), '"Ali\'nin Oyunu"');
        expect(komutSatiriTirnagi('a;rm -rf x', i), '"a;rm -rf x"');
        expect(komutSatiriTirnagi('', i), '""');
      }
    });
  });

  test('sisteme özgü açıklamalar', () {
    expect(dosyaIliskisiAciklamasi(Isletim.windows),
        'Çift tıklayınca çalıştır, sağ tıkta "Editör ile aç".');
    expect(dosyaIliskisiAciklamasi(Isletim.macos), "Çift tıklayınca TürKod'da açılır.");
    expect(dosyaIliskisiAciklamasi(Isletim.linux), 'Çift tıklayınca TürKod ile çalışır.');
    expect(pencereGoruntusuArayuzden(Isletim.windows), isFalse);
    expect(pencereGoruntusuArayuzden(Isletim.linux), isTrue);
    expect(pencereGoruntusuArayuzden(Isletim.macos), isTrue);
  });

  group('Yerel modeller: diskler', () {
    test('Windows: sürücü harfi', () {
      expect(surucuEtiketi('D', r'D:\', Isletim.windows), 'D:');
      expect(sistemPayiAdi(Isletim.windows), 'Windows');
      expect(baskaSurucuOnerisi(Isletim.windows), 'başka bir sürücü seç');
      expect(onerilenSurucuyeGecMetni(r'D:\TurKod\modeller', Isletim.windows),
          'D: sürücüsüne geç');
    });

    test('Linux/macOS: diskin klasörü', () {
      for (final i in [Isletim.linux, Isletim.macos]) {
        expect(surucuEtiketi('/', '/media/ali/Disk', i), '/media/ali/Disk');
        expect(surucuEtiketi('/', null, i), '/');
        expect(sistemPayiAdi(i), 'sistem');
        expect(baskaSurucuOnerisi(i), 'başka bir disk ya da klasör seç');
        expect(onerilenSurucuyeGecMetni('/media/ali/Disk/TurKod/modeller', i),
            'Daha çok yeri olan diske geç');
      }
    });
  });
}
