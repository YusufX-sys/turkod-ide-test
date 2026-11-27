import 'package:flutter_test/flutter_test.dart';
import 'package:turkod_ide/main.dart';

void main() {
  test('Rehber araması Türkçe harfsiz ve büyük harfli yazımı tanır', () {
    bool bulur(String aranan, String metin) =>
        rehberAramaAnahtari(metin).contains(rehberAramaAnahtari(aranan));
    expect(bulur('satranc', 'Satranç (python-chess)'), isTrue);
    expect(bulur('İSTATİSTİK', 'istatistiksel_grafik'), isTrue);
    expect(bulur('veri tablo', 'veri_tabloları'), isTrue);
    expect(bulur('Işık', 'ışık'), isTrue);
    expect(bulur('pandas', 'Veri Tabloları (pandas)'), isTrue);
    expect(bulur('torch', 'Satranç'), isFalse);
  });
}
