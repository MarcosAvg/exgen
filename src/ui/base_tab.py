"""
Clase base para unificar la lógica de las pestañas (Evidencias y Reportes).
"""
import threading
from collections.abc import Callable
from typing import Any

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gio, GLib, Gtk


class BaseTab(Gtk.Box):
    """
    Base para pestañas con utilidades comunes.
    """

    def __init__(self, toast_overlay: Adw.ToastOverlay):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.toast_overlay = toast_overlay
        self.set_vexpand(True)
        
        # Barra de progreso común
        self.progress_bar = Gtk.ProgressBar()
        self.progress_bar.set_visible(False)
        self.progress_bar.set_margin_bottom(12)
        self.progress_bar.add_css_class("floating-progress")
        
        # Almacén para el toast actual
        self.active_toast = None

    def show_alert(self, title: str, message: str):
        """Muestra un diálogo de alerta unificado."""
        dialog = Adw.MessageDialog(
            heading=title,
            body=message,
            transient_for=self.get_root()
        )
        dialog.add_response("ok", "Aceptar")
        dialog.set_default_response("ok")
        dialog.connect("response", lambda d, r: d.close())
        dialog.present()

    def open_file_dialog(
        self, 
        title: str, 
        filter_name: str, 
        mime_types: list[str], 
        initial_folder: str = None,
        multiple: bool = False,
        callback: Callable[[list[str]], None] = None
    ):
        """Selector de archivos genérico."""
        dialog = Gtk.FileDialog()
        dialog.set_title(title)
        
        f = Gtk.FileFilter()
        f.set_name(filter_name)
        for mt in mime_types:
            f.add_mime_type(mt)
            
        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(f)
        dialog.set_filters(filters)
        dialog.set_default_filter(f)

        if initial_folder:
            folder = Gio.File.new_for_path(initial_folder)
            dialog.set_initial_folder(folder)

        def on_response(source, result):
            try:
                paths = []
                if multiple:
                    list_model = source.open_multiple_finish(result)
                    if list_model:
                        for i in range(list_model.get_n_items()):
                            paths.append(list_model.get_item(i).get_path())
                else:
                    file = source.open_finish(result)
                    if file:
                        paths = [file.get_path()]
                
                if paths and callback:
                    GLib.idle_add(callback, paths)
            except GLib.Error:
                pass

        if multiple:
            dialog.open_multiple(self.get_root(), None, on_response)
        else:
            dialog.open(self.get_root(), None, on_response)

    def run_task_with_progress(
        self, 
        task_fn: Callable[[Any, Callable[[float, str], None]], Any], 
        data: Any, 
        start_msg: str,
        finish_callback: Callable[[Any], None]
    ):
        """Ejecuta una tarea en un hilo con barra de progreso y toast."""
        # Mostrar barra de progreso
        self.progress_bar.set_fraction(0.0)
        self.progress_bar.set_visible(True)
        
        # Mostrar toast informativo
        self.active_toast = Adw.Toast.new(start_msg)
        self.active_toast.set_timeout(0) # No desaparece solo
        self.toast_overlay.add_toast(self.active_toast)

        def progress_wrapper(fraction: float, message: str):
            GLib.idle_add(self._update_progress_ui, fraction, message)

        def worker():
            try:
                result = task_fn(data, progress_wrapper)
                GLib.idle_add(self._task_finished_wrapper, result, finish_callback)
            except Exception as e:
                GLib.idle_add(self._task_finished_wrapper, e, finish_callback)

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

    def _update_progress_ui(self, fraction: float, message: str):
        """Actualiza la UI con el progreso actual."""
        self.progress_bar.set_fraction(min(max(fraction, 0.0), 1.0))
        if self.active_toast and hasattr(self.active_toast, "set_title"):
            self.active_toast.set_title(message)

    def _task_finished_wrapper(self, result, callback):
        """Limpia la UI y ejecuta el callback de finalización."""
        self.progress_bar.set_visible(False)
        if self.active_toast:
            self.active_toast.dismiss()
            self.active_toast = None
            
        if callback:
            callback(result)
