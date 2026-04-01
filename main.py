import sys
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gio, Adw

from src.ui.main_window import MainWindow

class EvidenciaApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id='com.gen.evidencia',
                         flags=Gio.ApplicationFlags.FLAGS_NONE)
        self.connect('activate', self.on_activate)

    def on_activate(self, app):
        win = getattr(self, 'win', None)
        if not win:
            self.win = MainWindow(application=app)
        self.win.present()

if __name__ == '__main__':
    app = EvidenciaApp()
    sys.exit(app.run(sys.argv))
