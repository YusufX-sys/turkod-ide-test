import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:path/path.dart' as p;
import 'package:turkod_ide/pdf_notlari.dart';
import 'package:turkod_ide/platform_ayarlari.dart';

PdfCizgi cizgi(int sayfa, List<Offset> n) =>
    PdfCizgi(sayfa: sayfa, noktalar: n, renk: 0xFFDC2626, kalinlik: 0.01);

PdfYazi yazi(int sayfa, String metin, {Offset konum = const Offset(0.1, 0.1)}) =>
    PdfYazi(sayfa: sayfa, konum: konum, metin: metin, renk: 0xFF2563EB, boyut: 0.03);

void main() {
  tearDown(PdfNotDefteri.hepsiniUnut);

  group('geri al / yinele', () {
    test('ekle, geri al, yinele', () {
      final d = PdfNotDefteri(null);
      expect(d.geriAlinabilir, isFalse);
      final a = cizgi(1, const [Offset(0, 0), Offset(0.5, 0.5)]);
      final b = yazi(2, 'Merhaba');
      d.ekle(a);
      d.ekle(b);
      expect(d.notlar, [a, b]);
      d.geriAl();
      expect(d.notlar, [a]);
      expect(d.yinelenebilir, isTrue);
      d.yinele();
      expect(d.notlar, [a, b]);
      d.geriAl();
      d.geriAl();
      expect(d.bos, isTrue);
      expect(d.geriAlinabilir, isFalse);
      // Yeni değişiklik yinelenecekleri siler.
      d.ekle(b);
      expect(d.yinelenebilir, isFalse);
    });

    test('yazı değiştirme ve silme geri alınır', () {
      final d = PdfNotDefteri(null);
      final y = yazi(1, 'eski');
      d.ekle(y);
      final yeni = y.kopya(metin: 'yeni');
      d.degistir(y, yeni);
      expect((d.notlar.single as PdfYazi).metin, 'yeni');
      d.sil(yeni);
      expect(d.bos, isTrue);
      d.geriAl();
      d.geriAl();
      expect((d.notlar.single as PdfYazi).metin, 'eski');
    });

    test('ilk hâline döndürme bütün notları siler ve geri alınabilir', () {
      final d = PdfNotDefteri(null);
      d.ekle(cizgi(1, const [Offset(0.1, 0.1)]));
      d.ekle(yazi(3, 'not'));
      d.temizle();
      expect(d.bos, isTrue);
      d.geriAl();
      expect(d.notlar.length, 2);
    });

    test('geçmiş sınırı aşılmaz', () {
      final d = PdfNotDefteri(null);
      for (var i = 0; i < PdfNotDefteri.gecmisSiniri + 30; i++) {
        d.ekle(yazi(1, '$i'));
      }
      var adim = 0;
      while (d.geriAlinabilir) {
        d.geriAl();
        adim++;
      }
      expect(adim, PdfNotDefteri.gecmisSiniri);
      expect(d.notlar.length, 30);
    });
  });

  group('silgi', () {
    test('değdiği çizgiyi ve yazıyı siler, tek adımda geri alınır', () {
      final d = PdfNotDefteri(null);
      final yatay = cizgi(1, const [Offset(0.1, 0.5), Offset(0.9, 0.5)]);
      final uzak = cizgi(1, const [Offset(0.1, 0.9), Offset(0.9, 0.9)]);
      final baskaSayfa = cizgi(2, const [Offset(0.1, 0.5), Offset(0.9, 0.5)]);
      final y = yazi(1, 'Kodi', konum: const Offset(0.1, 0.2));
      d.ekle(yatay);
      d.ekle(uzak);
      d.ekle(baskaSayfa);
      d.ekle(y);

      d.silmeyeBasla();
      // Çizginin ortasına (uçlarına değil) değmek yeter.
      expect(d.silgi(1, const Offset(0.5, 0.505), 0.01), isTrue);
      expect(d.silgi(1, const Offset(0.5, 0.7), 0.01), isFalse);
      final kutu = pdfYaziKutusu(y);
      expect(d.silgi(1, kutu.center, 0.001), isTrue);
      d.silmeyiBitir();
      expect(d.notlar, [uzak, baskaSayfa]);

      d.geriAl();
      expect(d.notlar, [yatay, uzak, baskaSayfa, y]);
    });

    test('hiçbir şey silinmediyse geçmişe adım eklenmez', () {
      final d = PdfNotDefteri(null);
      d.ekle(cizgi(1, const [Offset(0.1, 0.1), Offset(0.2, 0.1)]));
      d.silmeyeBasla();
      d.silgi(1, const Offset(0.9, 0.9), 0.01);
      d.silmeyiBitir();
      d.geriAl();
      expect(d.bos, isTrue);
      expect(d.geriAlinabilir, isFalse);
    });

    test('kalın çizgi kenarından silinir', () {
      const c = PdfCizgi(
          sayfa: 1,
          noktalar: [Offset(0.1, 0.5), Offset(0.9, 0.5)],
          renk: 0,
          kalinlik: 0.1);
      expect(silgiDegiyorMu(c, 1, const Offset(0.5, 0.56), 0.02), isTrue);
      expect(silgiDegiyorMu(c, 1, const Offset(0.5, 0.6), 0.02), isFalse);
    });
  });

  group('kayıt', () {
    late Directory kok;
    setUp(() => kok = Directory.systemTemp.createTempSync('turkod_pdf_notlari_'));
    tearDown(() => kok.deleteSync(recursive: true));

    test('notlar diske yazılır ve yeniden okunur; boşalınca dosya silinir', () {
      final pdf = p.join(kok.path, 'kitap.pdf');
      final d = PdfNotDefteri.al(pdf, kok: kok.path);
      d.ekle(cizgi(4, const [Offset(0.25, 0.5), Offset(0.75, 0.5)]));
      d.ekle(const PdfCizgi(
          sayfa: 4,
          noktalar: [Offset(0.3, 0.3)],
          renk: 0xFFFACC15,
          kalinlik: 0.02,
          saydamlik: 0.4));
      d.ekle(yazi(5, 'Satır 1\nSatır 2'));
      d.kaydet();

      final dosya = PdfNotDefteri.notDosyasi(pdf, kok: kok.path);
      expect(dosya.existsSync(), isTrue);

      PdfNotDefteri.hepsiniUnut();
      final d2 = PdfNotDefteri.al(pdf, kok: kok.path);
      expect(d2.notlar.length, 3);
      final c = d2.notlar[0] as PdfCizgi;
      expect(c.sayfa, 4);
      expect(c.noktalar, const [Offset(0.25, 0.5), Offset(0.75, 0.5)]);
      expect((d2.notlar[1] as PdfCizgi).saydamlik, closeTo(0.4, 1e-9));
      expect((d2.notlar[2] as PdfYazi).metin, 'Satır 1\nSatır 2');
      expect(d2.geriAlinabilir, isFalse);

      d2.temizle();
      d2.kaydet();
      expect(dosya.existsSync(), isFalse);
    });

    test('aynı PDF aynı defteri ve geçmişi kullanır (sekme yeniden açılınca)', () {
      final pdf = p.join(kok.path, 'a.pdf');
      final d = PdfNotDefteri.al(pdf, kok: kok.path);
      d.ekle(yazi(1, 'x'));
      final tekrar = PdfNotDefteri.al(pdf, kok: kok.path);
      expect(identical(d, tekrar), isTrue);
      expect(tekrar.geriAlinabilir, isTrue);
    });

    test('bozuk not dosyası programı durdurmaz', () {
      final pdf = p.join(kok.path, 'bozuk.pdf');
      final dosya = PdfNotDefteri.notDosyasi(pdf, kok: kok.path)
        ..createSync(recursive: true)
        ..writeAsStringSync('{bozuk');
      expect(dosya.existsSync(), isTrue);
      final d = PdfNotDefteri.al(pdf, kok: kok.path);
      expect(d.bos, isTrue);
    });

    test('anahtar büyük / küçük harf ve ayraçtan etkilenmez', () {
      expect(PdfNotDefteri.pdfAnahtari('/a/B/Kitap.pdf', Isletim.windows),
          PdfNotDefteri.pdfAnahtari('/a/b/kitap.pdf', Isletim.windows));
      expect(PdfNotDefteri.pdfAnahtari('/a/B/Kitap.pdf', Isletim.macos),
          PdfNotDefteri.pdfAnahtari('/a/b/kitap.pdf', Isletim.macos));
      // Linux'ta büyük/küçük harf farkı ayrı dosyadır.
      expect(PdfNotDefteri.pdfAnahtari('/a/B/Kitap.pdf', Isletim.linux),
          isNot(PdfNotDefteri.pdfAnahtari('/a/b/kitap.pdf', Isletim.linux)));
      expect(PdfNotDefteri.pdfAnahtari('/a/b/kitap.pdf'),
          isNot(PdfNotDefteri.pdfAnahtari('/a/b/kitap2.pdf')));
      expect(PdfNotDefteri.pdfAnahtari('/x.pdf'), matches(RegExp(r'^[0-9a-f]{16}$')));
    });
  });

  test('bozuk not girdileri atlanır', () {
    expect(PdfNotu.fromJson({'tur': 'cizgi', 'sayfa': 1}), isNull);
    expect(PdfNotu.fromJson('x'), isNull);
    expect(
        PdfNotu.fromJson({
          'tur': 'yazi',
          'sayfa': 1,
          'renk': 0,
          'boyut': 0.02,
          'x': 0.1,
          'y': 0.1,
          'metin': '',
        }),
        isNull);
  });
}
