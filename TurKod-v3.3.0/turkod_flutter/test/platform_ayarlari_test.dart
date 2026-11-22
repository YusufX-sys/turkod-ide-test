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
    expect(exeDonusturmeVar(Isletim.windows), isTrue);
    expect(exeDonusturmeVar(Isletim.linux), isFalse);
    expect(exeDonusturmeVar(Isletim.macos), isFalse);
  });

  test('gömülü tarayıcı yalnızca Windows\'ta', () {
    expect(gomuluTarayiciVar(Isletim.windows), isTrue);
    expect(gomuluTarayiciVar(Isletim.linux), isFalse);
    expect(gomuluTarayiciVar(Isletim.macos), isFalse);
  });
}
