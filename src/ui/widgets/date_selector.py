"""
Widget reutilizable para selección de fecha mediante Gtk.Calendar en un Popover.
"""
from datetime import datetime

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import GObject, Gtk


class DateSelector(Gtk.Box):
    """
    Botón que abre un calendario para seleccionar una fecha.
    """

    __gsignals__ = {
        "date-changed": (GObject.SignalFlags.RUN_FIRST, None, (str,)),
    }

    def __init__(self, initial_date: datetime = None):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL)
        
        self.selected_date = initial_date or datetime.now()

        # Botón principal
        self.btn = Gtk.Button(label=self.selected_date.strftime("%d-%m-%Y"))
        self.btn.add_css_class("flat")
        self.btn.connect("clicked", self._on_clicked)
        self.append(self.btn)

        # Calendario (oculto hasta que se abre el popover)
        self.calendar = Gtk.Calendar()
        self._update_calendar_from_date(self.selected_date)
        
        # Popover
        self.popover = Gtk.Popover()
        self.popover.set_child(self.calendar)
        self.popover.set_parent(self.btn)
        
        # Conectar señales del calendario
        self.calendar.connect("day-selected", self._on_day_selected)

    def _on_clicked(self, _):
        """Abre el popover."""
        self.popover.popup()

    def _on_day_selected(self, _):
        """Actualiza la fecha al seleccionar un día."""
        g_date = self.calendar.get_date()
        if not g_date:
            return

        year = g_date.get_year()
        month = g_date.get_month() # GLib.DateTime mes es 1-12
        day = g_date.get_day_of_month()
        
        self.selected_date = datetime(year, month, day)
        date_str = self.selected_date.strftime("%d-%m-%Y")
        
        self.btn.set_label(date_str)
        self.popover.popdown()
        
        # Emitir señal de cambio
        self.emit("date-changed", date_str)

    def _update_calendar_from_date(self, date: datetime):
        """Sincroniza el widget Gtk.Calendar con un objeto datetime."""
        # Gtk4 Calendar usa setters individuales (año, mes, día)
        # Nota: Gtk.Calendar en Gtk4 no tiene un método directo de 'set_date' 
        # pero hereda de GtkWidget y tiene propiedades/métodos específicos.
        # En GTK 4.0+, se usa select_day(GDateTime) o setters directos.
        # Para compatibilidad, usamos los setters si están disponibles o intentamos via GLib.
        from gi.repository import GLib
        
        g_date = GLib.DateTime.new_local(
            date.year, date.month, date.day, 0, 0, 0
        )
        # En GTK 4, Calendar.select_day(GDateTime)
        try:
            self.calendar.select_day(g_date)
        except Exception:
            pass

    def get_date_string(self) -> str:
        """Retorna la fecha seleccionada como DD-MM-YYYY."""
        return self.selected_date.strftime("%d-%m-%Y")

    def get_date(self) -> datetime:
        """Retorna el objeto datetime seleccionado."""
        return self.selected_date

    def set_date(self, date: datetime):
        """Establece una nueva fecha programáticamente."""
        self.selected_date = date
        self.btn.set_label(date.strftime("%d-%m-%Y"))
        self._update_calendar_from_date(date)
