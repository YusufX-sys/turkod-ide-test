// Kodi'nin hâli: pozları, hareketleri ve çevresindeki efektler. Yapay zekâ
// her cevabında {"eylem": "ifade", "yuz": ..., "poz": ..., "hareket": ...,
// "efekt": ...} yazarak seçer (motor bunu cevabın "ifade" alanı yapar).
// Adlar motordaki (turkod_ide/kodi.py: KODI_YUZLERI ...) adlarla aynıdır.
// Yüz ifadelerinin çizimi KodiRessami'de (kodi.dart).

part of 'main.dart';

enum KodiPozu {
  normal,
  elSalla,
  dusun,
  zafer,
  basparmak,
  solaGoster,
  sagaGoster,
  omuzSilk,
  alkis,
  ellerBelde,
  yuzKapa,
}

enum KodiHareketi { yok, zipla, dans, don, titre, selam, salla }

enum KodiEfekti { yok, konfeti, kalpler, yildizlar, soru, unlem, zzz, nota }

/// "goz_kirp" → "gozKirp" (Dart adı).
String _deveHorgucu(String ad) {
  final parcalar = ad.split('_');
  return parcalar.first +
      [for (final p in parcalar.skip(1)) if (p.isNotEmpty) p[0].toUpperCase() + p.substring(1)]
          .join();
}

/// "gozKirp" → "goz_kirp" (motordaki ad).
String _yilanAdi(String ad) =>
    ad.replaceAllMapped(RegExp('[A-Z]'), (m) => '_${m[0]!.toLowerCase()}');

T? _addanBul<T extends Enum>(List<T> degerler, Object? ad) {
  if (ad == null) return null;
  final aranan = _deveHorgucu(ad.toString().trim());
  for (final d in degerler) {
    if (d.name == aranan) return d;
  }
  return null;
}

/// Yapay zekânın seçtiği hâl. Boş alan: o konuda program karar verir.
class KodiHali {
  final KodiIfadesi? yuz;
  final KodiPozu? poz;
  final KodiHareketi? hareket;
  final KodiEfekti? efekt;
  const KodiHali({this.yuz, this.poz, this.hareket, this.efekt});

  bool get bos => yuz == null && poz == null && hareket == null && efekt == null;

  /// Motorun gönderdiği sözlükten; bilinmeyen adlar atılır. Hiçbiri geçerli
  /// değilse null.
  static KodiHali? jsondan(Object? m) {
    if (m is! Map) return null;
    final h = KodiHali(
      // Konuşma ve dinleme yüzünü program seçer.
      yuz: switch (_addanBul(KodiIfadesi.values, m['yuz'])) {
        KodiIfadesi.konusuyor || KodiIfadesi.dinliyor => null,
        final y => y,
      },
      poz: _addanBul(KodiPozu.values, m['poz']),
      hareket: _addanBul(KodiHareketi.values, m['hareket']),
      efekt: _addanBul(KodiEfekti.values, m['efekt']),
    );
    return h.bos ? null : h;
  }

  Map<String, dynamic> json() => {
        if (yuz != null) 'yuz': _yilanAdi(yuz!.name),
        if (poz != null) 'poz': _yilanAdi(poz!.name),
        if (hareket != null) 'hareket': _yilanAdi(hareket!.name),
        if (efekt != null) 'efekt': _yilanAdi(efekt!.name),
      };
}

// ---------------------------------------------------------------------------
// Çizim yardımcıları (100 x 130'luk Kodi kutusunun birimleriyle)
// ---------------------------------------------------------------------------

const _kKonfetiRenkleri = [
  Color(0xFFF472B6),
  Color(0xFF22D3EE),
  Color(0xFFFACC15),
  Color(0xFF4ADE80),
  Color(0xFFA78BFA),
  Color(0xFFFB923C),
];

Path _yildizYolu(Offset m, double r, {double ic = 0.45}) {
  final p = Path();
  for (var i = 0; i < 10; i++) {
    final a = -math.pi / 2 + i * math.pi / 5;
    final rr = i.isEven ? r : r * ic;
    final n = m + Offset(math.cos(a), math.sin(a)) * rr;
    if (i == 0) {
      p.moveTo(n.dx, n.dy);
    } else {
      p.lineTo(n.dx, n.dy);
    }
  }
  return p..close();
}

Path _kalpYolu(Offset m, double r) {
  // r: kalbin yarı genişliği.
  final p = Path()
    ..moveTo(m.dx, m.dy + r * 0.9)
    ..cubicTo(m.dx - r * 1.3, m.dy + r * 0.1, m.dx - r * 0.9, m.dy - r * 1.0, m.dx,
        m.dy - r * 0.35)
    ..cubicTo(m.dx + r * 0.9, m.dy - r * 1.0, m.dx + r * 1.3, m.dy + r * 0.1, m.dx,
        m.dy + r * 0.9)
    ..close();
  return p;
}

/// Müzik notası (♪): yuvarlak baş, sap ve bayrak.
void _notaCiz(Canvas c, Offset bas, double s, Paint boya, {bool cift = false}) {
  c.save();
  c.translate(bas.dx, bas.dy);
  c.scale(s);
  c.save();
  c.rotate(-0.35);
  c.drawOval(Rect.fromCenter(center: Offset.zero, width: 6, height: 4.4), boya);
  c.restore();
  final cizgi = Paint()
    ..color = boya.color
    ..strokeWidth = 1.3
    ..strokeCap = StrokeCap.round;
  c.drawLine(const Offset(2.6, -0.6), const Offset(2.6, -11), cizgi);
  if (cift) {
    c.save();
    c.translate(7, -2.5);
    c.rotate(-0.35);
    c.drawOval(Rect.fromCenter(center: Offset.zero, width: 6, height: 4.4), boya);
    c.restore();
    c.drawLine(const Offset(9.6, -3.1), const Offset(9.6, -13.5), cizgi);
    c.drawLine(const Offset(2.6, -11), const Offset(9.6, -13.5), cizgi..strokeWidth = 2.4);
  } else {
    final bayrak = Path()
      ..moveTo(2.6, -11)
      ..quadraticBezierTo(7, -9, 6.2, -4.5);
    c.drawPath(
        bayrak,
        Paint()
          ..color = boya.color
          ..style = PaintingStyle.stroke
          ..strokeWidth = 1.3
          ..strokeCap = StrokeCap.round);
  }
  c.restore();
}

final Map<String, TextPainter> _efektYazilari = {};

TextPainter _efektYazisi(String yazi, double boy, Color renk) {
  return _efektYazilari.putIfAbsent(
      '$yazi|$boy|${renk.toARGB32()}',
      () => TextPainter(
            text: TextSpan(
                text: yazi,
                style: TextStyle(
                    color: renk,
                    fontSize: boy,
                    fontWeight: FontWeight.w900,
                    fontFamily: kMonoFontFamily)),
            textDirection: TextDirection.ltr,
          )..layout());
}

/// Kodi'nin çevresindeki efekt. [t]: 0-1 dönen zaman. Robotun dönüşünden
/// bağımsız çizilir (konfeti dans ederken de yukarıdan yağar).
void _kodiEfektiCiz(Canvas c, KodiEfekti efekt, double t) {
  switch (efekt) {
    case KodiEfekti.yok:
      return;
    case KodiEfekti.konfeti:
      for (var i = 0; i < 16; i++) {
        final faz = (t + i * 0.137) % 1.0;
        final x = (i * 37 + 9) % 104 - 2 + math.sin((faz + i) * 2 * math.pi) * 4;
        final y = -8 + faz * 128;
        c.save();
        c.translate(x, y);
        c.rotate((faz * 4 + i) * math.pi);
        c.drawRect(
            const Rect.fromLTWH(-1.8, -1, 3.6, 2.2),
            Paint()
              ..color = _kKonfetiRenkleri[i % _kKonfetiRenkleri.length]
                  .withValues(alpha: faz > 0.85 ? (1 - faz) / 0.15 : 1));
        c.restore();
      }
    case KodiEfekti.kalpler:
      for (var i = 0; i < 4; i++) {
        final faz = (t + i * 0.25) % 1.0;
        final x = (i.isEven ? 8.0 : 92.0) + math.sin(faz * 2 * math.pi + i) * 4;
        final y = 70 - faz * 68;
        final a = faz < 0.15 ? faz / 0.15 : (1 - faz) / 0.85;
        c.drawPath(_kalpYolu(Offset(x, y), 3.2 + faz * 2),
            Paint()..color = _kKodiPembe.withValues(alpha: a.clamp(0.0, 1.0)));
      }
    case KodiEfekti.yildizlar:
      const yerler = [Offset(9, 18), Offset(91, 14), Offset(4, 52), Offset(96, 48), Offset(50, -4)];
      for (var i = 0; i < yerler.length; i++) {
        final p = 0.5 + 0.5 * math.sin((t * 2 + i * 0.2) * 2 * math.pi);
        c.drawPath(_yildizYolu(yerler[i], 1.5 + 3 * p),
            Paint()..color = const Color(0xFFFACC15).withValues(alpha: 0.35 + 0.65 * p));
      }
    case KodiEfekti.soru:
    case KodiEfekti.unlem:
      final yazi = _efektYazisi(
          efekt == KodiEfekti.soru ? '?' : '!',
          20,
          efekt == KodiEfekti.soru ? _kKodiCamgobegi : const Color(0xFFFACC15));
      final zip = efekt == KodiEfekti.unlem
          ? 1 + 0.18 * math.max(0.0, math.sin(t * 2 * math.pi * 2))
          : 1.0;
      final oy = efekt == KodiEfekti.soru ? math.sin(t * 2 * math.pi) * 2 : 0.0;
      c.save();
      c.translate(88, 6 + oy);
      c.rotate(efekt == KodiEfekti.soru ? 0.18 : 0);
      c.scale(zip);
      yazi.paint(c, Offset(-yazi.width / 2, -yazi.height / 2));
      c.restore();
    case KodiEfekti.zzz:
      for (var i = 0; i < 3; i++) {
        final faz = (t + i / 3) % 1.0;
        final yazi = _efektYazisi('z', 8 + i * 2.5, _kKodiCamgobegi);
        final a = faz < 0.2 ? faz / 0.2 : (1 - faz) / 0.8;
        c.save();
        c.translate(74 + faz * 18, 14 - faz * 22);
        c.scale(0.6 + faz * 0.6);
        c.saveLayer(null, Paint()..color = Colors.white.withValues(alpha: a.clamp(0.0, 1.0)));
        yazi.paint(c, Offset(-yazi.width / 2, -yazi.height / 2));
        c.restore();
        c.restore();
      }
    case KodiEfekti.nota:
      for (var i = 0; i < 3; i++) {
        final faz = (t + i / 3) % 1.0;
        final sol = i == 1;
        final x = (sol ? 10.0 : 88.0) + math.sin(faz * 2 * math.pi * 2) * 3;
        final y = 60 - faz * 60;
        final a = faz < 0.15 ? faz / 0.15 : (1 - faz) / 0.85;
        _notaCiz(c, Offset(x, y), 1.0,
            Paint()
              ..color = (i == 2 ? _kKodiPembe : _kKodiCamgobegi)
                  .withValues(alpha: a.clamp(0.0, 1.0)),
            cift: i == 2);
      }
  }
}


/// Hareketin robotu yerinden oynatması (gölge hariç). [guc] 0-1: hareket
/// başlarken ve biterken yavaşça büyüyüp söner (bir anda başlamasın,
/// bir anda durmasın). Robotun gölgesi [golgeKucul] kadar küçülür.
({double golgeKucul}) _kodiHareketiUygula(Canvas c, KodiHareketi h, double t,
    {double guc = 1}) {
  if (guc <= 0) return (golgeKucul: 0);
  final dalga = math.sin(t * 2 * math.pi);
  switch (h) {
    case KodiHareketi.yok:
      return (golgeKucul: 0);
    case KodiHareketi.zipla:
      final y = math.sin(t * 2 * math.pi * 2).abs() * 11 * guc;
      c.translate(0, -y);
      return (golgeKucul: y * 1.4);
    case KodiHareketi.dans:
      final d = math.sin(t * 2 * math.pi * 2) * guc;
      c.translate(50 + d * 4, 118);
      c.rotate(d * 0.16);
      c.translate(-50, -118 - math.sin(t * 2 * math.pi * 4).abs() * 3 * guc);
      return (golgeKucul: 2 * guc);
    case KodiHareketi.don:
      // Hafifçe zıplayıp kendi çevresinde döner, kısa bir an durup yeniden
      // döner. Yatay döndüğü için kutusunun dışına taşmaz (masaüstü
      // penceresinde kutunun dışı kesilir).
      final a = t < 0.7 ? Curves.easeInOut.transform(t / 0.7) : 1.0;
      final y = math.sin(a * math.pi) * 8 * guc;
      final x = 1 + (math.cos(a * 2 * math.pi) - 1) * guc;
      c.translate(50, -y);
      c.scale(x.abs() < 0.12 ? 0.12 * (x < 0 ? -1 : 1) : x, 1);
      c.translate(-50, 0);
      return (golgeKucul: y * 1.5);
    case KodiHareketi.titre:
      c.translate(math.sin(t * 2 * math.pi * 13) * 1.6 * guc, 0);
      return (golgeKucul: 0);
    case KodiHareketi.selam:
      // Öne eğilip kalkar.
      final b = math.max(0.0, dalga) * guc;
      c.translate(50, 118);
      c.scale(1, 1 - 0.16 * b);
      c.translate(-50, -118);
      return (golgeKucul: 0);
    case KodiHareketi.salla:
      c.translate(50, 118);
      c.rotate(dalga * 0.09 * guc);
      c.translate(-50, -118);
      return (golgeKucul: 0);
  }
}

/// Bir kol: omuz → dirsek → el (her zaman üç nokta: pozlar arasında nokta
/// nokta geçilebilsin). [onde]: gövdenin önünde mi?
class _Kol {
  final List<Offset> noktalar;
  final bool basparmak;
  final bool isaret; // işaret parmağı uzatılmış
  final double el;
  final bool onde;
  const _Kol(this.noktalar,
      {this.basparmak = false, this.isaret = false, this.el = 5.5, this.onde = false});

  /// Düz kol: dirsek omuzla elin ortasında.
  _Kol.duz(Offset omuz, Offset uc, {this.isaret = false})
      : noktalar = [omuz, Offset.lerp(omuz, uc, 0.5)!, uc],
        basparmak = false,
        el = 5.5,
        onde = false;

  /// İki kol arasındaki ara duruş ([k]: 0 → a, 1 → b).
  static _Kol karisim(_Kol a, _Kol b, double k) => _Kol(
        [for (var i = 0; i < 3; i++) Offset.lerp(a.noktalar[i], b.noktalar[i], k)!],
        basparmak: k < 0.35 ? a.basparmak : (k > 0.65 && b.basparmak),
        isaret: k < 0.35 ? a.isaret : (k > 0.65 && b.isaret),
        el: a.el + (b.el - a.el) * k,
        onde: k < 0.5 ? a.onde : b.onde,
      );
}

/// Pozun kolları: [sol kol, sağ kol]. Sağ kol solun üstüne çizilir.
List<_Kol> _kodiPozKollari(KodiPozu poz, double t) {
  const solOmuz = Offset(26, 74);
  const sagOmuz = Offset(74, 74);
  final s = math.sin(t * 2 * math.pi);
  final solNormal = _Kol.duz(solOmuz, Offset(13, 93 + s * 1.5));
  final sagNormal = _Kol.duz(sagOmuz, Offset(87, 93 - s * 1.5));
  switch (poz) {
    case KodiPozu.normal:
      return [solNormal, sagNormal];
    case KodiPozu.elSalla:
      final aci = -1.25 + math.sin(t * 4 * math.pi) * 0.38;
      return [solNormal, _Kol.duz(sagOmuz, sagOmuz + Offset(math.cos(aci), math.sin(aci)) * 26)];
    case KodiPozu.dusun:
      // Sağ elin dirseği sol elde, sağ el çenede (parmaklarıyla çenesine
      // hafifçe vurur). Kollar gövdenin ve başın önündedir.
      final vurus = math.max(0.0, math.sin(t * 2 * math.pi * 3)) * 1.6;
      return [
        const _Kol([Offset(26, 75), Offset(31, 96), Offset(61, 99)], onde: true),
        _Kol([const Offset(74, 75), const Offset(63, 95), Offset(56.5, 63.5 - vurus)],
            onde: true),
      ];
    case KodiPozu.zafer:
      final k = math.sin(t * 2 * math.pi * 3) * 2.5;
      return [
        _Kol([solOmuz, const Offset(15, 62), Offset(9 - k * 0.3, 44 + k)]),
        _Kol([sagOmuz, const Offset(85, 62), Offset(91 + k * 0.3, 44 - k)]),
      ];
    case KodiPozu.basparmak:
      final k = math.max(0.0, math.sin(t * 2 * math.pi * 2)) * 2;
      return [
        solNormal,
        _Kol([sagOmuz, const Offset(88, 86), Offset(84, 72 - k)], basparmak: true),
      ];
    case KodiPozu.solaGoster:
      final k = math.sin(t * 2 * math.pi * 2) * 1.5;
      return [_Kol.duz(solOmuz, Offset(3 + k, 68), isaret: true), sagNormal];
    case KodiPozu.sagaGoster:
      final k = math.sin(t * 2 * math.pi * 2) * 1.5;
      return [solNormal, _Kol.duz(sagOmuz, Offset(97 - k, 68), isaret: true)];
    case KodiPozu.omuzSilk:
      final k = math.max(0.0, math.sin(t * 2 * math.pi)) * 3;
      return [
        _Kol([solOmuz, Offset(13, 86 - k), Offset(6, 75 - k)]),
        _Kol([sagOmuz, Offset(87, 86 - k), Offset(94, 75 - k)]),
      ];
    case KodiPozu.alkis:
      final ac = 1.5 + 6 * math.sin(t * 2 * math.pi * 4).abs();
      return [
        _Kol([solOmuz, const Offset(20, 92), Offset(50 - ac, 80)], onde: true),
        _Kol([sagOmuz, const Offset(80, 92), Offset(50 + ac, 80)], onde: true),
      ];
    case KodiPozu.ellerBelde:
      // Hafifçe kalçasını sallar (dimdik durmasın).
      final k = s * 1.2;
      return [
        _Kol([solOmuz, Offset(11, 86 + k), Offset(25, 97 + k * 0.5)], onde: true),
        _Kol([sagOmuz, Offset(89, 86 - k), Offset(75, 97 - k * 0.5)], onde: true),
      ];
    case KodiPozu.yuzKapa:
      // Arada parmak arasından bakar (sağ el kayar).
      final bak = math.max(0.0, math.sin(t * 2 * math.pi)) * 7;
      return [
        const _Kol([Offset(26, 75), Offset(31, 93), Offset(40, 38)], el: 7.5, onde: true),
        _Kol([const Offset(74, 75), const Offset(69, 93), Offset(60 + bak, 38 + bak * 0.4)],
            el: 7.5, onde: true),
      ];
  }
}

void _kodiKollariCiz(Canvas c, Iterable<_Kol> kollar) {
  final kol = Paint()
    ..color = _kKodiMor
    ..strokeWidth = 7
    ..strokeCap = StrokeCap.round
    ..strokeJoin = StrokeJoin.round
    ..style = PaintingStyle.stroke;
  final golge = Paint()
    ..color = _kKodiMorKoyu
    ..strokeWidth = 8.5
    ..strokeCap = StrokeCap.round
    ..strokeJoin = StrokeJoin.round
    ..style = PaintingStyle.stroke;
  final elBoya = Paint()..color = _kKodiPembe;
  for (final k in kollar) {
    final yol = Path()..moveTo(k.noktalar.first.dx, k.noktalar.first.dy);
    for (final n in k.noktalar.skip(1)) {
      yol.lineTo(n.dx, n.dy);
    }
    // Önde duran kollar koyu kenarla gövdeden ayrılır.
    if (k.onde) c.drawPath(yol, golge);
    c.drawPath(yol, kol);
    final el = k.noktalar.last;
    final fark = el - k.noktalar[1];
    final yon = fark.distance < 0.01 ? const Offset(0, 1) : fark / fark.distance;
    if (k.isaret) {
      c.drawLine(
          el,
          el + yon * 8,
          Paint()
            ..color = _kKodiPembe
            ..strokeWidth = 3
            ..strokeCap = StrokeCap.round);
    }
    if (k.basparmak) {
      c.drawLine(
          el,
          el + const Offset(0, -8),
          Paint()
            ..color = _kKodiPembe
            ..strokeWidth = 3.4
            ..strokeCap = StrokeCap.round);
    }
    c.drawCircle(el, k.el, elBoya);
  }
}

// ---------------------------------------------------------------------------
// Gösteriler: bir kez oynayan kısa animasyonlar (gelme, gitme, masaüstü ...)
// ---------------------------------------------------------------------------

enum KodiGosterisi {
  /// Kayarak gelip zıplar, yere yaylanarak iner.
  gel,

  /// Gitmeden önce göz kırpıp el sallar.
  git,

  /// Sürüklenip bırakılınca yere yaylanarak iner.
  yereIn,

  /// Masaüstüne çıkarken havaya sıçrayıp dönerek küçülür (ışınlanır).
  masaustuneCik,

  /// Masaüstü penceresinde (ya da TürKod'a dönünce) pıt diye belirir.
  belir,
}

extension KodiGosterisiBilgisi on KodiGosterisi {
  Duration get sure => switch (this) {
        KodiGosterisi.gel => const Duration(milliseconds: 1100),
        KodiGosterisi.git => const Duration(milliseconds: 480),
        KodiGosterisi.yereIn => const Duration(milliseconds: 520),
        KodiGosterisi.masaustuneCik => const Duration(milliseconds: 420),
        KodiGosterisi.belir => const Duration(milliseconds: 900),
      };

  /// Gösteri sürerken Kodi'nin hâli (boş alan: değişmez).
  KodiHali get hal => switch (this) {
        KodiGosterisi.gel =>
          const KodiHali(yuz: KodiIfadesi.heyecanli, efekt: KodiEfekti.yildizlar),
        KodiGosterisi.git => const KodiHali(yuz: KodiIfadesi.gozKirp, poz: KodiPozu.elSalla),
        KodiGosterisi.yereIn => const KodiHali(),
        KodiGosterisi.masaustuneCik => const KodiHali(
            yuz: KodiIfadesi.heyecanli, poz: KodiPozu.zafer, efekt: KodiEfekti.yildizlar),
        KodiGosterisi.belir => const KodiHali(
            yuz: KodiIfadesi.heyecanli, poz: KodiPozu.zafer, efekt: KodiEfekti.yildizlar),
      };

  /// [p] (0-1) anında robotun yer değiştirmesi, ölçeği ve dönüşü (robot
  /// kutusunun birimiyle; ayakları yere basar).
  ({double dy, double sx, double sy, double donus, double saydam}) duzen(double p) {
    double tepe(double a, double b) => p <= a || p >= b ? 0 : math.sin((p - a) / (b - a) * math.pi);
    switch (this) {
      case KodiGosterisi.gel:
        // Zıplar (0-0,5), yere inince ezilir (0,5-0,72), hafifçe sekip durur.
        final ez = tepe(0.5, 0.72);
        return (
          dy: -tepe(0, 0.5) * 0.14 - tepe(0.72, 0.9) * 0.03,
          sx: 1 + ez * 0.1,
          sy: 1 - ez * 0.14,
          donus: 0,
          saydam: 1,
        );
      case KodiGosterisi.git:
        return (dy: -tepe(0.1, 0.6) * 0.04, sx: 1, sy: 1, donus: -tepe(0, 1) * 0.08, saydam: 1);
      case KodiGosterisi.yereIn:
        final ez = tepe(0, 0.45);
        final sek = tepe(0.45, 0.8);
        return (dy: -sek * 0.04, sx: 1 + ez * 0.12, sy: 1 - ez * 0.16 + sek * 0.04, donus: 0,
            saydam: 1);
      case KodiGosterisi.masaustuneCik:
        // Hafif çömelir, sıçrar, dönerek küçülüp kaybolur.
        final comel = tepe(0, 0.25);
        final u = p < 0.2 ? 0.0 : Curves.easeIn.transform((p - 0.2) / 0.8);
        return (
          dy: -u * 0.35,
          sx: (1 + comel * 0.1) * (1 - u * 0.85),
          sy: (1 - comel * 0.12) * (1 - u * 0.85),
          donus: u * math.pi * 1.5,
          saydam: 1 - Curves.easeIn.transform(u),
        );
      case KodiGosterisi.belir:
        final b = Curves.easeOutBack.transform(math.min(1.0, p / 0.6));
        final ez = tepe(0.6, 0.85);
        return (
          dy: 0,
          sx: (0.2 + 0.8 * b) * (1 + ez * 0.08),
          sy: (0.2 + 0.8 * b) * (1 - ez * 0.1),
          donus: (1 - math.min(1.0, p / 0.6)) * -0.8,
          saydam: math.min(1.0, p / 0.25),
        );
    }
  }
}

// ---------------------------------------------------------------------------
// Kıpırdanmalar: Kodi boşta dururken arada bir kendi kendine yaptığı şeyler
// ---------------------------------------------------------------------------

class _Kipirti {
  final String ad;
  final Duration sure;
  final KodiHali hal;

  /// Gözlerin nereye baktığı ([p]: 0-1; -1..1, sonunda 0'a döner).
  final Offset Function(double p)? bakis;
  const _Kipirti(this.ad, this.sure, this.hal, {this.bakis});
}

Offset _etrafaBak(double p) =>
    Offset(math.sin(p * 2 * math.pi) * (p < 0.5 ? 1 : 0.9), -0.25 * math.sin(p * math.pi));
Offset _asagiBak(double p) =>
    Offset(-0.8 * math.sin(p * math.pi), 0.75 * math.sin(p * math.pi));
Offset _yukariBak(double p) =>
    Offset(0.5 * math.sin(p * math.pi), -0.8 * math.sin(p * math.pi));

const _kKipirtilar = [
  _Kipirti('etrafa bakınır', Duration(milliseconds: 3000), KodiHali(), bakis: _etrafaBak),
  _Kipirti('koda göz atar', Duration(milliseconds: 2600), KodiHali(yuz: KodiIfadesi.merakli),
      bakis: _asagiBak),
  _Kipirti('gerinir', Duration(milliseconds: 2400),
      KodiHali(yuz: KodiIfadesi.uykulu, poz: KodiPozu.zafer)),
  _Kipirti('el sallar', Duration(milliseconds: 2000), KodiHali(poz: KodiPozu.elSalla)),
  _Kipirti('dans eder', Duration(milliseconds: 2600),
      KodiHali(hareket: KodiHareketi.dans, efekt: KodiEfekti.nota)),
  _Kipirti('zıplar', Duration(milliseconds: 1300),
      KodiHali(yuz: KodiIfadesi.heyecanli, hareket: KodiHareketi.zipla)),
  _Kipirti('göz kırpar', Duration(milliseconds: 1800),
      KodiHali(yuz: KodiIfadesi.gozKirp, poz: KodiPozu.basparmak)),
  _Kipirti('ıslık çalar', Duration(milliseconds: 2600),
      KodiHali(poz: KodiPozu.ellerBelde, hareket: KodiHareketi.salla, efekt: KodiEfekti.nota)),
  _Kipirti('düşünür', Duration(milliseconds: 2400),
      KodiHali(yuz: KodiIfadesi.merakli, poz: KodiPozu.dusun, efekt: KodiEfekti.soru),
      bakis: _yukariBak),
];
