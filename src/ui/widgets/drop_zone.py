from collections.abc import Callable

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
from gi.repository import Adw, Gdk, Gtk


class DropZoneCard(Gtk.Box):
    def __init__(
        self,
        title: str,
        context: str,
        *,
        on_select_clicked: Callable[[str], None],
        on_drop_paths: Callable[[list[str], str], None],
    ):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self._context = context
        self._on_select_clicked = on_select_clicked
        self._on_drop_paths = on_drop_paths
        self.add_css_class("dz-card")
        self.set_hexpand(True)
        self.set_vexpand(True)

        lbl_title = Gtk.Label(label=title)
        lbl_title.add_css_class("heading")
        lbl_title.add_css_class("dim-label")
        self.append(lbl_title)

        self.content_bin = Adw.Bin()
        self.content_bin.set_vexpand(True)
        self.content_bin.set_hexpand(True)
        self.append(self.content_bin)

        self.placeholder = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.placeholder.set_valign(Gtk.Align.CENTER)

        icon = Gtk.Image.new_from_icon_name("insert-image-symbolic")
        icon.set_pixel_size(32)
        icon.add_css_class("dim-label")
        self.placeholder.append(icon)

        self.lbl_subtitle = Gtk.Label(label="Arrastra o Clica aquí")
        self.lbl_subtitle.add_css_class("dim-label")
        self.lbl_subtitle.add_css_class("caption")
        self.placeholder.append(self.lbl_subtitle)

        self.content_bin.set_child(self.placeholder)

        click = Gtk.GestureClick()
        click.connect("pressed", self._on_pressed_select)
        self.add_controller(click)

        try:
            drop = Gtk.DropTarget.new(Gdk.FileList, Gdk.DragAction.COPY)
            drop.connect("drop", self._on_drop)
            drop.connect(
                "enter",
                lambda t, x, y: self.add_css_class("drag-hover") or Gdk.DragAction.COPY,
            )
            drop.connect("leave", lambda t: self.remove_css_class("drag-hover"))
            self.add_controller(drop)
        except Exception:
            pass

    def _on_pressed_select(self, *_args):
        self._on_select_clicked(self._context)

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
                self._on_drop_paths(valid_paths, self._context)
            return True
        except Exception:
            return False

    def update_preview(self, paths):
        if not paths:
            self.content_bin.set_child(self.placeholder)
            return

        try:
            pic = Gtk.Picture.new_for_filename(paths[0])
            pic.set_can_shrink(True)
            if hasattr(pic, "set_content_fit"):
                pic.set_content_fit(Gtk.ContentFit.COVER)
            elif hasattr(pic, "set_keep_aspect_ratio"):
                pic.set_keep_aspect_ratio(True)

            frame = Gtk.Frame()
            frame.add_css_class("preview-frame")
            frame.set_child(pic)

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
        except Exception:
            self.lbl_subtitle.set_text(f"{len(paths)} Seleccionadas")
            self.content_bin.set_child(self.placeholder)
