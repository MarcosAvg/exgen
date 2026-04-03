import os
import threading
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Gio, GLib
from src.models.data_models import EvidenciaData
from src.services.pdf_generator import generar_pdf
from src.utils.config_manager import get_save_path, set_save_path, get_last_image_dir, set_last_image_dir

class MainWindow(Adw.ApplicationWindow):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_title("Generador de Evidencia")
        self.set_default_size(1000, 560)

        # Main Layout
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        
        # HeaderBar
        header = Adw.HeaderBar()
        main_box.append(header)

        # ScrolledWindow para contenido largo
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        main_box.append(scrolled)
        
        # Adw.Clamp para mantener márgenes pero permitiendo expansión
        self.main_clamp = Adw.Clamp()
        self.main_clamp.set_margin_top(24)
        self.main_clamp.set_margin_bottom(24)
        self.main_clamp.set_margin_start(24)
        self.main_clamp.set_margin_end(24)
        self.main_clamp.set_maximum_size(600) # Tamaño inicial móvil
        self.main_clamp.set_tightening_threshold(400)
        scrolled.set_child(self.main_clamp)

        # Contenedor principal de secciones
        self.content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=32)
        self.main_clamp.set_child(self.content_box)

        # SECCIÓN IZQUIERDA: Formularios
        self.left_col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=24)
        self.left_col.set_hexpand(True)
        self.content_box.append(self.left_col)

        # SECCIÓN DERECHA: Imágenes y Acción
        self.right_col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=24)
        self.right_col.set_hexpand(True)
        self.content_box.append(self.right_col)

        # --- Grupo 1: Datos Generales ---
        grp_datos = Adw.PreferencesGroup(title="Datos Generales")
        self.entry_plantel = Adw.EntryRow(title="Plantel")
        self.entry_cct = Adw.EntryRow(title="CCT")
        self.entry_direccion = Adw.EntryRow(title="Dirección")
        self.entry_municipio = Adw.EntryRow(title="Municipio")
        grp_datos.add(self.entry_plantel)
        grp_datos.add(self.entry_cct)
        grp_datos.add(self.entry_direccion)
        grp_datos.add(self.entry_municipio)
        self.left_col.append(grp_datos)

        # --- Grupo 2: Concepto ---
        grp_concepto = Adw.PreferencesGroup(title="Concepto")
        self.entry_num = Adw.EntryRow(title="Número")
        self.entry_desc = Adw.EntryRow(title="Descripción/Texto")
        grp_concepto.add(self.entry_num)
        grp_concepto.add(self.entry_desc)
        self.left_col.append(grp_concepto)

        # --- Grupo 3: Carpeta de Destino ---
        grp_destino = Adw.PreferencesGroup(title="Carpeta de Destino")
        self.save_path = get_save_path()
        self.row_destino = Adw.ActionRow(title="Directorio de Guardado", subtitle=self.save_path)
        btn_folder = Gtk.Button(icon_name="folder-open-symbolic")
        btn_folder.set_valign(Gtk.Align.CENTER)
        btn_folder.connect("clicked", self.on_select_folder)
        self.row_destino.add_suffix(btn_folder)
        grp_destino.add(self.row_destino)
        self.right_col.append(grp_destino)

        # --- Grupo 4: Imágenes ---
        grp_imgs = Adw.PreferencesGroup(title="Imágenes")
        self.paths_antes = []
        self.paths_durante = []
        self.paths_despues = []

        self.row_antes = Adw.ActionRow(title="ANTES", subtitle="Ninguna seleccionada")
        btn_antes = Gtk.Button(label="Seleccionar")
        btn_antes.set_valign(Gtk.Align.CENTER)
        btn_antes.connect("clicked", self.on_select_image, "antes")
        self.row_antes.add_suffix(btn_antes)
        grp_imgs.add(self.row_antes)

        self.row_durante = Adw.ActionRow(title="DURANTE", subtitle="Ninguna seleccionada")
        btn_durante = Gtk.Button(label="Seleccionar")
        btn_durante.set_valign(Gtk.Align.CENTER)
        btn_durante.connect("clicked", self.on_select_image, "durante")
        self.row_durante.add_suffix(btn_durante)
        grp_imgs.add(self.row_durante)

        self.row_despues = Adw.ActionRow(title="DESPUÉS", subtitle="Ninguna seleccionada")
        btn_despues = Gtk.Button(label="Seleccionar")
        btn_despues.set_valign(Gtk.Align.CENTER)
        btn_despues.connect("clicked", self.on_select_image, "despues")
        self.row_despues.add_suffix(btn_despues)
        grp_imgs.add(self.row_despues)
        self.right_col.append(grp_imgs)

        # --- Acción de Generación ---
        self.btn_gen = Gtk.Button(label="Generar PDF")
        self.btn_gen.set_margin_top(12)
        self.btn_gen.add_css_class("suggested-action")
        self.btn_gen.add_css_class("pill")
        self.btn_gen.set_size_request(-1, 50)
        self.btn_gen.connect("clicked", self.on_generate_pdf)
        self.right_col.append(self.btn_gen)

        self.progress_bar = Gtk.ProgressBar()
        self.progress_bar.set_visible(False)
        self.right_col.append(self.progress_bar)

        self.progress_label = Gtk.Label(label="")
        self.progress_label.set_visible(False)
        self.progress_label.add_css_class("caption")
        self.right_col.append(self.progress_label)

        # --- BREAKPOINT RESPONSIVO ---
        # Si el ancho de la ventana es superior a 900px, activar modo Desktop
        try:
            self.breakpoint = Adw.Breakpoint.new(Adw.BreakpointCondition.parse("min-width: 900px"))
            self.breakpoint.add_setter(self.content_box, "orientation", Gtk.Orientation.HORIZONTAL)
            self.breakpoint.add_setter(self.main_clamp, "maximum-size", 10000) # Expandir totalmente
            self.add_breakpoint(self.breakpoint)
        except (AttributeError, TypeError):
            # Compatibilidad con versiones de libadwaita menores a 1.4
            pass
            
        self.set_content(main_box)

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
        
        # Iniciar en la última carpeta usada
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
                
                count = len(paths)
                subtitle = f"{count} imagen seleccionada" if count == 1 else f"{count} imágenes seleccionadas"

                if context == "antes":
                    self.paths_antes = paths
                    self.row_antes.set_subtitle(subtitle)
                elif context == "durante":
                    self.paths_durante = paths
                    self.row_durante.set_subtitle(subtitle)
                elif context == "despues":
                    self.paths_despues = paths
                    self.row_despues.set_subtitle(subtitle)
                
                # Guardar la ruta de la carpeta para la próxima vez
                if paths:
                    set_last_image_dir(os.path.dirname(paths[0]))
        except GLib.Error as e:
            pass

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
            concepto_texto=self.entry_desc.get_text().strip(),
            img_antes=self.paths_antes,
            img_durante=self.paths_durante,
            img_despues=self.paths_despues
        )

        missing = []
        if not data.plantel: missing.append("Plantel")

        if missing:
            self.show_alert("Faltan datos", f"Por favor completa al menos el campo Plantel.")
            return

        # Construir nombre de archivo personalizado
        filename = f"{data.concepto_numero} - {data.plantel}.pdf"
        invalid_chars = r'<>:"/\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, "_")
            
        full_path = os.path.join(self.save_path, filename)

        # Preparar UI para carga
        self.btn_gen.set_sensitive(False)
        self.progress_bar.set_visible(True)
        self.progress_bar.set_fraction(0.0)
        self.progress_label.set_visible(True)
        self.progress_label.set_text("Iniciando...")

        # Lanzar hilo
        thread = threading.Thread(target=self.generate_pdf_worker, args=(data, full_path))
        thread.daemon = True
        thread.start()

    def generate_pdf_worker(self, data, filename):
        try:
            out_path = generar_pdf(data, output_path=filename, progress_callback=self.report_progress_from_thread)
            GLib.idle_add(self.on_pdf_success, out_path)
        except Exception as e:
            GLib.idle_add(self.on_pdf_error, str(e))

    def report_progress_from_thread(self, fraction, text):
        GLib.idle_add(self.update_progress_ui, fraction, text)

    def update_progress_ui(self, fraction, text):
        self.progress_bar.set_fraction(fraction)
        self.progress_label.set_text(text)

    def on_pdf_success(self, out_path):
        self.reset_progress_ui()
        self.show_alert("Éxito", f"PDF generado correctamente en:\n{out_path}")

    def on_pdf_error(self, error_msg):
        self.reset_progress_ui()
        self.show_alert("Error", f"Ocurrió un error al generar PDF: {error_msg}")

    def reset_progress_ui(self):
        self.btn_gen.set_sensitive(True)
        self.progress_bar.set_visible(False)
        self.progress_label.set_visible(False)
        self.progress_label.set_text("")

    def show_alert(self, title, message):
        dialog = Adw.MessageDialog(
            heading=title,
            body=message,
            transient_for=self,
        )
        dialog.add_response("ok", "Aceptar")
        dialog.set_default_response("ok")
        dialog.connect("response", lambda d, r: d.close())
        dialog.present()
