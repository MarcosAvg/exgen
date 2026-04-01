import os
import json

CONFIG_DIR = os.path.expanduser("~/.config/evidencia_app")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")

def ensure_config_dir():
    if not os.path.exists(CONFIG_DIR):
        os.makedirs(CONFIG_DIR, exist_ok=True)

def get_save_path():
    """Retorna la ruta de guardado desde el archivo de configuración o la carpeta HOME por defecto."""
    ensure_config_dir()
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                data = json.load(f)
                path = data.get("save_path")
                if path and os.path.isdir(path):
                    return path
        except (ValueError, json.JSONDecodeError):
            pass
    return os.path.expanduser("~/Documentos") if os.path.exists(os.path.expanduser("~/Documentos")) else os.path.expanduser("~")

def set_save_path(path):
    """Guarda la ruta seleccionada en el archivo de configuración JSON."""
    ensure_config_dir()
    data = {"save_path": path}
    with open(CONFIG_FILE, 'w') as f:
        json.dump(data, f, indent=4)
