import Cocoa
import FlutterMacOS

/// Finder'dan çift tıklanan, Dock'a bırakılan ya da "open -a TurKod.app x.trpy"
/// ile gönderilen dosyalar macOS'ta komut satırıyla değil "belge aç" Apple
/// olayıyla gelir; eskiden hiç ele alınmıyor, TürKod açılıp dosya açılmıyordu.
/// Windows'taki "turkod/tek_ornek" kanalıyla aynı sözleşme: Dart oturumu
/// yükleyince "hazir" çağırıp biriken dosyaları alır, sonrakiler
/// "dosyalariAc" ile gönderilir (lib/main.dart: _tekOrnekKanaliniBagla).
final class DosyaAcmaKoprusu: NSObject {
  static let ortak = DosyaAcmaKoprusu()
  private var bekleyen: [String] = []
  private var dartHazir = false
  private var kanal: FlutterMethodChannel?

  /// Apple olay işleyicisi uygulama açılırken (willFinishLaunching) kurulur:
  /// Apple'ın belgelediği yer burasıdır; daha önce kurulursa AppKit kendi
  /// varsayılanıyla ezer, daha sonra kurulursa açılıştaki olay kaçar.
  func olayiDinle() {
    NotificationCenter.default.addObserver(
      forName: NSApplication.willFinishLaunchingNotification, object: nil, queue: nil
    ) { [weak self] _ in
      guard let self = self else { return }
      NSAppleEventManager.shared().setEventHandler(
        self, andSelector: #selector(self.belgeleriAc(_:yanit:)),
        forEventClass: AEEventClass(kCoreEventClass), andEventID: AEEventID(kAEOpenDocuments))
    }
  }

  func bagla(_ messenger: FlutterBinaryMessenger) {
    let k = FlutterMethodChannel(name: "turkod/tek_ornek", binaryMessenger: messenger)
    k.setMethodCallHandler { [weak self] cagri, sonuc in
      guard let self = self, cagri.method == "hazir" else {
        sonuc(FlutterMethodNotImplemented)
        return
      }
      let liste = self.bekleyen
      self.bekleyen.removeAll()
      self.dartHazir = true
      sonuc(liste)
    }
    kanal = k
  }

  @objc func belgeleriAc(_ olay: NSAppleEventDescriptor, yanit: NSAppleEventDescriptor) {
    guard let liste = olay.paramDescriptor(forKeyword: AEKeyword(keyDirectObject)) else { return }
    var yollar: [String] = []
    if liste.numberOfItems == 0 {
      if let url = liste.fileURLValue { yollar.append(url.path) }
    } else {
      for i in 1...liste.numberOfItems {
        if let url = liste.atIndex(i)?.fileURLValue { yollar.append(url.path) }
      }
    }
    ac(yollar)
    NSApp.activate(ignoringOtherApps: true)
  }

  func ac(_ yollar: [String]) {
    guard !yollar.isEmpty else { return }
    if dartHazir, let k = kanal {
      k.invokeMethod("dosyalariAc", arguments: yollar)
    } else {
      bekleyen.append(contentsOf: yollar)
    }
  }
}

class MainFlutterWindow: NSWindow {
  /// Kodi masaüstü penceresi (TürKod'un ikinci süreci, --kodi-penceresi):
  /// saydam, kenarsız, hep üstte; yalnızca robot ve balonun alanı tıklanır.
  private var kodiKipi = false
  private var kodiKanali: FlutterMethodChannel?
  /// Tıklanabilir alanlar: Flutter koordinatları (sol üst köşe, mantıksal piksel).
  private var bolgeler: [NSRect] = []
  private var fareZamanlayici: Timer?

  // Kenarsız pencere varsayılan olarak klavye alamaz: Kodi'nin balonuna yazılabilsin.
  override var canBecomeKey: Bool { return kodiKipi || super.canBecomeKey }
  override var canBecomeMain: Bool { return kodiKipi || super.canBecomeMain }

  override func awakeFromNib() {
    let argumanlar = Array(CommandLine.arguments.dropFirst())
    kodiKipi = argumanlar.contains("--kodi-penceresi")
    let proje = FlutterDartProject()
    // Dart'ın main(args)'ı Kodi penceresi olduğunu ve komut satırıyla gelen
    // dosyaları (turkod --editor x.trpy) buradan alır.
    proje.dartEntrypointArguments = argumanlar
    let flutterViewController = FlutterViewController(project: proje)
    self.contentViewController = flutterViewController
    if kodiKipi {
      kodiPenceresiniKur(flutterViewController)
    } else {
      DosyaAcmaKoprusu.ortak.olayiDinle()
      DosyaAcmaKoprusu.ortak.bagla(flutterViewController.engine.binaryMessenger)
      // Şablonun 800x600 penceresi IDE için dardı: 1280x800 (ekran küçükse sığdırılır),
      // ortada açılır. Başlık uygulama adından gelir (Info.plist: TürKod).
      self.title = "TürKod"
      self.minSize = NSSize(width: 900, height: 600)
      let ekran = NSScreen.main?.visibleFrame.size ?? NSSize(width: 1280, height: 800)
      self.setContentSize(NSSize(width: min(1280, ekran.width - 40),
                                 height: min(800, ekran.height - 40)))
      self.center()
    }

    RegisterGeneratedPlugins(registry: flutterViewController)

    super.awakeFromNib()
    if kodiKipi && argumanlar.contains("--kodi-gizli") {
      // Önceden hazırlanan pencere gizli bekler ("goster" ile görünür).
      DispatchQueue.main.async { self.orderOut(nil) }
    }
  }

  private func kodiPenceresiniKur(_ vc: FlutterViewController) {
    // Dock'ta ikinci bir TürKod simgesi görünmesin.
    NSApp.setActivationPolicy(.accessory)
    styleMask = [.borderless]
    isOpaque = false
    backgroundColor = .clear
    hasShadow = false
    level = .floating
    collectionBehavior = [.canJoinAllSpaces, .fullScreenAuxiliary]
    vc.backgroundColor = .clear
    title = "Kodi"
    setContentSize(NSSize(width: 440, height: 760))
    konumla(NSEvent.mouseLocation)

    let kanal = FlutterMethodChannel(name: "turkod/kodi_penceresi",
                                     binaryMessenger: vc.engine.binaryMessenger)
    kanal.setMethodCallHandler { [weak self] cagri, sonuc in
      self?.isle(cagri, sonuc)
    }
    kodiKanali = kanal
    // Tıklamalar robot ve balonun dışında alttaki pencerelere geçer: fare
    // bölgelerin dışındayken pencere fareyi yok sayar.
    fareZamanlayici = Timer.scheduledTimer(withTimeInterval: 0.05, repeats: true) {
      [weak self] _ in self?.fareyiDenetle()
    }
  }

  /// Robot sağ altta durur: fare robotun ortasına gelsin (Windows ile aynı).
  private func konumla(_ fare: NSPoint) {
    let boyut = frame.size
    var koken = NSPoint(x: fare.x - boyut.width + 64, y: fare.y - 70)
    let ekran = NSScreen.screens.first { NSMouseInRect(fare, $0.frame, false) } ?? NSScreen.main
    if let alan = ekran?.visibleFrame {
      koken.x = min(max(koken.x, alan.minX), alan.maxX - boyut.width)
      koken.y = min(max(koken.y, alan.minY), alan.maxY - boyut.height)
    }
    setFrameOrigin(koken)
  }

  private func fareyiDenetle() {
    guard isVisible, let icerik = contentView else { return }
    let m = mouseLocationOutsideOfEventStream
    let nokta = NSPoint(x: m.x, y: icerik.bounds.height - m.y)
    let icinde = bolgeler.contains { $0.contains(nokta) }
    if ignoresMouseEvents == icinde {
      ignoresMouseEvents = !icinde
    }
  }

  private func sayi(_ v: Any) -> CGFloat {
    if let d = v as? Double { return CGFloat(d) }
    if let i = v as? Int { return CGFloat(i) }
    if let n = v as? NSNumber { return CGFloat(n.doubleValue) }
    return 0
  }

  private func isle(_ cagri: FlutterMethodCall, _ sonuc: @escaping FlutterResult) {
    switch cagri.method {
    case "goster":
      // Konum fareden alınır (Windows'taki fiziksel piksel koordinatları burada yok).
      konumla(NSEvent.mouseLocation)
      orderFrontRegardless()
      sonuc(nil)
    case "gizle":
      orderOut(nil)
      sonuc(nil)
    case "kapat":
      sonuc(nil)
      NSApp.terminate(nil)
    case "bolge":
      var yeni: [NSRect] = []
      for parca in (cagri.arguments as? [Any]) ?? [] {
        guard let d = parca as? [Any], d.count >= 4 else { continue }
        yeni.append(NSRect(x: sayi(d[0]), y: sayi(d[1]), width: sayi(d[2]), height: sayi(d[3])))
      }
      bolgeler = yeni
      fareyiDenetle()
      sonuc(nil)
    case "surukle":
      // Pencere fareyle taşınır; düğme bırakılana kadar (Windows'un taşıma döngüsü gibi).
      guard NSEvent.pressedMouseButtons & 1 == 1 else { sonuc(false); return }
      let baslangic = NSEvent.mouseLocation
      let koken = frame.origin
      while true {
        guard let olay = nextEvent(matching: [.leftMouseDragged, .leftMouseUp],
                                   until: Date.distantFuture, inMode: .eventTracking,
                                   dequeue: true) else { break }
        if olay.type == .leftMouseUp { break }
        let m = NSEvent.mouseLocation
        setFrameOrigin(NSPoint(x: koken.x + m.x - baslangic.x, y: koken.y + m.y - baslangic.y))
      }
      sonuc(false)
    case "anaPencereyiOneGetir":
      // Aynı uygulamanın öbür süreci (asıl TürKod penceresi) öne gelir.
      let ben = NSRunningApplication.current.processIdentifier
      if let kimlik = Bundle.main.bundleIdentifier {
        for uygulama in NSRunningApplication.runningApplications(withBundleIdentifier: kimlik)
        where uygulama.processIdentifier != ben {
          uygulama.activate(options: [.activateIgnoringOtherApps])
        }
      }
      sonuc(nil)
    default:
      sonuc(FlutterMethodNotImplemented)
    }
  }
}
