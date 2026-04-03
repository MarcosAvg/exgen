import os
import json

CONFIG_DIR = os.path.expanduser("~/.config/evidencia_app")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")

def ensure_config_dir():
    if not os.path.exists(CONFIG_DIR):
        os.makedirs(CONFIG_DIR, exist_ok=True)

def _load_config():
    ensure_config_dir()
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except (ValueError, json.JSONDecodeError):
            pass
    return {}

def _save_config(config_dict):
    ensure_config_dir()
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config_dict, f, indent=4)

def get_save_path():
    config = _load_config()
    path = config.get("save_path")
    if path and os.path.isdir(path):
        return path
    return os.path.expanduser("~/Documentos") if os.path.exists(os.path.expanduser("~/Documentos")) else os.path.expanduser("~")

def set_save_path(path):
    config = _load_config()
    config["save_path"] = path
    _save_config(config)

def get_last_image_dir():
    config = _load_config()
    path = config.get("last_image_dir")
    if path and os.path.isdir(path):
        return path
    return os.path.expanduser("~")

def set_last_image_dir(path):
    config = _load_config()
    config["last_image_dir"] = path
    _save_config(config)
