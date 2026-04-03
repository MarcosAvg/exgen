import os
import threading
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
gi.require_version('Gdk', '4.0')
from gi.repository import Gtk, Adw, Gio, GLib, Pango, Gdk, GObject
from src.models.data_models import EvidenciaData
from src.services.pdf_generator import generar_pdf
from src.utils.config_manager import get_save_path, set_save_path, get_last_image_dir, set_last_image_dir

class DropZoneCard(Gtk.Box):
    def __init__(self, title, context, main_window):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.context = context
        self.main_window = main_window
        self.add_css_class("dz-card")
        self.set_hexpand(True)
        self.set_vexpand(True)
        
        # Título de la tarjeta (Ej. ANTES)
        lbl_title = Gtk.Label(label=title)
        lbl_title.add_css_class("heading")
        lbl_title.add_css_class("dim-label")
        self.append(lbl_title)
        
        # Contenedor dinámico (Muestra el placeholder o la imagen real)
        self.content_bin = Adw.Bin()
        self.content_bin.set_vexpand(True)
        self.content_bin.set_hexpand(True)
        self.append(self.content_bin)
        
        # Vaciado / Estado Inicial
        self.placeholder = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.placeholder.set_valign(Gtk.Align.CENTER)
        
        icon = Gtk.Image.new_from_icon_name("insert-image-symbolic")
        icon.set_pixel_size(32) # Icono más pequeño
        icon.add_css_class("dim-label")
        self.placeholder.append(icon)
        
        self.lbl_subtitle = Gtk.Label(label="Arrastra o Clica aquí")
        self.lbl_subtitle.add_css_class("dim-label")
        self.lbl_subtitle.add_css_class("caption")
        self.placeholder.append(self.lbl_subtitle)
        
        self.content_bin.set_child(self.placeholder)
        
        # Clics para abrir selector nativo
        click = Gtk.GestureClick()
        click.connect("pressed", lambda *args: self.main_window.on_select_image(None, self.context))
        self.add_controller(click)
        
        # Receptor de Arrastrar y Soltar (DND)
        try:
            drop = Gtk.DropTarget.new(Gdk.FileList, Gdk.DragAction.COPY)
            drop.connect("drop", self.main_window.on_drop_image, self.context)
            drop.connect("enter", lambda t, x, y: self.add_css_class("drag-hover") or Gdk.DragAction.COPY)
            drop.connect("leave", lambda t: self.remove_css_class("drag-hover"))
            self.add_controller(drop)
        except Exception:
            pass

    def update_preview(self, paths):
        if not paths:
            self.content_bin.set_child(self.placeholder)
            return

        # Previsualización nativa de GTK4
        try:
            pic = Gtk.Picture.new_for_filename(paths[0])
            pic.set_can_shrink(True)
            if hasattr(pic, "set_content_fit"): # GTK 4.8+
                pic.set_content_fit(Gtk.ContentFit.COVER)
            elif hasattr(pic, "set_keep_aspect_ratio"):
                pic.set_keep_aspect_ratio(True)
                
            # Marco para redondear las esquinas de la imagen si se desea
            frame = Gtk.Frame()
            frame.add_css_class("preview-frame")
            frame.set_child(pic)

            # Capa superior para añadir "Badges" si hay más de 1 imagen
            overlay = Gtk.Overlay()
            overlay.set_child(frame)
            
            if len(paths) > 1:
                badge = Gtk.Label(label=f"+{len(paths)-1}")
                badge.add_css_class("numeric-badge")
                badge.set_valign(Gtk.Align.START)
                badge.set_halign(Gtk.Align.END)
                badge.set_margin_top(8)
                badge.set_margin_end(8)
                overlay.add_overlay(badge)
                
            self.content_bin.set_child(overlay)
        except Exception as e:
            # Si la imagen falla en cargar (corrupta), mantenemos placeholder y cambiamos texto
            self.lbl_subtitle.set_text(f"{len(paths)} Seleccionadas")
            self.content_bin.set_child(self.placeholder)

class MainWindow(Adw.ApplicationWindow):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_title("Generador de Evidencia")
        self.set_default_size(800, 950)

        # 1. Overlay (Toasts)
        self.toast_overlay = Adw.ToastOverlay()
        self.set_content(self.toast_overlay)

        # 2. ToolbarView
        self.toolbar_view = Adw.ToolbarView()
        self.toast_overlay.set_child(self.toolbar_view)
        
        header = Adw.HeaderBar()
        self.toolbar_view.add_top_bar(header)

        # 3.1 Barra inferior para la acción principal (Al centro)
        bottom_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        bottom_bar.set_margin_top(12)
        bottom_bar.set_margin_bottom(12)
        bottom_bar.set_margin_start(12)
        bottom_bar.set_margin_end(12)
        
        # Espaciador Izquierda
        bottom_bar.append(Gtk.Box(hexpand=True))

        self.btn_gen = Gtk.Button(label="Generar PDF")
        self.btn_gen.add_css_class("suggested-action")
        self.btn_gen.add_css_class("pill")
        self.btn_gen.set_size_request(180, 44) 
        self.btn_gen.connect("clicked", self.on_generate_pdf)
        bottom_bar.append(self.btn_gen)
        
        # Espaciador Derecha
        bottom_bar.append(Gtk.Box(hexpand=True))
        
        self.toolbar_view.add_bottom_bar(bottom_bar)
        
        # 3.2 Botón Ajustes (En la cabecera)
        btn_settings = Gtk.MenuButton(icon_name="document-properties-symbolic")
        popover_settings = Gtk.Popover()
        
        grp_destino = Adw.PreferencesGroup(title="Ajustes")
        grp_destino.set_margin_top(8)
        grp_destino.set_margin_bottom(8)
        grp_destino.set_margin_start(8)
        grp_destino.set_margin_end(8)
        
        self.save_path = get_save_path()
        self.row_destino = Adw.ActionRow(title="Guardar en...", subtitle=self.save_path)
        btn_folder = Gtk.Button(icon_name="folder-open-symbolic", valign=Gtk.Align.CENTER)
        btn_folder.connect("clicked", self.on_select_folder)
        self.row_destino.add_suffix(btn_folder)
        grp_destino.add(self.row_destino)
        
        popover_settings.set_child(grp_destino)
        btn_settings.set_popover(popover_settings)
        header.pack_end(btn_settings)

        # 4. Scroll & Contenedor Único Central (Dashboard Style)
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        self.toolbar_view.set_content(scrolled)
        
        self.main_clamp = Adw.Clamp()
        self.main_clamp.set_margin_top(32)
        self.main_clamp.set_margin_bottom(48)
        self.main_clamp.set_margin_start(24)
        self.main_clamp.set_margin_end(24)
        self.main_clamp.set_maximum_size(960) # Excelente para Widescreen
        scrolled.set_child(self.main_clamp)

        # Contenedor Flujo Vertical
        self.content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=24) # Reducido de 42
        self.main_clamp.set_child(self.content_box)

        # --- SECCIÓN 1: Detalles (Datos + Concepto unificados) ---
        grp_detalles = Adw.PreferencesGroup(title="Detalles de Inspección")
        self.entry_plantel = Adw.EntryRow(title="Plantel")
        self.entry_cct = Adw.EntryRow(title="CCT")
        self.entry_direccion = Adw.EntryRow(title="Dirección")
        self.entry_municipio = Adw.EntryRow(title="Municipio")
        self.entry_num = Adw.EntryRow(title="Número")
        
        self.row_desc = Adw.PreferencesRow()
        self.row_desc.add_css_class("multiline-entry")
        
        hbox_desc = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        hbox_desc.set_margin_top(8)
        hbox_desc.set_margin_bottom(8)
        hbox_desc.set_margin_start(12)
        hbox_desc.set_margin_end(12)
        
        vbox_desc = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        vbox_desc.set_hexpand(True)
        
        self.lbl_desc = Gtk.Label(label="Descripción del Concepto", xalign=0)
        self.lbl_desc.add_css_class("anim-label")
        self.lbl_desc.add_css_class("float-down")
        
        self.entry_desc = Gtk.TextView()
        self.entry_desc.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.entry_desc.set_accepts_tab(False)
        self.entry_desc.set_hexpand(True)
        self.entry_desc.set_size_request(-1, 24)
        
        self.icon_edit = Gtk.Image.new_from_icon_name("document-edit-symbolic")
        self.icon_edit.set_valign(Gtk.Align.CENTER)
        self.icon_edit.add_css_class("dim-label")
        self.icon_edit.add_css_class("anim-icon")
        
        vbox_desc.append(self.lbl_desc)
        vbox_desc.append(self.entry_desc)
        hbox_desc.append(vbox_desc)
        hbox_desc.append(self.icon_edit)
        self.row_desc.set_child(hbox_desc)
        
        grp_detalles.add(self.entry_plantel)
        grp_detalles.add(self.entry_cct)
        grp_detalles.add(self.entry_direccion)
        grp_detalles.add(self.entry_municipio)
        grp_detalles.add(self.entry_num)
        grp_detalles.add(self.row_desc)
        self.content_box.append(grp_detalles)

        # --- SECCIÓN 2: Galería Panorámica de Fotos (Drop Zones Horizontales) ---
        box_galeria = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        
        lbl_imgs = Gtk.Label(label="Fotografías (Visuales)", xalign=0)
        lbl_imgs.add_css_class("heading")
        box_galeria.append(lbl_imgs)
        
        self.imgs_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=24)
        self.imgs_box.set_homogeneous(True) # ¡Hace que las 3 pesen lo mismo!
        
        self.dz_antes = DropZoneCard("ANTES", "antes", self)
        self.dz_durante = DropZoneCard("DURANTE", "durante", self)
        self.dz_despues = DropZoneCard("DESPUÉS", "despues", self)
        
        self.imgs_box.append(self.dz_antes)
        self.imgs_box.append(self.dz_durante)
        self.imgs_box.append(self.dz_despues)
        box_galeria.append(self.imgs_box)
        
        self.content_box.append(box_galeria)

        # ESTILOS CSS INYECTADOS
        provider = Gtk.CssProvider()
        provider.load_from_data("""
            textview, textview text { background-color: transparent; padding: 0; margin: 0; }
            row.multiline-entry:focus-within { box-shadow: inset 0 0 0 2px @accent_color; }
            .anim-label { transition: all 200ms cubic-bezier(0.25, 0.46, 0.45, 0.94); opacity: 0.55; }
            .anim-label.float-up { font-size: 9pt; transform: none; }
            .anim-label.float-down { font-size: 11pt; transform: translateY(12px); }
            .anim-icon { transition: opacity 200ms ease; }
            
            /* Tarjeta Drop Zone */
            .dz-card {
                background-color: @window_bg_color;
                border: 2px dashed @shade_color;
                border-radius: 12px;
                padding: 12px;
                transition: all 200ms ease;
                min-height: 160px;
            }
            .dz-card:hover {
                border-color: @accent_color;
                background-color: alpha(@accent_color, 0.05);
            }
            .dz-card.drag-hover {
                border-style: solid;
                border-color: @accent_color;
                background-color: alpha(@accent_color, 0.15);
            }
            .preview-frame {
                border-radius: 8px;
                border: 1px solid @shade_color;
            }
            .numeric-badge {
                background-color: @accent_bg_color;
                color: @accent_fg_color;
                border-radius: 99px;
                padding: 4px 10px;
                font-weight: bold;
                font-size: 10pt;
                box-shadow: 0 2px 4px rgba(0,0,0,0.3);
            }
        """.encode())
        self.entry_desc.get_style_context().add_provider(provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        self.row_desc.get_style_context().add_provider(provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        self.lbl_desc.get_style_context().add_provider(provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        self.icon_edit.get_style_context().add_provider(provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        
        Gtk.StyleContext.add_provider_for_display(
             Gdk.Display.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        ) # Hacemos los estilos del DragAndDrop globales
        
        # Animación label
        def update_label_state(*args):
            has_text = self.entry_desc.get_buffer().get_char_count() > 0
            is_focused = self.entry_desc.has_focus()
            if has_text or is_focused:
                self.lbl_desc.remove_css_class("float-down")
                self.lbl_desc.add_css_class("float-up")
                self.icon_edit.set_opacity(0.0)
            else:
                self.lbl_desc.remove_css_class("float-up")
                self.lbl_desc.add_css_class("float-down")
                self.icon_edit.set_opacity(1.0)
                
        self.entry_desc.get_buffer().connect("changed", update_label_state)
        self.entry_desc.connect("notify::has-focus", update_label_state)
        GLib.idle_add(update_label_state)

        # Estado de rutas
        self.paths_antes = []
        self.paths_durante = []
        self.paths_despues = []

    def on_drop_image(self, target, value, x, y, context):
        try:
            target.get_widget().remove_css_class("drag-hover")
            paths = []
            if type(value).__name__ == "FileList":
                files = value.get_files()
                for i in range(files.get_n_items()):
                    f = files.get_item(i)
                    paths.append(f.get_path())
            valid_paths = [p for p in paths if p.lower().endswith(('.png', '.jpg', '.jpeg'))]
            if valid_paths:
                self.update_image_state(valid_paths, context)
            return True
        except Exception:
            return False

    def on_select_image(self, btn, context):
        dialog = Gtk.FileDialog()
        dialog.set_title("Selecciona la imagen de evidencia")
        f = Gtk.FileFilter()
        f.set_name("Imágenes")
        f.add_mime_type("image/png")
        f.add_mime_type("image/jpeg")
        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(f)
        dialog.set_filters(filters)
        dialog.set_default_filter(f)
        
        last_dir = get_last_image_dir()
        if os.path.exists(last_dir):
            dialog.set_initial_folder(Gio.File.new_for_path(last_dir))
        
        dialog.open_multiple(self, None, self.on_file_dialog_response, context)

    def on_file_dialog_response(self, dialog, result, context):
        try:
            list_model = dialog.open_multiple_finish(result)
            if list_model:
                paths = []
                for i in range(list_model.get_n_items()):
                    f = list_model.get_item(i)
                    paths.append(f.get_path())
                if not paths: return
                self.update_image_state(paths, context)
                set_last_image_dir(os.path.dirname(paths[0]))
        except GLib.Error:
            pass

    def update_image_state(self, paths, context):
        if context == "antes":
            self.paths_antes = paths
            self.dz_antes.update_preview(paths)
        elif context == "durante":
            self.paths_durante = paths
            self.dz_durante.update_preview(paths)
        elif context == "despues":
            self.paths_despues = paths
            self.dz_despues.update_preview(paths)

    def on_select_folder(self, btn):
        dialog = Gtk.FileDialog()
        dialog.set_title("Selecciona la carpeta de destino")
        dialog.select_folder(self, None, self.on_folder_dialog_response)

    def on_folder_dialog_response(self, dialog, result):
        try:
            folder = dialog.select_folder_finish(result)
            if folder:
                path = folder.get_path()
                self.save_path = path
                self.row_destino.set_subtitle(path)
                set_save_path(path)
        except GLib.Error:
            pass

    def on_generate_pdf(self, btn):
        data = EvidenciaData(
            plantel=self.entry_plantel.get_text().strip(),
            cct=self.entry_cct.get_text().strip(),
            direccion=self.entry_direccion.get_text().strip(),
            municipio=self.entry_municipio.get_text().strip(),
            concepto_numero=self.entry_num.get_text().strip(),
            concepto_texto=self.get_textview_text(self.entry_desc),
            img_antes=self.paths_antes,
            img_durante=self.paths_durante,
            img_despues=self.paths_despues
        )

        missing = []
        if not data.plantel: missing.append("Plantel")
        # Validar si al menos hay una foto (opcional, pero útil)
        
        if missing:
            self.show_alert("Faltan datos obligatorios", "Por favor completa al menos el campo Plantel.")
            return

        filename = f"{data.concepto_numero} - {data.plantel}.pdf"
        invalid_chars = r'<>:"/\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, "_")
            
        full_path = os.path.join(self.save_path, filename)

        self.btn_gen.set_sensitive(False)
        
        self.toast_gen = Adw.Toast.new("Generando PDF...")
        self.toast_gen.set_timeout(0)
        self.toast_overlay.add_toast(self.toast_gen)

        thread = threading.Thread(target=self.generate_pdf_worker, args=(data, full_path))
        thread.daemon = True
        thread.start()

    def generate_pdf_worker(self, data, filename):
        try:
            out_path = generar_pdf(data, output_path=filename)
            GLib.idle_add(self.on_pdf_success, out_path)
        except Exception as e:
            GLib.idle_add(self.on_pdf_error, str(e))

    def on_pdf_success(self, out_path):
        self.btn_gen.set_sensitive(True)
        if hasattr(self, 'toast_gen'):
            self.toast_gen.dismiss()
            
        nice_name = os.path.basename(out_path)
        success_toast = Adw.Toast.new(f"Reporte Completado: {nice_name}")
        self.toast_overlay.add_toast(success_toast)

    def on_pdf_error(self, error_msg):
        self.btn_gen.set_sensitive(True)
        if hasattr(self, 'toast_gen'):
            self.toast_gen.dismiss()
        self.show_alert("Error", f"Ocurrió un error al generar PDF: {error_msg}")

    def show_alert(self, title, message):
        dialog = Adw.MessageDialog(heading=title, body=message, transient_for=self)
        dialog.add_response("ok", "Aceptar")
        dialog.set_default_response("ok")
        dialog.connect("response", lambda d, r: d.close())
        dialog.present()

    def get_textview_text(self, textview):
        buffer = textview.get_buffer()
        start, end = buffer.get_bounds()
        return buffer.get_text(start, end, True).strip()
