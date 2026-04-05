import os
import threading

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("Gdk", "4.0")
from gi.repository import Adw, Gtk

from src.ui.catalog_config_window import CatalogConfigWindow
from src.ui.evidencias_tab import EvidenciasTab
from src.ui.reportes_tab import ReportesTab
from src.utils.config_manager import (
    get_catalog_system,
    get_save_path,
    set_save_path,
)


class MainWindow(Adw.ApplicationWindow):
    """Ventana principal con sistema de pestañas."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_title("Generador de Evidencia")
        self.set_default_size(1200, 850)

        # Toast overlay global
        self.toast_overlay = Adw.ToastOverlay()
        self.set_content(self.toast_overlay)

        # Toolbar view
        self.toolbar_view = Adw.ToolbarView()
        self.toast_overlay.set_child(self.toolbar_view)

        # Header
        header = Adw.HeaderBar()
        self.toolbar_view.add_top_bar(header)

        # ViewSwitcher en el centro del HeaderBar
        self.view_switcher_title = Adw.ViewSwitcherTitle()
        header.set_title_widget(self.view_switcher_title)

        # Botón de generar (discreto en el HeaderBar - ahora a la izquierda)
        self.btn_gen = Gtk.Button(label="Generar PDF")
        self.btn_gen.connect("clicked", self.on_generate_pdf)
        header.pack_start(self.btn_gen)

        # Botón de ajustes/configuración
        btn_settings = Gtk.MenuButton(icon_name="document-properties-symbolic")
        self.popover_settings = Gtk.Popover()
        grp_destino = Adw.PreferencesGroup(title="Ajustes")
        grp_destino.set_margin_top(8)
        grp_destino.set_margin_bottom(8)
        grp_destino.set_margin_start(8)
        grp_destino.set_margin_end(8)

        self.save_path = get_save_path()
        self.row_destino = Adw.ActionRow(title="Carpeta de Destino", subtitle=self.save_path)
        self.row_destino.set_activatable(True)
        self.row_destino.connect("activated", self.on_select_folder)
        btn_folder = Gtk.Button(icon_name="folder-open-symbolic", valign=Gtk.Align.CENTER)
        btn_folder.set_tooltip_text("Seleccionar carpeta")
        btn_folder.connect("clicked", self.on_select_folder)
        self.row_destino.add_suffix(btn_folder)
        grp_destino.add(self.row_destino)

        # Fila de Catálogos (Nueva opción unificada)
        self.row_catalogos = Adw.ActionRow(title="Configuración de Catálogos", subtitle="Administrar listas y dependencias")
        self.row_catalogos.set_activatable(True)
        self.row_catalogos.connect("activated", self.on_open_catalog_config)
        btn_cat = Gtk.Button(icon_name="edit-symbolic", valign=Gtk.Align.CENTER)
        btn_cat.add_css_class("flat")
        btn_cat.set_tooltip_text("Configurar")
        btn_cat.connect("clicked", self.on_open_catalog_config)
        self.row_catalogos.add_suffix(btn_cat)
        grp_destino.add(self.row_catalogos)

        self.popover_settings.set_child(grp_destino)
        btn_settings.set_popover(self.popover_settings)
        header.pack_end(btn_settings)

        # ViewStack con pestañas
        self.stack = Adw.ViewStack()
        self.stack.set_vexpand(True)
        self.view_switcher_title.set_stack(self.stack)
        self.toolbar_view.set_content(self.stack)

        # Pestaña 1: Reportes
        self.tab_reportes = ReportesTab(self.toast_overlay)
        page_reportes = self.stack.add_titled_with_icon(
            self.tab_reportes, 
            "reportes", 
            "Reportes", 
            "document-edit-symbolic"
        )

        # Pestaña 2: Evidencias
        self.tab_evidencias = EvidenciasTab(self.toast_overlay)
        page_evidencias = self.stack.add_titled_with_icon(
            self.tab_evidencias, 
            "evidencias", 
            "Evidencias", 
            "photo-library-symbolic"
        )

        # Sincronizar texto del botón al cambiar de pestaña
        self.stack.connect("notify::visible-child", self._on_tab_switched)
        self._on_tab_switched(None, None)

    def _on_tab_switched(self, *args):
        """Callback cuando se cambia de pestaña."""
        current = self.stack.get_visible_child()
        if current == self.tab_reportes:
            self.btn_gen.set_label("Generar PDF")
        else:
            self.btn_gen.set_label("Generar Evidencia")

    def on_generate_pdf(self, btn):
        """Genera PDF según la pestaña activa."""
        current = self.stack.get_visible_child()
        btn.set_sensitive(False)

        def callback(success, path):
            btn.set_sensitive(True)

        if current == self.tab_reportes:
            self.tab_reportes.generate_pdf(callback)
        else:
            self.tab_evidencias.generate_pdf(callback)

    def on_open_catalog_config(self, *args):
        """Abre la ventana de configuración de catálogos y refresca las pestañas."""
        # Cerrar el popover manualmente (mejor UX)
        self.popover_settings.popdown()
        
        def on_save():
            # Notificar a la pestaña de evidencias que recargue los catálogos
            if hasattr(self, "tab_evidencias") and hasattr(self.tab_evidencias, "refresh_catalogs"):
                self.tab_evidencias.refresh_catalogs()
        
        window = CatalogConfigWindow(parent=self, on_save=on_save)
        window.present()

    def on_select_folder(self, *args):
        """Abre diálogo para seleccionar carpeta de destino."""
        self.popover_settings.popdown()
        dialog = Gtk.FileDialog()
        dialog.set_title("Selecciona la carpeta de destino")
        dialog.select_folder(self, None, self.on_folder_dialog_response)

    def on_folder_dialog_response(self, dialog, result):
        """Procesa selección de carpeta."""
        try:
            folder = dialog.select_folder_finish(result)
            if folder:
                path = folder.get_path()
                self.save_path = path
                self.row_destino.set_subtitle(path)
                set_save_path(path)
                # Actualizar ruta en ambas pestañas
                self.tab_reportes.save_path = path
                self.tab_evidencias.save_path = path
        except Exception:
            pass

