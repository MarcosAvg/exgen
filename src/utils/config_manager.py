import os
import json
from src.domain.catalog_models import CatalogSystem

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

def get_master_pptx_path():
    config = _load_config()
    return config.get("master_pptx_path")

def set_master_pptx_path(path):
    config = _load_config()
    config["master_pptx_path"] = path
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


def get_catalog_system() -> CatalogSystem:
    """Carga el sistema de catálogos desde configuración."""
    config = _load_config()
    catalog_data = config.get("catalog_system", {})
    if catalog_data:
        return CatalogSystem.from_dict(catalog_data)
    return CatalogSystem()


def set_catalog_system(system: CatalogSystem) -> None:
    """Guarda el sistema de catálogos en configuración."""
    config = _load_config()
    config["catalog_system"] = system.to_dict()
    _save_config(config)


def get_last_evidence_image_dir():
    """Directorio de imágenes para la pestaña Evidencias."""
    config = _load_config()
    path = config.get("last_evidence_image_dir")
    if path and os.path.isdir(path):
        return path
    return os.path.expanduser("~")


def set_last_evidence_image_dir(path):
    config = _load_config()
    config["last_evidence_image_dir"] = path
    _save_config(config)

def get_last_date():
    """Fecha utilizada en la última generación."""
    config = _load_config()
    return config.get("last_date")

def set_last_date(date_str):
    config = _load_config()
    config["last_date"] = date_str
    _save_config(config)

def get_auto_date_enabled() -> bool:
    config = _load_config()
    return config.get("auto_date_enabled", False)

def set_auto_date_enabled(enabled: bool):
    config = _load_config()
    config["auto_date_enabled"] = enabled
    _save_config(config)

def get_auto_date_limit() -> int:
    config = _load_config()
    return config.get("auto_date_limit", 2)

def set_auto_date_limit(limit: int):
    config = _load_config()
    config["auto_date_limit"] = limit
    _save_config(config)
