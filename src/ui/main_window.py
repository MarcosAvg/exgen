import os
import threading

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("Gdk", "4.0")
from gi.repository import Adw, Gio, GLib, Gtk

from src.application.evidence_report import (
    GenerateReportError,
    GenerateReportSuccess,
    run_generate_evidence_report,
)
from src.domain.models import EvidenciaData
from src.ui.styles import install_main_window_styles
from src.ui.widgets.drop_zone import DropZoneCard
from src.utils.config_manager import (
    get_last_image_dir,
    get_save_path,
    set_last_image_dir,
    set_save_path,
)


class MainWindow(Adw.ApplicationWindow):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_title("Generador de Evidencia")
        self.set_default_size(800, 950)

        self.toast_overlay = Adw.ToastOverlay()
        self.set_content(self.toast_overlay)

        self.toolbar_view = Adw.ToolbarView()
        self.toast_overlay.set_child(self.toolbar_view)

        header = Adw.HeaderBar()
        self.toolbar_view.add_top_bar(header)

        bottom_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        bottom_bar.set_margin_top(12)
        bottom_bar.set_margin_bottom(12)
        bottom_bar.set_margin_start(12)
        bottom_bar.set_margin_end(12)
        bottom_bar.append(Gtk.Box(hexpand=True))

        self.btn_gen = Gtk.Button(label="Generar PDF")
        self.btn_gen.add_css_class("suggested-action")
        self.btn_gen.add_css_class("pill")
        self.btn_gen.set_size_request(180, 44)
        self.btn_gen.connect("clicked", self.on_generate_pdf)
        bottom_bar.append(self.btn_gen)
        bottom_bar.append(Gtk.Box(hexpand=True))
        self.toolbar_view.add_bottom_bar(bottom_bar)

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

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        self.toolbar_view.set_content(scrolled)

        self.main_clamp = Adw.Clamp()
        self.main_clamp.set_margin_top(32)
        self.main_clamp.set_margin_bottom(48)
        self.main_clamp.set_margin_start(24)
        self.main_clamp.set_margin_end(24)
        self.main_clamp.set_maximum_size(960)
        scrolled.set_child(self.main_clamp)

        self.content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=24)
        self.main_clamp.set_child(self.content_box)

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

        box_galeria = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        lbl_imgs = Gtk.Label(label="Fotografías (Visuales)", xalign=0)
        lbl_imgs.add_css_class("heading")
        box_galeria.append(lbl_imgs)

        self.imgs_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=24)
        self.imgs_box.set_homogeneous(True)

        self.dz_antes = DropZoneCard(
            "ANTES",
            "antes",
            on_select_clicked=self.open_image_picker,
            on_drop_paths=self.update_image_state,
        )
        self.dz_durante = DropZoneCard(
            "DURANTE",
            "durante",
            on_select_clicked=self.open_image_picker,
            on_drop_paths=self.update_image_state,
        )
        self.dz_despues = DropZoneCard(
            "DESPUÉS",
            "despues",
            on_select_clicked=self.open_image_picker,
            on_drop_paths=self.update_image_state,
        )

        self.imgs_box.append(self.dz_antes)
        self.imgs_box.append(self.dz_durante)
        self.imgs_box.append(self.dz_despues)
        box_galeria.append(self.imgs_box)
        self.content_box.append(box_galeria)

        install_main_window_styles(
            [self.entry_desc, self.row_desc, self.lbl_desc, self.icon_edit]
        )

        def update_label_state(*_args):
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

        self.paths_antes = []
        self.paths_durante = []
        self.paths_despues = []

    def open_image_picker(self, context):
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
                if not paths:
                    return
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

    def _collect_evidencia_data(self) -> EvidenciaData:
        return EvidenciaData(
            plantel=self.entry_plantel.get_text().strip(),
            cct=self.entry_cct.get_text().strip(),
            direccion=self.entry_direccion.get_text().strip(),
            municipio=self.entry_municipio.get_text().strip(),
            concepto_numero=self.entry_num.get_text().strip(),
            concepto_texto=self._get_textview_text(self.entry_desc),
            img_antes=self.paths_antes,
            img_durante=self.paths_durante,
            img_despues=self.paths_despues,
        )

    def on_generate_pdf(self, btn):
        data = self._collect_evidencia_data()
        self.btn_gen.set_sensitive(False)
        self.toast_gen = Adw.Toast.new("Generando PDF...")
        self.toast_gen.set_timeout(0)
        self.toast_overlay.add_toast(self.toast_gen)
        thread = threading.Thread(target=self._generate_report_worker, args=(data,))
        thread.daemon = True
        thread.start()

    def _generate_report_worker(self, data: EvidenciaData):
        result = run_generate_evidence_report(data, self.save_path)
        GLib.idle_add(self._on_generate_report_finished, result)

    def _on_generate_report_finished(self, result: GenerateReportSuccess | GenerateReportError):
        self.btn_gen.set_sensitive(True)
        if hasattr(self, "toast_gen"):
            self.toast_gen.dismiss()
        if isinstance(result, GenerateReportSuccess):
            nice_name = os.path.basename(result.output_path)
            success_toast = Adw.Toast.new(f"Reporte Completado: {nice_name}")
            self.toast_overlay.add_toast(success_toast)
        else:
            self.show_alert(result.title, result.message)

    def show_alert(self, title, message):
        dialog = Adw.MessageDialog(heading=title, body=message, transient_for=self)
        dialog.add_response("ok", "Aceptar")
        dialog.set_default_response("ok")
        dialog.connect("response", lambda d, r: d.close())
        dialog.present()

    @staticmethod
    def _get_textview_text(textview):
        buffer = textview.get_buffer()
        start, end = buffer.get_bounds()
        return buffer.get_text(start, end, True).strip()
