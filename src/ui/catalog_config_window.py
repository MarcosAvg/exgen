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

from src.domain.catalog_models import Catalog, CatalogSystem, CatalogDependency
from src.utils.config_manager import CONFIG_FILE, get_catalog_system, set_catalog_system


class CatalogConfigWindow(Adw.Window):
    """Ventana de configuración simplificada de catálogos."""

    def __init__(self, parent=None, on_save: Callable[[], None] = None):
        super().__init__(title="Configuración de Catálogos")
        self.set_transient_for(parent)
        self.set_modal(True)
        self.set_default_size(600, 750)
        self.on_save_callback = on_save

        # Cargar sistema
        self.catalog_system = get_catalog_system()

        # Toast overlay
        self.toast_overlay = Adw.ToastOverlay()
        self.set_content(self.toast_overlay)

        # Toolbar view
        self.toolbar = Adw.ToolbarView()
        self.toast_overlay.set_child(self.toolbar)

        # Header
        header = Adw.HeaderBar()
        header.set_show_end_title_buttons(False)
        self.toolbar.add_top_bar(header)

        btn_cancel = Gtk.Button(label="Cancelar")
        btn_cancel.connect("clicked", lambda _: self.close())
        header.pack_start(btn_cancel)

        btn_save = Gtk.Button(label="Guardar")
        btn_save.add_css_class("suggested-action")
        btn_save.connect("clicked", self._on_save)
        header.pack_end(btn_save)

        self._refresh_ui()

    # ─── Creación de filas ───────────────────────────────────────────

    def _create_catalog_row(self, catalog: Catalog, editable: bool, deletable: bool) -> Adw.ActionRow:
        """Crea una ActionRow nativa para un catálogo."""
        items_count = len(catalog.items)
        subtitle = f"{items_count} valor{'es' if items_count != 1 else ''}"
        if not catalog.items:
            subtitle = "Sin valores"

        if catalog.dependencies:
            dep_parts = []
            for dep in catalog.dependencies:
                parent = self.catalog_system.get_catalog_by_name(dep.parent_name)
                p_label = parent.label if parent else dep.parent_name
                vals = ", ".join(dep.values[:3])
                if len(dep.values) > 3:
                    vals += "…"
                dep_parts.append(f"{p_label} ({vals})")
            subtitle += "\nCondiciones: " + " Y ".join(dep_parts)

        row = Adw.ActionRow(title=catalog.name, subtitle=f"Etiqueta: {catalog.label} | {subtitle}")

        if editable:
            btn_edit = Gtk.Button(icon_name="document-edit-symbolic",
                                 valign=Gtk.Align.CENTER,
                                 tooltip_text="Editar valores")
            btn_edit.add_css_class("flat")
            btn_edit.connect("clicked", lambda _, c=catalog: self._edit_catalog_items(c))
            row.add_suffix(btn_edit)

            btn_config = Gtk.Button(icon_name="emblem-system-symbolic",
                                   valign=Gtk.Align.CENTER,
                                   tooltip_text="Configurar dependencias")
            btn_config.add_css_class("flat")
            btn_config.connect("clicked", lambda _, c=catalog: self._show_catalog_metadata_dialog(c))
            row.add_suffix(btn_config)

        if deletable:
            btn_remove = Gtk.Button(icon_name="user-trash-symbolic",
                                   valign=Gtk.Align.CENTER,
                                   tooltip_text="Eliminar catálogo")
            btn_remove.add_css_class("flat")
            btn_remove.connect("clicked", lambda _, n=catalog.name: self._remove_catalog(n))
            row.add_suffix(btn_remove)

        return row

    # ─── Refresh ─────────────────────────────────────────────────────

    def _refresh_ui(self):
        """Limpia y reconstruye usando PreferencesPage/Group nativos."""
        self.prefs_page = Adw.PreferencesPage()
        self.toolbar.set_content(self.prefs_page)

        # Info
        grp_info = Adw.PreferencesGroup(title="Ubicación de datos")
        row_path = Adw.ActionRow(title="Archivo de configuración", subtitle=CONFIG_FILE)
        row_path.add_css_class("dim-label")
        grp_info.add(row_path)
        self.prefs_page.add(grp_info)

        # Catálogos base
        grp_base = Adw.PreferencesGroup(title="Catálogos Base",
                                        description="Estos catálogos siempre aparecen primero")
        for cat in self.catalog_system.get_base_catalogs():
            grp_base.add(self._create_catalog_row(cat, editable=True, deletable=False))
        self.prefs_page.add(grp_base)

        # Catálogos adicionales
        grp_dep = Adw.PreferencesGroup(title="Catálogos Adicionales",
                                       description="Cada catálogo aquí crea un dropdown automáticamente")
        for cat in self.catalog_system.get_dependent_catalogs():
            grp_dep.add(self._create_catalog_row(cat, editable=True, deletable=True))

        if not self.catalog_system.get_dependent_catalogs():
            empty = Adw.ActionRow(title="Sin catálogos adicionales",
                                  subtitle="Usa el botón de abajo para crear uno")
            empty.add_css_class("dim-label")
            grp_dep.add(empty)

        # Fila nativa para agregar
        row_add = Adw.ActionRow(title="Agregar catálogo")
        row_add.set_activatable(True)
        row_add.add_prefix(Gtk.Image(icon_name="list-add-symbolic"))
        row_add.connect("activated", lambda _: self._show_catalog_metadata_dialog(None))
        grp_dep.add(row_add)

        self.prefs_page.add(grp_dep)

    # ─── Diálogo: Crear / Editar Catálogo ────────────────────────────

    def _show_catalog_metadata_dialog(self, catalog: Catalog | None):
        """Diálogo nativo para crear o editar un catálogo con dependencias."""
        is_edit = catalog is not None
        title = "Editar Catálogo" if is_edit else "Nuevo Catálogo"

        dialog = Adw.MessageDialog(transient_for=self, heading=title)
        dialog.add_response("cancel", "Cancelar")
        dialog.add_response("save", "Guardar" if is_edit else "Crear")
        dialog.set_response_appearance("save", Adw.ResponseAppearance.SUGGESTED)
        dialog.set_default_response("save")

        # Copia local de dependencias
        local_deps = []
        if is_edit:
            for dep in catalog.dependencies:
                local_deps.append(CatalogDependency(dep.parent_name, dep.values.copy()))

        # Contenido
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)

        # Campos básicos usando Adw.EntryRow (nativo, como en reportes_tab)
        grp_basic = Adw.PreferencesGroup(title="Datos Básicos")
        entry_name = Adw.EntryRow(title="Nombre técnico",
                                  text=catalog.name if is_edit else "")
        entry_name.set_sensitive(not is_edit)
        grp_basic.add(entry_name)

        entry_label = Adw.EntryRow(title="Etiqueta visible",
                                   text=catalog.label if is_edit else "")
        grp_basic.add(entry_label)
        box.append(grp_basic)

        # Dependencias
        grp_deps = Adw.PreferencesGroup(title="Condiciones de Visibilidad",
                                        description="El catálogo se muestra si se cumplen todas (AND)")

        deps_container = Gtk.ListBox()
        deps_container.add_css_class("boxed-list")
        deps_container.set_selection_mode(Gtk.SelectionMode.NONE)

        def refresh_deps():
            child = deps_container.get_first_child()
            while child:
                deps_container.remove(child)
                child = deps_container.get_first_child()

            if not local_deps:
                r = Adw.ActionRow(title="Siempre visible",
                                  subtitle="Sin condiciones configuradas")
                r.add_css_class("dim-label")
                deps_container.append(r)
            else:
                for i, dep in enumerate(local_deps):
                    parent = self.catalog_system.get_catalog_by_name(dep.parent_name)
                    p_label = parent.label if parent else dep.parent_name
                    vals = ", ".join(dep.values) if dep.values else "Sin valores"

                    r = Adw.ActionRow(title=p_label, subtitle=vals)

                    btn_e = Gtk.Button(icon_name="document-edit-symbolic",
                                       valign=Gtk.Align.CENTER)
                    btn_e.add_css_class("flat")
                    btn_e.connect("clicked", lambda _, d=dep: self._edit_dependency_values(d, refresh_deps))
                    r.add_suffix(btn_e)

                    btn_d = Gtk.Button(icon_name="user-trash-symbolic",
                                       valign=Gtk.Align.CENTER)
                    btn_d.add_css_class("flat")
                    btn_d.connect("clicked", lambda _, idx=i: [local_deps.pop(idx), refresh_deps()])
                    r.add_suffix(btn_d)

                    deps_container.append(r)

            # Fila para agregar condición
            row_add_dep = Adw.ActionRow(title="Agregar condición")
            row_add_dep.set_activatable(True)
            row_add_dep.add_prefix(Gtk.Image(icon_name="list-add-symbolic"))
            row_add_dep.connect("activated",
                                lambda _: self._add_dependency(local_deps, entry_name.get_text(), refresh_deps))
            deps_container.append(row_add_dep)

        refresh_deps()
        grp_deps.add(deps_container)
        box.append(grp_deps)

        dialog.set_extra_child(box)

        def on_response(d, response):
            if response == "save":
                name = entry_name.get_text().strip().lower().replace(" ", "_")
                label = entry_label.get_text().strip()
                if not name or not label:
                    self._show_toast("Nombre y etiqueta son obligatorios")
                    return
                try:
                    if is_edit:
                        catalog.label = label
                        catalog.dependencies = local_deps
                    else:
                        new_cat = self.catalog_system.add_catalog(name, label)
                        new_cat.dependencies = local_deps
                    self._refresh_ui()
                except ValueError as e:
                    self._show_toast(str(e))
            d.close()

        dialog.connect("response", on_response)
        dialog.present()

    # ─── Diálogo: Agregar dependencia ────────────────────────────────

    def _add_dependency(self, local_deps, current_name, callback):
        """Diálogo para elegir de qué catálogo depende."""
        existing = {d.parent_name for d in local_deps}
        potential, p_names = [], []
        for c in self.catalog_system.catalogs:
            if c.name != current_name and c.name not in existing:
                potential.append(c.label)
                p_names.append(c.name)

        if not potential:
            self._show_toast("No hay más catálogos disponibles")
            return

        dialog = Adw.MessageDialog(transient_for=self, heading="Nueva Condición")
        dialog.add_response("cancel", "Cancelar")
        dialog.add_response("next", "Siguiente")
        dialog.set_response_appearance("next", Adw.ResponseAppearance.SUGGESTED)

        grp = Adw.PreferencesGroup()
        combo = Adw.ComboRow(title="Depende de", model=Gtk.StringList.new(potential))
        grp.add(combo)
        dialog.set_extra_child(grp)

        def on_res(d, res):
            if res == "next":
                p_name = p_names[combo.get_selected()]
                new_dep = CatalogDependency(p_name, [])
                local_deps.append(new_dep)
                GLib.idle_add(lambda: self._edit_dependency_values(new_dep, callback))
            d.close()

        dialog.connect("response", on_res)
        dialog.present()

    # ─── Diálogo: Editar valores de dependencia ──────────────────────

    def _edit_dependency_values(self, dependency: CatalogDependency, callback):
        """Diálogo para marcar qué valores activan la dependencia."""
        parent_cat = self.catalog_system.get_catalog_by_name(dependency.parent_name)
        if not parent_cat:
            return

        dialog = Adw.MessageDialog(transient_for=self,
                                   heading=f"Valores de {parent_cat.label}",
                                   body="Selecciona los valores que activan esta condición")
        dialog.add_response("done", "Aceptar")
        dialog.set_response_appearance("done", Adw.ResponseAppearance.SUGGESTED)
        dialog.set_default_response("done")

        grp = Adw.PreferencesGroup()
        checks = {}
        for item in parent_cat.items:
            row = Adw.ActionRow(title=item)
            chk = Gtk.CheckButton(valign=Gtk.Align.CENTER)
            if item in dependency.values:
                chk.set_active(True)
            row.add_prefix(chk)
            row.set_activatable_widget(chk)
            grp.add(row)
            checks[item] = chk

        dialog.set_extra_child(grp)

        def on_res(d, res):
            dependency.values = [txt for txt, chk in checks.items() if chk.get_active()]
            callback()
            d.close()

        dialog.connect("response", on_res)
        dialog.present()

    # ─── Diálogo: Editar items de un catálogo ────────────────────────

    def _edit_catalog_items(self, catalog: Catalog):
        """Ventana nativa para gestionar los valores de un catálogo."""
        dialog = Adw.Window(transient_for=self,
                            title=f"Editar: {catalog.label}",
                            modal=True)
        dialog.set_default_size(450, 500)

        toolbar = Adw.ToolbarView()
        dialog.set_content(toolbar)

        header = Adw.HeaderBar()
        header.set_show_end_title_buttons(False)
        toolbar.add_top_bar(header)

        btn_close = Gtk.Button(label="Cerrar")
        btn_close.connect("clicked", lambda _: [self._refresh_ui(), dialog.close()])
        header.pack_end(btn_close)

        prefs_page = Adw.PreferencesPage()
        toolbar.set_content(prefs_page)

        def refresh_items():
            # Crear una nueva página cada vez para evitar errores al limpiar widgets internos
            new_prefs_page = Adw.PreferencesPage()
            toolbar.set_content(new_prefs_page)

            grp_items = Adw.PreferencesGroup(title="Valores",
                                             description=f"Lista de opciones para {catalog.label}")
            new_prefs_page.add(grp_items)

            if not catalog.items:
                empty = Adw.ActionRow(title="Sin valores registrados",
                                     subtitle="Usa el campo de abajo para agregar")
                empty.add_css_class("dim-label")
                grp_items.add(empty)
            else:
                for i, item in enumerate(catalog.items):
                    row = Adw.ActionRow(title=item)

                    btn_up = Gtk.Button(icon_name="go-up-symbolic",
                                        valign=Gtk.Align.CENTER)
                    btn_up.add_css_class("flat")
                    btn_up.set_sensitive(i > 0)
                    btn_up.connect("clicked",
                                   lambda _, idx=i: self._move_item(catalog, idx, -1, refresh_items))
                    row.add_suffix(btn_up)

                    btn_down = Gtk.Button(icon_name="go-down-symbolic",
                                          valign=Gtk.Align.CENTER)
                    btn_down.add_css_class("flat")
                    btn_down.set_sensitive(i < len(catalog.items) - 1)
                    btn_down.connect("clicked",
                                     lambda _, idx=i: self._move_item(catalog, idx, 1, refresh_items))
                    row.add_suffix(btn_down)

                    btn_rename = Gtk.Button(icon_name="document-edit-symbolic",
                                            valign=Gtk.Align.CENTER,
                                            tooltip_text="Renombrar elemento")
                    btn_rename.add_css_class("flat")
                    btn_rename.connect("clicked",
                                       lambda _, it=item: self._rename_item(catalog, it, refresh_items))
                    row.add_suffix(btn_rename)

                    btn_rm = Gtk.Button(icon_name="user-trash-symbolic",
                                        valign=Gtk.Align.CENTER)
                    btn_rm.add_css_class("flat")
                    btn_rm.connect("clicked",
                                   lambda _, it=item: self._remove_item(catalog, it, refresh_items))
                    row.add_suffix(btn_rm)

                    grp_items.add(row)

            # Grupo para agregar (siempre al final)
            grp_add = Adw.PreferencesGroup()
            entry_new = Adw.EntryRow(title="Nuevo valor")
            entry_new.add_suffix(Gtk.Image(icon_name="list-add-symbolic"))
            entry_new.connect("apply", lambda _: self._add_item(catalog, entry_new, refresh_items))
            entry_new.connect("entry-activated",
                              lambda _: self._add_item(catalog, entry_new, refresh_items))
            grp_add.add(entry_new)
            new_prefs_page.add(grp_add)

        refresh_items()
        dialog.present()

    # ─── Helpers ─────────────────────────────────────────────────────

    def _add_item(self, catalog: Catalog, entry_row: Adw.EntryRow, refresh_cb):
        value = entry_row.get_text().strip()
        if value and value not in catalog.items:
            catalog.items.append(value)
            entry_row.set_text("")
            refresh_cb()

    def _rename_item(self, catalog: Catalog, old_item: str, refresh_cb):
        """Muestra un diálogo para renombrar un elemento con propagación."""
        dialog = Adw.MessageDialog(transient_for=self, heading=f"Renombrar: {old_item}")
        dialog.add_response("cancel", "Cancelar")
        dialog.add_response("rename", "Renombrar")
        dialog.set_response_appearance("rename", Adw.ResponseAppearance.SUGGESTED)

        entry = Adw.EntryRow(title="Nuevo nombre", text=old_item)
        grp = Adw.PreferencesGroup()
        grp.add(entry)
        dialog.set_extra_child(grp)

        def on_res(d, res):
            if res == "rename":
                new_name = entry.get_text().strip()
                if new_name and new_name != old_item:
                    self.catalog_system.rename_item(catalog.name, old_item, new_name)
                    refresh_cb()
            d.close()

        dialog.connect("response", on_res)
        dialog.present()

    def _remove_item(self, catalog: Catalog, item: str, refresh_cb):
        if item in catalog.items:
            catalog.items.remove(item)
            refresh_cb()

    def _move_item(self, catalog: Catalog, index: int, direction: int, refresh_cb):
        new_index = index + direction
        if 0 <= new_index < len(catalog.items):
            catalog.items[index], catalog.items[new_index] = (
                catalog.items[new_index], catalog.items[index])
            refresh_cb()

    def _remove_catalog(self, name: str):
        try:
            self.catalog_system.remove_catalog(name)
            self._refresh_ui()
        except ValueError as e:
            self._show_toast(str(e))

    def _on_save(self, _):
        set_catalog_system(self.catalog_system)
        self._show_toast("Configuración guardada")
        if self.on_save_callback:
            self.on_save_callback()
        GLib.timeout_add(500, self.close)

    def _show_toast(self, message: str):
        toast = Adw.Toast.new(message)
        toast.set_timeout(2)
        self.toast_overlay.add_toast(toast)
