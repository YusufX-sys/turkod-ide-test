import 'dart:async';
import 'dart:typed_data';
import 'dart:ui' as ui;

import 'package:flutter/gestures.dart';
import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart' show RenderRepaintBoundary;
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';
import 'package:turkod_ide/main.dart' as app;

Finder _yazi(String s) => find.textContaining(s, findRichText: true);

class _Ortam {
  _Ortam([app.BackendService? b]) : backend = b ?? app.BackendService();
  final app.BackendService backend;
  late final ayarlar = app.SettingsProvider(backend);
  late final kodi = app.KodiProvider(backend);
  late final ui = app.UiProvider();
  late final ed = app.EditorProvider(backend);
  late final agac = app.FileTreeProvider(backend);
  late final terminal = app.TerminalProvider(backend);

  Widget sar(Widget child) => MultiProvider(
        providers: [
          Provider<app.BackendService>.value(value: backend),
          ChangeNotifierProvider<app.SettingsProvider>.value(value: ayarlar),
          ChangeNotifierProvider<app.UiProvider>.value(value: ui),
          ChangeNotifierProvider<app.EditorProvider>.value(value: ed),
          ChangeNotifierProvider<app.FileTreeProvider>.value(value: agac),
          ChangeNotifierProvider<app.TerminalProvider>.value(value: terminal),
          ChangeNotifierProvider<app.KodiProvider>.value(value: kodi),
        ],
        child: MaterialApp(
          theme: app.AppThemeRegistry.build('Modern Koyu'),
          home: Scaffold(body: child),
        ),
      );
}

/// Kodi sorularına cevabı elle verilen, ayarları kabul eden sahte arka uç.
class _SahteBackend extends app.BackendService {
  final cevap = Completer<Map<String, dynamic>>();
  final ayarlar = <String, dynamic>{};
  final komutlar = <String>[];
  final sorular = <String>[];
  @override
  Future<Map<String, dynamic>> call(String command,
      [Map<String, dynamic> params = const {}]) {
    komutlar.add(command);
    if (command == 'kodi_sor') {
      sorular.add(params['mesaj'].toString());
      return cevap.future;
    }
    if (command == 'kodi_dinle') {
      return Future.value({'ok': true, 'metin': 'Seni duyuyor muyum?'});
    }
    if (command == 'ayar_set') ayarlar[params['anahtar'] as String] = params['deger'];
    return Future.value({'ok': true});
  }
}

Future<void> _bekle(WidgetTester tester, int ms) async {
  for (var i = 0; i < ms ~/ 50; i++) {
    await tester.pump(const Duration(milliseconds: 50));
  }
}

void main() {
  testWidgets('Kodi her ifadede çizilir (simge dahil)', (tester) async {
    await tester.pumpWidget(MaterialApp(
      home: Scaffold(
        body: Wrap(children: [
          for (final i in app.KodiIfadesi.values)
            app.KodiRobotu(ifade: i, elSalla: i == app.KodiIfadesi.mutlu),
          // Düşünürken pencerenin ortası soldaysa sola dönük (aynalı) çizilir.
          const app.KodiRobotu(ifade: app.KodiIfadesi.dusunceli, solaBak: true),
          const app.KodiSimgesi(),
        ]),
      ),
    ));
    await tester.pump(const Duration(milliseconds: 500));
    expect(tester.takeException(), isNull);
    expect(find.byType(app.KodiRobotu), findsNWidgets(app.KodiIfadesi.values.length + 1));
  });

  testWidgets('Kodi kayarak gelir, harf harf selam verir ve gider', (tester) async {
    final o = _Ortam();
    await tester.binding.setSurfaceSize(const Size(900, 700));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    await tester.pumpWidget(o.sar(const SizedBox.expand(child: app.KodiKatmani())));
    // Kapalıyken hiçbir şey çizilmez.
    expect(find.byType(app.KodiRobotu), findsNothing);

    o.kodi.ac();
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 100));
    expect(find.byType(app.KodiRobotu), findsOneWidget);
    // Kayma sürerken balon yok.
    expect(_yazi('Merhaba'), findsNothing);

    await tester.pump(const Duration(milliseconds: 700)); // vardı
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));
    // Harf harf: selamın yalnızca başı yazılmış olmalı.
    expect(_yazi('Merh'), findsWidgets);
    expect(_yazi('Merhaba, ben Kodi!'), findsNothing);

    // Fare balonun üstünde gezinirken yazı yazılır: eskiden kare bittikten
    // sonra liste kaydırılıyor, fare izleyicisi yerleşimi bitmemiş Kodi'de
    // isabet testi yapıp hata zinciri başlatıyordu.
    final fare = await tester.createGesture(kind: PointerDeviceKind.mouse);
    await fare.addPointer(location: const Offset(700, 560));
    addTearDown(fare.removePointer);
    for (var i = 0; i < 70; i++) {
      await fare.moveTo(Offset(560 + (i % 7) * 40.0, 450 + (i % 5) * 30.0));
      await tester.pump(const Duration(milliseconds: 100));
    }
    expect(tester.takeException(), isNull);
    expect(_yazi('Merhaba, ben Kodi!'), findsOneWidget);
    expect(_yazi('birlikte yapalım; yardımcı olabilirim!'), findsOneWidget);
    expect(o.kodi.mesajlar.length, 2);

    // Motor bağlı değilken soru: Kodi dostça bir hata söyler.
    await tester.enterText(find.byType(TextField), 'Seni kim yaptı?');
    await tester.tap(find.byTooltip('Gönder (Enter)'));
    await tester.pump();
    await _bekle(tester, 4000);
    expect(_yazi('Seni kim yaptı?'), findsOneWidget);
    expect(_yazi('TürKod motoruna ulaşamadım'), findsOneWidget);

    // Yeni sohbet: Kodi baştan "Merhaba, ben Kodi!" der, yardım cümlesi gelir.
    o.kodi.temizle();
    await _bekle(tester, 6000);
    expect(_yazi('Seni kim yaptı?'), findsNothing);
    expect(o.kodi.mesajlar.first.metin, 'Merhaba, ben Kodi!');
    expect(o.kodi.mesajlar.length, 2);

    // Gider: önce el sallar (hâlâ görünür), kayma bitince tamamen kaybolur.
    o.kodi.kapat();
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));
    expect(find.byType(app.KodiRobotu), findsOneWidget);
    await tester.pump(const Duration(milliseconds: 300));
    await tester.pump(const Duration(milliseconds: 800));
    await tester.pump();
    expect(find.byType(app.KodiRobotu), findsNothing);

    // Yeniden çağrılınca yeni sohbetle, selamla gelir.
    o.kodi.ac();
    await _bekle(tester, 6000);
    expect(o.kodi.mesajlar.first.metin, 'Merhaba, ben Kodi!');
    expect(o.kodi.mesajlar.length, 2);
    o.kodi.kapat();
    await _bekle(tester, 1000);
  });

  testWidgets('Kodi basılı tutup sürüklenir, çift tıklayınca yerine döner',
      (tester) async {
    final o = _Ortam();
    await tester.binding.setSurfaceSize(const Size(900, 700));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    await tester.pumpWidget(o.sar(const SizedBox.expand(child: app.KodiKatmani())));
    o.kodi.ac();
    await tester.pump();
    await _bekle(tester, 2500); // kayarak gelme bitsin
    final ilk = tester.getTopLeft(find.byType(app.KodiRobotu));

    // Beklemeden sürüklenir (eskiden yarım saniyeye yakın basılı tutmak
    // gerekiyordu): fareyle basıp hemen çekmek yeter.
    final g = await tester.startGesture(tester.getCenter(find.byType(app.KodiRobotu)),
        kind: PointerDeviceKind.mouse);
    for (var i = 0; i < 10; i++) {
      await g.moveBy(const Offset(-30, -25));
      await tester.pump(const Duration(milliseconds: 16));
    }
    await g.up();
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300)); // büyüme geri dönsün
    final yeni = tester.getTopLeft(find.byType(app.KodiRobotu));
    expect(yeni.dx, closeTo(ilk.dx - 300, 2));
    expect(yeni.dy, closeTo(ilk.dy - 250, 2));
    // Yukarıda yer azalınca balon robotun altına açılır, ekrandan taşmaz.
    expect(tester.takeException(), isNull);

    final robot = tester.getCenter(find.byType(app.KodiRobotu));
    await tester.tapAt(robot);
    await tester.pump(const Duration(milliseconds: 60));
    await tester.tapAt(robot);
    await tester.pump(const Duration(milliseconds: 400));
    final geri = tester.getTopLeft(find.byType(app.KodiRobotu));
    expect(geri.dx, closeTo(ilk.dx, 2));
    expect(geri.dy, closeTo(ilk.dy, 2));

    // Selam ve yazı zamanlayıcıları bitsin, Kodi gitsin.
    await _bekle(tester, 9000);
    o.kodi.kapat();
    await _bekle(tester, 1000);
    await tester.pumpWidget(const SizedBox());
    await tester.pump(const Duration(seconds: 1));
  });

  testWidgets('Kodi balonu köşesinden büyütülüp küçültülür, kaydırılır',
      (tester) async {
    final o = _Ortam();
    await tester.binding.setSurfaceSize(const Size(1000, 760));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    await tester.pumpWidget(o.sar(const SizedBox.expand(child: app.KodiKatmani())));
    o.kodi.ac();
    await tester.pump();
    await _bekle(tester, 9000); // selam bitsin

    final tutamac = find.byTooltip(
        'Balonu büyütmek ya da küçültmek için sürükle (çift tıkla: varsayılan boyut)');
    expect(tutamac, findsOneWidget);
    final balon = find.byType(Scrollbar);
    expect(balon, findsOneWidget); // sohbet sığmayınca kaydırma çubuğu
    final once = tester.getSize(find.ancestor(of: balon, matching: find.byType(Stack)).first);

    // Balon robotun üstünde: tutamaç sol üstte, yukarı/sola çekince büyür.
    await tester.drag(tutamac, const Offset(-120, -150));
    await tester.pump();
    final sonra = tester.getSize(find.ancestor(of: balon, matching: find.byType(Stack)).first);
    // Sürükleme eşiği (birkaç piksel) düşülür.
    expect(sonra.width, greaterThan(once.width + 95));
    expect(sonra.height, greaterThan(once.height + 100));

    // Çift tıklama: varsayılan boyut.
    await tester.tap(tutamac);
    await tester.pump(const Duration(milliseconds: 60));
    await tester.tap(tutamac);
    await tester.pump(const Duration(milliseconds: 400));
    final geri = tester.getSize(find.ancestor(of: balon, matching: find.byType(Stack)).first);
    expect(geri.width, closeTo(once.width, 2));
    expect(tester.takeException(), isNull);

    o.kodi.kapat();
    await _bekle(tester, 1000);
    await tester.pumpWidget(const SizedBox());
    await tester.pump(const Duration(seconds: 1));
  });

  testWidgets('Kodi eylemleri: güvenli olan yapılır, diğeri izin ister',
      (tester) async {
    final o = _Ortam();
    await tester.binding.setSurfaceSize(const Size(900, 760));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    await tester.pumpWidget(o.sar(const SizedBox.expand(child: app.KodiKatmani())));
    o.kodi.ac();
    await tester.pump();
    await _bekle(tester, 9000); // selam bitsin
    expect(o.ui.showAi, isTrue);

    o.kodi.mesajlar.add(app.KodiMesaji(true, 'Tamam, hallediyorum!', eylemler: [
      app.KodiEylemi('panel', {'eylem': 'panel', 'panel': 'ai', 'durum': 'kapat'}),
      app.KodiEylemi('komut', {'eylem': 'komut', 'id': 'run.run', 'etiket': 'Çalıştır'}),
      app.KodiEylemi('kod_yaz', {
        'eylem': 'kod_yaz',
        'hedef': 'yeni_sekme',
        'ad': 'sayac.trpy',
        'kod': 'için i aralık(3):\n    yazdır(i)',
      }),
    ]));
    o.kodi.yenile();
    await _bekle(tester, 3000);

    // Panel kendiliğinden kapandı; komut ve kod için izin isteniyor.
    expect(o.ui.showAi, isFalse);
    expect(_yazi('AI Asistan kapandı'), findsOneWidget);
    expect(_yazi('komutunu çalıştırayım mı?'), findsOneWidget);
    expect(_yazi('Bu kodu (2 satır) senin için yazayım mı?'), findsOneWidget);

    await tester.tap(find.text('Vazgeç').first);
    await tester.pump();
    expect(_yazi('Vazgeçildi'), findsOneWidget);

    await tester.tap(find.text('Yeni sekmede aç').first);
    await _bekle(tester, 500);
    expect(o.ed.tabs.map((t) => t.name), contains('sayac.trpy'));
    expect(o.ed.activeTab?.content, contains('yazdır(i)'));
    expect(_yazi('Kod yeni bir sekmeye yazıldı'), findsOneWidget);
    expect(tester.takeException(), isNull);

    // Satıra git ve ara: izin istemeden yapılır (Türkçe harf duyarsız arama).
    o.kodi.mesajlar.add(app.KodiMesaji(true, 'Bakıyorum!', eylemler: [
      app.KodiEylemi('ara', {'eylem': 'ara', 'metin': 'YAZDIR', 'sira': 1}),
      app.KodiEylemi('satira_git', {'eylem': 'satira_git', 'satir': 9}),
    ]));
    o.kodi.yenile();
    await _bekle(tester, 2000);
    expect(_yazi('"YAZDIR" 2. satırda bulundu'), findsOneWidget);
    expect(_yazi('Dosyada 2 satır var; 9. satır yok'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets('Kodi: hazır sorular, vazgeç, ayar eylemi, kodsuz komut', (tester) async {
    final sahte = _SahteBackend();
    final o = _Ortam(sahte);
    await tester.binding.setSurfaceSize(const Size(1000, 760));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    await tester.pumpWidget(o.sar(const SizedBox.expand(child: app.KodiKatmani())));
    o.kodi.ac();
    await tester.pump();
    await _bekle(tester, 9000); // selam bitsin

    // Daha hiçbir şey sorulmadı: hazır sorular görünür.
    for (final s in app.kKodiHazirSorular) {
      expect(find.text(s), findsOneWidget);
    }
    await tester.tap(find.text('Kitapta döngüler nerede?'));
    await tester.pump();
    expect(o.kodi.bekliyor, isTrue);
    expect(find.text('Hatamı bulur musun?'), findsNothing); // soru sorulunca kalkar
    expect(find.byTooltip('Vazgeç (cevabı bekleme)'), findsOneWidget);

    // Vazgeç: geç gelen cevap gösterilmez.
    await tester.tap(find.byTooltip('Vazgeç (cevabı bekleme)'));
    await _bekle(tester, 2500);
    expect(o.kodi.bekliyor, isFalse);
    expect(_yazi('Peki, vazgeçtim!'), findsOneWidget);
    sahte.cevap.complete({'ok': true, 'cevap': 'GEÇ GELEN CEVAP', 'eylemler': []});
    await _bekle(tester, 1000);
    expect(_yazi('GEÇ GELEN CEVAP'), findsNothing);

    // Ayar eylemi kendiliğinden; kod dosyası yokken Çalıştır dostça reddedilir.
    o.kodi.mesajlar.add(app.KodiMesaji(true, 'Tamam!', eylemler: [
      app.KodiEylemi('ayar', {'eylem': 'ayar', 'ad': 'tema', 'deger': 'Açık'}),
      app.KodiEylemi('ayar', {'eylem': 'ayar', 'ad': 'yazi_boyutu', 'deger': 18}),
      app.KodiEylemi('komut', {'eylem': 'komut', 'id': 'run.run', 'etiket': 'Çalıştır'}),
    ]));
    o.kodi.yenile();
    await _bekle(tester, 1500);
    expect(sahte.ayarlar['tema'], 'Açık');
    expect(sahte.ayarlar['yazi_boyutu'], 18);
    expect(_yazi('Tema: Açık'), findsOneWidget);
    await tester.tap(find.text('İzin ver'));
    await tester.pump();
    expect(_yazi('Önce bir kod dosyası açmalısın'), findsOneWidget);
    expect(tester.takeException(), isNull);

    o.kodi.kapat();
    await _bekle(tester, 1000);
    await tester.pumpWidget(const SizedBox());
    await tester.pump(const Duration(seconds: 1));
  });

  testWidgets('Kodi programı yönetir: eklenti, ayar, Ayarlar bölümü, komut, yetkiler',
      (tester) async {
    final sahte = _SahteBackend();
    final o = _Ortam(sahte);
    await tester.binding.setSurfaceSize(const Size(1000, 760));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    await tester.pumpWidget(o.sar(const SizedBox.expand(child: app.KodiKatmani())));
    o.kodi.ac();
    await tester.pump();
    await _bekle(tester, 9000); // selam bitsin

    Future<void> soyle(List<app.KodiEylemi> eylemler) async {
      o.kodi.mesajlar.add(app.KodiMesaji(true, 'Hemen!', eylemler: eylemler));
      o.kodi.yenile();
      await _bekle(tester, 1500);
    }

    // İzin istemeden: eklenti, ayar, Ayarlar bölümü; EXE paneli izinsiz
    // komuttur (kod dosyası yokken dostça reddedilir).
    await soyle([
      app.KodiEylemi('eklenti',
          {'eylem': 'eklenti', 'id': 'odak_zamanlayici', 'durum': 'ac', 'etiket': 'Odak'}),
      app.KodiEylemi('ayar', {'eylem': 'ayar', 'ad': 'satir_numaralari', 'deger': 'kapalı'}),
      app.KodiEylemi('ayar', {'eylem': 'ayar', 'ad': 'girinti_boyutu', 'deger': 3}),
      app.KodiEylemi('ayar', {'eylem': 'ayar', 'ad': 'kodi_yetki_ayar', 'deger': false}),
      app.KodiEylemi('ayarlar_ac', {'eylem': 'ayarlar_ac', 'bolum': 'kodi'}),
      app.KodiEylemi('komut', {'eylem': 'komut', 'id': 'run.exe'}),
      app.KodiEylemi('model_ata', {'eylem': 'model_ata', 'gorev': 'sohbet', 'model': 'yok-boyle-model'}),
    ]);
    expect(sahte.ayarlar['eklentiler'], contains('odak_zamanlayici'));
    expect(_yazi('Odak Zamanlayıcı etkinleştirildi'), findsOneWidget);
    expect(sahte.ayarlar['satir_numaralari'], isFalse);
    expect(_yazi('Satır numaraları: kapalı'), findsOneWidget);
    expect(_yazi('yalnızca 2, 4, 8 olabilir'), findsOneWidget);
    expect(sahte.ayarlar.containsKey('kodi_yetki_ayar'), isFalse);
    expect(_yazi('Bu ayarı yalnızca sen değiştirebilirsin'), findsOneWidget);
    expect(app.ayarlarHedefi.value, 'kodi');
    expect(o.ed.tabs.any((t) => t.path == app.kSettingsPath), isTrue);
    expect(_yazi('Ayarlar açıldı: Kodi'), findsOneWidget);
    expect(_yazi('Önce bir kod dosyası açmalısın'), findsOneWidget);
    expect(_yazi('"yok-boyle-model" diye bir model bulamadım'), findsOneWidget);
    expect(find.text('İzin ver'), findsNothing);
    app.ayarlarHedefi.value = null;

    // Kullanıcı Ayarlar → Kodi'de eklenti yetkisini kapattı.
    await o.ayarlar.setValue(app.kKodiYetkiEklenti, false);
    await soyle([
      app.KodiEylemi('eklenti',
          {'eylem': 'eklenti', 'id': 'odak_zamanlayici', 'durum': 'kapat', 'etiket': 'Odak'}),
    ]);
    expect(_yazi('Eklentileri yönetmeme izin verilmemiş'), findsOneWidget);
    expect(sahte.ayarlar['eklentiler'], contains('odak_zamanlayici'));

    // "Her işten önce izin istesin": panel açmak bile sorulur.
    o.kodi.hepSor = true;
    await soyle([
      app.KodiEylemi('panel', {'eylem': 'panel', 'panel': 'terminal', 'durum': 'ac'}),
    ]);
    expect(_yazi('panelini açayım mı?'), findsOneWidget);
    expect(o.ui.showTerminal, isFalse);
    expect(tester.takeException(), isNull);

    // Bağlam: bütün komutlar, eklentiler, ayarlar ve yetkiler gider.
    final baglam = app.kodiYonetimBaglami(tester.element(find.byType(app.KodiKatmani)));
    final komutlar = [for (final k in baglam['komutlar'] as List) k['id']];
    expect(komutlar, containsAll(['run.exe', 'view.keybindings', 'file.save']));
    expect(komutlar, isNot(contains('help.kodi')));
    expect((baglam['ayarlar'] as Map).keys, isNot(contains('kodi_yetki_ayar')));
    expect((baglam['yetkiler'] as Map)['eklenti'], isFalse);

    o.kodi.kapat();
    await _bekle(tester, 1000);
    await tester.pumpWidget(const SizedBox());
    await tester.pump(const Duration(seconds: 1));
  });

  testWidgets('Kodi: mikrofonla sorulan soru, otomatik model', (tester) async {
    final sahte = _SahteBackend();
    final o = _Ortam(sahte);
    await tester.binding.setSurfaceSize(const Size(1000, 760));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    await tester.pumpWidget(o.sar(const SizedBox.expand(child: app.KodiKatmani())));
    o.kodi.ac();
    await tester.pump();
    await _bekle(tester, 9000);

    // Kodi görevi atanmamış: AI Paneli sohbet modeli kullanılır.
    expect(o.ayarlar.kodiAtamasi, isNull);
    await o.ayarlar.setValue('ai_gorev_atamalari', {
      'sohbet': {'saglayici': 'groq', 'model': 'gpt-oss'}
    });
    expect(o.ayarlar.kodiAtamasi, const app.AiAtama('groq', 'gpt-oss'));
    await o.ayarlar.setValue('ai_gorev_atamalari', {
      'sohbet': {'saglayici': 'groq', 'model': 'gpt-oss'},
      'kodi': {'saglayici': 'groq', 'model': 'qwen'},
    });
    expect(o.ayarlar.kodiAtamasi, const app.AiAtama('groq', 'qwen'));

    await tester.tap(find.byTooltip('Sesle sor: bas ve konuş, susunca Kodi anlar'));
    await _bekle(tester, 500);
    expect(sahte.komutlar, contains('kodi_dinle'));
    expect(sahte.sorular, ['Seni duyuyor muyum?']);
    expect(_yazi('Seni duyuyor muyum?'), findsOneWidget);
    sahte.cevap.complete({'ok': true, 'cevap': 'Duyuyorum!', 'eylemler': []});
    await _bekle(tester, 2000);
    expect(_yazi('Duyuyorum!'), findsOneWidget);
    expect(tester.takeException(), isNull);

    o.kodi.kapat();
    await _bekle(tester, 1000);
    await tester.pumpWidget(const SizedBox());
    await tester.pump(const Duration(seconds: 1));
  });

  testWidgets('Kodi balonu en dar hâlinde de düğmeler taşmaz', (tester) async {
    final o = _Ortam(_SahteBackend());
    await tester.binding.setSurfaceSize(const Size(900, 760));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    await o.ayarlar.setValue('kodi_balon', [200, 360]); // en dara (260) sınırlanır
    await tester.pumpWidget(o.sar(const SizedBox.expand(child: app.KodiKatmani())));
    o.kodi.ac();
    await tester.pump();
    await _bekle(tester, 9000);
    // Eskiden başlıktaki 8 düğme tek satıra sığmıyor, balonun dışına taşıyordu.
    expect(tester.takeException(), isNull);
    expect(find.byTooltip('Kodi gitsin'), findsOneWidget);
    o.kodi.kapat();
    await _bekle(tester, 1000);
    await tester.pumpWidget(const SizedBox());
    await tester.pump(const Duration(seconds: 1));
  });

  testWidgets('Kodi izin verilince kodu editöre canlı yazar', (tester) async {
    final o = _Ortam();
    await tester.binding.setSurfaceSize(const Size(900, 760));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    await tester.pumpWidget(o.sar(const SizedBox.expand(child: app.KodiKatmani())));
    final editor = TextEditingController();
    addTearDown(editor.dispose);
    o.ed.uiController = editor; // editörün yazı denetçisi yerine
    o.kodi.ac();
    await tester.pump();
    await _bekle(tester, 9000);

    final kod = List.generate(40, (i) => 'yazdır($i)').join('\n');
    o.kodi.mesajlar.add(app.KodiMesaji(true, 'Kodun hazır! Nereye yazayım?', eylemler: [
      app.KodiEylemi('kod_yaz',
          {'eylem': 'kod_yaz', 'hedef': 'yeni_sekme', 'ad': 'canli.trpy', 'kod': kod}),
    ]));
    o.kodi.yenile();
    await _bekle(tester, 2000);
    // Kod sohbette gösterilmez; önce izin istenir.
    expect(_yazi('yazdır(39)'), findsNothing);
    expect(_yazi('Bu kodu (40 satır) senin için yazayım mı?'), findsOneWidget);

    await tester.tap(find.text('Yeni sekmede aç').first);
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));
    // Yazılıyor: kodun bir kısmı editörde, tamamı değil.
    expect(editor.text.length, inExclusiveRange(0, kod.length));
    expect(kod.startsWith(editor.text), isTrue);
    await _bekle(tester, 4000);
    expect(editor.text, kod);
    expect(o.ed.activeTab?.name, 'canli.trpy');
    expect(o.ed.activeTab?.content, kod);
    expect(_yazi('Kod yeni bir sekmeye yazıldı'), findsOneWidget);
    expect(tester.takeException(), isNull);

    o.kodi.kapat();
    await _bekle(tester, 1000);
    await tester.pumpWidget(const SizedBox());
    await tester.pump(const Duration(seconds: 1));
  });

  testWidgets('Kodi her yüz, poz, hareket ve efektle çizilir', (tester) async {
    await tester.pumpWidget(MaterialApp(
      home: Scaffold(
        body: SingleChildScrollView(
          child: Wrap(children: [
            for (final p in app.KodiPozu.values)
              app.KodiRobotu(boy: 40, poz: p, solaBak: p == app.KodiPozu.dusun),
            for (final h in app.KodiHareketi.values) app.KodiRobotu(boy: 40, hareket: h),
            for (final e in app.KodiEfekti.values) app.KodiRobotu(boy: 40, efekt: e),
            for (final i in app.KodiIfadesi.values)
              app.KodiRobotu(boy: 40, ifade: i, konusuyor: true, efekt: app.KodiEfekti.zzz),
          ]),
        ),
      ),
    ));
    // Hareketlerin bütün evreleri (dönen zaman 2,6 sn).
    for (var i = 0; i < 14; i++) {
      await tester.pump(const Duration(milliseconds: 200));
    }
    expect(tester.takeException(), isNull);
    await tester.pumpWidget(const SizedBox());
  });

  test('Kodi hâli motorun adlarından okunur, bilinmeyen atılır', () {
    final h = app.KodiHali.jsondan({
      'yuz': 'goz_kirp',
      'poz': 'sola_goster',
      'hareket': 'ejderha',
      'efekt': 'kalpler',
    })!;
    expect(h.yuz, app.KodiIfadesi.gozKirp);
    expect(h.poz, app.KodiPozu.solaGoster);
    expect(h.hareket, isNull);
    expect(h.efekt, app.KodiEfekti.kalpler);
    expect(h.json(), {'yuz': 'goz_kirp', 'poz': 'sola_goster', 'efekt': 'kalpler'});
    // Konuşma ve dinleme yüzünü program seçer; hiçbiri geçerli değilse hâl yok.
    expect(app.KodiHali.jsondan({'yuz': 'konusuyor'}), isNull);
    expect(app.KodiHali.jsondan('mutlu'), isNull);
    expect(app.KodiHali.jsondan(null), isNull);
  });

  test('Kodi hâli sohbetle kaydedilir; eski kayıt bozulmaz', () {
    final m = app.KodiMesaji(true, 'Yaşasın!',
        ifade: const app.KodiHali(yuz: app.KodiIfadesi.heyecanli, efekt: app.KodiEfekti.konfeti));
    final geri = app.KodiMesaji.jsondan(m.json());
    expect(geri.ifade?.yuz, app.KodiIfadesi.heyecanli);
    expect(geri.ifade?.efekt, app.KodiEfekti.konfeti);
    final eski = app.KodiMesaji.jsondan({'kodiden': true, 'metin': 'Selam', 'eylemler': []});
    expect(eski.ifade, isNull);
    expect(eski.json().containsKey('ifade'), isFalse);
  });

  testWidgets('Yapay zekânın seçtiği hâl gösterilir, sonra Kodi normale döner ve uyuklar',
      (tester) async {
    final sahte = _SahteBackend();
    final o = _Ortam(sahte);
    await tester.binding.setSurfaceSize(const Size(1000, 760));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    await tester.pumpWidget(o.sar(const SizedBox.expand(child: app.KodiKatmani())));
    o.kodi.ac();
    await tester.pump();
    await _bekle(tester, 9000); // selam bitsin
    app.KodiRobotu robot() => tester.widget<app.KodiRobotu>(find.byType(app.KodiRobotu));

    await tester.tap(find.text('Kitapta döngüler nerede?'));
    await tester.pump();
    expect(robot().ifade, app.KodiIfadesi.dusunceli);
    sahte.cevap.complete({
      'ok': true,
      'cevap': 'Döngüler kitabın beşinci bölümünde, hadi bakalım!',
      'eylemler': [],
      'ifade': {'yuz': 'heyecanli', 'poz': 'zafer', 'hareket': 'zipla', 'efekt': 'konfeti'},
    });
    await _bekle(tester, 300);
    // Cevap yazılırken seçilen yüzle konuşur.
    expect(robot().ifade, app.KodiIfadesi.heyecanli);
    expect(robot().konusuyor, isTrue);
    expect(robot().poz, app.KodiPozu.zafer);
    expect(robot().hareket, app.KodiHareketi.zipla);
    expect(robot().efekt, app.KodiEfekti.konfeti);
    // Yazma bitince bir süre o hâlde kalır.
    await _bekle(tester, 4000);
    expect(robot().konusuyor, isFalse);
    expect(robot().poz, app.KodiPozu.zafer);
    // Sonra normale döner.
    await _bekle(tester, 7000);
    expect(robot().ifade, app.KodiIfadesi.mutlu);
    expect(robot().poz, app.KodiPozu.normal);
    expect(robot().efekt, app.KodiEfekti.yok);
    // Uzun süre bir şey olmazsa uyuklar.
    await tester.pump(const Duration(minutes: 2, seconds: 1));
    await tester.pump();
    expect(robot().ifade, app.KodiIfadesi.uykulu);
    expect(robot().efekt, app.KodiEfekti.zzz);
    expect(tester.takeException(), isNull);
    await tester.pumpWidget(const SizedBox());
    await tester.pump(const Duration(seconds: 1));
  });

  app.KodiRessami ressam(WidgetTester tester) => tester
      .widget<CustomPaint>(find.descendant(
          of: find.byType(app.KodiRobotu), matching: find.byType(CustomPaint)))
      .painter! as app.KodiRessami;

  testWidgets('Kodi bir hâlden ötekine yumuşakça geçer', (tester) async {
    Widget robot(app.KodiIfadesi i, app.KodiPozu p) =>
        MaterialApp(home: Center(child: app.KodiRobotu(ifade: i, poz: p)));
    await tester.pumpWidget(robot(app.KodiIfadesi.mutlu, app.KodiPozu.normal));
    await tester.pump(const Duration(milliseconds: 100));
    expect(ressam(tester).gecis, 1);

    await tester.pumpWidget(robot(app.KodiIfadesi.heyecanli, app.KodiPozu.zafer));
    await tester.pump(const Duration(milliseconds: 150));
    // Geçiş sürüyor: eski hâl yeni hâle karışıyor.
    final r = ressam(tester);
    expect(r.gecis, inExclusiveRange(0.0, 1.0));
    expect(r.oncekiIfade, app.KodiIfadesi.mutlu);
    expect(r.oncekiPoz, app.KodiPozu.normal);
    expect(r.ifade, app.KodiIfadesi.heyecanli);
    expect(r.poz, app.KodiPozu.zafer);
    await tester.pump(const Duration(milliseconds: 400));
    expect(ressam(tester).gecis, 1);

    // Düşünürken pencerenin ortasına dönerken de bir anda aynalanmaz.
    await tester.pumpWidget(const MaterialApp(
        home: Center(
            child: app.KodiRobotu(ifade: app.KodiIfadesi.dusunceli, solaBak: true))));
    await tester.pump(const Duration(milliseconds: 200));
    expect(ressam(tester).ayna, inExclusiveRange(-1.0, 1.0));
    await tester.pump(const Duration(milliseconds: 400));
    expect(ressam(tester).ayna, -1);
    expect(tester.takeException(), isNull);
    await tester.pumpWidget(const SizedBox());
  });

  testWidgets('Gösteriler oynar ve biter', (tester) async {
    for (final g in app.KodiGosterisi.values) {
      await tester.pumpWidget(MaterialApp(
          home: Center(child: app.KodiRobotu(key: ValueKey(g), gosteri: g, gosteriNo: 1))));
      await tester.pump(const Duration(milliseconds: 60));
      final h = g.hal;
      if (h.yuz != null) expect(ressam(tester).ifade, h.yuz, reason: '$g');
      for (var i = 0; i < 12; i++) {
        await tester.pump(const Duration(milliseconds: 100));
      }
      // Gösteri bitince Kodi her zamanki hâline döner.
      await tester.pump(const Duration(milliseconds: 600));
      expect(ressam(tester).ifade, app.KodiIfadesi.mutlu, reason: '$g');
      expect(ressam(tester).poz, app.KodiPozu.normal, reason: '$g');
      expect(tester.takeException(), isNull, reason: '$g');
    }
    await tester.pumpWidget(const SizedBox());
  });

  testWidgets('Kodi boşta kendi kendine kıpırdanır, sonra dinlenir', (tester) async {
    await tester.pumpWidget(
        const MaterialApp(home: Center(child: app.KodiRobotu(kipirdan: true))));
    var kipirdadi = 0;
    var oncekiBos = true;
    for (var i = 0; i < 1200; i++) {
      await tester.pump(const Duration(milliseconds: 250));
      final r = ressam(tester);
      final bos = r.ifade == app.KodiIfadesi.mutlu &&
          r.poz == app.KodiPozu.normal &&
          r.hareket == app.KodiHareketi.yok &&
          r.efekt == app.KodiEfekti.yok &&
          r.bakis == Offset.zero;
      if (oncekiBos && !bos) kipirdadi++;
      oncekiBos = bos;
    }
    // 5 dakikada en çok 8 kez kıpırdanır (bilgisayarı yormasın), hiç değilse
    // birkaç kez.
    expect(kipirdadi, inInclusiveRange(3, 8));
    expect(tester.takeException(), isNull);
    await tester.pumpWidget(const SizedBox());
  });

  testWidgets('Kodi gelince zıplar, bırakılınca yere yaylanarak iner', (tester) async {
    final o = _Ortam();
    await tester.binding.setSurfaceSize(const Size(900, 700));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    await tester.pumpWidget(o.sar(const SizedBox.expand(child: app.KodiKatmani())));
    o.kodi.ac();
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 800)); // kayma bitti
    await tester.pump(const Duration(milliseconds: 200));
    expect(tester.widget<app.KodiRobotu>(find.byType(app.KodiRobotu)).gosteri,
        app.KodiGosterisi.gel);
    expect(ressam(tester).ifade, app.KodiIfadesi.heyecanli);
    await _bekle(tester, 6000);

    // Sürüklenirken havada şaşırır, kollarını açar.
    final robot = tester.getCenter(find.byType(app.KodiRobotu));
    final g = await tester.startGesture(robot);
    await g.moveBy(const Offset(-40, -30));
    await tester.pump(const Duration(milliseconds: 500));
    expect(ressam(tester).ifade, app.KodiIfadesi.saskin);
    expect(ressam(tester).poz, app.KodiPozu.zafer);
    await g.moveBy(const Offset(-80, -40));
    await g.up();
    await tester.pump(const Duration(milliseconds: 60));
    expect(tester.widget<app.KodiRobotu>(find.byType(app.KodiRobotu)).gosteri,
        app.KodiGosterisi.yereIn);
    await _bekle(tester, 1200);
    expect(ressam(tester).ifade, isNot(app.KodiIfadesi.saskin));
    expect(tester.takeException(), isNull);
    o.kodi.kapat();
    await _bekle(tester, 1500);
  });

  testWidgets('Emojili cevap harf harf yazılırken emoji bölünmez', (tester) async {
    // Eskiden yazı emojinin ortasından kesiliyor, Flutter "string is not
    // well-formed UTF-16" hatası veriyordu.
    final sahte = _SahteBackend();
    final o = _Ortam(sahte);
    await tester.binding.setSurfaceSize(const Size(1000, 760));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    await tester.pumpWidget(o.sar(const SizedBox.expand(child: app.KodiKatmani())));
    o.kodi.ac();
    await tester.pump();
    await _bekle(tester, 9000); // selam bitsin
    await tester.tap(find.text('Kitapta döngüler nerede?'));
    await tester.pump();
    sahte.cevap.complete({
      'ok': true,
      'cevap': '🌟 Sürpriz: Mor Yıldız Yağmuru! 🌟🎨 **Hadi** 👍🏽 bakalım 👨‍👩‍👧',
      'eylemler': [],
    });
    for (var i = 0; i < 200; i++) {
      await tester.pump(const Duration(milliseconds: 7));
      expect(tester.takeException(), isNull, reason: '$i. karede');
    }
    await _bekle(tester, 2000);
    expect(_yazi('bakalım 👨‍👩‍👧'), findsOneWidget);
    o.kodi.kapat();
    await _bekle(tester, 1500);
  });

  test('Yarım metin emojiyi bölmez', () {
    const s = 'a🌟b';
    expect(app.kodiYarimMetin(s, 0), '');
    expect(app.kodiYarimMetin(s, 1), 'a');
    expect(app.kodiYarimMetin(s, 2), 'a🌟'); // emojinin yarısı değil tamamı
    expect(app.kodiYarimMetin(s, 3), 'a🌟');
    expect(app.kodiYarimMetin(s, 99), s);
    expect(app.kodiYarimMetin('Türkçe', 3), 'Tür');
  });

  test('Silüet: boyalı yerleri birleşik dikdörtgenlerle kaplar', () {
    // 6x4 resim: (1..2, 0..1) kare ve (4, 3) tek nokta boyalı.
    const w = 6, h = 4;
    final rgba = Uint8List(w * h * 4);
    void boya(int x, int y) => rgba[(y * w + x) * 4 + 3] = 255;
    boya(1, 0);
    boya(2, 0);
    boya(1, 1);
    boya(2, 1);
    boya(4, 3);
    rgba[(3 * w + 0) * 4 + 3] = 10; // eşiğin altında: boş sayılır
    final r = app.kodiSilueti(rgba, w, h, hucre: 2, genislet: 0);
    expect(r, unorderedEquals([
      const Rect.fromLTRB(2, 0, 6, 4), // iki satır tek dikdörtgen
      const Rect.fromLTRB(8, 6, 10, 8),
    ]));
    // Genişletince kenarlar da kaplanır.
    final g = app.kodiSilueti(rgba, w, h, genislet: 1);
    bool kapli(double x, double y) => g.any((d) => d.contains(Offset(x, y)));
    expect(kapli(0.5, 2.5), isTrue);
    expect(kapli(5.5, 0.5), isFalse);
    expect(app.kodiSilueti(Uint8List(0), 0, 0), isEmpty);
  });

  testWidgets('Gerçek Kodi çiziminin silüeti kutusundan küçüktür', (tester) async {
    final anahtar = GlobalKey();
    await tester.pumpWidget(MaterialApp(
        home: Center(child: app.KodiRobotu(key: anahtar, boy: 130))));
    await tester.pump(const Duration(milliseconds: 100));
    final rb = tester.renderObject<RenderRepaintBoundary>(find.descendant(
        of: find.byKey(anahtar), matching: find.byType(RepaintBoundary)).first);
    late List<Rect> siluet;
    await tester.runAsync(() async {
      final resim = rb.toImageSync(pixelRatio: 0.5);
      final veri = await resim.toByteData(format: ui.ImageByteFormat.rawRgba);
      siluet = app.kodiSilueti(veri!.buffer.asUint8List(), resim.width, resim.height, hucre: 2);
      resim.dispose();
    });
    final kutu = Offset.zero & rb.size;
    final alan = siluet.fold<double>(0, (t, r) => t + r.width * r.height);
    final oran = alan / (kutu.width * kutu.height);
    expect(oran, inExclusiveRange(0.3, 0.85));
    bool kapli(Offset o) => siluet.any((r) => r.contains(o));
    // Kafa ve gövde kesilir; kutunun köşeleri (boşluk) kesilmez.
    expect(kapli(Offset(kutu.width / 2, kutu.height * 0.3)), isTrue);
    expect(kapli(Offset(kutu.width / 2, kutu.height * 0.65)), isTrue);
    expect(kapli(const Offset(2, 2)), isFalse);
    expect(kapli(Offset(kutu.width - 2, 2)), isFalse);
    await tester.pumpWidget(const SizedBox());
  });

  test('Tarayıcı kimliğinden Edge işareti çıkar', () {
    const edge = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
        '(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.2903.86';
    expect(app.kromKimligi(edge),
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
        '(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36');
    const krom = 'Mozilla/5.0 (X11) Chrome/131.0.0.0 Safari/537.36';
    expect(app.kromKimligi(krom), krom);
  });
}
