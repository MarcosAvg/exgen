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
        background-color: alpha(@window_bg_color, 0.4);
        border: 2px dashed @shade_color;
        border-radius: 16px;
        padding: 16px;
        transition: all 250ms ease-out;
        min-height: 180px;
    }
    .dz-card:hover {
        border-color: @accent_color;
        background-color: alpha(@accent_color, 0.08);
        transform: translateY(-2px);
    }
    .dz-card.drag-hover {
        border-style: solid;
        border-color: @accent_color;
        background-color: alpha(@accent_color, 0.12);
        box-shadow: 0 0 0 4px alpha(@accent_color, 0.1);
    }
    .preview-frame {
        border-radius: 12px;
        border: 1px solid @shade_color;
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
    }
    .numeric-badge {
        background-color: @accent_bg_color;
        color: @accent_fg_color;
        border-radius: 8px;
        padding: 4px 8px;
        font-weight: 800;
        font-size: 9pt;
        box-shadow: 0 4px 12px rgba(0,0,0,0.4);
        border: 1px solid alpha(white, 0.1);
    }
    
    /* Pulido para HeaderBar y Switcher */
    headerbar {
        border-bottom: 1px solid @shade_color;
    }
    
    .floating-progress {
        margin: 0;
        border-radius: 0;
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
