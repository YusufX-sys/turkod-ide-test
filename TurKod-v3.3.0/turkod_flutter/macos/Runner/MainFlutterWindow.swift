import Cocoa
import FlutterMacOS

class MainFlutterWindow: NSWindow {
  override func awakeFromNib() {
    let flutterViewController = FlutterViewController()
    self.contentViewController = flutterViewController
    // Şablonun 800x600 penceresi IDE için dardı: 1280x800 (ekran küçükse sığdırılır),
    // ortada açılır. Başlık uygulama adından gelir (Info.plist: TürKod).
    self.title = "TürKod"
    self.minSize = NSSize(width: 900, height: 600)
    let ekran = NSScreen.main?.visibleFrame.size ?? NSSize(width: 1280, height: 800)
    self.setContentSize(NSSize(width: min(1280, ekran.width - 40),
                               height: min(800, ekran.height - 40)))
    self.center()

    RegisterGeneratedPlugins(registry: flutterViewController)

    super.awakeFromNib()
  }
}
