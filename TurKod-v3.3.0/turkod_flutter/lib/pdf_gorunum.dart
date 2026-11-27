// PDF sekmesi: .pdf dosyaları metin olarak değil, sayfa sayfa görüntülenir.
// Yakınlaştırma / uzaklaştırma, sayfa gezinme ve sığdırma düğmeleri vardır.
// Sağdaki tutamaç sürüklenerek belge hızla gezilir; sayfa kutusuna numara
// yazılıp Enter'a basılınca o sayfaya gidilir.
//
// İkinci çubukta not araçları vardır: kalem, yazı ve silgi (renk, kalınlık,
// boyut ayarlanır). Notlar PDF'in kendisini değiştirmez; pdf_notlari.dart
// içinde ayrı saklanır. Ctrl+Z / Ctrl+Y geri alır / yineler, "İlk hâline
// döndür" (önce sorar) bütün notları siler. Fare orta tuşuyla sürüklenerek
// gezilir; orta tuşa tıklayınca otomatik kaydırma açılır.

part of 'main.dart';

class PdfSekmesi extends StatefulWidget {
  final String yol;
  const PdfSekmesi({super.key, required this.yol});

  /// Bir PDF'i belli bir sayfada açma isteği (ör. Kodi "kitabı 35. sayfada
  /// aç" dediğinde). Sekme hazırsa hemen, değilse açılınca o sayfaya gider.
  static final sayfaIstegi = ValueNotifier<({String yol, int sayfa})?>(null);
  @override
  State<PdfSekmesi> createState() => _PdfSekmesiState();
}

class _PdfSekmesiState extends State<PdfSekmesi> {
  final _ctrl = PdfViewerController();
  final _odak = FocusNode(debugLabel: 'pdf');
  final _sayfaKutusu = TextEditingController();
  final _sayfaOdak = FocusNode(debugLabel: 'pdf-sayfa');
  int? _sayfa;
  int _sayfaSayisi = 0;
  double _yakinlik = 1;
  bool _hazir = false;

  /// Sığdırma kipi: 'genislik' | 'sayfa' | 'serbest' (elle yakınlaştırıldı).
  /// Görünüm boyutu değişince (pencere açılırken büyür, panel açılıp
  /// kapanır) sayfa bu kipe göre yeniden sığdırılır; eskiden açılışta küçük
  /// pencereye göre hesaplanan ölçek kalıyor, sayfanın sağı kesiliyordu.
  String _kip = 'genislik';
  Timer? _yenidenSigdir;

  // --- Not araçları ---
  late final PdfNotDefteri _defter = PdfNotDefteri.al(widget.yol);
  final PdfAracAyarlari _ayarlar = PdfAracAyarlari.ortak;
  PdfAraci _arac = PdfAraci.el;

  /// Kalemle çizilen çizginin noktaları (sayfa genişliğine oranla).
  List<Offset>? _cizim;
  int _cizimSayfasi = 0;
  double _cizimGenisligi = 1;

  /// Silginin son değdiği yer (belge koordinatı; hızlı sürüklemede arası
  /// da silinsin diye).
  Offset? _silgiSon;

  /// Silgi dairesinin ekrandaki yeri.
  Offset? _silgiImlec;

  /// Yazılmakta olan yazı.
  _YaziDuzeni? _yazi;
  final _yaziKutusu = TextEditingController();
  final _yaziOdak = FocusNode(debugLabel: 'pdf-yazi');

  // --- Fare orta tuşu ---
  Offset? _ortaSon;
  Offset _ortaBaslangic = Offset.zero;
  bool _ortaSurukledi = false;

  /// Otomatik kaydırma: orta tuşa tıklanınca açılır; fare merkezden ne kadar
  /// uzaklaşırsa belge o yöne o kadar hızlı kayar. Herhangi bir tıklama ya da
  /// Esc kapatır.
  Offset? _otoMerkez;
  Offset _imlec = Offset.zero;
  Timer? _otoZamanlayici;

  bool get _kitapMi => p.basename(widget.yol) == kKitapDosyasi;

  /// Sayfa kutusunda ya da yazı kutusunda yazılırken klavye kısayolları
  /// (Ctrl+Z, Home, End ...) metin kutusunun kendisine kalır.
  bool get _metinOdakta => _sayfaOdak.hasFocus || _yaziOdak.hasFocus;

  @override
  void initState() {
    super.initState();
    _ctrl.addListener(_yakinlikGuncelle);
    PdfSekmesi.sayfaIstegi.addListener(_sayfaIstegi);
    _defter.addListener(_yenile);
    _ayarlar.addListener(_yenile);
    _sayfaOdak.addListener(_yenile);
    _yaziOdak.addListener(_yenile);
  }

  void _yenile() {
    if (mounted) setState(() {});
  }

  /// Bu PDF için bekleyen sayfa isteği varsa (görüntüleyici hazırken) uygular.
  void _sayfaIstegi() {
    final istek = PdfSekmesi.sayfaIstegi.value;
    if (istek == null || !_hazir || !mounted) return;
    if (!yollarAyniMi(istek.yol, widget.yol)) return;
    PdfSekmesi.sayfaIstegi.value = null;
    _sayfayaGit(istek.sayfa);
  }

  @override
  void dispose() {
    PdfSekmesi.sayfaIstegi.removeListener(_sayfaIstegi);
    _ctrl.removeListener(_yakinlikGuncelle);
    _defter.removeListener(_yenile);
    _ayarlar.removeListener(_yenile);
    _sayfaOdak.removeListener(_yenile);
    _yaziOdak.removeListener(_yenile);
    // Yarım kalan yazı ve çizgi kaybolmasın; sekme kapanırken diske yazılır.
    _yaziyiBitir(yenile: false);
    _cizimiBitir();
    _defter.silmeyiBitir();
    _defter.bekleyeniKaydet();
    _yenidenSigdir?.cancel();
    _otoZamanlayici?.cancel();
    _odak.dispose();
    _sayfaKutusu.dispose();
    _sayfaOdak.dispose();
    _yaziKutusu.dispose();
    _yaziOdak.dispose();
    super.dispose();
  }

  void _yakinlikGuncelle() {
    if (!mounted || !_ctrl.isReady) return;
    final z = _ctrl.currentZoom;
    if ((z - _yakinlik).abs() > 0.001) {
      setState(() => _yakinlik = z);
    } else if (_yazi != null) {
      // Yazı kutusu sayfayla birlikte kaysın.
      setState(() {});
    }
  }

  // ---------------------------------------------------------------------------
  // Not araçları
  // ---------------------------------------------------------------------------

  void _aracSec(PdfAraci a) {
    _yaziyiBitir();
    setState(() {
      _arac = a;
      _silgiImlec = null;
    });
    _odak.requestFocus();
  }

  /// Belge koordinatındaki noktanın sayfası ve o sayfanın belgedeki yeri.
  ({int sayfa, Rect alan})? _sayfaBul(Offset belge) {
    if (!_ctrl.isReady) return null;
    final alanlar = _ctrl.layout.pageLayouts;
    for (var i = 0; i < alanlar.length; i++) {
      if (alanlar[i].contains(belge)) return (sayfa: i + 1, alan: alanlar[i]);
    }
    return null;
  }

  Rect? _sayfaAlani(int sayfa) {
    if (!_ctrl.isReady) return null;
    final alanlar = _ctrl.layout.pageLayouts;
    return sayfa >= 1 && sayfa <= alanlar.length ? alanlar[sayfa - 1] : null;
  }

  static Offset _oranla(Offset belge, Rect alan) =>
      Offset((belge.dx - alan.left) / alan.width, (belge.dy - alan.top) / alan.width);

  void _araciBas(PointerDownEvent e) {
    if (_otoMerkez != null || (e.buttons & kPrimaryButton) == 0) return;
    final belge = _ctrl.globalToDocument(e.position);
    if (belge == null) return;
    switch (_arac) {
      case PdfAraci.el:
        return;
      case PdfAraci.kalem:
        final s = _sayfaBul(belge);
        if (s == null) return;
        _cizimSayfasi = s.sayfa;
        _cizimGenisligi = s.alan.width;
        _cizim = [_oranla(belge, s.alan)];
        _taslagiGuncelle();
      case PdfAraci.silgi:
        _defter.silmeyeBasla();
        _silgiSon = null;
        _sil(belge);
      case PdfAraci.yazi:
        // Yazı açıksa sayfaya tıklamak onu bitirir.
        if (_yazi != null) {
          _yaziyiBitir();
          return;
        }
        final s = _sayfaBul(belge);
        if (s == null) return;
        final nokta = _oranla(belge, s.alan);
        // Var olan bir yazıya tıklandıysa o düzenlenir.
        PdfYazi? eski;
        for (final n in _defter.sayfaNotlari(s.sayfa).toList().reversed) {
          if (n is PdfYazi && pdfYaziKutusu(n).inflate(0.004).contains(nokta)) {
            eski = n;
            break;
          }
        }
        _yaziyaBasla(_YaziDuzeni(
          sayfa: s.sayfa,
          konum: eski?.konum ?? nokta,
          eski: eski,
          renk: eski?.renk ?? _ayarlar.yaziRengi,
          boyut: eski?.boyut ?? _ayarlar.yaziBoyutu / s.alan.width,
        ));
    }
  }

  void _araciSurukle(PointerMoveEvent e) {
    if (_arac == PdfAraci.silgi) setState(() => _silgiImlec = e.localPosition);
    if ((e.buttons & kPrimaryButton) == 0) return;
    final belge = _ctrl.globalToDocument(e.position);
    if (belge == null) return;
    switch (_arac) {
      case PdfAraci.kalem:
        final cizim = _cizim;
        final alan = _sayfaAlani(_cizimSayfasi);
        if (cizim == null || alan == null) return;
        final yeni = _oranla(belge, alan);
        // Ekranda 1 pikselden kısa adımlar eklenmez (dosya şişmesin).
        final ekranda = (yeni - cizim.last).distance * alan.width * _ctrl.currentZoom;
        if (ekranda < 1.2) return;
        cizim.add(yeni);
        _taslagiGuncelle();
      case PdfAraci.silgi:
        _sil(belge);
      default:
        return;
    }
  }

  void _araciBirak(PointerEvent e) {
    switch (_arac) {
      case PdfAraci.kalem:
        _cizimiBitir();
      case PdfAraci.silgi:
        _silgiSon = null;
        _defter.silmeyiBitir();
      default:
        return;
    }
  }

  void _taslagiGuncelle() {
    final cizim = _cizim;
    _defter.taslak = cizim == null
        ? null
        : PdfCizgi(
            sayfa: _cizimSayfasi,
            noktalar: cizim,
            renk: _ayarlar.kalemRengi,
            kalinlik: _ayarlar.kalemKalinligi / _cizimGenisligi,
            saydamlik: _ayarlar.kalemSaydamligi,
          );
    _defter.boya();
  }

  void _cizimiBitir() {
    final t = _defter.taslak;
    _cizim = null;
    _defter.taslak = null;
    if (t == null) return;
    _defter.ekle(PdfCizgi(
      sayfa: t.sayfa,
      noktalar: List.unmodifiable(t.noktalar),
      renk: t.renk,
      kalinlik: t.kalinlik,
      saydamlik: t.saydamlik,
    ));
  }

  /// Silginin ekrandaki dairesinin içinde kalan notları siler; son yerden bu
  /// yere kadar olan yol da silinir.
  void _sil(Offset belge) {
    final yaricapBelge = _ayarlar.silgiBoyutu / 2 / _ctrl.currentZoom;
    final onceki = _silgiSon;
    _silgiSon = belge;
    final noktalar = <Offset>[belge];
    if (onceki != null) {
      final adim = math.max(1.0, yaricapBelge / 2);
      final n = ((belge - onceki).distance / adim).floor().clamp(0, 200);
      for (var i = 1; i <= n; i++) {
        noktalar.add(Offset.lerp(onceki, belge, i / (n + 1))!);
      }
    }
    for (final b in noktalar) {
      final s = _sayfaBul(b);
      if (s == null) continue;
      _defter.silgi(s.sayfa, _oranla(b, s.alan), yaricapBelge / s.alan.width);
    }
  }

  void _yaziyaBasla(_YaziDuzeni y) {
    _yaziKutusu.text = y.eski?.metin ?? '';
    _yaziKutusu.selection = TextSelection.collapsed(offset: _yaziKutusu.text.length);
    _defter.gizli = y.eski;
    _defter.boya();
    setState(() => _yazi = y);
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted && _yazi == y) _yaziOdak.requestFocus();
    });
  }

  /// Yazıyı bitirir: boşsa eklenmez (var olan yazı boşaltıldıysa silinir).
  void _yaziyiBitir({bool iptal = false, bool yenile = true}) {
    final y = _yazi;
    if (y == null) return;
    _yazi = null;
    _defter.gizli = null;
    final metin = _yaziKutusu.text.trimRight();
    if (!iptal) {
      final eski = y.eski;
      final yeni =
          PdfYazi(sayfa: y.sayfa, konum: y.konum, metin: metin, renk: y.renk, boyut: y.boyut);
      if (eski == null) {
        if (metin.trim().isNotEmpty) _defter.ekle(yeni);
      } else if (metin.trim().isEmpty) {
        _defter.sil(eski);
      } else if (eski.metin != metin || eski.renk != y.renk || eski.boyut != y.boyut) {
        _defter.degistir(eski, yeni);
      }
    }
    _defter.boya();
    if (yenile && mounted) {
      setState(() {});
      _odak.requestFocus();
    }
  }

  /// Ayar değiştirildikten sonra klavye yazı kutusuna (yoksa PDF'e) döner.
  void _odagiGeriVer() => (_yazi != null ? _yaziOdak : _odak).requestFocus();

  void _geriAl() {
    _yaziyiBitir();
    _defter.geriAl();
  }

  void _yinele() {
    _yaziyiBitir();
    _defter.yinele();
  }

  Future<void> _ilkHalineDondur() async {
    _yaziyiBitir();
    if (_defter.bos) return;
    final ad = _kitapMi ? 'Kitap' : 'PDF';
    final sayi = _defter.notlar.length;
    final evet = await showDialog<bool>(
      context: context,
      builder: (c) {
        final cs = Theme.of(c).colorScheme;
        return AlertDialog(
          icon: Icon(Icons.warning_amber_rounded, color: cs.error, size: 34),
          title: Text('$ad ilk hâline dönsün mü?'),
          content: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 420),
            child: Text('Sayfalara çizdiğin bütün çizgiler ve yazdığın bütün yazılar '
                '($sayi not) silinecek. $ad ilk açıldığı gibi tertemiz olacak.\n\n'
                'Fikrini değiştirirsen, programı kapatmadan Geri Al '
                '(${kisayolTusuAdi()} + Z) ile hepsini geri getirebilirsin.'),
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(c, false), child: const Text('Vazgeç')),
            FilledButton.icon(
              style: FilledButton.styleFrom(backgroundColor: cs.error, foregroundColor: cs.onError),
              onPressed: () => Navigator.pop(c, true),
              icon: const Icon(Icons.restart_alt_rounded, size: 18),
              label: const Text('Evet, ilk hâline döndür'),
            ),
          ],
        );
      },
    );
    if (evet == true) _defter.temizle();
    if (mounted) _odak.requestFocus();
  }

  // ---------------------------------------------------------------------------
  // Fare orta tuşu: sürükleyerek gezme ve otomatik kaydırma
  // ---------------------------------------------------------------------------

  /// Belgeyi ekranda [fark] kadar kaydırır.
  void _kaydir(Offset fark) {
    if (!_ctrl.isReady || fark == Offset.zero) return;
    _ctrl.value = Matrix4.translationValues(fark.dx, fark.dy, 0)..multiply(_ctrl.value);
  }

  void _isaretciBas(PointerDownEvent e) {
    if (_yazi == null) _odak.requestFocus();
    if (_otoMerkez != null) {
      _otoKaydirmayiBitir();
      return;
    }
    if (e.kind == PointerDeviceKind.mouse && (e.buttons & kMiddleMouseButton) != 0) {
      _ortaSon = e.position;
      _ortaBaslangic = e.localPosition;
      _ortaSurukledi = false;
      setState(() {});
    }
  }

  void _isaretciSurukle(PointerMoveEvent e) {
    _imlec = e.localPosition;
    final son = _ortaSon;
    if (son == null || (e.buttons & kMiddleMouseButton) == 0) return;
    if ((e.localPosition - _ortaBaslangic).distance > 4) _ortaSurukledi = true;
    _kaydir(e.position - son);
    _ortaSon = e.position;
  }

  void _isaretciBirak(PointerEvent e) {
    if (_ortaSon == null) return;
    final tiklama = !_ortaSurukledi && e is PointerUpEvent;
    _ortaSon = null;
    if (tiklama) {
      _otoKaydirmayaBasla(e.localPosition);
    } else {
      setState(() {});
    }
  }

  void _otoKaydirmayaBasla(Offset merkez) {
    _imlec = merkez;
    setState(() => _otoMerkez = merkez);
    _otoZamanlayici?.cancel();
    _otoZamanlayici = Timer.periodic(const Duration(milliseconds: 16), (_) {
      final m = _otoMerkez;
      if (m == null || !mounted) return;
      final v = _imlec - m;
      final uzaklik = v.distance;
      const olu = 12.0; // merkezin çevresinde durur
      if (uzaklik <= olu) return;
      final hiz = math.min(60.0, (uzaklik - olu) * 0.12);
      _kaydir(-v / uzaklik * hiz);
    });
  }

  void _otoKaydirmayiBitir() {
    _otoZamanlayici?.cancel();
    _otoZamanlayici = null;
    if (mounted) setState(() => _otoMerkez = null);
  }

  void _esc() {
    if (_otoMerkez != null) {
      _otoKaydirmayiBitir();
    } else if (_arac != PdfAraci.el) {
      _aracSec(PdfAraci.el);
    }
  }

  // Her adımda %25 (paketin kendi basamakları sığdırma ölçeğinde takılıyordu).
  Future<void> _yakinlas() => _olcekle(1.25);
  Future<void> _uzaklas() => _olcekle(1 / 1.25);

  Future<void> _olcekle(double kat) async {
    if (!_ctrl.isReady) return;
    _kip = 'serbest';
    final hedef = (_ctrl.currentZoom * kat).clamp(_ctrl.minScale, _ctrl.maxScale);
    await _ctrl.setZoom(_ctrl.centerPosition, hedef.toDouble());
  }

  Future<void> _genisligeSigdir() async {
    _kip = 'genislik';
    if (_ctrl.isReady) await _ctrl.setZoom(_ctrl.centerPosition, _ctrl.coverScale);
  }

  Future<void> _sayfayiSigdir() async {
    _kip = 'sayfa';
    if (!_ctrl.isReady) return;
    await _ctrl.setZoom(_ctrl.centerPosition, _ctrl.alternativeFitScale ?? _ctrl.minScale);
  }

  Future<void> _sayfayaGit(int n) async {
    if (!_ctrl.isReady || _sayfaSayisi == 0) return;
    await _ctrl.goToPage(pageNumber: n.clamp(1, _sayfaSayisi));
  }

  /// Sayfa kutusu, yazılırken değil, sayfa değişince güncellenir.
  void _sayfaKutusunuGuncelle() {
    if (_sayfaOdak.hasFocus) return;
    final metin = '${_sayfa ?? 1}';
    if (_sayfaKutusu.text != metin) _sayfaKutusu.text = metin;
  }

  void _sayfaKutusuGonder(String metin) {
    final n = int.tryParse(metin.trim());
    if (n != null) _sayfayaGit(n);
    _odak.requestFocus();
    setState(_sayfaKutusunuGuncelle);
  }

  /// Ctrl + fare tekerleği (macOS'ta Cmd): yakınlaştırır / uzaklaştırır.
  void _tekerlek(PointerSignalEvent e) {
    if (e is! PointerScrollEvent || !kisayolTusuBasili()) {
      return;
    }
    GestureBinding.instance.pointerSignalResolver.register(e, (ev) {
      final s = ev as PointerScrollEvent;
      if (s.scrollDelta.dy < 0) {
        _yakinlas();
      } else {
        _uzaklas();
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final koyu = Theme.of(context).brightness == Brightness.dark;
    final cubuk = Container(
      height: 40,
      padding: const EdgeInsets.symmetric(horizontal: 10),
      decoration: BoxDecoration(
        color: cs.surfaceContainer,
        border: Border(bottom: BorderSide(color: cs.outlineVariant)),
      ),
      child: Row(children: [
        const Icon(Icons.picture_as_pdf_rounded, size: 18, color: Color(0xFFEF4444)),
        const SizedBox(width: 8),
        // Kalan bütün genişlik adındır (Flexible + Spacer yarıya bölüyor,
        // uzun adlar gereksiz yere kısalıyordu).
        Expanded(
          child: Text(p.basename(widget.yol),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: TextStyle(fontSize: 13, fontWeight: FontWeight.w600, color: cs.onSurface)),
        ),
        const SizedBox(width: 8),
        // Sayfa gezinme
        PanelDugmesi(
          ikon: Icons.keyboard_arrow_up_rounded,
          ipucu: 'Önceki sayfa',
          onPressed: _hazir && (_sayfa ?? 1) > 1 ? () => _sayfayaGit((_sayfa ?? 1) - 1) : null,
        ),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 6),
          child: !_hazir
              ? Text('Yükleniyor…',
                  style: TextStyle(fontSize: 12, color: cs.onSurface.withValues(alpha: 0.8)))
              : Row(mainAxisSize: MainAxisSize.min, children: [
                  Text('Sayfa ',
                      style: TextStyle(fontSize: 12, color: cs.onSurface.withValues(alpha: 0.8))),
                  // Numarayı yaz, Enter'a bas: o sayfaya gidilir.
                  Tooltip(
                    message: 'Sayfa numarasını yaz, Enter\'a bas',
                    child: SizedBox(
                      width: 46,
                      height: 26,
                      child: TextField(
                        controller: _sayfaKutusu,
                        focusNode: _sayfaOdak,
                        textAlign: TextAlign.center,
                        keyboardType: TextInputType.number,
                        inputFormatters: [FilteringTextInputFormatter.digitsOnly],
                        style: TextStyle(fontSize: 12, color: cs.onSurface),
                        decoration: InputDecoration(
                          isDense: true,
                          contentPadding: const EdgeInsets.symmetric(horizontal: 4, vertical: 6),
                          filled: true,
                          fillColor: cs.surfaceContainerHighest,
                          border: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(6),
                              borderSide: BorderSide(color: cs.outlineVariant)),
                          enabledBorder: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(6),
                              borderSide: BorderSide(color: cs.outlineVariant)),
                        ),
                        onTap: () => _sayfaKutusu.selection =
                            TextSelection(baseOffset: 0, extentOffset: _sayfaKutusu.text.length),
                        onSubmitted: _sayfaKutusuGonder,
                        onTapOutside: (_) {
                          _sayfaOdak.unfocus();
                          setState(_sayfaKutusunuGuncelle);
                        },
                      ),
                    ),
                  ),
                  Text(' / $_sayfaSayisi',
                      style: TextStyle(fontSize: 12, color: cs.onSurface.withValues(alpha: 0.8))),
                ]),
        ),
        PanelDugmesi(
          ikon: Icons.keyboard_arrow_down_rounded,
          ipucu: 'Sonraki sayfa',
          onPressed:
              _hazir && (_sayfa ?? 1) < _sayfaSayisi ? () => _sayfayaGit((_sayfa ?? 1) + 1) : null,
        ),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 8),
          child: SizedBox(height: 20, child: VerticalDivider(width: 1, color: cs.outlineVariant)),
        ),
        // Yakınlaştırma
        PanelDugmesi(
          ikon: Icons.zoom_out_rounded,
          ipucu: 'Uzaklaştır (${kisayolTusuAdi()} + -)',
          onPressed: _hazir ? _uzaklas : null,
        ),
        Container(
          width: 58,
          alignment: Alignment.center,
          child: Text('%${(_yakinlik * 100).round()}',
              style: TextStyle(
                  fontSize: 12,
                  fontWeight: FontWeight.w600,
                  color: cs.onSurface.withValues(alpha: 0.85))),
        ),
        PanelDugmesi(
          ikon: Icons.zoom_in_rounded,
          ipucu: 'Yakınlaştır (${kisayolTusuAdi()} + +)',
          onPressed: _hazir ? _yakinlas : null,
        ),
        const SizedBox(width: 4),
        PanelDugmesi(
          ikon: Icons.fit_screen_outlined,
          ipucu: 'Genişliğe sığdır (${kisayolTusuAdi()} + 0)',
          onPressed: _hazir ? _genisligeSigdir : null,
        ),
        PanelDugmesi(
          ikon: Icons.crop_portrait_rounded,
          ipucu: 'Bütün sayfayı göster',
          onPressed: _hazir ? _sayfayiSigdir : null,
        ),
      ]),
    );

    return CallbackShortcuts(
      bindings: {
        // macOS'ta Ctrl yerine Cmd.
        platformKisayolu(const SingleActivator(LogicalKeyboardKey.equal, control: true)): _yakinlas,
        platformKisayolu(const SingleActivator(LogicalKeyboardKey.numpadAdd, control: true)):
            _yakinlas,
        platformKisayolu(const SingleActivator(LogicalKeyboardKey.minus, control: true)): _uzaklas,
        platformKisayolu(const SingleActivator(LogicalKeyboardKey.numpadSubtract, control: true)):
            _uzaklas,
        platformKisayolu(const SingleActivator(LogicalKeyboardKey.digit0, control: true)):
            _genisligeSigdir,
        const SingleActivator(LogicalKeyboardKey.pageDown): () => _sayfayaGit((_sayfa ?? 1) + 1),
        const SingleActivator(LogicalKeyboardKey.pageUp): () => _sayfayaGit((_sayfa ?? 1) - 1),
        // Metin kutusunda yazılırken bu tuşlar kutunun kendisine kalır.
        if (!_metinOdakta) ...{
          const SingleActivator(LogicalKeyboardKey.home): () => _sayfayaGit(1),
          const SingleActivator(LogicalKeyboardKey.end): () => _sayfayaGit(_sayfaSayisi),
          platformKisayolu(const SingleActivator(LogicalKeyboardKey.keyZ, control: true)): _geriAl,
          platformKisayolu(const SingleActivator(LogicalKeyboardKey.keyY, control: true)): _yinele,
          platformKisayolu(
              const SingleActivator(LogicalKeyboardKey.keyZ, control: true, shift: true)): _yinele,
          const SingleActivator(LogicalKeyboardKey.escape): _esc,
        },
      },
      child: Focus(
        focusNode: _odak,
        autofocus: true,
        child: Column(children: [
          cubuk,
          _aracCubugu(cs),
          Expanded(
            child: Listener(
              onPointerSignal: _tekerlek,
              onPointerDown: _isaretciBas,
              onPointerMove: _isaretciSurukle,
              onPointerHover: (e) => _imlec = e.localPosition,
              onPointerUp: _isaretciBirak,
              onPointerCancel: _isaretciBirak,
              child: MouseRegion(
                cursor: _otoMerkez != null || _ortaSon != null
                    ? SystemMouseCursors.allScroll
                    : MouseCursor.defer,
                child: Stack(children: [
                  Positioned.fill(child: _goruntuleyici(cs, koyu)),
                  if (_arac != PdfAraci.el && _hazir) Positioned.fill(child: _aracKatmani(cs)),
                  if (_yazi != null) _yaziAlani(cs),
                  if (_otoMerkez != null) _otoKaydirmaIsareti(cs, _otoMerkez!),
                ]),
              ),
            ),
          ),
        ]),
      ),
    );
  }

  Widget _goruntuleyici(ColorScheme cs, bool koyu) {
    return PdfViewer.file(
      widget.yol,
      controller: _ctrl,
      params: PdfViewerParams(
        margin: 14,
        backgroundColor: koyu ? const Color(0xFF2B2F36) : const Color(0xFFE5E7EB),
        // Boyut derleme sırasında da değişebilir: sığdırma sonraya
        // ertelenir (ard arda değişimlerde bir kez yapılır).
        onViewSizeChanged: (yeni, eski, c) {
          if (eski == null || _kip == 'serbest') return;
          if ((yeni.width - eski.width).abs() < 1 && (yeni.height - eski.height).abs() < 1) {
            return;
          }
          _yenidenSigdir?.cancel();
          _yenidenSigdir = Timer(const Duration(milliseconds: 150), () {
            if (!mounted || !_ctrl.isReady) return;
            _kip == 'sayfa' ? _sayfayiSigdir() : _genisligeSigdir();
          });
        },
        onViewerReady: (doc, c) {
          if (!mounted) return;
          setState(() {
            _hazir = true;
            _sayfaSayisi = doc.pages.length;
            _sayfa = c.pageNumber ?? 1;
            _yakinlik = c.currentZoom;
            _sayfaKutusunuGuncelle();
          });
          _sayfaIstegi();
        },
        onPageChanged: (n) {
          if (mounted && n != null) {
            setState(() {
              _sayfa = n;
              _sayfaKutusunuGuncelle();
            });
          }
        },
        // Sağdaki kaydırma tutamacı: sürüklenerek belge hızla
        // gezilir, üstünde o anki sayfa yazar.
        viewerOverlayBuilder: (context, size, handleLinkTap) => [
          PdfViewerScrollThumb(
            controller: _ctrl,
            orientation: ScrollbarOrientation.right,
            thumbSize: const Size(46, 30),
            margin: 4,
            thumbBuilder: (context, boyut, sayfa, c) => MouseRegion(
              cursor: SystemMouseCursors.grab,
              child: Tooltip(
                message: 'Sürükleyerek hızla gez',
                waitDuration: const Duration(milliseconds: 600),
                child: Container(
                  decoration: BoxDecoration(
                    color: cs.primary,
                    borderRadius: BorderRadius.circular(8),
                    boxShadow: const [
                      BoxShadow(color: Color(0x55000000), blurRadius: 6, offset: Offset(0, 2)),
                    ],
                  ),
                  alignment: Alignment.center,
                  child: Text('${sayfa ?? ''}',
                      style: TextStyle(
                          color: cs.onPrimary, fontSize: 12, fontWeight: FontWeight.w700)),
                ),
              ),
            ),
          ),
        ],
        errorBannerBuilder: (context, hata, _, __) => Center(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Text('PDF açılamadı: $hata',
                textAlign: TextAlign.center, style: TextStyle(color: cs.error)),
          ),
        ),
        // Notlar her sayfanın üstüne boyanır (sayfayla birlikte
        // kayar ve büyür).
        pageOverlaysBuilder: _sayfaNotlari,
      ),
    );
  }

  List<Widget> _sayfaNotlari(BuildContext context, Rect alan, PdfPage sayfa) => [
        Positioned.fill(
          child: IgnorePointer(
            child: RepaintBoundary(
              child: CustomPaint(painter: PdfNotBoyayici(_defter, sayfa.pageNumber)),
            ),
          ),
        ),
      ];

  /// Kalem / yazı / silgi seçiliyken sayfanın üstündeki katman: fareyi
  /// görüntüleyiciden önce yakalar (sürükleyince sayfa kaymaz, çizilir).
  /// Tekerlek yine belgeyi kaydırır.
  Widget _aracKatmani(ColorScheme cs) {
    final imlec = switch (_arac) {
      PdfAraci.kalem => SystemMouseCursors.precise,
      PdfAraci.yazi => SystemMouseCursors.text,
      PdfAraci.silgi => SystemMouseCursors.none,
      PdfAraci.el => MouseCursor.defer,
    };
    final silgi = _silgiImlec;
    return MouseRegion(
      cursor: _otoMerkez != null || _ortaSon != null ? SystemMouseCursors.allScroll : imlec,
      onHover:
          _arac == PdfAraci.silgi ? (e) => setState(() => _silgiImlec = e.localPosition) : null,
      onExit: (_) {
        if (_silgiImlec != null) setState(() => _silgiImlec = null);
      },
      child: Listener(
        behavior: HitTestBehavior.opaque,
        onPointerDown: _araciBas,
        onPointerMove: _araciSurukle,
        onPointerUp: _araciBirak,
        onPointerCancel: _araciBirak,
        // macOS dokunmatik yüzeyinde iki parmakla kaydırma / yakınlaştırma.
        onPointerPanZoomStart: _ctrl.handlePointerPanZoomEvent,
        onPointerPanZoomUpdate: _ctrl.handlePointerPanZoomEvent,
        onPointerPanZoomEnd: _ctrl.handlePointerPanZoomEvent,
        onPointerSignal: (e) {
          if (e is PointerScrollEvent && !kisayolTusuBasili()) {
            GestureBinding.instance.pointerSignalResolver
                .register(e, _ctrl.handlePointerSignalEvent);
          }
        },
        child: Stack(children: [
          if (_arac == PdfAraci.silgi && silgi != null)
            Positioned(
              left: silgi.dx - _ayarlar.silgiBoyutu / 2,
              top: silgi.dy - _ayarlar.silgiBoyutu / 2,
              child: IgnorePointer(
                child: Container(
                  width: _ayarlar.silgiBoyutu,
                  height: _ayarlar.silgiBoyutu,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: Colors.white.withValues(alpha: 0.35),
                    border: Border.all(color: const Color(0xFF374151), width: 1.5),
                  ),
                ),
              ),
            ),
        ]),
      ),
    );
  }

  /// Yazı aracının metin kutusu; yazının sayfadaki yerinde durur.
  Widget _yaziAlani(ColorScheme cs) {
    final y = _yazi!;
    final alan = _sayfaAlani(y.sayfa);
    if (alan == null) return const SizedBox.shrink();
    final yer = _ctrl.documentToLocal(
        Offset(alan.left + y.konum.dx * alan.width, alan.top + y.konum.dy * alan.width));
    final punto = (y.boyut * alan.width * _ctrl.currentZoom).clamp(4.0, 400.0);
    const bosluk = 4.0;
    return Positioned(
      left: yer.dx - bosluk - 1.5,
      top: yer.dy - bosluk - 1.5,
      child: CallbackShortcuts(
        bindings: {
          // Enter bitirir, Shift+Enter yeni satır, Esc vazgeçer.
          const SingleActivator(LogicalKeyboardKey.enter): _yaziyiBitir,
          const SingleActivator(LogicalKeyboardKey.numpadEnter): _yaziyiBitir,
          const SingleActivator(LogicalKeyboardKey.escape): () => _yaziyiBitir(iptal: true),
        },
        child: Container(
          padding: const EdgeInsets.all(bosluk),
          constraints: const BoxConstraints(minWidth: 60),
          decoration: BoxDecoration(
            color: Colors.white.withValues(alpha: 0.55),
            borderRadius: BorderRadius.circular(4),
            border: Border.all(color: cs.primary, width: 1.5),
          ),
          child: IntrinsicWidth(
            child: TextField(
              key: const ValueKey('pdf-yazi-kutusu'),
              controller: _yaziKutusu,
              focusNode: _yaziOdak,
              maxLines: null,
              keyboardType: TextInputType.multiline,
              cursorColor: Color(y.renk),
              style: pdfYaziBicimi(Color(y.renk), punto),
              decoration: InputDecoration.collapsed(
                hintText: 'Buraya yaz…',
                hintStyle: pdfYaziBicimi(Color(y.renk).withValues(alpha: 0.45), punto),
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _otoKaydirmaIsareti(ColorScheme cs, Offset merkez) {
    const r = 15.0;
    return Positioned(
      left: merkez.dx - r,
      top: merkez.dy - r,
      child: IgnorePointer(
        child: Container(
          width: r * 2,
          height: r * 2,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            color: cs.surface.withValues(alpha: 0.9),
            border: Border.all(color: cs.primary, width: 1.5),
            boxShadow: const [BoxShadow(color: Color(0x44000000), blurRadius: 4)],
          ),
          child: Icon(Icons.open_with_rounded, size: 18, color: cs.primary),
        ),
      ),
    );
  }

  // ---------------------------------------------------------------------------
  // Araç çubuğu (ikinci satır)
  // ---------------------------------------------------------------------------

  Widget _aracCubugu(ColorScheme cs) {
    final yineleTusu = suankiIsletim == Isletim.macos
        ? '${kisayolTusuAdi()} + Shift + Z'
        : '${kisayolTusuAdi()} + Y';
    Widget arac(PdfAraci a, IconData ikon, String ipucu) => PanelDugmesi(
          key: ValueKey('pdf-arac-${a.name}'),
          ikon: ikon,
          ipucu: ipucu,
          secili: _arac == a,
          onPressed: _hazir ? () => _aracSec(a) : null,
        );
    final ayrac = Padding(
      padding: const EdgeInsets.symmetric(horizontal: 8),
      child: SizedBox(height: 20, child: VerticalDivider(width: 1, color: cs.outlineVariant)),
    );
    final sol = Row(mainAxisSize: MainAxisSize.min, children: [
      arac(PdfAraci.el, Icons.pan_tool_outlined, 'Gez: sürükleyerek sayfaları kaydır (Esc)'),
      arac(PdfAraci.kalem, Icons.edit_outlined, 'Kalem: sayfaya çiz'),
      arac(PdfAraci.yazi, Icons.text_fields_rounded, 'Yazı: sayfaya tıkla ve yaz'),
      arac(PdfAraci.silgi, Icons.cleaning_services_outlined,
          'Silgi: çizgilerin ve yazıların üstünden geç'),
      ayrac,
      ..._aracAyarlari(cs),
    ]);
    final sag = Row(mainAxisSize: MainAxisSize.min, children: [
      const SizedBox(width: 12),
      PanelDugmesi(
        key: const ValueKey('pdf-geri-al'),
        ikon: Icons.undo_rounded,
        ipucu: 'Geri al (${kisayolTusuAdi()} + Z)',
        onPressed: _defter.geriAlinabilir || _yazi != null ? _geriAl : null,
      ),
      PanelDugmesi(
        key: const ValueKey('pdf-yinele'),
        ikon: Icons.redo_rounded,
        ipucu: 'Yinele ($yineleTusu)',
        onPressed: _defter.yinelenebilir ? _yinele : null,
      ),
      PanelDugmesi(
        key: const ValueKey('pdf-ilk-hal'),
        ikon: Icons.restart_alt_rounded,
        ipucu: "${_kitapMi ? 'Kitabı' : "PDF'i"} ilk hâline döndür "
            '(bütün çizimleri ve yazıları siler)',
        onPressed: _defter.bos ? null : _ilkHalineDondur,
      ),
    ]);
    // Araçlar ve ayarları dar yerde kayar; geri al / yinele / ilk hâl hep
    // görünür kalır.
    return Container(
      height: 38,
      padding: const EdgeInsets.only(left: 10, right: 6),
      decoration: BoxDecoration(
        color: cs.surfaceContainerLow,
        border: Border(bottom: BorderSide(color: cs.outlineVariant)),
      ),
      child: Row(children: [
        Expanded(
          child: SingleChildScrollView(scrollDirection: Axis.horizontal, child: sol),
        ),
        sag,
      ]),
    );
  }

  /// Seçili aracın ayarları: renk, kalınlık, koyuluk, boyut.
  List<Widget> _aracAyarlari(ColorScheme cs) {
    final a = _ayarlar;
    final ipucuBicimi = TextStyle(fontSize: 12, color: cs.onSurface.withValues(alpha: 0.7));
    switch (_arac) {
      case PdfAraci.el:
        return [
          Text('Orta tekerleğe basılı tutup sürükleyerek de gezebilirsin', style: ipucuBicimi),
        ];
      case PdfAraci.kalem:
        return [
          _renkSecici(cs, a.kalemRengi, (r) => a.degistir(() => a.kalemRengi = r)),
          const SizedBox(width: 10),
          _kaydirici(
              cs,
              'Kalınlık',
              a.kalemKalinligi,
              PdfAracAyarlari.kalemEnAz,
              PdfAracAyarlari.kalemEnCok,
              '${a.kalemKalinligi.round()}',
              (v) => a.degistir(() => a.kalemKalinligi = v.roundToDouble())),
          _kaydirici(
              cs,
              'Koyuluk',
              a.kalemSaydamligi,
              PdfAracAyarlari.saydamlikEnAz,
              1,
              '%${(a.kalemSaydamligi * 100).round()}',
              (v) => a.degistir(() => a.kalemSaydamligi = (v * 20).round() / 20)),
        ];
      case PdfAraci.yazi:
        return [
          _renkSecici(cs, _yazi?.renk ?? a.yaziRengi, (r) {
            a.degistir(() => a.yaziRengi = r);
            _yazi?.renk = r;
            _odagiGeriVer();
          }),
          const SizedBox(width: 10),
          _kaydirici(cs, 'Boyut', a.yaziBoyutu, PdfAracAyarlari.yaziEnAz, PdfAracAyarlari.yaziEnCok,
              '${a.yaziBoyutu.round()}', (v) {
            a.degistir(() => a.yaziBoyutu = v.roundToDouble());
            final y = _yazi;
            final alan = y == null ? null : _sayfaAlani(y.sayfa);
            if (y != null && alan != null) y.boyut = a.yaziBoyutu / alan.width;
          }),
          Text('Enter: bitir · Shift+Enter: yeni satır', style: ipucuBicimi),
        ];
      case PdfAraci.silgi:
        return [
          _kaydirici(
              cs,
              'Boyut',
              a.silgiBoyutu,
              PdfAracAyarlari.silgiEnAz,
              PdfAracAyarlari.silgiEnCok,
              '${a.silgiBoyutu.round()}',
              (v) => a.degistir(() => a.silgiBoyutu = v.roundToDouble())),
          Text('Silmek istediğin çizginin ya da yazının üstünden geç', style: ipucuBicimi),
        ];
    }
  }

  static const _renkAdlari = [
    'Siyah',
    'Kırmızı',
    'Turuncu',
    'Sarı',
    'Yeşil',
    'Mavi',
    'Mor',
    'Pembe',
    'Beyaz',
  ];

  Widget _renkSecici(ColorScheme cs, int secili, ValueChanged<int> sec) {
    return Row(mainAxisSize: MainAxisSize.min, children: [
      for (var i = 0; i < PdfAracAyarlari.renkler.length; i++)
        Tooltip(
          message: _renkAdlari[i],
          waitDuration: const Duration(milliseconds: 400),
          child: MouseRegion(
            cursor: SystemMouseCursors.click,
            child: GestureDetector(
              key: ValueKey('pdf-renk-$i'),
              onTap: () => sec(PdfAracAyarlari.renkler[i]),
              child: Container(
                width: 22,
                height: 22,
                margin: const EdgeInsets.symmetric(horizontal: 1.5),
                alignment: Alignment.center,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  border: Border.all(
                      color: secili == PdfAracAyarlari.renkler[i] ? cs.primary : Colors.transparent,
                      width: 2),
                ),
                child: Container(
                  width: 15,
                  height: 15,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: Color(PdfAracAyarlari.renkler[i]),
                    border: Border.all(color: cs.outline.withValues(alpha: 0.6)),
                  ),
                ),
              ),
            ),
          ),
        ),
    ]);
  }

  Widget _kaydirici(ColorScheme cs, String ad, double deger, double enAz, double enCok,
      String gosterim, ValueChanged<double> degisti) {
    return Row(mainAxisSize: MainAxisSize.min, children: [
      Text(ad, style: TextStyle(fontSize: 12, color: cs.onSurface.withValues(alpha: 0.8))),
      SizedBox(
        width: 110,
        height: 30,
        child: SliderTheme(
          data: SliderTheme.of(context).copyWith(
            trackHeight: 3,
            thumbShape: const RoundSliderThumbShape(enabledThumbRadius: 7),
            overlayShape: const RoundSliderOverlayShape(overlayRadius: 13),
          ),
          child: Slider(
            key: ValueKey('pdf-ayar-$ad'),
            value: deger.clamp(enAz, enCok),
            min: enAz,
            max: enCok,
            onChanged: degisti,
            onChangeEnd: (_) => _odagiGeriVer(),
          ),
        ),
      ),
      SizedBox(
        width: 42,
        child: Text(gosterim,
            style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: cs.onSurface)),
      ),
      const SizedBox(width: 6),
    ]);
  }
}

/// Yazılmakta olan yazının bilgileri; renk ve boyut yazarken değişebilir.
class _YaziDuzeni {
  _YaziDuzeni({
    required this.sayfa,
    required this.konum,
    required this.eski,
    required this.renk,
    required this.boyut,
  });

  final int sayfa;
  final Offset konum;
  final PdfYazi? eski;
  int renk;
  double boyut;
}
