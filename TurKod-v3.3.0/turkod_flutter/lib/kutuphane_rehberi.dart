// Öğren → Kütüphane Rehberi: TürKod'un tanıdığı bütün kütüphanelerin
// ayrıntılı açıklaması, Türkçe adları, bütün çevirileri ve örnek kodu.
// Veriler arka uçtan gelir (turkod_ide/kutuphane_rehberi.py).
part of 'main.dart';

Future<void> kutuphaneRehberiniAc(BuildContext context) => showDialog<void>(
      context: context,
      builder: (_) => const KutuphaneRehberi(),
    );

/// Arama için: Türkçe büyük/küçük harf (İ/ı) ve Türkçe harfsiz yazım
/// ("satranc" -> "satranç") aynı sayılır; "_" boşluk gibidir.
String rehberAramaAnahtari(String metin) {
  const donustur = {
    'İ': 'i',
    'I': 'i',
    'ı': 'i',
    'Ç': 'c',
    'ç': 'c',
    'Ğ': 'g',
    'ğ': 'g',
    'Ö': 'o',
    'ö': 'o',
    'Ş': 's',
    'ş': 's',
    'Ü': 'u',
    'ü': 'u',
    'â': 'a',
    'Â': 'a',
    'î': 'i',
    'û': 'u',
    '_': ' ',
  };
  final b = StringBuffer();
  for (final h in metin.split('')) {
    b.write(donustur[h] ?? h.toLowerCase());
  }
  return b.toString();
}

class KutuphaneRehberi extends StatefulWidget {
  const KutuphaneRehberi({super.key});

  @override
  State<KutuphaneRehberi> createState() => _KutuphaneRehberiState();
}

class _KutuphaneRehberiState extends State<KutuphaneRehberi> {
  List<Map<String, dynamic>> _liste = [];
  String? _hata;
  bool _yukleniyor = true;
  String _arama = '';
  String? _secili;
  final Map<String, Map<String, dynamic>> _ayrintilar = {};
  bool _ayrintiYukleniyor = false;

  BackendService get _backend => context.read<BackendService>();

  @override
  void initState() {
    super.initState();
    _listeyiYukle();
  }

  Future<void> _listeyiYukle() async {
    try {
      final r = await _backend.call('kutuphane_listesi');
      if (!mounted) return;
      final liste = (r['kutuphaneler'] as List? ?? [])
          .map((e) => Map<String, dynamic>.from(e as Map))
          .toList();
      setState(() {
        _liste = liste;
        _yukleniyor = false;
      });
      if (liste.isNotEmpty) _sec(liste.first['py'] as String);
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _yukleniyor = false;
        _hata = 'Kütüphane listesi alınamadı: $e';
      });
    }
  }

  Future<void> _sec(String py) async {
    setState(() => _secili = py);
    if (_ayrintilar.containsKey(py)) return;
    setState(() => _ayrintiYukleniyor = true);
    try {
      final r = await _backend.call('kutuphane_ayrintisi', {'py': py});
      if (!mounted) return;
      setState(() => _ayrintilar[py] = r);
    } catch (e) {
      if (!mounted) return;
      setState(() => _ayrintilar[py] = {'ok': false, 'hata': '$e'});
    } finally {
      if (mounted) setState(() => _ayrintiYukleniyor = false);
    }
  }

  bool _eslesir(Map<String, dynamic> k) {
    final a = rehberAramaAnahtari(_arama.trim());
    if (a.isEmpty) return true;
    final adlar = (k['turkce_adlar'] as List? ?? []).join(' ');
    return rehberAramaAnahtari(
            '${k['py']} ${k['ad']} ${k['ozet']} ${k['kategori']} $adlar')
        .contains(a);
  }

  @override
  Widget build(BuildContext context) {
    final boyut = MediaQuery.of(context).size;
    return Dialog(
      insetPadding: const EdgeInsets.all(24),
      child: SizedBox(
        width: boyut.width * 0.9,
        height: boyut.height * 0.88,
        child: Column(children: [
          _baslik(context),
          const Divider(height: 1),
          Expanded(
            child: _yukleniyor
                ? const Center(child: CircularProgressIndicator())
                : _hata != null
                    ? Center(child: Text(_hata!))
                    : Row(children: [
                        SizedBox(width: 300, child: _solListe(context)),
                        const VerticalDivider(width: 1),
                        Expanded(child: _ayrinti(context)),
                      ]),
          ),
        ]),
      ),
    );
  }

  Widget _baslik(BuildContext context) => Padding(
        padding: const EdgeInsets.fromLTRB(16, 10, 8, 10),
        child: Row(children: [
          const Icon(Icons.local_library_outlined),
          const SizedBox(width: 10),
          const Expanded(
            child: Text('Kütüphane Rehberi',
                style: TextStyle(fontSize: 17, fontWeight: FontWeight.w600)),
          ),
          if (!_yukleniyor && _hata == null)
            Text('${_liste.length} kütüphane',
                style: TextStyle(
                    fontSize: 12,
                    color: Theme.of(context)
                        .colorScheme
                        .onSurface
                        .withValues(alpha: 0.6))),
          IconButton(
            tooltip: 'Kapat',
            icon: const Icon(Icons.close),
            onPressed: () => Navigator.pop(context),
          ),
        ]),
      );

  Widget _solListe(BuildContext context) {
    final tema = Theme.of(context);
    final gorunen = _liste.where(_eslesir).toList();
    final ogeler = <Widget>[];
    String? kategori;
    for (final k in gorunen) {
      if (k['kategori'] != kategori) {
        kategori = k['kategori'] as String?;
        ogeler.add(Padding(
          padding: const EdgeInsets.fromLTRB(12, 12, 12, 4),
          child: Text((kategori ?? '').toUpperCase(),
              style: TextStyle(
                  fontSize: 11,
                  fontWeight: FontWeight.w600,
                  letterSpacing: 0.6,
                  color: tema.colorScheme.primary)),
        ));
      }
      final py = k['py'] as String;
      ogeler.add(ListTile(
        key: ValueKey('kutuphane_$py'),
        dense: true,
        selected: py == _secili,
        title: Text('${k['ad']}', style: const TextStyle(fontSize: 13)),
        subtitle: Text('${k['turkce_ad'] ?? py}',
            style: TextStyle(
                fontSize: 11,
                fontFamily: kMonoFontFamily,
                fontFamilyFallback: kMonoFontFallback)),
        trailing: k['standart'] == true
            ? null
            : const Tooltip(
                message: 'Ayrıca kurulması gerekir',
                child: Icon(Icons.download_outlined, size: 16)),
        onTap: () => _sec(py),
      ));
    }
    return Column(children: [
      Padding(
        padding: const EdgeInsets.all(8),
        child: TextField(
          key: const ValueKey('kutuphane_arama'),
          autofocus: true,
          decoration: const InputDecoration(
            isDense: true,
            prefixIcon: Icon(Icons.search, size: 18),
            hintText: 'Kütüphane ara (ad, konu, Türkçe ad)…',
            border: OutlineInputBorder(),
          ),
          onChanged: (v) => setState(() => _arama = v),
        ),
      ),
      Expanded(
        child: gorunen.isEmpty
            ? const Center(child: Text('Eşleşen kütüphane yok.'))
            : ListView(children: ogeler),
      ),
    ]);
  }

  Widget _ayrinti(BuildContext context) {
    final py = _secili;
    if (py == null) return const SizedBox.shrink();
    final a = _ayrintilar[py];
    if (a == null) {
      return _ayrintiYukleniyor
          ? const Center(child: CircularProgressIndicator())
          : const SizedBox.shrink();
    }
    if (a['ok'] != true) {
      return Center(child: Text('${a['hata'] ?? 'Ayrıntı alınamadı.'}'));
    }
    return _KutuphaneAyrintisi(key: ValueKey('ayrinti_$py'), veri: a);
  }
}

class _KutuphaneAyrintisi extends StatefulWidget {
  final Map<String, dynamic> veri;
  const _KutuphaneAyrintisi({super.key, required this.veri});

  @override
  State<_KutuphaneAyrintisi> createState() => _KutuphaneAyrintisiState();
}

class _KutuphaneAyrintisiState extends State<_KutuphaneAyrintisi> {
  String _uyeArama = '';
  bool _turkodOrnek = true;

  Map<String, dynamic> get v => widget.veri;

  List<List<String>> _ciftler(String anahtar) => (v[anahtar] as List? ?? [])
      .map((e) => (e as List).map((x) => x.toString()).toList())
      .toList();

  @override
  Widget build(BuildContext context) {
    final tema = Theme.of(context);
    final soluk = tema.colorScheme.onSurface.withValues(alpha: 0.65);
    final adlar = (v['turkce_adlar'] as List? ?? []).cast<Object>();
    final ilkAd = adlar.isEmpty ? v['py'] : adlar.first;
    final uyeler = _ciftler('uyeler');
    final metotlar = _ciftler('metotlar');
    final a = _uyeArama.trim().toLowerCase();
    bool eslesir(List<String> c) =>
        a.isEmpty || c.any((x) => x.toLowerCase().contains(a));
    final uyeSuzulmus = uyeler.where(eslesir).toList();
    final metotSuzulmus = metotlar.where(eslesir).toList();

    return CustomScrollView(slivers: [
      SliverPadding(
        padding: const EdgeInsets.fromLTRB(20, 16, 20, 0),
        sliver: SliverList.list(children: [
          Text('${v['ad']}',
              style:
                  const TextStyle(fontSize: 22, fontWeight: FontWeight.w600)),
          const SizedBox(height: 4),
          Text('${v['ozet']}', style: TextStyle(fontSize: 14, color: soluk)),
          const SizedBox(height: 10),
          Wrap(spacing: 6, runSpacing: 6, children: [
            Chip(
                visualDensity: VisualDensity.compact,
                label: Text('${v['kategori']}')),
            Chip(
                visualDensity: VisualDensity.compact,
                avatar: Icon(
                    v['standart'] == true
                        ? Icons.check_circle_outline
                        : Icons.download_outlined,
                    size: 16),
                label: Text(v['standart'] == true
                    ? 'Python ile birlikte gelir'
                    : 'Ayrıca kurulur')),
            Chip(
                visualDensity: VisualDensity.compact,
                label: Text(uyeler.isEmpty && metotlar.isEmpty
                    ? 'Python adlarıyla yazılır'
                    : '${uyeler.length + metotlar.length} Türkçe karşılık')),
          ]),
          const SizedBox(height: 14),
          _bilgiSatiri('İçe aktarma', 'içe_aktar ${v['turkce_ad'] ?? ilkAd}'),
          if (adlar.length > 1)
            _bilgiSatiri('Öbür adları',
                adlar.where((ad) => ad != v['turkce_ad']).join('   ·   ')),
          if (v['kurulum'] != null)
            _bilgiSatiri('Kurulum (terminalde)', '${v['kurulum']}'),
          const SizedBox(height: 16),
          Row(children: [
            _bolumBasligi('Açıklama'),
            const Spacer(),
            _dilSecici(),
          ]),
          ..._aciklamaParagraflari(context,
              '${(_turkodOrnek ? v['aciklama_turkod'] : null) ?? v['aciklama'] ?? ''}'),
          if ('${v['ornek_python'] ?? ''}'.isNotEmpty) ...[
            const SizedBox(height: 12),
            _ornek(context),
          ],
          const SizedBox(height: 18),
          _bolumBasligi('Bütün Türkçe karşılıklar'),
          Text(
            'Bu kütüphanedeki adları Türkçe yazabilirsin; TürKod çalıştırırken '
            'Python adına çevirir. Örnek: $ilkAd.'
            '${uyeler.isNotEmpty ? uyeler.first[0] : '...'}',
            style: TextStyle(fontSize: 12.5, color: soluk),
          ),
          const SizedBox(height: 8),
          TextField(
            key: const ValueKey('kutuphane_uye_arama'),
            decoration: const InputDecoration(
              isDense: true,
              prefixIcon: Icon(Icons.search, size: 18),
              hintText: 'Türkçe ya da Python adıyla ara…',
              border: OutlineInputBorder(),
            ),
            onChanged: (s) => setState(() => _uyeArama = s),
          ),
          const SizedBox(height: 8),
        ]),
      ),
      if (uyeSuzulmus.isNotEmpty) ...[
        _altBaslik(context, 'Modül üyeleri', uyeSuzulmus.length),
        _ciftListesi(uyeSuzulmus),
      ],
      if (metotSuzulmus.isNotEmpty) ...[
        _altBaslik(context, 'Nesne metotları', metotSuzulmus.length),
        _ciftListesi(metotSuzulmus),
      ],
      if (uyeSuzulmus.isEmpty && metotSuzulmus.isEmpty)
        SliverToBoxAdapter(
          child: Padding(
            padding: const EdgeInsets.all(20),
            child: Text(
                uyeler.isEmpty && metotlar.isEmpty
                    ? 'Bu kütüphanenin üyeleri Python adlarıyla yazılır.'
                    : 'Eşleşen ad yok.',
                style: TextStyle(color: soluk)),
          ),
        ),
      const SliverToBoxAdapter(child: SizedBox(height: 24)),
    ]);
  }

  Widget _bolumBasligi(String metin) => Padding(
        padding: const EdgeInsets.only(bottom: 8),
        child: Text(metin,
            style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w600)),
      );

  Widget _bilgiSatiri(String etiket, String deger) => Padding(
        padding: const EdgeInsets.only(bottom: 6),
        child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          SizedBox(
              width: 150,
              child: Text(etiket,
                  style: const TextStyle(
                      fontSize: 12.5, fontWeight: FontWeight.w600))),
          Expanded(
              child: SelectableText(deger,
                  style: TextStyle(
                      fontSize: 12.5,
                      fontFamily: kMonoFontFamily,
                      fontFamilyFallback: kMonoFontFallback))),
        ]),
      );

  /// `ters tırnak` içindeki adlar kod yazı tipiyle, "- " satırları madde
  /// işaretiyle gösterilir.
  List<Widget> _aciklamaParagraflari(BuildContext context, String metin) {
    final tema = Theme.of(context);
    final kodStili = TextStyle(
      fontFamily: kMonoFontFamily,
      fontFamilyFallback: kMonoFontFallback,
      fontSize: 13,
      backgroundColor: tema.colorScheme.surfaceContainerHighest,
    );
    TextSpan satir(String s) {
      final parcalar = s.split('`');
      return TextSpan(children: [
        for (var i = 0; i < parcalar.length; i++)
          TextSpan(text: parcalar[i], style: i.isOdd ? kodStili : null),
      ]);
    }

    final sonuc = <Widget>[];
    for (final paragraf in metin.split(RegExp(r'\n\s*\n'))) {
      for (final s in paragraf.split('\n')) {
        if (s.trim().isEmpty) continue;
        final madde = s.trimLeft().startsWith('- ');
        final govde = madde ? s.trimLeft().substring(2) : s;
        sonuc.add(Padding(
          padding: EdgeInsets.only(left: madde ? 12 : 0, bottom: 4),
          child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
            if (madde) const Text('•  ', style: TextStyle(fontSize: 14)),
            Expanded(
              child: SelectableText.rich(
                satir(govde),
                style: const TextStyle(fontSize: 14, height: 1.45),
              ),
            ),
          ]),
        ));
      }
      sonuc.add(const SizedBox(height: 8));
    }
    return sonuc;
  }

  /// TürKod / Python seçimi: açıklamadaki kod parçalarını ve örneği birlikte
  /// değiştirir (varsayılan TürKod: kütüphanenin Türkçe adlarıyla).
  Widget _dilSecici() => SegmentedButton<bool>(
        showSelectedIcon: false,
        style: const ButtonStyle(visualDensity: VisualDensity.compact),
        segments: const [
          ButtonSegment(value: true, label: Text('TürKod')),
          ButtonSegment(value: false, label: Text('Python')),
        ],
        selected: {_turkodOrnek},
        onSelectionChanged: (s) => setState(() => _turkodOrnek = s.first),
      );

  Widget _ornek(BuildContext context) {
    final tema = Theme.of(context);
    final turkod = '${v['ornek_turkod'] ?? ''}';
    final python = '${v['ornek_python'] ?? ''}';
    final gosterilen = _turkodOrnek && turkod.isNotEmpty ? turkod : python;
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Row(children: [
        _bolumBasligi('Örnek'),
        const Spacer(),
        _dilSecici(),
        const SizedBox(width: 8),
        IconButton(
          tooltip: 'Kopyala',
          icon: const Icon(Icons.copy, size: 18),
          onPressed: () {
            Clipboard.setData(ClipboardData(text: gosterilen));
            ScaffoldMessenger.maybeOf(context)?.showSnackBar(
                const SnackBar(content: Text('Örnek kopyalandı.')));
          },
        ),
        TextButton.icon(
          icon: const Icon(Icons.open_in_new, size: 18),
          label: const Text('Editörde aç'),
          onPressed: () {
            final ed = context.read<EditorProvider>();
            final ad = '${v['py']}'.replaceAll('.', '_');
            Navigator.pop(context);
            // Pencere kapandığı için bağlam verilmez; aynı adlı sekme varsa
            // ad kendiliğinden benzersiz yapılır.
            ed.createUntitled(
              name: _turkodOrnek ? '${ad}_ornek.trpy' : '${ad}_ornek.py',
              content: gosterilen,
              dirty: true,
            );
          },
        ),
      ]),
      Container(
        width: double.infinity,
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: tema.colorScheme.surfaceContainerHighest,
          borderRadius: BorderRadius.circular(6),
        ),
        child: SelectableText(gosterilen.trimRight(),
            style: TextStyle(
                fontFamily: kMonoFontFamily,
                fontFamilyFallback: kMonoFontFallback,
                fontSize: 13,
                height: 1.4)),
      ),
    ]);
  }

  Widget _altBaslik(BuildContext context, String metin, int sayi) =>
      SliverToBoxAdapter(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(20, 10, 20, 4),
          child: Row(children: [
            Expanded(
                child: Text('Türkçe',
                    style: TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.w600,
                        color: Theme.of(context).colorScheme.primary))),
            Expanded(
                child: Text('Python  ·  $metin ($sayi)',
                    style: TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.w600,
                        color: Theme.of(context).colorScheme.primary))),
          ]),
        ),
      );

  Widget _ciftListesi(List<List<String>> ciftler) {
    final stil = TextStyle(
        fontFamily: kMonoFontFamily,
        fontFamilyFallback: kMonoFontFallback,
        fontSize: 12.5);
    return SliverPadding(
      padding: const EdgeInsets.symmetric(horizontal: 20),
      sliver: SliverFixedExtentList(
        itemExtent: 26,
        delegate: SliverChildBuilderDelegate(
          (context, i) {
            final c = ciftler[i];
            return Row(children: [
              Expanded(child: SelectableText(c[0], maxLines: 1, style: stil)),
              Expanded(child: SelectableText(c[1], maxLines: 1, style: stil)),
            ]);
          },
          childCount: ciftler.length,
        ),
      ),
    );
  }
}
