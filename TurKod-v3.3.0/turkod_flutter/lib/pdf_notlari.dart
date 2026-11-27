// PDF sekmesinde sayfaların üstüne eklenen notlar: kalemle çizgiler ve
// yazılar. PDF dosyasının kendisi hiç değişmez; notlar veri klasöründe
// (pdf_notlari/<anahtar>.json) ayrı tutulur. "İlk hâline döndür" bu notları
// siler. Geri al / yinele geçmişi program açık kaldıkça (sekme kapanıp
// açılsa da) korunur.
//
// Koordinatlar sayfa genişliğine bölünmüş sayılardır (x ve y ikisi de
// genişliğe göre): yakınlaştırma ne olursa olsun not sayfada aynı yerde
// durur. Kalınlık ve yazı boyutu da aynı ölçektedir.

import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:path/path.dart' as p;

import 'platform_ayarlari.dart';

/// Notların klasörü veri klasöründedir; otomatik testlerde (TURKOD_TEST_PROFIL)
/// kullanıcının gerçek notlarına dokunulmasın diye test klasörüne yönlenir.
String _notKoku() {
  final profil = Platform.environment['TURKOD_TEST_PROFIL'];
  return profil != null && profil.isNotEmpty ? profil : veriKlasoru();
}

/// PDF sekmesindeki araçlar.
enum PdfAraci { el, kalem, yazi, silgi }

/// Bir not: çizgi ya da yazı. Notlar değişmez; değişiklik yeni nesneyle olur.
@immutable
sealed class PdfNotu {
  const PdfNotu();

  /// 1'den başlayan sayfa numarası.
  int get sayfa;
  Map<String, dynamic> toJson();

  static PdfNotu? fromJson(Object? j) {
    if (j is! Map) return null;
    try {
      final sayfa = (j['sayfa'] as num).toInt();
      final renk = (j['renk'] as num).toInt();
      switch (j['tur']) {
        case 'cizgi':
          final ham = (j['noktalar'] as List).cast<num>();
          final noktalar = <Offset>[
            for (var i = 0; i + 1 < ham.length; i += 2)
              Offset(ham[i].toDouble(), ham[i + 1].toDouble()),
          ];
          if (noktalar.isEmpty) return null;
          return PdfCizgi(
            sayfa: sayfa,
            noktalar: noktalar,
            renk: renk,
            kalinlik: (j['kalinlik'] as num).toDouble(),
            saydamlik: ((j['saydamlik'] as num?) ?? 1).toDouble(),
          );
        case 'yazi':
          final metin = j['metin'] as String;
          if (metin.isEmpty) return null;
          return PdfYazi(
            sayfa: sayfa,
            konum: Offset((j['x'] as num).toDouble(), (j['y'] as num).toDouble()),
            metin: metin,
            renk: renk,
            boyut: (j['boyut'] as num).toDouble(),
          );
      }
    } catch (_) {}
    return null;
  }
}

class PdfCizgi extends PdfNotu {
  @override
  final int sayfa;
  final List<Offset> noktalar;
  final int renk;

  /// Çizgi kalınlığı (sayfa genişliğine oranla).
  final double kalinlik;

  /// 0..1; 1 tam koyu, düşük değerler fosforlu kalem gibi.
  final double saydamlik;

  const PdfCizgi({
    required this.sayfa,
    required this.noktalar,
    required this.renk,
    required this.kalinlik,
    this.saydamlik = 1,
  });

  @override
  Map<String, dynamic> toJson() => {
        'tur': 'cizgi',
        'sayfa': sayfa,
        'renk': renk,
        'kalinlik': kalinlik,
        'saydamlik': saydamlik,
        'noktalar': [
          for (final n in noktalar) ...[_yuvarla(n.dx), _yuvarla(n.dy)],
        ],
      };
}

class PdfYazi extends PdfNotu {
  @override
  final int sayfa;

  /// Yazının sol üst köşesi.
  final Offset konum;
  final String metin;
  final int renk;

  /// Yazı boyutu (sayfa genişliğine oranla).
  final double boyut;

  const PdfYazi({
    required this.sayfa,
    required this.konum,
    required this.metin,
    required this.renk,
    required this.boyut,
  });

  PdfYazi kopya({String? metin}) => PdfYazi(
      sayfa: sayfa, konum: konum, metin: metin ?? this.metin, renk: renk, boyut: boyut);

  @override
  Map<String, dynamic> toJson() => {
        'tur': 'yazi',
        'sayfa': sayfa,
        'renk': renk,
        'boyut': boyut,
        'x': _yuvarla(konum.dx),
        'y': _yuvarla(konum.dy),
        'metin': metin,
      };
}

double _yuvarla(double d) => (d * 100000).roundToDouble() / 100000;

/// Yazı notlarının çizim biçimi; ölçme ve boyama aynı biçimi kullanır.
TextStyle pdfYaziBicimi(Color renk, double punto) =>
    TextStyle(color: renk, fontSize: punto, height: 1.2, fontWeight: FontWeight.w500);

/// Yazının sayfadaki kutusu (sayfa genişliğine oranla).
Rect pdfYaziKutusu(PdfYazi y) {
  const olcek = 1000.0;
  final tp = TextPainter(
    text: TextSpan(text: y.metin, style: pdfYaziBicimi(Colors.black, y.boyut * olcek)),
    textDirection: TextDirection.ltr,
  )..layout();
  final r = Rect.fromLTWH(y.konum.dx, y.konum.dy, tp.width / olcek, tp.height / olcek);
  tp.dispose();
  return r;
}

double _parcayaUzaklik(Offset n, Offset a, Offset b) {
  final ab = b - a;
  final uzunluk2 = ab.dx * ab.dx + ab.dy * ab.dy;
  if (uzunluk2 == 0) return (n - a).distance;
  final t = (((n.dx - a.dx) * ab.dx + (n.dy - a.dy) * ab.dy) / uzunluk2).clamp(0.0, 1.0);
  return (n - (a + ab * t)).distance;
}

/// Silgi [nokta] çevresinde [yaricap] kadar alanda bu notu siler mi?
bool silgiDegiyorMu(PdfNotu not, int sayfa, Offset nokta, double yaricap) {
  if (not.sayfa != sayfa) return false;
  switch (not) {
    case PdfCizgi c:
      final sinir = yaricap + c.kalinlik / 2;
      if (c.noktalar.length == 1) return (c.noktalar.first - nokta).distance <= sinir;
      for (var i = 0; i + 1 < c.noktalar.length; i++) {
        if (_parcayaUzaklik(nokta, c.noktalar[i], c.noktalar[i + 1]) <= sinir) return true;
      }
      return false;
    case PdfYazi y:
      return pdfYaziKutusu(y).inflate(yaricap).contains(nokta);
  }
}

/// Bir PDF'in notları ve geri al / yinele geçmişi.
class PdfNotDefteri extends ChangeNotifier {
  PdfNotDefteri(this.dosya);

  /// Notların kaydedildiği dosya (null: kaydedilmez, testler).
  final File? dosya;

  static const int gecmisSiniri = 200;

  List<PdfNotu> _notlar = const [];
  final List<List<PdfNotu>> _geri = [];
  final List<List<PdfNotu>> _ileri = [];

  /// Çizilmekte olan çizgi (bırakılınca nota dönüşür).
  PdfCizgi? taslak;

  /// Yazı düzenlenirken eski hâli sayfada gösterilmez.
  PdfYazi? gizli;

  bool _yuklendi = false;
  Timer? _kayit;

  List<PdfNotu> get notlar => _notlar;
  bool get bos => _notlar.isEmpty;
  bool get geriAlinabilir => _geri.isNotEmpty;
  bool get yinelenebilir => _ileri.isNotEmpty;

  Iterable<PdfNotu> sayfaNotlari(int sayfa) => _notlar.where((n) => n.sayfa == sayfa);

  // --- Program boyunca tek defter (sekme kapanıp açılınca geçmiş kalır) ---

  static final Map<String, PdfNotDefteri> _defterler = {};

  /// [pdfYolu] için defteri verir; ilk istekte diskten yükler.
  static PdfNotDefteri al(String pdfYolu, {String? kok}) {
    final anahtar = pdfAnahtari(pdfYolu);
    return _defterler.putIfAbsent(anahtar, () {
      final d = PdfNotDefteri(notDosyasi(pdfYolu, kok: kok));
      d._yukle(pdfYolu);
      return d;
    });
  }

  /// PDF yolundan dosya adına uygun, sisteme göre değişmeyen anahtar
  /// (büyük / küçük harf ve ayraç farkı aynı dosyayı gösterir).
  static String pdfAnahtari(String pdfYolu) {
    final yol = p.normalize(p.absolute(pdfYolu)).replaceAll('\\', '/').toLowerCase();
    // FNV-1a, 64 bit.
    var h = 0xcbf29ce484222325;
    for (final b in utf8.encode(yol)) {
      h ^= b;
      h *= 0x100000001b3; // 64 bitte taşar (istenen)
    }
    return h.toUnsigned(64).toRadixString(16).padLeft(16, '0');
  }

  static File notDosyasi(String pdfYolu, {String? kok}) => File(p.join(
      kok ?? _notKoku(), 'pdf_notlari', '${pdfAnahtari(pdfYolu)}.json'));

  void _yukle(String pdfYolu) {
    final f = dosya;
    _yuklendi = true;
    if (f == null) return;
    try {
      if (!f.existsSync()) return;
      final j = jsonDecode(f.readAsStringSync());
      if (j is! Map || j['notlar'] is! List) return;
      _notlar = List.unmodifiable(
          (j['notlar'] as List).map(PdfNotu.fromJson).whereType<PdfNotu>());
    } catch (_) {
      // Bozuk dosya: notsuz başlanır, dosyaya ilk değişiklikte yazılır.
    }
  }

  /// Diskten yeniden okur (testler).
  @visibleForTesting
  void yenidenYukle(String pdfYolu) {
    _notlar = const [];
    _geri.clear();
    _ileri.clear();
    _yukle(pdfYolu);
    notifyListeners();
  }

  // --- Değişiklikler (hepsi geri alınabilir) ---

  void _uygula(List<PdfNotu> yeni) {
    _geri.add(_notlar);
    if (_geri.length > gecmisSiniri) _geri.removeAt(0);
    _ileri.clear();
    _notlar = List.unmodifiable(yeni);
    _degisti();
  }

  void ekle(PdfNotu not) => _uygula([..._notlar, not]);

  void degistir(PdfNotu eski, PdfNotu yeni) {
    final i = _notlar.indexOf(eski);
    if (i < 0) return;
    _uygula([..._notlar]..[i] = yeni);
  }

  void sil(PdfNotu not) {
    if (!_notlar.contains(not)) return;
    _uygula([..._notlar]..remove(not));
  }

  /// Bütün notları siler (PDF'i ilk hâline döndürür). Geri alınabilir.
  void temizle() {
    if (_notlar.isEmpty) return;
    _uygula(const []);
  }

  void geriAl() {
    if (_geri.isEmpty) return;
    _ileri.add(_notlar);
    _notlar = _geri.removeLast();
    _degisti();
  }

  void yinele() {
    if (_ileri.isEmpty) return;
    _geri.add(_notlar);
    _notlar = _ileri.removeLast();
    _degisti();
  }

  // --- Silgi: bir sürükleme tek adımda geri alınır ---

  List<PdfNotu>? _silmeOncesi;

  void silmeyeBasla() => _silmeOncesi ??= _notlar;

  /// Silginin değdiği notları siler; bir şey silindiyse true.
  bool silgi(int sayfa, Offset nokta, double yaricap) {
    final kalan = [
      for (final n in _notlar)
        if (!silgiDegiyorMu(n, sayfa, nokta, yaricap)) n,
    ];
    if (kalan.length == _notlar.length) return false;
    _silmeOncesi ??= _notlar;
    _notlar = List.unmodifiable(kalan);
    notifyListeners();
    return true;
  }

  void silmeyiBitir() {
    final once = _silmeOncesi;
    _silmeOncesi = null;
    if (once == null || identical(once, _notlar)) return;
    _geri.add(once);
    if (_geri.length > gecmisSiniri) _geri.removeAt(0);
    _ileri.clear();
    _degisti();
  }

  /// Taslak çizgi ya da gizli yazı değişince yalnızca yeniden boyanır.
  void boya() => notifyListeners();

  void _degisti() {
    notifyListeners();
    _kayit?.cancel();
    _kayit = Timer(const Duration(milliseconds: 400), kaydet);
  }

  /// Notları hemen diske yazar (not yoksa dosya silinir).
  void kaydet() {
    _kayit?.cancel();
    _kayit = null;
    final f = dosya;
    if (f == null || !_yuklendi) return;
    try {
      if (_notlar.isEmpty) {
        if (f.existsSync()) f.deleteSync();
        return;
      }
      f.parent.createSync(recursive: true);
      final gecici = File('${f.path}.yeni');
      gecici.writeAsStringSync(jsonEncode({
        'surum': 1,
        'notlar': [for (final n in _notlar) n.toJson()],
      }));
      gecici.renameSync(f.path);
    } catch (_) {
      // Yazılamazsa notlar program açık kaldıkça bellekte durur.
    }
  }

  /// Bekleyen kayıt varsa hemen yazar (sekme kapanırken).
  void bekleyeniKaydet() {
    if (_kayit != null) kaydet();
  }

  /// Testler arasında defterleri unutur.
  @visibleForTesting
  static void hepsiniUnut() => _defterler.clear();
}

/// Araçların ayarları (renk, kalınlık, boyut); bütün PDF'lerde ortaktır ve
/// veri klasöründe saklanır.
class PdfAracAyarlari extends ChangeNotifier {
  PdfAracAyarlari({this.dosya});

  final File? dosya;

  static const List<int> renkler = [
    0xFF111827, // siyah
    0xFFDC2626, // kırmızı
    0xFFF97316, // turuncu
    0xFFFACC15, // sarı
    0xFF16A34A, // yeşil
    0xFF2563EB, // mavi
    0xFF9333EA, // mor
    0xFFEC4899, // pembe
    0xFFFFFFFF, // beyaz
  ];

  static const double kalemEnAz = 1, kalemEnCok = 24;
  static const double yaziEnAz = 8, yaziEnCok = 48;
  static const double silgiEnAz = 4, silgiEnCok = 60;
  static const double saydamlikEnAz = 0.2;

  int kalemRengi = 0xFFDC2626;
  double kalemKalinligi = 3;
  double kalemSaydamligi = 1;
  int yaziRengi = 0xFF2563EB;
  double yaziBoyutu = 16;
  double silgiBoyutu = 16;

  static PdfAracAyarlari? _ortak;

  /// Bütün PDF sekmelerinin kullandığı ayarlar.
  static PdfAracAyarlari get ortak => _ortak ??= () {
        final a = PdfAracAyarlari(
            dosya: File(p.join(_notKoku(), 'pdf_notlari', 'araclar.json')));
        a._yukle();
        return a;
      }();

  void _yukle() {
    final f = dosya;
    if (f == null) return;
    try {
      if (!f.existsSync()) return;
      final j = jsonDecode(f.readAsStringSync());
      if (j is! Map) return;
      double sayi(String ad, double v, double enAz, double enCok) =>
          ((j[ad] as num?)?.toDouble() ?? v).clamp(enAz, enCok).toDouble();
      kalemRengi = (j['kalemRengi'] as num?)?.toInt() ?? kalemRengi;
      kalemKalinligi = sayi('kalemKalinligi', kalemKalinligi, kalemEnAz, kalemEnCok);
      kalemSaydamligi = sayi('kalemSaydamligi', kalemSaydamligi, saydamlikEnAz, 1);
      yaziRengi = (j['yaziRengi'] as num?)?.toInt() ?? yaziRengi;
      yaziBoyutu = sayi('yaziBoyutu', yaziBoyutu, yaziEnAz, yaziEnCok);
      silgiBoyutu = sayi('silgiBoyutu', silgiBoyutu, silgiEnAz, silgiEnCok);
    } catch (_) {}
  }

  Timer? _kayit;

  /// Bir ayarı değiştirir: `ayarlar.degistir(() => ayarlar.kalemRengi = r)`.
  void degistir(void Function() fn) {
    fn();
    notifyListeners();
    _kayit?.cancel();
    _kayit = Timer(const Duration(milliseconds: 500), _kaydet);
  }

  void _kaydet() {
    final f = dosya;
    if (f == null) return;
    try {
      f.parent.createSync(recursive: true);
      f.writeAsStringSync(jsonEncode({
        'kalemRengi': kalemRengi,
        'kalemKalinligi': kalemKalinligi,
        'kalemSaydamligi': kalemSaydamligi,
        'yaziRengi': yaziRengi,
        'yaziBoyutu': yaziBoyutu,
        'silgiBoyutu': silgiBoyutu,
      }));
    } catch (_) {}
  }
}

/// Bir sayfanın notlarını boyar. Boyut, sayfanın ekrandaki boyutudur.
class PdfNotBoyayici extends CustomPainter {
  PdfNotBoyayici(this.defter, this.sayfa) : super(repaint: defter);

  final PdfNotDefteri defter;
  final int sayfa;

  @override
  void paint(Canvas canvas, Size size) {
    final w = size.width;
    if (w <= 0) return;
    canvas.save();
    canvas.clipRect(Offset.zero & size);
    for (final n in defter.sayfaNotlari(sayfa)) {
      if (identical(n, defter.gizli)) continue;
      _ciz(canvas, n, w);
    }
    final t = defter.taslak;
    if (t != null && t.sayfa == sayfa) _ciz(canvas, t, w);
    canvas.restore();
  }

  static void _ciz(Canvas canvas, PdfNotu n, double w) {
    switch (n) {
      case PdfCizgi c:
        final renk = Color(c.renk).withValues(alpha: c.saydamlik);
        final kalem = Paint()
          ..color = renk
          ..strokeWidth = math.max(0.5, c.kalinlik * w)
          ..strokeCap = StrokeCap.round
          ..strokeJoin = StrokeJoin.round
          ..style = PaintingStyle.stroke
          ..isAntiAlias = true;
        if (c.noktalar.length == 1) {
          canvas.drawCircle(c.noktalar.first * w, kalem.strokeWidth / 2,
              Paint()..color = renk);
          return;
        }
        final yol = Path()..moveTo(c.noktalar.first.dx * w, c.noktalar.first.dy * w);
        for (final k in c.noktalar.skip(1)) {
          yol.lineTo(k.dx * w, k.dy * w);
        }
        // Saydam kalemde üst üste binen parçalar koyulaşmasın: tek yol.
        canvas.drawPath(yol, kalem);
      case PdfYazi y:
        final tp = TextPainter(
          text: TextSpan(text: y.metin, style: pdfYaziBicimi(Color(y.renk), y.boyut * w)),
          textDirection: TextDirection.ltr,
        )..layout();
        tp.paint(canvas, y.konum * w);
        tp.dispose();
    }
  }

  @override
  bool shouldRepaint(PdfNotBoyayici old) => old.defter != defter || old.sayfa != sayfa;
}
