"""
Pestaña Reportes - contenido original de MainWindow.
Generación de reportes con formato carta y background.
"""
import os
import threading

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gio, GLib, Gtk

from src.application.evidence_report import (
    GenerateReportError,
    GenerateReportSuccess,
    run_generate_evidence_report,
    run_generate_pptx_report,
)
from src.domain.models import EvidenciaData
from src.ui.base_tab import BaseTab
from src.ui.styles import install_main_window_styles
from src.ui.widgets.drop_zone import DropZoneCard
from src.utils.config_manager import (
    get_last_image_dir,
    get_save_path,
    set_last_image_dir,
)


class ReportesTab(BaseTab):
    """Pestaña de Reportes - funcionalidad original."""

    def __init__(self, toast_overlay: Adw.ToastOverlay):
        super().__init__(toast_overlay)

        # Contenedor scrollable
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        self.append(scrolled)

        # Contenedor principal Grid para proporciones fijas (10 columnas)
        self.main_grid = Gtk.Grid()
        self.main_grid.set_column_homogeneous(True)
        self.main_grid.set_column_spacing(0) # Espaciado manual para control fino
        self.main_grid.set_margin_top(24)
        self.main_grid.set_margin_bottom(32)
        self.main_grid.set_margin_start(32)
        self.main_grid.set_margin_end(32)
        scrolled.set_child(self.main_grid)

        # Columna Izquierda: Detalles (4 de 10 columnas = 40%)
        self.left_column = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        self.left_column.set_margin_end(32) # El "gap" entre columnas
        self.main_grid.attach(self.left_column, 0, 0, 4, 1)

        # Columna Derecha: Galería e Imágenes (6 de 10 columnas = 60%)
        self.right_column = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        self.main_grid.attach(self.right_column, 4, 0, 6, 1)

        # Barra de progreso (de BaseTab) - Columna derecha
        self.right_column.append(self.progress_bar)

        # Contenido de la Columna Izquierda
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
        
        self.row_expand = Adw.ActionRow(
            title="Expandir espacio",
            subtitle="Ocupar toda la hoja si faltan conceptos (Antes/Durante/Después)"
        )
        self.switch_expand = Gtk.Switch()
        self.switch_expand.set_valign(Gtk.Align.CENTER)
        self.row_expand.add_suffix(self.switch_expand)

        grp_detalles.add(self.entry_plantel)
        grp_detalles.add(self.entry_cct)
        grp_detalles.add(self.entry_direccion)
        grp_detalles.add(self.entry_municipio)
        grp_detalles.add(self.entry_num)
        grp_detalles.add(self.row_desc)
        grp_detalles.add(self.row_expand)
        self.left_column.append(grp_detalles)

        # Contenido de la Columna Derecha (Galería)
        box_galeria = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        lbl_imgs = Gtk.Label(label="Fotografías (Visuales)", xalign=0)
        lbl_imgs.add_css_class("heading")
        box_galeria.append(lbl_imgs)

        self.imgs_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=24)
        self.imgs_box.set_vexpand(False)

        self.dz_antes = DropZoneCard(
            "ANTES",
            "antes",
            on_select_clicked=self.open_image_picker,
            on_drop_paths=self.update_image_state,
            on_clear=self._clear_images,
        )
        self.dz_durante = DropZoneCard(
            "DURANTE",
            "durante",
            on_select_clicked=self.open_image_picker,
            on_drop_paths=self.update_image_state,
            on_clear=self._clear_images,
        )
        self.dz_despues = DropZoneCard(
            "DESPUÉS",
            "despues",
            on_select_clicked=self.open_image_picker,
            on_drop_paths=self.update_image_state,
            on_clear=self._clear_images,
        )

        self.imgs_box.append(self.dz_antes)
        self.imgs_box.append(self.dz_durante)
        self.imgs_box.append(self.dz_despues)
        box_galeria.append(self.imgs_box)
        self.right_column.append(box_galeria)

        # Estilos
        install_main_window_styles(
            [self.entry_desc, self.row_desc, self.lbl_desc, self.icon_edit]
        )

        # Animación del label
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

        # Guardar rutas
        self.save_path = get_save_path()
        self.paths_antes = []
        self.paths_durante = []
        self.paths_despues = []

    def open_image_picker(self, context):
        """Abre diálogo para seleccionar imágenes."""
        last_dir = get_last_image_dir()
        self.open_file_dialog(
            title="Selecciona la imagen de evidencia",
            filter_name="Imágenes",
            mime_types=["image/png", "image/jpeg"],
            initial_folder=last_dir if os.path.exists(last_dir) else None,
            multiple=True,
            callback=lambda paths: self._on_images_selected(paths, context)
        )

    def _on_images_selected(self, paths: list[str], context: str):
        """Procesa imágenes seleccionadas desde el diálogo."""
        if paths:
            self.update_image_state(paths, context)
            set_last_image_dir(os.path.dirname(paths[0]))

    def _clear_images(self, context: str):
        """Limpia las imágenes de un campo específico."""
        self.update_image_state([], context)

    def update_image_state(self, paths, context):
        """Actualiza el estado de imágenes según contexto."""
        if context == "antes":
            self.paths_antes = paths
            self.dz_antes.update_preview(paths)
        elif context == "durante":
            self.paths_durante = paths
            self.dz_durante.update_preview(paths)
        elif context == "despues":
            self.paths_despues = paths
            self.dz_despues.update_preview(paths)

    def _collect_evidencia_data(self) -> EvidenciaData:
        """Recopila datos del formulario."""
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
            expandir_espacio=self.switch_expand.get_active(),
        )

    def generate_pdf(self, callback=None):
        """Inicia generación de PDF."""
        data = self._collect_evidencia_data()

        # Validar datos mínimos
        if not data.plantel:
            self.show_alert("Faltan datos", "Por favor completa al menos el campo Plantel.")
            return False

        # Ejecutar tarea con progreso
        def task(data_in, progress_cb):
            return run_generate_evidence_report(data_in, self.save_path, progress_callback=progress_cb)

        self.run_task_with_progress(
            task, 
            data, 
            "Generando PDF...",
            lambda res: self._on_generate_finished(res, callback)
        )
        return True

    def generate_pptx(self, master_path, callback=None):
        """Inicia generación de PPTX."""
        data = self._collect_evidencia_data()
        if not data.plantel:
            self.show_alert("Faltan datos", "Por favor completa al menos el campo Plantel.")
            return False

        def task(data_in, progress_cb):
            return run_generate_pptx_report(data_in, master_path, progress_callback=progress_cb)

        self.run_task_with_progress(
            task,
            data,
            "Anexando a PPT Maestro...",
            lambda res: self._on_generate_finished(res, callback)
        )
        return True

    def _on_generate_finished(self, result, callback):
        """Callback cuando termina generación."""
        if isinstance(result, GenerateReportSuccess):
            nice_name = os.path.basename(result.output_path)
            success_toast = Adw.Toast.new(f"Reporte Completado: {nice_name}")
            self.toast_overlay.add_toast(success_toast)
            if callback:
                callback(True, result.output_path)
        elif isinstance(result, GenerateReportError):
            self.show_alert(result.title, result.message)
            if callback:
                callback(False, None)
        else:
            self.show_alert("Error inesperado", str(result))
            if callback:
                callback(False, None)

    @staticmethod
    def _get_textview_text(textview):
        """Extrae texto de un TextView."""
        buffer = textview.get_buffer()
        start, end = buffer.get_bounds()
        return buffer.get_text(start, end, True).strip()

    def clear(self):
        """Limpia el formulario."""
        self.entry_plantel.set_text("")
        self.entry_cct.set_text("")
        self.entry_direccion.set_text("")
        self.entry_municipio.set_text("")
        self.entry_num.set_text("")
        buffer = self.entry_desc.get_buffer()
        buffer.set_text("")
        self.paths_antes = []
        self.paths_durante = []
        self.paths_despues = []
        self.dz_antes.update_preview([])
        self.dz_durante.update_preview([])
        self.dz_despues.update_preview([])
        self.switch_expand.set_active(False)
