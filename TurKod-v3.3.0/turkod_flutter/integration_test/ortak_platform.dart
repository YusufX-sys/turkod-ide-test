// Entegrasyon testlerinin sisteme göre değişen kısmı (Windows, Linux, macOS).
//
// TürKod'un kısayolları macOS'ta Ctrl yerine Cmd ile çalışır
// (lib/platform_ayarlari.dart: platformKisayolu). Testler kısayol basarken ve
// menüde kısayol metni ararken bu yardımcıları kullanır.
import 'dart:io';

import 'package:flutter/services.dart';

/// Kısayolların ana değiştirici tuşu: macOS'ta Cmd, diğerlerinde Ctrl.
LogicalKeyboardKey get kisayolTusu =>
    Platform.isMacOS ? LogicalKeyboardKey.metaLeft : LogicalKeyboardKey.controlLeft;

/// Menüde görünen adı: "Cmd" ya da "Ctrl" (ör. "$kisayolAdi+W").
String get kisayolAdi => Platform.isMacOS ? 'Cmd' : 'Ctrl';
