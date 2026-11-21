// Entegrasyon testlerinin ortak yardımcıları (Windows, Linux, macOS).
//
// - Kısayollar: TürKod'un kısayolları macOS'ta Ctrl yerine Cmd ile çalışır
//   (lib/platform_ayarlari.dart: platformKisayolu).
// - Menüler: bir menü kapanırken (animasyon) ikincisine tıklanırsa tıklama menünün
//   arka planına gider ve hiçbir şey açılmaz. Ekranın yazılımla çizildiği
//   makinelerde (CI, Linux Xvfb) animasyon yavaştır; sabit süre beklemek yerine
//   menünün gerçekten açılması / kapanması beklenir.
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';

/// Kısayolların ana değiştirici tuşu: macOS'ta Cmd, diğerlerinde Ctrl.
LogicalKeyboardKey get kisayolTusu =>
    Platform.isMacOS ? LogicalKeyboardKey.metaLeft : LogicalKeyboardKey.controlLeft;

/// Menüde görünen adı: "Cmd" ya da "Ctrl" (ör. "$kisayolAdi+W").
String get kisayolAdi => Platform.isMacOS ? 'Cmd' : 'Ctrl';

/// Ekranda açık (ya da kapanmakta olan) menünün öğeleri.
Finder get acikMenuOgeleri => find.byWidgetPredicate((w) => w is PopupMenuItem);

Future<void> _adim(WidgetTester t) async {
  await t.pump(const Duration(milliseconds: 100));
  await Future<void>.delayed(const Duration(milliseconds: 100));
}

/// Açık menüyü kapatır ve tamamen kapanana dek bekler (en çok ~10 sn).
Future<void> menuyuKapat(WidgetTester t) async {
  if (acikMenuOgeleri.evaluate().isEmpty) return;
  await t.sendKeyEvent(LogicalKeyboardKey.escape);
  for (var i = 0; i < 50; i++) {
    await _adim(t);
    if (acikMenuOgeleri.evaluate().isEmpty) return;
    // Esc yetmediyse menünün arka planına (sol üst köşe) dokunulur.
    if (i == 15) await t.tapAt(const Offset(2, 2));
  }
}

/// Önce açık menüyü kapatır, sonra [ad] menüsünü açar ve öğeleri görünene dek bekler.
Future<void> menuyuAc(WidgetTester t, String ad) async {
  await menuyuKapat(t);
  await t.tap(find.text(ad).first);
  for (var i = 0; i < 50; i++) {
    await _adim(t);
    if (acikMenuOgeleri.evaluate().isNotEmpty) break;
  }
  // Açılış animasyonu bitsin: öğelere ancak yerleştikten sonra tıklanabilir.
  for (var i = 0; i < 4; i++) {
    await _adim(t);
  }
}
