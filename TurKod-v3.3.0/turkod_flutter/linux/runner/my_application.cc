#include "my_application.h"

#include <flutter_linux/flutter_linux.h>
#ifdef GDK_WINDOWING_X11
#include <gdk/gdkx.h>
#endif

#include "flutter/generated_plugin_registrant.h"

struct _MyApplication {
  GtkApplication parent_instance;
  char** dart_entrypoint_arguments;
  // Kodi masaüstü penceresi (TürKod'un ikinci süreci, --kodi-penceresi):
  // saydam, kenarsız, hep üstte; yalnızca robot ve balonun alanı tıklanır.
  gboolean kodi_kipi;
  gboolean kodi_gizli;
  GtkWindow* pencere;
  FlMethodChannel* kodi_kanali;
  // Tek editör örneği: ikinci başlatmada ("Editör ile aç") dosyalar bu
  // pencereye iletilir. Dart "hazir" diyene kadar biriktirilir.
  FlMethodChannel* tek_ornek_kanali;
  GPtrArray* bekleyen_dosyalar;  // gchar* (g_free)
  gboolean dart_hazir;
};

G_DEFINE_TYPE(MyApplication, my_application, GTK_TYPE_APPLICATION)

// Called when first Flutter frame received.
static void first_frame_cb(MyApplication* self, FlView* view) {
  // Önceden hazırlanan Kodi penceresi gizli kalır ("goster" bekler).
  if (self->kodi_kipi && self->kodi_gizli) return;
  gtk_widget_show(gtk_widget_get_toplevel(GTK_WIDGET(view)));
}

static gboolean arguman_var(char** argumanlar, const char* ad) {
  if (argumanlar == nullptr) return FALSE;
  for (char** a = argumanlar; *a != nullptr; a++) {
    if (g_strcmp0(*a, ad) == 0) return TRUE;
  }
  return FALSE;
}

// Robot sağ altta durur: fare robotun ortasına gelsin (Windows ile aynı).
// Wayland pencere konumunu uygulamaya bırakmaz; orada pencere yöneticisi yerleştirir.
static void kodi_konumla(GtkWindow* pencere) {
  GdkDisplay* ekran = gdk_display_get_default();
  if (ekran == nullptr) return;
  GdkSeat* koltuk = gdk_display_get_default_seat(ekran);
  GdkDevice* fare = koltuk ? gdk_seat_get_pointer(koltuk) : nullptr;
  if (fare == nullptr) return;
  gint x = 0, y = 0;
  gdk_device_get_position(fare, nullptr, &x, &y);
  gint genislik = 440, yukseklik = 760;
  gtk_window_get_size(pencere, &genislik, &yukseklik);
  gint sol = x - genislik + 64;
  gint ust = y - yukseklik + 70;
  GdkMonitor* monitor = gdk_display_get_monitor_at_point(ekran, x, y);
  if (monitor != nullptr) {
    GdkRectangle alan;
    gdk_monitor_get_workarea(monitor, &alan);
    if (sol + genislik > alan.x + alan.width) sol = alan.x + alan.width - genislik;
    if (ust + yukseklik > alan.y + alan.height) ust = alan.y + alan.height - yukseklik;
    if (sol < alan.x) sol = alan.x;
    if (ust < alan.y) ust = alan.y;
  }
  gtk_window_move(pencere, sol, ust);
}

static double fl_sayi(FlValue* v) {
  if (v == nullptr) return 0;
  switch (fl_value_get_type(v)) {
    case FL_VALUE_TYPE_FLOAT:
      return fl_value_get_float(v);
    case FL_VALUE_TYPE_INT:
      return static_cast<double>(fl_value_get_int(v));
    default:
      return 0;
  }
}

static void kodi_cagrisi(FlMethodChannel* kanal, FlMethodCall* cagri, gpointer veri) {
  MyApplication* self = MY_APPLICATION(veri);
  GtkWindow* pencere = self->pencere;
  const gchar* ad = fl_method_call_get_name(cagri);
  g_autoptr(FlMethodResponse) cevap = nullptr;

  if (g_strcmp0(ad, "goster") == 0) {
    kodi_konumla(pencere);
    gtk_widget_show(GTK_WIDGET(pencere));
    gtk_window_set_keep_above(pencere, TRUE);
    cevap = FL_METHOD_RESPONSE(fl_method_success_response_new(nullptr));
  } else if (g_strcmp0(ad, "gizle") == 0) {
    gtk_widget_hide(GTK_WIDGET(pencere));
    cevap = FL_METHOD_RESPONSE(fl_method_success_response_new(nullptr));
  } else if (g_strcmp0(ad, "kapat") == 0) {
    gtk_window_close(pencere);
    cevap = FL_METHOD_RESPONSE(fl_method_success_response_new(nullptr));
  } else if (g_strcmp0(ad, "surukle") == 0) {
    // Pencere yöneticisinin taşıma döngüsü (fare düğmesi basılıyken).
    GdkDisplay* ekran = gdk_display_get_default();
    GdkSeat* koltuk = ekran ? gdk_display_get_default_seat(ekran) : nullptr;
    GdkDevice* fare = koltuk ? gdk_seat_get_pointer(koltuk) : nullptr;
    GdkWindow* gw = gtk_widget_get_window(GTK_WIDGET(pencere));
    if (fare != nullptr && gw != nullptr) {
      GdkModifierType durum = static_cast<GdkModifierType>(0);
      gdk_device_get_state(fare, gw, nullptr, &durum);
      gint x = 0, y = 0;
      gdk_device_get_position(fare, nullptr, &x, &y);
      if (durum & GDK_BUTTON1_MASK) {
        gtk_window_begin_move_drag(pencere, 1, x, y, GDK_CURRENT_TIME);
      }
    }
    cevap = FL_METHOD_RESPONSE(fl_method_success_response_new(fl_value_new_bool(FALSE)));
  } else if (g_strcmp0(ad, "bolge") == 0) {
    // Yalnızca robot ve balonun alanı tıklanabilir; geri kalanında
    // tıklamalar alttaki pencerelere geçer. [x, y, g, y, yarıçap]...
    FlValue* liste = fl_method_call_get_args(cagri);
    cairo_region_t* bolge = cairo_region_create();
    if (liste != nullptr && fl_value_get_type(liste) == FL_VALUE_TYPE_LIST) {
      for (size_t i = 0; i < fl_value_get_length(liste); i++) {
        FlValue* d = fl_value_get_list_value(liste, i);
        if (fl_value_get_type(d) != FL_VALUE_TYPE_LIST || fl_value_get_length(d) < 4) continue;
        cairo_rectangle_int_t r = {
            static_cast<int>(fl_sayi(fl_value_get_list_value(d, 0))),
            static_cast<int>(fl_sayi(fl_value_get_list_value(d, 1))),
            static_cast<int>(fl_sayi(fl_value_get_list_value(d, 2))),
            static_cast<int>(fl_sayi(fl_value_get_list_value(d, 3)))};
        cairo_region_union_rectangle(bolge, &r);
      }
    }
    GdkWindow* gw = gtk_widget_get_window(GTK_WIDGET(pencere));
    if (gw != nullptr) gdk_window_input_shape_combine_region(gw, bolge, 0, 0);
    cairo_region_destroy(bolge);
    cevap = FL_METHOD_RESPONSE(fl_method_success_response_new(nullptr));
  } else if (g_strcmp0(ad, "anaPencereyiOneGetir") == 0) {
    // Başka süreçteki pencereyi öne getirmek GTK'da yok; TürKod penceresi
    // kullanıcının tıklamasıyla öne gelir.
    cevap = FL_METHOD_RESPONSE(fl_method_success_response_new(nullptr));
  } else {
    cevap = FL_METHOD_RESPONSE(fl_method_not_implemented_response_new());
  }
  g_autoptr(GError) hata = nullptr;
  if (!fl_method_call_respond(cagri, cevap, &hata)) {
    g_warning("Kodi penceresi cevap veremedi: %s", hata->message);
  }
}

// Tek editör örneği (Windows'taki runner/flutter_window.cpp ile aynı sözleşme):
// Dart, oturumu yükledikten sonra "turkod/tek_ornek" kanalında "hazir" çağırır
// ve o ana kadar biriken dosyaları alır; sonrakiler "dosyalariAc" ile iletilir.
static void tek_ornek_cagrisi(FlMethodChannel* kanal, FlMethodCall* cagri, gpointer veri) {
  MyApplication* self = MY_APPLICATION(veri);
  g_autoptr(FlMethodResponse) cevap = nullptr;
  if (g_strcmp0(fl_method_call_get_name(cagri), "hazir") == 0) {
    g_autoptr(FlValue) liste = fl_value_new_list();
    for (guint i = 0; i < self->bekleyen_dosyalar->len; i++) {
      fl_value_append_take(liste, fl_value_new_string(static_cast<const gchar*>(
                                      g_ptr_array_index(self->bekleyen_dosyalar, i))));
    }
    if (self->bekleyen_dosyalar->len > 0) {
      g_ptr_array_remove_range(self->bekleyen_dosyalar, 0, self->bekleyen_dosyalar->len);
    }
    self->dart_hazir = TRUE;
    cevap = FL_METHOD_RESPONSE(fl_method_success_response_new(liste));
  } else {
    cevap = FL_METHOD_RESPONSE(fl_method_not_implemented_response_new());
  }
  g_autoptr(GError) hata = nullptr;
  if (!fl_method_call_respond(cagri, cevap, &hata)) {
    g_warning("Tek örnek kanalı cevap veremedi: %s", hata->message);
  }
}

// Implements GApplication::open: TürKod zaten açıkken ikinci başlatmanın
// dosyaları (g_application_open ile) buraya gelir; sekme olarak açılırlar.
static void my_application_open(GApplication* application, GFile** files, gint n_files,
                                const gchar* hint) {
  MyApplication* self = MY_APPLICATION(application);
  if (self->pencere == nullptr) g_application_activate(application);
  g_autoptr(FlValue) liste = fl_value_new_list();
  for (gint i = 0; i < n_files; i++) {
    g_autofree gchar* yol = g_file_get_path(files[i]);
    if (yol == nullptr) continue;
    if (self->dart_hazir && self->tek_ornek_kanali != nullptr) {
      fl_value_append_take(liste, fl_value_new_string(yol));
    } else {
      g_ptr_array_add(self->bekleyen_dosyalar, g_strdup(yol));
    }
  }
  if (fl_value_get_length(liste) > 0) {
    fl_method_channel_invoke_method(self->tek_ornek_kanali, "dosyalariAc", liste, nullptr,
                                    nullptr, nullptr);
  }
  if (self->pencere != nullptr) gtk_window_present(self->pencere);
}

// Implements GApplication::activate.
static void my_application_activate(GApplication* application) {
  MyApplication* self = MY_APPLICATION(application);
  // İkinci başlatma (dosyasız) yeni pencere açmaz; açık pencere öne gelir.
  if (self->pencere != nullptr) {
    gtk_window_present(self->pencere);
    return;
  }
  GtkWindow* window =
      GTK_WINDOW(gtk_application_window_new(GTK_APPLICATION(application)));
  self->pencere = window;
  self->kodi_kipi = arguman_var(self->dart_entrypoint_arguments, "--kodi-penceresi");
  self->kodi_gizli =
      self->kodi_kipi && arguman_var(self->dart_entrypoint_arguments, "--kodi-gizli");

  if (self->kodi_kipi) {
    gtk_window_set_title(window, "Kodi");
    gtk_window_set_decorated(window, FALSE);
    gtk_window_set_keep_above(window, TRUE);
    gtk_window_set_skip_taskbar_hint(window, TRUE);
    gtk_window_set_skip_pager_hint(window, TRUE);
    gtk_window_set_default_size(window, 440, 760);
    // Saydam pencere: bileşikleştirici (compositor) varsa arka plan görünür.
    GdkScreen* ekran = gtk_widget_get_screen(GTK_WIDGET(window));
    GdkVisual* gorsel = ekran ? gdk_screen_get_rgba_visual(ekran) : nullptr;
    if (gorsel != nullptr) gtk_widget_set_visual(GTK_WIDGET(window), gorsel);
    gtk_widget_set_app_paintable(GTK_WIDGET(window), TRUE);
    kodi_konumla(window);
  } else {
    // Use a header bar when running in GNOME as this is the common style used
    // by applications and is the setup most users will be using (e.g. Ubuntu
    // desktop).
    // If running on X and not using GNOME then just use a traditional title bar
    // in case the window manager does more exotic layout, e.g. tiling.
    // If running on Wayland assume the header bar will work (may need changing
    // if future cases occur).
    gboolean use_header_bar = TRUE;
#ifdef GDK_WINDOWING_X11
    GdkScreen* screen = gtk_window_get_screen(window);
    if (GDK_IS_X11_SCREEN(screen)) {
      const gchar* wm_name = gdk_x11_screen_get_window_manager_name(screen);
      if (g_strcmp0(wm_name, "GNOME Shell") != 0) {
        use_header_bar = FALSE;
      }
    }
#endif
    if (use_header_bar) {
      GtkHeaderBar* header_bar = GTK_HEADER_BAR(gtk_header_bar_new());
      gtk_widget_show(GTK_WIDGET(header_bar));
      gtk_header_bar_set_title(header_bar, "TürKod");
      gtk_header_bar_set_show_close_button(header_bar, TRUE);
      gtk_window_set_titlebar(window, GTK_WIDGET(header_bar));
    } else {
      gtk_window_set_title(window, "TürKod");
    }

    gtk_window_set_default_size(window, 1280, 720);
  }

  g_autoptr(FlDartProject) project = fl_dart_project_new();
  fl_dart_project_set_dart_entrypoint_arguments(
      project, self->dart_entrypoint_arguments);

  FlView* view = fl_view_new(project);
  GdkRGBA background_color;
  // Background defaults to black, override it here if necessary, e.g. #00000000
  // for transparent.
  gdk_rgba_parse(&background_color, self->kodi_kipi ? "rgba(0,0,0,0)" : "#000000");
  fl_view_set_background_color(view, &background_color);
  gtk_widget_show(GTK_WIDGET(view));
  gtk_container_add(GTK_CONTAINER(window), GTK_WIDGET(view));

  // Show the window when Flutter renders.
  // Requires the view to be realized so we can start rendering.
  g_signal_connect_swapped(view, "first-frame", G_CALLBACK(first_frame_cb),
                           self);
  gtk_widget_realize(GTK_WIDGET(view));

  fl_register_plugins(FL_PLUGIN_REGISTRY(view));

  if (self->kodi_kipi) {
    FlEngine* motor = fl_view_get_engine(view);
    g_autoptr(FlStandardMethodCodec) kodek = fl_standard_method_codec_new();
    self->kodi_kanali = fl_method_channel_new(fl_engine_get_binary_messenger(motor),
                                              "turkod/kodi_penceresi",
                                              FL_METHOD_CODEC(kodek));
    fl_method_channel_set_method_call_handler(self->kodi_kanali, kodi_cagrisi, self,
                                              nullptr);
  } else {
    FlEngine* motor = fl_view_get_engine(view);
    g_autoptr(FlStandardMethodCodec) kodek = fl_standard_method_codec_new();
    self->tek_ornek_kanali = fl_method_channel_new(fl_engine_get_binary_messenger(motor),
                                                   "turkod/tek_ornek",
                                                   FL_METHOD_CODEC(kodek));
    fl_method_channel_set_method_call_handler(self->tek_ornek_kanali, tek_ornek_cagrisi,
                                              self, nullptr);
  }

  gtk_widget_grab_focus(GTK_WIDGET(view));
}

// Implements GApplication::local_command_line.
static gboolean my_application_local_command_line(GApplication* application,
                                                  gchar*** arguments,
                                                  int* exit_status) {
  MyApplication* self = MY_APPLICATION(application);
  // Strip out the first argument as it is the binary name.
  self->dart_entrypoint_arguments = g_strdupv(*arguments + 1);

  // Kodi masaüstü penceresi aynı programın ikinci sürecidir
  // (--kodi-penceresi): tek örneğe takılmaz, kendi penceresini açar.
  if (arguman_var(self->dart_entrypoint_arguments, "--kodi-penceresi")) {
    g_application_set_flags(application, G_APPLICATION_NON_UNIQUE);
  }

  g_autoptr(GError) error = nullptr;
  if (!g_application_register(application, nullptr, &error)) {
    g_warning("Failed to register: %s", error->message);
    *exit_status = 1;
    return TRUE;
  }

  if (g_application_get_is_remote(application)) {
    // TürKod zaten açık ("Editör ile aç"): dosyalar açık pencereye iletilir
    // (göreli yollar bu sürecin klasörüne göre çözülür), bu süreç kapanır.
    g_autoptr(GPtrArray) dosyalar = g_ptr_array_new_with_free_func(g_object_unref);
    for (char** a = self->dart_entrypoint_arguments; a != nullptr && *a != nullptr; a++) {
      if ((*a)[0] == '\0' || g_str_has_prefix(*a, "--")) continue;
      g_ptr_array_add(dosyalar, g_file_new_for_commandline_arg(*a));
    }
    if (dosyalar->len > 0) {
      g_application_open(application, reinterpret_cast<GFile**>(dosyalar->pdata),
                         static_cast<gint>(dosyalar->len), "");
    } else {
      g_application_activate(application);
    }
    *exit_status = 0;
    return TRUE;
  }

  g_application_activate(application);
  *exit_status = 0;

  return TRUE;
}

// Implements GApplication::startup.
static void my_application_startup(GApplication* application) {
  // MyApplication* self = MY_APPLICATION(object);

  // Perform any actions required at application startup.

  G_APPLICATION_CLASS(my_application_parent_class)->startup(application);
}

// Implements GApplication::shutdown.
static void my_application_shutdown(GApplication* application) {
  // MyApplication* self = MY_APPLICATION(object);

  // Perform any actions required at application shutdown.

  G_APPLICATION_CLASS(my_application_parent_class)->shutdown(application);
}

// Implements GObject::dispose.
static void my_application_dispose(GObject* object) {
  MyApplication* self = MY_APPLICATION(object);
  g_clear_pointer(&self->dart_entrypoint_arguments, g_strfreev);
  g_clear_object(&self->kodi_kanali);
  g_clear_object(&self->tek_ornek_kanali);
  g_clear_pointer(&self->bekleyen_dosyalar, g_ptr_array_unref);
  G_OBJECT_CLASS(my_application_parent_class)->dispose(object);
}

static void my_application_class_init(MyApplicationClass* klass) {
  G_APPLICATION_CLASS(klass)->activate = my_application_activate;
  G_APPLICATION_CLASS(klass)->open = my_application_open;
  G_APPLICATION_CLASS(klass)->local_command_line =
      my_application_local_command_line;
  G_APPLICATION_CLASS(klass)->startup = my_application_startup;
  G_APPLICATION_CLASS(klass)->shutdown = my_application_shutdown;
  G_OBJECT_CLASS(klass)->dispose = my_application_dispose;
}

static void my_application_init(MyApplication* self) {
  self->bekleyen_dosyalar = g_ptr_array_new_with_free_func(g_free);
}

MyApplication* my_application_new() {
  // Set the program name to the application ID, which helps various systems
  // like GTK and desktop environments map this running application to its
  // corresponding .desktop file. This ensures better integration by allowing
  // the application to be recognized beyond its binary name.
  g_set_prgname(APPLICATION_ID);

  // Tek örnek (APPLICATION_ID: org.turkod.TurKod, CMakeLists.txt): TürKod açıkken
  // yeniden başlatılınca dosyalar açık pencereye gider (open). Kodi penceresi
  // local_command_line'da NON_UNIQUE yapılır.
  return MY_APPLICATION(g_object_new(my_application_get_type(),
                                     "application-id", APPLICATION_ID, "flags",
                                     G_APPLICATION_HANDLES_OPEN, nullptr));
}
