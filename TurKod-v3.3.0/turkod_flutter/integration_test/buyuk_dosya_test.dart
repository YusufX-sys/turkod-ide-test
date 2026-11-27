// Büyük dosyada uzak bir satıra tıklayınca ve yazınca editörün kaymadığını
// gerçek uygulamada dener.
//
// Eskiden imlecin yeri "(satır - 1) × yazı boyutu × 1,4" diye tahmin ediliyordu;
// gerçek satır yüksekliği tam piksele yuvarlandığından (Consolas 14 punto: 20,
// tahmin 19,6) fark 2000. satırda ~800 piksele çıkıyor, tıklanan satır "görünmüyor"
// sanılıp ekranın en altına kaydırılıyordu.
//
// ÇALIŞTIRMA (ayarlar boş bir klasöre yönlendirilmeden test durur):
//   set TURKOD_TEST_PROFIL=<boş bir klasör>\turkod_buyuk_...
//   flutter test integration_test/buyuk_dosya_test.dart -d windows
import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';
import 'package:path/path.dart' as p;
import 'package:provider/provider.dart';
import 'package:re_editor/re_editor.dart' as re;
import 'package:turkod_ide/main.dart' as app;

import 'ortak_platform.dart';

final _sonuc = <String>[];
void _kontrol(String madde, bool gecti, [String ayrinti = '']) {
  final satir = 'SONUÇ|${gecti ? "GEÇTİ" : "KALDI"}|$madde|$ayrinti';
  _sonuc.add(satir);
  // ignore: avoid_print
  print(satir);
}

Future<void> _bekle(WidgetTester t, Duration d) async {
  final son = DateTime.now().add(d);
  while (DateTime.now().isBefore(son)) {
    await t.pump(const Duration(milliseconds: 50));
    await Future<void>.delayed(const Duration(milliseconds: 50));
  }
}

Future<bool> _bulanaKadar(WidgetTester t, Finder f, {int sn = 60}) async {
  final son = DateTime.now().add(Duration(seconds: sn));
  while (DateTime.now().isBefore(son)) {
    await t.pump(const Duration(milliseconds: 100));
    await Future<void>.delayed(const Duration(milliseconds: 100));
    if (f.evaluate().isNotEmpty) return true;
  }
  return false;
}

/// Editörün dikey kaydırma konumu.
ScrollPosition _dikey(WidgetTester t) {
  for (final e in find
      .descendant(of: find.byType(re.CodeEditor).first, matching: find.byType(Scrollable))
      .evaluate()) {
    final s = (e as StatefulElement).state as ScrollableState;
    if (s.position.axis == Axis.vertical) return s.position;
  }
  throw StateError('Editörün dikey kaydırıcısı bulunamadı');
}

int _imlecSatiri(TextEditingController c) {
  final off = c.selection.baseOffset.clamp(0, c.text.length);
  return '\n'.allMatches(c.text.substring(0, off)).length + 1;
}

void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('Büyük dosyada tıklama ve yazma kaydırmaz', (t) async {
    final ev = Platform.environment['TURKOD_TEST_PROFIL'] ?? '';
    if (!p.basename(ev).startsWith('turkod_buyuk_')) {
      fail('Güvenlik: TURKOD_TEST_PROFIL bir sandbox klasörü değil ($ev).');
    }
    final ayarDosyasi = File(p.join(ev, '.turkod_ayarlar.json'));
    if (!ayarDosyasi.existsSync()) {
      ayarDosyasi.writeAsStringSync(jsonEncode({'arayuz_turu_goruldu': true}));
    }
    app.main(const []);
    expect(await _bulanaKadar(t, find.text('Dosya'), sn: 90), isTrue);
    await _bekle(t, const Duration(seconds: 3));
    final ed = t.element(find.text('Dosya').first).read<app.EditorProvider>();

    final metin = [for (var i = 1; i <= 2500; i++) 'yazdır("satır $i")'].join('\n');
    await ed.createUntitled(content: metin);
    await _bekle(t, const Duration(seconds: 2));
    final c = ed.uiController!;

    // Ctrl+G ile 2000. satıra git.
    await t.tap(find.byType(re.CodeEditor).first);
    await t.sendKeyDownEvent(kisayolTusu);
    await t.sendKeyEvent(LogicalKeyboardKey.keyG);
    await t.sendKeyUpEvent(kisayolTusu);
    await _bekle(t, const Duration(milliseconds: 800));
    final pencere = find.widgetWithText(AlertDialog, 'Satıra Git');
    expect(pencere, findsOneWidget);
    await t.enterText(find.descendant(of: pencere, matching: find.byType(TextField)), '2000');
    await t.testTextInput.receiveAction(TextInputAction.done);
    await _bekle(t, const Duration(seconds: 1));
    _kontrol('Satıra Git 2000. satıra götürür', _imlecSatiri(c) == 2000,
        'imleç satırı=${_imlecSatiri(c)}');

    // Görünen alanın ortasına tıkla: kaydırma değişmemeli, imleç ~2000 olmalı.
    final once = _dikey(t).pixels;
    final kutu = t.getRect(find.byType(re.CodeEditor).first);
    await t.tapAt(Offset(kutu.left + 200, kutu.center.dy));
    await _bekle(t, const Duration(seconds: 1));
    final sonra = _dikey(t).pixels;
    final tiklanan = _imlecSatiri(c);
    _kontrol('Uzak satıra tıklayınca editör kaymaz', (sonra - once).abs() < 2,
        'önce=$once sonra=$sonra');
    _kontrol('Tıklanan satır görünen satırdır', (tiklanan - 2000).abs() < 40,
        'imleç satırı=$tiklanan');

    // Yazma: imlecin olduğu yere bir harf eklenince de kaymamalı.
    final yer = c.selection.baseOffset;
    c.value = TextEditingValue(
      text: c.text.replaceRange(yer, yer, 'x'),
      selection: TextSelection.collapsed(offset: yer + 1),
    );
    await _bekle(t, const Duration(seconds: 1));
    final yazinca = _dikey(t).pixels;
    _kontrol('Uzak satırda yazınca editör kaymaz', (yazinca - sonra).abs() < 2,
        'önce=$sonra sonra=$yazinca');

    // Silme (geri al gibi): yine kaymamalı.
    c.value = TextEditingValue(
      text: c.text.replaceRange(yer, yer + 1, ''),
      selection: TextSelection.collapsed(offset: yer),
    );
    await _bekle(t, const Duration(seconds: 1));
    final silince = _dikey(t).pixels;
    _kontrol('Uzak satırda silince editör kaymaz', (silince - yazinca).abs() < 2,
        'önce=$yazinca sonra=$silince');

    // --- Satırın görünümdeki yeri. Gerçek satır yüksekliği kaydırma
    // ölçülerinden hesaplanır (üst/alt boşluk 8'er piksel).
    double satirYuksekligi() {
      final d = _dikey(t);
      return (d.maxScrollExtent + d.viewportDimension - 16) / 2500;
    }

    /// Satırın görünür alandaki üst kenarı (0: en üst).
    double satirinYeri(int satir) =>
        8 + (satir - 1) * satirYuksekligi() - _dikey(t).pixels;

    bool ortada(int satir) {
      final d = _dikey(t);
      final lh = satirYuksekligi();
      return (satirinYeri(satir) + lh / 2 - d.viewportDimension / 2).abs() < lh * 1.5;
    }

    // Satıra Git satırı ortalar (eskiden alt kenara, kaydırma çubuğunun
    // altına koyuyordu).
    _kontrol('Satıra Git satırı ortalar', ortada(2000),
        'yer=${satirinYeri(2000).toStringAsFixed(1)} görünüm=${_dikey(t).viewportDimension}');

    // Uzağa sıçrayan seçim (Bul / Sorunlar gibi): satır ortalanır.
    final hedef300 = '\n'.allMatches(c.text).take(299).last.end;
    c.selection = TextSelection(baseOffset: hedef300, extentOffset: hedef300 + 6);
    await _bekle(t, const Duration(seconds: 1));
    _kontrol('Uzak satıra sıçrayan seçim satırı ortalar', ortada(300),
        'yer=${satirinYeri(300).toStringAsFixed(1)}');

    // Görünen son satıra inmek: satır kaydırma çubuğunun altında kalmaz.
    {
      final d = _dikey(t);
      final lh = satirYuksekligi();
      final sonSatir = ((d.pixels + d.viewportDimension - 8) / lh).floor();
      final bas = '\n'.allMatches(c.text).take(sonSatir - 1).last.end;
      c.selection = TextSelection.collapsed(offset: bas);
      await _bekle(t, const Duration(seconds: 1));
      final alt = satirinYeri(sonSatir) + lh;
      _kontrol('En alttaki satır kaydırma çubuğunun üstünde kalır',
          alt <= _dikey(t).viewportDimension - 16,
          'satır=$sonSatir alt kenar=${alt.toStringAsFixed(1)} görünüm=${_dikey(t).viewportDimension}');
    }

    final kalan = _sonuc.where((s) => s.contains('|KALDI|')).toList();
    expect(kalan, isEmpty, reason: kalan.join('\n'));
  });
}
