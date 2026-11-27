// Kitabı (PDF sekmesi) gerçek uygulamada açıp not araçlarını kullanıcı gibi
// dener: kalemle çizme, yazı ekleme, silgi, Ctrl+Z / Ctrl+Y, orta tuşla gezme
// ve "İlk hâline döndür" (uyarı penceresiyle). Her madde için RAPOR satırı.
//
// ÇALIŞTIRMA (notlar ve ayarlar boş bir klasöre yönlendirilmeden test durur):
//   set TURKOD_TEST_PROFIL=<boş bir klasör>\turkod_pdf_...
//   flutter test integration_test/pdf_araclari_test.dart -d windows
// TURKOD_EKRAN_BETIGI verilirse (PowerShell betiği) önemli adımlarda
// pencerenin ekran görüntüsü alınır.
import 'dart:convert';
import 'dart:io';

import 'package:flutter/gestures.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';
import 'package:path/path.dart' as p;
import 'package:pdfrx/pdfrx.dart';
import 'package:provider/provider.dart';
import 'package:turkod_ide/main.dart' as app;
import 'package:turkod_ide/pdf_notlari.dart';
import 'package:turkod_ide/yardim.dart';

import 'ortak_platform.dart';

final _sonuc = <String>[];

void _kontrol(String madde, bool gecti, [String ayrinti = '']) {
  final satir = 'RAPOR|${gecti ? "GEÇTİ" : "KALDI"}|$madde|$ayrinti';
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

Future<bool> _kosulBekle(WidgetTester t, bool Function() kosul, {int sn = 20}) async {
  final son = DateTime.now().add(Duration(seconds: sn));
  while (DateTime.now().isBefore(son)) {
    await t.pump(const Duration(milliseconds: 100));
    await Future<void>.delayed(const Duration(milliseconds: 100));
    if (kosul()) return true;
  }
  return false;
}

Future<void> _ekran(String ad) async {
  if (!Platform.isWindows) return;
  final betik = Platform.environment['TURKOD_EKRAN_BETIGI'];
  if (betik == null || betik.isEmpty) return;
  final cikti = p.join(p.dirname(betik), 'ekran_pdf_$ad.png');
  await Process.run(
      'powershell', ['-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', betik, cikti]);
}

Future<void> _tuslar(WidgetTester t, LogicalKeyboardKey tus,
    {bool ctrl = false, bool shift = false}) async {
  if (ctrl) await t.sendKeyDownEvent(kisayolTusu);
  if (shift) await t.sendKeyDownEvent(LogicalKeyboardKey.shiftLeft);
  await t.sendKeyEvent(tus);
  if (shift) await t.sendKeyUpEvent(LogicalKeyboardKey.shiftLeft);
  if (ctrl) await t.sendKeyUpEvent(kisayolTusu);
  await _bekle(t, const Duration(milliseconds: 500));
}

/// Fareyle [noktalar] boyunca sürükler.
Future<void> _surukle(WidgetTester t, List<Offset> noktalar,
    {int dugme = kPrimaryMouseButton}) async {
  final g = await t.startGesture(noktalar.first, kind: PointerDeviceKind.mouse, buttons: dugme);
  for (final n in noktalar.skip(1)) {
    await g.moveTo(n);
    await t.pump(const Duration(milliseconds: 16));
  }
  await g.up();
  await _bekle(t, const Duration(milliseconds: 400));
}

Future<void> _dugme(WidgetTester t, String anahtar) async {
  await t.tap(find.byKey(ValueKey(anahtar)));
  await _bekle(t, const Duration(milliseconds: 500));
}

void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('Kitap: kalem, yazı, silgi, geri al, orta tuş, ilk hâline döndür', (t) async {
    final ev = Platform.environment['TURKOD_TEST_PROFIL'] ?? '';
    if (!p.basename(ev).startsWith('turkod_pdf_')) {
      fail('Güvenlik: TURKOD_TEST_PROFIL bir sandbox klasörü değil ($ev).');
    }
    File(p.join(ev, '.turkod_ayarlar.json'))
        .writeAsStringSync(jsonEncode({'arayuz_turu_goruldu': true, 'son_proje_dizini': ev}));

    app.main(const []);
    expect(await _kosulBekle(t, () => find.text('Dosya').evaluate().isNotEmpty, sn: 90), isTrue,
        reason: 'Ana pencere açılmadı');
    final ctx = t.element(find.text('Dosya').first);
    final ed = ctx.read<app.EditorProvider>();
    await _bekle(t, const Duration(seconds: 2));

    final kitap = belgeYolu(kKitapDosyasi);
    expect(kitap, isNotNull, reason: 'Kitap PDF bulunamadı');
    await ed.openFile(kitap!);
    final defter = PdfNotDefteri.al(kitap);
    _kontrol('Not dosyası test klasöründe', PdfNotDefteri.notDosyasi(kitap).path.startsWith(ev),
        PdfNotDefteri.notDosyasi(kitap).path);
    defter.temizle(); // önceki çalıştırmadan kalan olmasın

    bool hazir() {
      final f = find.byKey(const ValueKey('pdf-arac-kalem'));
      return f.evaluate().isNotEmpty &&
          (f.evaluate().first.widget as app.PanelDugmesi).onPressed != null;
    }

    expect(await _kosulBekle(t, hazir, sn: 60), isTrue, reason: 'PDF sekmesi hazır olmadı');
    await _bekle(t, const Duration(seconds: 2));
    _kontrol(
        'Araç çubuğunda kalem, yazı, silgi, geri al, yinele, ilk hâl',
        [
          'pdf-arac-el',
          'pdf-arac-kalem',
          'pdf-arac-yazi',
          'pdf-arac-silgi',
          'pdf-geri-al',
          'pdf-yinele',
          'pdf-ilk-hal',
        ].every((k) => find.byKey(ValueKey(k)).evaluate().isNotEmpty));

    final alan = t.getRect(find.byType(PdfViewer));
    final orta = alan.center;
    final ctrl = (t.widget(find.byType(PdfViewer)) as PdfViewer).controller!;

    // ------------------------------------------------ kalem
    await _dugme(t, 'pdf-arac-kalem');
    _kontrol(
        'Kalem ayarları görünür (renk, kalınlık, koyuluk)',
        find.byKey(const ValueKey('pdf-renk-5')).evaluate().isNotEmpty &&
            find.byKey(const ValueKey('pdf-ayar-Kalınlık')).evaluate().isNotEmpty &&
            find.byKey(const ValueKey('pdf-ayar-Koyuluk')).evaluate().isNotEmpty);
    await _dugme(t, 'pdf-renk-4'); // yeşil
    final matrisOnce = ctrl.value.clone();
    await _surukle(t, [
      for (var i = 0; i <= 12; i++) orta + Offset(-150.0 + i * 25, (i % 2 == 0 ? -20 : 20)),
    ]);
    final cizgi = defter.notlar.whereType<PdfCizgi>().toList();
    _kontrol('Kalemle çizilen çizgi not olur', cizgi.length == 1, '${defter.notlar.length} not');
    _kontrol(
        'Çizgi seçilen renkte', cizgi.isNotEmpty && cizgi.first.renk == PdfAracAyarlari.renkler[4]);
    _kontrol('Kalemle sürüklerken sayfa kaymaz', ctrl.value == matrisOnce);
    await _ekran('01_kalem');

    // ------------------------------------------------ geri al / yinele
    await _tuslar(t, LogicalKeyboardKey.keyZ, ctrl: true);
    _kontrol('$kisayolAdi+Z çizgiyi geri alır', defter.bos);
    await _tuslar(t, LogicalKeyboardKey.keyY, ctrl: true);
    _kontrol('$kisayolAdi+Y çizgiyi geri getirir', defter.notlar.length == 1);
    await _tuslar(t, LogicalKeyboardKey.keyZ, ctrl: true);
    await _tuslar(t, LogicalKeyboardKey.keyZ, ctrl: true, shift: true);
    _kontrol('$kisayolAdi+Shift+Z de yineler', defter.notlar.length == 1);
    await _dugme(t, 'pdf-geri-al');
    _kontrol('Geri al düğmesi çalışır', defter.bos);
    await _dugme(t, 'pdf-yinele');
    _kontrol('Yinele düğmesi çalışır', defter.notlar.length == 1);

    // ------------------------------------------------ yazı
    await _dugme(t, 'pdf-arac-yazi');
    await t.tapAt(orta + const Offset(-120, 90));
    final kutuAcildi = await _kosulBekle(
        t, () => find.byKey(const ValueKey('pdf-yazi-kutusu')).evaluate().isNotEmpty,
        sn: 5);
    _kontrol('Yazı aracıyla tıklayınca yazı kutusu açılır', kutuAcildi);
    if (kutuAcildi) {
      await t.enterText(find.byKey(const ValueKey('pdf-yazi-kutusu')), 'Merhaba Kodi!');
      await _bekle(t, const Duration(milliseconds: 400));
      await _ekran('02_yazi_yaziliyor');
      // Yazarken Ctrl+Z kutunun kendisine kalır, notları geri almaz.
      await _tuslar(t, LogicalKeyboardKey.enter);
    }
    final yazilar = defter.notlar.whereType<PdfYazi>().toList();
    _kontrol(
        'Enter yazıyı sayfaya ekler',
        yazilar.length == 1 && yazilar.first.metin == 'Merhaba Kodi!',
        yazilar.map((y) => y.metin).join(','));
    _kontrol(
        'Yazı kutusu kapanır', find.byKey(const ValueKey('pdf-yazi-kutusu')).evaluate().isEmpty);
    await _ekran('03_yazi');

    // ------------------------------------------------ silgi
    await _dugme(t, 'pdf-arac-silgi');
    _kontrol('Silgi boyutu ayarlanabilir',
        find.byKey(const ValueKey('pdf-ayar-Boyut')).evaluate().isNotEmpty);
    await _surukle(t, [
      for (var i = 0; i <= 10; i++) orta + Offset(-30.0 + i * 6, -60 + i * 12.0),
    ]);
    _kontrol('Silgi değdiği çizgiyi siler', defter.notlar.whereType<PdfCizgi>().isEmpty,
        '${defter.notlar.length} not kaldı');
    _kontrol('Silgi değmediği yazıya dokunmaz', defter.notlar.whereType<PdfYazi>().length == 1);
    await _tuslar(t, LogicalKeyboardKey.keyZ, ctrl: true);
    _kontrol('Silme tek adımda geri alınır', defter.notlar.length == 2);

    // ------------------------------------------------ orta tuş
    await _dugme(t, 'pdf-arac-el');
    final yOnce = ctrl.value.getTranslation().y;
    await _surukle(t, [orta, orta + const Offset(0, -80), orta + const Offset(0, -200)],
        dugme: kMiddleMouseButton);
    final yFark = ctrl.value.getTranslation().y - yOnce;
    _kontrol('Orta tuşla sürükleyince sayfa kayar', yFark < -100, 'fark=$yFark');
    // Kalem seçiliyken de orta tuş gezdirir, çizmez.
    await _dugme(t, 'pdf-arac-kalem');
    final sayi = defter.notlar.length;
    final y2 = ctrl.value.getTranslation().y;
    await _surukle(t, [orta, orta + const Offset(0, 150)], dugme: kMiddleMouseButton);
    _kontrol('Kalem seçiliyken orta tuş çizmez, gezdirir',
        defter.notlar.length == sayi && ctrl.value.getTranslation().y - y2 > 100);
    // Orta tuşa tıklama: otomatik kaydırma; fare aşağıdayken belge kayar.
    final y3 = ctrl.value.getTranslation().y;
    final fare =
        await t.startGesture(orta, kind: PointerDeviceKind.mouse, buttons: kMiddleMouseButton);
    await fare.up();
    await fare.moveTo(orta + const Offset(0, 120));
    await _bekle(t, const Duration(milliseconds: 600));
    final otoKaydi = ctrl.value.getTranslation().y - y3;
    _kontrol('Orta tuşa tıklayınca otomatik kaydırma', otoKaydi < -50, 'fark=$otoKaydi');
    await _ekran('04_otomatik_kaydirma');
    await _tuslar(t, LogicalKeyboardKey.escape);
    final y4 = ctrl.value.getTranslation().y;
    await _bekle(t, const Duration(milliseconds: 400));
    _kontrol('Esc otomatik kaydırmayı durdurur', (ctrl.value.getTranslation().y - y4).abs() < 1);

    // ------------------------------------------------ ilk hâline döndür
    defter.kaydet();
    final dosya = PdfNotDefteri.notDosyasi(kitap);
    _kontrol('Notlar diske kaydedilir', dosya.existsSync());
    await _dugme(t, 'pdf-ilk-hal');
    final uyari = find.textContaining('ilk hâline dönsün mü?');
    _kontrol('İlk hâline döndürmeden önce uyarı çıkar', uyari.evaluate().isNotEmpty);
    await _ekran('05_uyari');
    await t.tap(find.text('Vazgeç'));
    await _bekle(t, const Duration(milliseconds: 600));
    _kontrol('Vazgeç notlara dokunmaz', defter.notlar.length == 2);
    await _dugme(t, 'pdf-ilk-hal');
    await t.tap(find.text('Evet, ilk hâline döndür'));
    await _bekle(t, const Duration(seconds: 1));
    _kontrol('Onaylayınca bütün notlar silinir', defter.bos);
    defter.kaydet();
    _kontrol('Not dosyası da silinir', !dosya.existsSync());
    await _tuslar(t, LogicalKeyboardKey.keyZ, ctrl: true);
    _kontrol('İlk hâline döndürme de geri alınabilir', defter.notlar.length == 2);
    defter.temizle();
    defter.kaydet();

    final kalan = _sonuc.where((s) => s.contains('|KALDI|')).toList();
    expect(kalan, isEmpty, reason: kalan.join('\n'));
  });
}
