"""
Ventana de configuración simplificada para catálogos.
Cada catálogo creado automáticamente genera un dropdown.
"""
import os
from collections.abc import Callable

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, GLib, Gtk

from src.domain.catalog_models import Catalog, CatalogSystem
from src.utils.config_manager import CONFIG_FILE, get_catalog_system, set_catalog_system


class CatalogConfigWindow(Adw.Window):
    """Ventana de configuración simplificada de catálogos."""

    def __init__(self, parent=None, on_save: Callable[[], None] = None):
        super().__init__(title="Configuración de Catálogos")
        self.set_transient_for(parent)
        self.set_modal(True)
        self.set_default_size(600, 700)
        self.on_save_callback = on_save

        # Cargar sistema
        self.catalog_system = get_catalog_system()

        # Toast overlay
        self.toast_overlay = Adw.ToastOverlay()
        self.set_content(self.toast_overlay)

        # Toolbar view
        toolbar = Adw.ToolbarView()
        self.toast_overlay.set_child(toolbar)

        # Header
        header = Adw.HeaderBar()
        header.set_show_end_title_buttons(False)
        toolbar.add_top_bar(header)

        # Botón cancelar
        btn_cancel = Gtk.Button(label="Cancelar")
        btn_cancel.connect("clicked", lambda _: self.close())
        header.pack_start(btn_cancel)

        # Botón guardar
        btn_save = Gtk.Button(label="Guardar")
        btn_save.add_css_class("suggested-action")
        btn_save.connect("clicked", self._on_save)
        header.pack_end(btn_save)

        # Contenido principal
        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        toolbar.set_content(scroll)

        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        self.main_box.set_margin_top(16)
        self.main_box.set_margin_bottom(16)
        self.main_box.set_margin_start(16)
        self.main_box.set_margin_end(16)
        scroll.set_child(self.main_box)

        # Info de ubicación del JSON
        info_group = Adw.PreferencesGroup(title="Ubicación de datos")
        row_path = Adw.ActionRow(
            title="Archivo de configuración",
            subtitle=CONFIG_FILE
        )
        row_path.add_css_class("dim-label")
        # Cargar datos iniciales
        self._refresh_ui()

    def _create_catalog_row(self, catalog: Catalog, editable: bool, deletable: bool) -> Adw.ActionRow:
        """Crea una fila para un catálogo."""
        items_count = len(catalog.items)
        subtitle = f"{items_count} valor{'es' if items_count != 1 else ''}"
        if not catalog.items:
            subtitle = "Sin valores - haz clic en el icono para agregar"
        
        if catalog.parent_name:
            parent = self.catalog_system.get_catalog_by_name(catalog.parent_name)
            p_label = parent.label if parent else catalog.parent_name
            p_values = ", ".join(catalog.parent_values)
            subtitle += f"\nDepende de: {p_label} ({p_values})"

        row = Adw.ActionRow(
            title=catalog.label,
            subtitle=subtitle
        )

        # Botón editar items
        if editable:
            btn_edit = Gtk.Button(icon_name="document-edit-symbolic")
            btn_edit.add_css_class("flat")
            btn_edit.set_valign(Gtk.Align.CENTER)
            btn_edit.set_tooltip_text("Editar valores")
            btn_edit.connect("clicked", lambda _, c=catalog: self._edit_catalog_items(c))
            row.add_suffix(btn_edit)

        # Botón configurar metadatos/dependencias
        if editable:
            btn_config = Gtk.Button(icon_name="emblem-system-symbolic")
            btn_config.add_css_class("flat")
            btn_config.set_valign(Gtk.Align.CENTER)
            btn_config.set_tooltip_text("Configurar dependencias")
            btn_config.connect("clicked", lambda _, c=catalog: self._on_edit_catalog_metadata(c))
            row.add_suffix(btn_config)

        # Botón eliminar (solo para dependientes)
        if deletable:
            btn_remove = Gtk.Button(icon_name="user-trash-symbolic")
            btn_remove.add_css_class("flat")
            btn_remove.add_css_class("error")
            btn_remove.set_valign(Gtk.Align.CENTER)
            btn_remove.set_tooltip_text("Eliminar catálogo")
            btn_remove.connect("clicked", lambda _, n=catalog.name: self._remove_catalog(n))
            row.add_suffix(btn_remove)

        return row

    def _refresh_ui(self):
        """Limpia y reconstruye toda la interfaz para evitar duplicados."""
        # Limpiar main_box completamente
        child = self.main_box.get_first_child()
        while child:
            self.main_box.remove(child)
            child = self.main_box.get_first_child()

        # 1. Info de ubicación
        info_group = Adw.PreferencesGroup(title="Ubicación de datos")
        row_path = Adw.ActionRow(title="Archivo de configuración", subtitle=CONFIG_FILE)
        row_path.add_css_class("dim-label")
        info_group.add(row_path)
        self.main_box.append(info_group)

        self.main_box.append(Gtk.Separator())

        # 2. Catálogos Base
        base_group = Adw.PreferencesGroup(title="Catálogos Base (Fijos)")
        base_group.set_description("Estos catálogos siempre aparecen primero")
        for catalog in self.catalog_system.get_base_catalogs():
            row = self._create_catalog_row(catalog, editable=True, deletable=False)
            base_group.add(row)
        self.main_box.append(base_group)

        # 3. Catálogos Adicionales
        dep_group = Adw.PreferencesGroup(title="Catálogos Adicionales")
        dep_group.set_description("Cada catálogo aquí crea un dropdown automáticamente")
        
        for catalog in self.catalog_system.get_dependent_catalogs():
            row = self._create_catalog_row(catalog, editable=True, deletable=True)
            dep_group.add(row)

        if not self.catalog_system.get_dependent_catalogs():
            empty_row = Adw.ActionRow(title="No hay catálogos adicionales", subtitle="Haz clic abajo para crear uno")
            empty_row.add_css_class("dim-label")
            dep_group.add(empty_row)

        btn_add = Gtk.Button(label="+ Agregar Catálogo")
        btn_add.add_css_class("pill")
        btn_add.set_margin_top(8)
        btn_add.connect("clicked", self._on_add_catalog)
        dep_group.add(btn_add)
        
        self.main_box.append(dep_group)

        # 4. Ayuda
        help_label = Gtk.Label(label="Tip: Edita los valores haciendo clic en el icono del lápiz")
        help_label.add_css_class("dim-label")
        help_label.set_margin_top(16)
        self.main_box.append(help_label)

    def _on_add_catalog(self, _):
        """Abre diálogo para agregar nuevo catálogo."""
        self._show_catalog_metadata_dialog(None)

    def _on_edit_catalog_metadata(self, catalog: Catalog):
        """Abre diálogo para editar metadatos de un catálogo existente."""
        self._show_catalog_metadata_dialog(catalog)

    def _show_catalog_metadata_dialog(self, catalog: Catalog | None):
        """Diálogo unificado para crear o editar metadatos y dependencias."""
        is_edit = catalog is not None
        title = "Editar Catálogo" if is_edit else "Nuevo Catálogo"
        
        dialog = Adw.MessageDialog(transient_for=self, heading=title)
        dialog.add_response("cancel", "Cancelar")
        dialog.add_response("save", "Guardar" if is_edit else "Agregar")
        dialog.set_response_appearance("save", Adw.ResponseAppearance.SUGGESTED)
        dialog.set_default_response("save")

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_margin_top(12)
        box.set_margin_bottom(12)
        box.set_margin_start(12)
        box.set_margin_end(12)

        # Nombre técnico (deshabilitado en edición para evitar romper persistencia)
        entry_name = Gtk.Entry(text=catalog.name if is_edit else "")
        entry_name.set_placeholder_text("Nombre técnico (ej: pisos, ids)")
        entry_name.set_sensitive(not is_edit)
        box.append(Gtk.Label(label="Nombre técnico:", xalign=0))
        box.append(entry_name)

        # Etiqueta visible
        entry_label = Gtk.Entry(text=catalog.label if is_edit else "")
        entry_label.set_placeholder_text("Etiqueta visible (ej: Pisos, IDs)")
        box.append(Gtk.Label(label="Etiqueta visible:", xalign=0))
        box.append(entry_label)

        # Dependencias
        box.append(Gtk.Separator())
        box.append(Gtk.Label(label="Dependencia (Opcional):", xalign=0))

        # Lista de posibles padres
        potential_parents = ["Ninguno (Siempre visible)"]
        parent_names = [""]
        for c in self.catalog_system.catalogs:
            # En modo edición, no puede depender de sí mismo
            if not is_edit or c.name != catalog.name:
                potential_parents.append(c.label)
                parent_names.append(c.name)

        # Usar un ListBox para que el ComboRow se vea y funcione bien
        list_box = Gtk.ListBox()
        list_box.set_selection_mode(Gtk.SelectionMode.NONE)
        list_box.add_css_class("boxed-list")
        
        combo_parent = Adw.ComboRow(
            title="Depende de",
            model=Gtk.StringList.new(potential_parents)
        )
        
        # Seleccionar el actual si existe
        if is_edit and catalog.parent_name:
            try:
                idx = parent_names.index(catalog.parent_name)
                combo_parent.set_selected(idx)
            except ValueError:
                combo_parent.set_selected(0)
        else:
            combo_parent.set_selected(0)
            
        list_box.append(combo_parent)
        box.append(list_box)

        # Contenedor para valores activadores
        box.append(Gtk.Label(label="Valores activadores (marcar para activar):", xalign=0))
        
        values_scroll = Gtk.ScrolledWindow()
        values_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        values_scroll.set_min_content_height(150)
        values_scroll.set_propagate_natural_height(True)
        
        values_list = Gtk.ListBox()
        values_list.set_selection_mode(Gtk.SelectionMode.NONE)
        values_list.add_css_class("boxed-list")
        values_scroll.set_child(values_list)
        box.append(values_scroll)

        def update_values_view(p_name):
            # Limpiar lista anterior
            child = values_list.get_first_child()
            while child:
                values_list.remove(child)
                child = values_list.get_first_child()
            
            if not p_name:
                values_scroll.set_visible(False)
                return
            
            parent_catalog = self.catalog_system.get_catalog_by_name(p_name)
            if not parent_catalog or not parent_catalog.items:
                empty = Adw.ActionRow(title="El catálogo padre no tiene valores")
                empty.add_css_class("dim-label")
                values_list.append(empty)
                values_scroll.set_visible(True)
                return

            for item in parent_catalog.items:
                row = Adw.ActionRow(title=item)
                check = Gtk.CheckButton(valign=Gtk.Align.CENTER)
                # Si estamos editando y este valor ya estaba guardado, marcarlo
                if is_edit and p_name == catalog.parent_name and item in catalog.parent_values:
                    check.set_active(True)
                
                row.add_prefix(check)
                # Permitir activar haciendo clic en la fila
                row.set_activatable_widget(check)
                values_list.append(row)
            
            values_scroll.set_visible(True)

        # Vincular cambio de padre a actualización de valores
        combo_parent.connect("notify::selected", lambda *args: update_values_view(parent_names[combo_parent.get_selected()]))
        
        # Carga inicial
        update_values_view(parent_names[combo_parent.get_selected()])

        dialog.set_extra_child(box)

        def on_response(d, response):
            if response == "save":
                name = entry_name.get_text().strip().lower().replace(" ", "_")
                label = entry_label.get_text().strip()
                parent_idx = combo_parent.get_selected()
                parent_name = parent_names[parent_idx] if parent_idx > 0 else None
                
                # Recolectar valores marcados
                selected_values = []
                if parent_name:
                    item_row = values_list.get_first_child()
                    while item_row:
                        if isinstance(item_row, Adw.ActionRow):
                            check = item_row.get_activatable_widget()
                            if isinstance(check, Gtk.CheckButton) and check.get_active():
                                selected_values.append(item_row.get_title())
                        item_row = item_row.get_next_sibling()

                if not name or not label:
                    self._show_error("Debes ingresar nombre y etiqueta")
                    return

                try:
                    if is_edit:
                        catalog.label = label
                        catalog.parent_name = parent_name
                        catalog.parent_values = selected_values
                    else:
                        new_cat = self.catalog_system.add_catalog(name, label)
                        new_cat.parent_name = parent_name
                        new_cat.parent_values = selected_values
                    
                    self._refresh_ui()
                except ValueError as e:
                    self._show_error(str(e))

            d.close()

        dialog.connect("response", on_response)
        dialog.present()

    def _remove_catalog(self, name: str):
        """Elimina un catálogo."""
        try:
            self.catalog_system.remove_catalog(name)
            self._refresh_dependent_catalogs()
        except ValueError as e:
            self._show_error(str(e))

    def _edit_catalog_items(self, catalog: Catalog):
        """Abre diálogo para editar items de un catálogo."""
        dialog = Adw.Window(
            transient_for=self,
            title=f"Editar: {catalog.label}",
            modal=True
        )
        dialog.set_default_size(500, 500)

        toolbar = Adw.ToolbarView()
        dialog.set_content(toolbar)

        header = Adw.HeaderBar()
        header.set_show_end_title_buttons(False)
        toolbar.add_top_bar(header)

        def on_close(*args):
            self._refresh_ui()
            dialog.close()

        btn_close = Gtk.Button(label="Cerrar")
        btn_close.connect("clicked", on_close)
        header.pack_end(btn_close)

        # Contenido
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_margin_top(12)
        box.set_margin_bottom(12)
        box.set_margin_start(12)
        box.set_margin_end(12)

        # Lista de items
        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)

        list_box = Gtk.ListBox()
        list_box.set_selection_mode(Gtk.SelectionMode.NONE)
        list_box.add_css_class("boxed-list")

        def refresh_items():
            # Limpiar
            child = list_box.get_first_child()
            while child:
                list_box.remove(child)
                child = list_box.get_first_child()

            # Mostrar items
            if not catalog.items:
                empty = Adw.ActionRow(title="No hay valores registrados")
                empty.add_css_class("dim-label")
                list_box.append(empty)
            else:
                for i, item in enumerate(catalog.items):
                    row = Adw.ActionRow(title=item)

                    btn_up = Gtk.Button(icon_name="go-up-symbolic")
                    btn_up.add_css_class("flat")
                    btn_up.set_sensitive(i > 0)
                    btn_up.connect("clicked", lambda _, idx=i: self._move_item(catalog, idx, -1, refresh_items))
                    row.add_suffix(btn_up)

                    btn_down = Gtk.Button(icon_name="go-down-symbolic")
                    btn_down.add_css_class("flat")
                    btn_down.set_sensitive(i < len(catalog.items) - 1)
                    btn_down.connect("clicked", lambda _, idx=i: self._move_item(catalog, idx, 1, refresh_items))
                    row.add_suffix(btn_down)

                    btn_remove = Gtk.Button(icon_name="user-trash-symbolic")
                    btn_remove.add_css_class("flat")
                    btn_remove.connect("clicked", lambda _, it=item: self._remove_item(catalog, it, refresh_items))
                    row.add_suffix(btn_remove)

                    list_box.append(row)

        refresh_items()
        scroll.set_child(list_box)
        box.append(scroll)

        # Agregar nuevo item
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        entry_new = Gtk.Entry()
        entry_new.set_hexpand(True)
        entry_new.set_placeholder_text("Nuevo valor...")
        entry_new.connect("activate", lambda _: self._add_item(catalog, entry_new, refresh_items))
        hbox.append(entry_new)

        btn_add = Gtk.Button(icon_name="list-add-symbolic")
        btn_add.add_css_class("suggested-action")
        btn_add.connect("clicked", lambda _: self._add_item(catalog, entry_new, refresh_items))
        hbox.append(btn_add)

        box.append(hbox)
        toolbar.set_content(box)

        dialog.present()

    def _add_item(self, catalog: Catalog, entry: Gtk.Entry, refresh_callback):
        """Agrega un item al catálogo."""
        value = entry.get_text().strip()
        if value and value not in catalog.items:
            catalog.items.append(value)
            entry.set_text("")
            refresh_callback()

    def _remove_item(self, catalog: Catalog, item: str, refresh_callback):
        """Elimina un item del catálogo."""
        if item in catalog.items:
            catalog.items.remove(item)
            refresh_callback()

    def _move_item(self, catalog: Catalog, index: int, direction: int, refresh_callback):
        """Mueve un item arriba o abajo en la lista."""
        new_index = index + direction
        if 0 <= new_index < len(catalog.items):
            catalog.items[index], catalog.items[new_index] = catalog.items[new_index], catalog.items[index]
            refresh_callback()

    def _on_save(self, _):
        """Guarda los cambios."""
        set_catalog_system(self.catalog_system)

        toast = Adw.Toast.new("Configuración guardada")
        toast.set_timeout(2)
        self.toast_overlay.add_toast(toast)

        if self.on_save_callback:
            self.on_save_callback()

        # Cerrar ventana
        GLib.timeout_add(500, self.close)

    def _show_error(self, message: str):
        """Muestra error en toast."""
        toast = Adw.Toast.new(message)
        toast.add_css_class("error")
        self.toast_overlay.add_toast(toast)
