"""
Widget DropZone para selección de múltiples imágenes sin categorías.
Muestra previews en grid con scroll.
"""
from collections.abc import Callable

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
from gi.repository import Gdk, Gtk, GObject


class EvidenceDropZone(Gtk.Box):
    """
    DropZone para evidencias - soporta múltiples imágenes sin categorías.
    Muestra previews en grid scrollable.
    """

    def __init__(
        self,
        on_select_clicked: Callable[[], None],
        on_drop_paths: Callable[[list[str]], None],
        on_remove_image: Callable[[int], None] | None = None,
    ):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.on_select_clicked = on_select_clicked
        self.on_drop_paths = on_drop_paths
        self.on_remove_image = on_remove_image

        self.image_paths: list[str] = []

        # Header
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        lbl_title = Gtk.Label(label="Imágenes de Evidencia")
        lbl_title.add_css_class("heading")
        header.append(lbl_title)

        self.append(header)

        # Area de drop (usamos overlay para alternar entre placeholder y contenido)
        self.drop_area = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.drop_area.add_css_class("dz-card")
        self.drop_area.set_vexpand(True)

        overlay = Gtk.Overlay()
        self.drop_area.append(overlay)

        # Scroll para las imágenes
        self.scroll = Gtk.ScrolledWindow()
        self.scroll.set_vexpand(True)
        self.scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        self.flow_box = Gtk.FlowBox()
        self.flow_box.set_max_children_per_line(2)
        self.flow_box.set_min_children_per_line(2)
        self.flow_box.set_selection_mode(Gtk.SelectionMode.NONE)
        self.flow_box.set_column_spacing(8)
        self.flow_box.set_row_spacing(8)
        self.flow_box.set_homogeneous(True)

        self.scroll.set_child(self.flow_box)

        # Placeholder cuando no hay imágenes
        self.placeholder = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.placeholder.set_valign(Gtk.Align.CENTER)

        icon = Gtk.Image.new_from_icon_name("insert-image-symbolic")
        icon.set_pixel_size(48)
        icon.add_css_class("dim-label")
        self.placeholder.append(icon)

        lbl_placeholder = Gtk.Label(label="Arrastra o Clica aquí")
        lbl_placeholder.add_css_class("dim-label")
        lbl_placeholder.add_css_class("caption")
        self.placeholder.append(lbl_placeholder)
        
        overlay.set_child(self.scroll)
        overlay.add_overlay(self.placeholder)

        # Sincronizar visibilidad
        self.flow_box.bind_property(
            "visible",
            self.placeholder,
            "visible",
            GObject.BindingFlags.INVERT_BOOLEAN
        )
        # También ocultar el scroll si no hay nada
        self.placeholder.bind_property(
            "visible",
            self.scroll,
            "visible",
            GObject.BindingFlags.INVERT_BOOLEAN
        )

        # Contador
        self.lbl_count = Gtk.Label(label="0 imágenes")
        self.lbl_count.add_css_class("dim-label")
        self.lbl_count.add_css_class("caption")
        self.lbl_count.set_halign(Gtk.Align.END)

        self.append(self.drop_area)
        self.append(self.lbl_count)

        # Click para abrir selector
        click = Gtk.GestureClick()
        click.connect("pressed", lambda *_: self.on_select_clicked())
        self.drop_area.add_controller(click)

        # Drop target
        try:
            drop = Gtk.DropTarget.new(Gdk.FileList, Gdk.DragAction.COPY)
            drop.connect("drop", self._on_drop)
            drop.connect(
                "enter",
                lambda t, x, y: self.drop_area.add_css_class("drag-hover") or Gdk.DragAction.COPY,
            )
            drop.connect("leave", lambda t: self.drop_area.remove_css_class("drag-hover"))
            self.drop_area.add_controller(drop)
        except Exception:
            pass

    def _on_drop(self, target, value, x, y):
        try:
            target.get_widget().remove_css_class("drag-hover")
            paths = []
            if type(value).__name__ == "FileList":
                files = value.get_files()
                for i in range(files.get_n_items()):
                    f = files.get_item(i)
                    paths.append(f.get_path())
            valid_paths = [p for p in paths if p.lower().endswith((".png", ".jpg", ".jpeg"))]
            if valid_paths:
                self.on_drop_paths(valid_paths)
            return True
        except Exception:
            return False

    def update_images(self, paths: list[str]):
        """Actualiza la lista de imágenes mostradas."""
        self.image_paths = paths

        # Limpiar flow box
        child = self.flow_box.get_first_child()
        while child:
            self.flow_box.remove(child)
            child = self.flow_box.get_first_child()

        if not paths:
            self.lbl_count.set_text("0 imágenes")
            self.placeholder.set_visible(True)
            self.flow_box.set_visible(False)
            return

        self.lbl_count.set_text(f"{len(paths)} imagen{'es' if len(paths) > 1 else ''}")
        self.placeholder.set_visible(False)
        self.flow_box.set_visible(True)

        # Agregar previews
        for i, path in enumerate(paths):
            frame = self._create_image_preview(path, i)
            self.flow_box.append(frame)

    def _create_image_preview(self, path: str, index: int) -> Gtk.Widget:
        """Crea un preview de imagen cuadrado con controles."""
        # AspectFrame para forzar el cuadrado
        aspect = Gtk.AspectFrame(ratio=1.0, obey_child=False)
        aspect.set_hexpand(True)

        overlay = Gtk.Overlay()
        aspect.set_child(overlay)

        # Imagen
        try:
            pic = Gtk.Picture.new_for_filename(path)
            pic.set_can_shrink(True)
            if hasattr(pic, "set_content_fit"):
                pic.set_content_fit(Gtk.ContentFit.COVER)
            elif hasattr(pic, "set_keep_aspect_ratio"):
                pic.set_keep_aspect_ratio(True)
        except Exception:
            pic = Gtk.Image.new_from_icon_name("image-x-generic-symbolic")

        frame = Gtk.Frame()
        frame.add_css_class("preview-frame")
        frame.set_child(pic)
        overlay.set_child(frame)

        # Botón eliminar
        btn_remove = Gtk.Button(icon_name="window-close-symbolic")
        btn_remove.add_css_class("circular")
        btn_remove.add_css_class("flat")
        btn_remove.set_size_request(24, 24)
        btn_remove.set_valign(Gtk.Align.START)
        btn_remove.set_halign(Gtk.Align.END)
        btn_remove.set_margin_top(6)
        btn_remove.set_margin_end(6)

        if self.on_remove_image:
            btn_remove.connect("clicked", lambda _, idx=index: self.on_remove_image(idx))

        overlay.add_overlay(btn_remove)

        # Número de orden
        lbl_num = Gtk.Label(label=str(index + 1))
        lbl_num.add_css_class("numeric-badge")
        lbl_num.set_valign(Gtk.Align.START)
        lbl_num.set_halign(Gtk.Align.START)
        lbl_num.set_margin_top(4)
        lbl_num.set_margin_start(4)
        overlay.add_overlay(lbl_num)

        return overlay

    def get_image_paths(self) -> list[str]:
        """Retorna las rutas de las imágenes en orden."""
        return self.image_paths.copy()
