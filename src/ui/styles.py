import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
from gi.repository import Gdk, Gtk

MAIN_WINDOW_CSS = """
    textview, textview text { background-color: transparent; padding: 0; margin: 0; }
    row.multiline-entry:focus-within { box-shadow: inset 0 0 0 2px @accent_color; }
    .anim-label { transition: all 200ms cubic-bezier(0.25, 0.46, 0.45, 0.94); opacity: 0.55; }
    .anim-label.float-up { font-size: 9pt; transform: none; }
    .anim-label.float-down { font-size: 11pt; transform: translateY(12px); }
    .anim-icon { transition: opacity 200ms ease; }

    .dz-card {
        background-color: @window_bg_color;
        border: 2px dashed @shade_color;
        border-radius: 12px;
        padding: 12px;
        transition: all 200ms ease;
        min-height: 160px;
    }
    .dz-card:hover {
        border-color: @accent_color;
        background-color: alpha(@accent_color, 0.05);
    }
    .dz-card.drag-hover {
        border-style: solid;
        border-color: @accent_color;
        background-color: alpha(@accent_color, 0.15);
    }
    .preview-frame {
        border-radius: 8px;
        border: 1px solid @shade_color;
    }
    .numeric-badge {
        background-color: @accent_bg_color;
        color: @accent_fg_color;
        border-radius: 99px;
        padding: 4px 10px;
        font-weight: bold;
        font-size: 10pt;
        box-shadow: 0 2px 4px rgba(0,0,0,0.3);
    }
"""


def install_main_window_styles(widgets: list) -> Gtk.CssProvider:
    provider = Gtk.CssProvider()
    provider.load_from_data(MAIN_WINDOW_CSS.encode())
    priority = Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
    for w in widgets:
        w.get_style_context().add_provider(provider, priority)
    disp = Gdk.Display.get_default()
    if disp:
        Gtk.StyleContext.add_provider_for_display(disp, provider, priority)
    return provider
