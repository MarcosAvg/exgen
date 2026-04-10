"""
UI de la pestaña Evidencias - dropdowns jerárquicos y generación de PDF.
"""
import os
import threading
from datetime import datetime

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gio, GLib, Gtk

from src.application.evidence_photo import (
    GenerateEvidenceError,
    GenerateEvidenceSuccess,
    run_generate_evidence_pdf,
)
from src.domain.catalog_models import EvidencePhotoData
from src.ui.base_tab import BaseTab
from src.ui.catalog_config_window import CatalogConfigWindow
from src.ui.widgets.date_selector import DateSelector
from src.ui.widgets.evidence_drop_zone import EvidenceDropZone
from src.utils.config_manager import (
    get_catalog_system,
    get_last_evidence_image_dir,
    get_save_path,
    set_last_evidence_image_dir,
)


class EvidenciasTab(BaseTab):
    """Pestaña de Evidencias con dropdowns jerárquicos."""

    def __init__(self, toast_overlay: Adw.ToastOverlay):
        super().__init__(toast_overlay)
        self.set_vexpand(True)

        # Cargar sistema de catálogos
        self.catalog_system = get_catalog_system()

        # Dropdowns dinámicos y sus widgets
        self.all_dropdowns: dict[str, Adw.ComboRow] = {}
        self.dependent_rows: dict[str, Adw.ActionRow] = {}

        # Contenedor scrollable
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        self.append(scrolled)

        # Contenedor principal Grid para proporciones fijas (10 columnas)
        self.main_grid = Gtk.Grid()
        self.main_grid.set_column_homogeneous(True)
        self.main_grid.set_column_spacing(0)
        self.main_grid.set_margin_top(24)
        self.main_grid.set_margin_bottom(32)
        self.main_grid.set_margin_start(32)
        self.main_grid.set_margin_end(32)
        scrolled.set_child(self.main_grid)

        # Columna Izquierda: Configuración (40% -> 4 de 10 columnas)
        self.left_column = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        self.left_column.set_margin_end(32)
        self.main_grid.attach(self.left_column, 0, 0, 4, 1)

        # Columna Derecha: Resultados e Imágenes (60% -> 6 de 10 columnas)
        self.right_column = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        self.main_grid.attach(self.right_column, 4, 0, 6, 1)
        
        # Opcional: Asegurar que el contenido de la derecha se expanda bien dentro de su celda
        self.right_column.set_hexpand(True)

        # Barra de progreso (de BaseTab) - Ahora solo en la columna derecha
        self.right_column.append(self.progress_bar)

        # Contenido de la Columna Izquierda
        grp_principal = Adw.PreferencesGroup(title="Ubicación y Equipo")

        # Edificio
        edificio_catalog = self.catalog_system.get_catalog_by_name("edificio")
        items = edificio_catalog.items if edificio_catalog else []
        self.dropdown_edificio = Adw.ComboRow(
            title=edificio_catalog.label if edificio_catalog else "Edificio",
            model=Gtk.StringList.new(items or ["Sin datos"])
        )
        self.dropdown_edificio.connect("notify::selected", self._on_catalog_changed)
        grp_principal.add(self.dropdown_edificio)

        # Tipo de Equipo
        equipo_catalog = self.catalog_system.get_catalog_by_name("tipo_equipo")
        items_eq = equipo_catalog.items if equipo_catalog else []
        self.dropdown_equipo = Adw.ComboRow(
            title=equipo_catalog.label if equipo_catalog else "Tipo de Equipo",
            model=Gtk.StringList.new(items_eq or ["Sin datos"])
        )
        self.dropdown_equipo.connect("notify::selected", self._on_catalog_changed)
        grp_principal.add(self.dropdown_equipo)

        self.all_dropdowns["edificio"] = self.dropdown_edificio
        self.all_dropdowns["tipo_equipo"] = self.dropdown_equipo

        self.left_column.append(grp_principal)

        # Grupo: Catálogos dependientes
        self.grp_dependientes = Adw.PreferencesGroup(title="Información Adicional")
        self.left_column.append(self.grp_dependientes)

        # Grupo: Fecha
        grp_datos = Adw.PreferencesGroup(title="Datos del Reporte")
        self.date_selector = DateSelector()
        row_fecha = Adw.ActionRow(title="Fecha")
        row_fecha.add_suffix(self.date_selector)
        grp_datos.add(row_fecha)
        self.left_column.append(grp_datos)

        # (El botón de configuración ahora está en el menú de ajustes de la barra superior)

        # Contenido de la Columna Derecha (Imágenes)
        self.drop_zone = EvidenceDropZone(
            on_select_clicked=self._on_select_images,
            on_drop_paths=self._on_images_dropped,
            on_remove_image=self._on_remove_image,
            on_clear_all=self._clear_all_images,
        )
        self.right_column.append(self.drop_zone)

        # Inicializar dropdowns dependientes
        self._refresh_dependent_dropdowns()

        # Guardar ruta
        self.save_path = get_save_path()

        # Lista de imágenes seleccionadas
        self.image_paths: list[str] = []

    def _create_combobox(self, title: str, items: list[str]) -> Adw.ComboRow:
        """Crea un ComboRow con los items dados."""
        model = Gtk.StringList.new(items or ["Sin datos"])
        combo = Adw.ComboRow(title=title, model=model)
        combo.set_selected(0)
        return combo

    def _refresh_dependent_dropdowns(self):
        """Reconstruye los dropdowns según los catálogos dependientes."""
        # Limpiar grupo existente - solo remover AdwActionRow (no el GtkBox interno)
        child = self.grp_dependientes.get_first_child()
        while child:
            next_child = child.get_next_sibling()
            # Solo remover si es un PreferencesRow (ActionRow hereda de esto)
            if isinstance(child, Adw.PreferencesRow):
                self.grp_dependientes.remove(child)
            child = next_child

        # Mantener solo los base en all_dropdowns antes de reconstruir
        self.all_dropdowns = {
            "edificio": self.dropdown_edificio,
            "tipo_equipo": self.dropdown_equipo
        }
        self.dependent_rows.clear()

        # Crear dropdowns según catálogos dependientes
        dependent_catalogs = self.catalog_system.get_dependent_catalogs()

        if not dependent_catalogs:
            # Mensaje cuando no hay catálogos adicionales
            row_info = Adw.ActionRow(
                title="No hay campos adicionales",
                subtitle="Usa 'Configurar Catálogos' para agregar más dropdowns"
            )
            row_info.add_css_class("dim-label")
            self.grp_dependientes.add(row_info)
            return

        for catalog in dependent_catalogs:
            combo = self._create_combobox(catalog.label, catalog.items)
            combo.connect("notify::selected", self._on_catalog_changed)
            self.grp_dependientes.add(combo)

            self.all_dropdowns[catalog.name] = combo
            self.dependent_rows[catalog.name] = combo
        
        # Actualizar visibilidad inicial
        self._update_visibility()

    def _on_catalog_changed(self, *args):
        """Callback cuando cambia cualquier catálogo."""
        self._update_visibility()

    def _update_visibility(self):
        """Calcula qué catálogos deben ser visibles según sus dependencias."""
        # Necesitamos iterar hasta que no haya más cambios para manejar dependencias anidadas
        changed = True
        iterations = 0
        while changed and iterations < 10: # Límite de seguridad
            changed = False
            iterations += 1
            
            for catalog in self.catalog_system.get_dependent_catalogs():
                row = self.dependent_rows.get(catalog.name)
                if not row:
                    continue
                
                was_visible = row.get_visible()
                should_be_visible = True
                
                if catalog.parent_name:
                    parent_combo = self.all_dropdowns.get(catalog.parent_name)
                    if parent_combo:
                        # Un catálogo es visible si su padre es visible Y el valor coincide
                        parent_visible = parent_combo.get_visible()
                        selected_item = parent_combo.get_selected_item()
                        parent_value = selected_item.get_string() if selected_item else ""
                        
                        should_be_visible = parent_visible and (parent_value in catalog.parent_values)
                    else:
                        should_be_visible = False
                
                if was_visible != should_be_visible:
                    row.set_visible(should_be_visible)
                    # Si deja de ser visible, limpiar selección (requisito del usuario)
                    if not should_be_visible:
                        row.set_selected(0)
                    changed = True

    def refresh_catalogs(self):
        """Recarga los catálogos y actualiza la UI. Útil cuando se cambia la config desde MainWindow."""
        # Recargar catálogos
        self.catalog_system = get_catalog_system()
        
        # Actualizar dropdowns principales
        edificio = self.catalog_system.get_catalog_by_name("edificio")
        if edificio:
            self._update_dropdown_model(self.dropdown_edificio, edificio.items)
        
        equipo = self.catalog_system.get_catalog_by_name("tipo_equipo")
        if equipo:
            self._update_dropdown_model(self.dropdown_equipo, equipo.items)
            
        # Actualizar dropdowns dependientes
        self._refresh_dependent_dropdowns()

    def _on_open_config(self, _):
        """Ya no se usa directamente desde aquí, pero redirigimos al de MainWindow si fuera necesario."""
        self.get_root().on_open_catalog_config()

    def _update_dropdown_model(self, combo: Adw.ComboRow, items: list[str]):
        """Actualiza el modelo de un ComboRow."""
        model = Gtk.StringList.new(items or ["Sin datos"])
        combo.set_model(model)
        combo.set_selected(0)

    def _on_select_images(self):
        """Abre diálogo para seleccionar imágenes."""
        last_dir = get_last_evidence_image_dir()
        self.open_file_dialog(
            title="Seleccionar imágenes de evidencia",
            filter_name="Imágenes",
            mime_types=["image/png", "image/jpeg"],
            initial_folder=last_dir if os.path.exists(last_dir) else None,
            multiple=True,
            callback=self._on_images_selected
        )

    def _on_images_selected(self, paths: list[str]):
        """Procesa imágenes seleccionadas desde el diálogo."""
        if paths:
            self._add_images(paths)
            set_last_evidence_image_dir(os.path.dirname(paths[0]))

    def _on_images_dropped(self, paths: list[str]):
        """Procesa imágenes arrastradas."""
        self._add_images(paths)

    def _add_images(self, paths: list[str]):
        """Reemplaza la lista actual con las nuevas imágenes seleccionadas."""
        valid = [p for p in paths if p.lower().endswith((".png", ".jpg", ".jpeg"))]
        if valid:
            self.image_paths = valid
            self.drop_zone.update_images(self.image_paths)

    def _on_remove_image(self, index: int):
        """Elimina una imagen por índice."""
        if 0 <= index < len(self.image_paths):
            self.image_paths.pop(index)
            self.drop_zone.update_images(self.image_paths)

    def _clear_all_images(self):
        """Limpia todas las imágenes de evidencia."""
        self.image_paths = []
        self.drop_zone.update_images([])

    def get_evidence_data(self) -> EvidencePhotoData:
        """Recopila los datos actuales para generar PDF."""
        # Obtener edificio
        edificio_item = self.dropdown_edificio.get_selected_item()
        edificio = edificio_item.get_string() if edificio_item else ""

        # Obtener tipo de equipo
        equipo_item = self.dropdown_equipo.get_selected_item()
        tipo_equipo = equipo_item.get_string() if equipo_item else ""

        # Obtener valores de catálogos dependientes (solo si son visibles)
        dependent_values = {}
        for catalog in self.catalog_system.get_dependent_catalogs():
            row = self.dependent_rows.get(catalog.name)
            if row and row.get_visible():
                item = row.get_selected_item()
                if item:
                    value = item.get_string()
                    if value and value != "Sin datos":
                        dependent_values[catalog.name] = value

        # Obtener fecha del widget DateSelector
        fecha = self.date_selector.get_date_string()

        return EvidencePhotoData(
            edificio=edificio,
            tipo_equipo=tipo_equipo,
            fecha=fecha,
            dependent_values=dependent_values,
            imagenes=self.image_paths.copy(),
        )

    def generate_pdf(self, callback=None):
        """Inicia generación de PDF."""
        data = self.get_evidence_data()

        # Validar datos
        if not data.edificio or not data.tipo_equipo:
            self.show_alert("Datos incompletos", "Selecciona Edificio y Tipo de Equipo.")
            return False

        if not data.imagenes:
            self.show_alert("Sin imágenes", "Agrega al menos una imagen.")
            return False

        # Ejecutar tarea con progreso
        def task(data_in, progress_cb):
            return run_generate_evidence_pdf(data_in, self.save_path, progress_cb)

        self.run_task_with_progress(
            task, 
            data, 
            "Generando PDF de Evidencias...",
            lambda res: self._on_generate_finished(res, callback)
        )
        return True

    def _on_generate_finished(self, result, callback):
        """Callback cuando termina la generación."""
        if isinstance(result, GenerateEvidenceSuccess):
            nice_name = os.path.basename(result.output_path)
            success_toast = Adw.Toast.new(f"PDF Generado: {nice_name}")
            self.toast_overlay.add_toast(success_toast)
            if callback:
                callback(True, result.output_path)
        elif isinstance(result, GenerateEvidenceError):
            self.show_alert(result.title, result.message)
            if callback:
                callback(False, None)
        else:
            # Error inesperado (excepción en el worker)
            self.show_alert("Error inesperado", str(result))
            if callback:
                callback(False, None)

    def clear(self):
        """Limpia el formulario."""
        self.dropdown_edificio.set_selected(0)
        self.dropdown_equipo.set_selected(0)
        for dropdown in self.dependent_dropdowns.values():
            dropdown.set_selected(0)
        self.image_paths = []
        self.drop_zone.update_images([])
