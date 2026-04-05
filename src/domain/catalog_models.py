"""
Sistema simplificado de catálogos - cada catálogo es automáticamente un dropdown.
"""
from dataclasses import dataclass, field


@dataclass
class Catalog:
    """
    Un catálogo representa tanto los valores disponibles como un dropdown en la UI.
    Los dos primeros catálogos son Edificio y Tipo de Equipo (fijos).
    Los siguientes son dependientes y aparecen dinámicamente.
    """
    name: str  # identificador técnico
    label: str  # etiqueta visible en la UI
    items: list[str] = field(default_factory=list)
    order: int = 0  # orden de aparición en la UI
    parent_name: str | None = None  # catálogo del que depende
    parent_values: list[str] = field(default_factory=list)  # valores que lo activan


@dataclass
class CatalogSystem:
    """Sistema de catálogos simplificado."""
    catalogs: list[Catalog] = field(default_factory=list)

    def __post_init__(self):
        # Asegurar que existan los catálogos base si la lista está vacía
        if not self.catalogs:
            self.catalogs = [
                Catalog(name="edificio", label="Edificio", order=0),
                Catalog(name="tipo_equipo", label="Tipo de Equipo", order=1),
            ]

    def get_base_catalogs(self) -> list[Catalog]:
        """Retorna Edificio y Tipo de Equipo (los dos primeros)."""
        return self.catalogs[:2] if len(self.catalogs) >= 2 else self.catalogs

    def get_dependent_catalogs(self) -> list[Catalog]:
        """Retorna catálogos dependientes (del tercero en adelante)."""
        return self.catalogs[2:] if len(self.catalogs) > 2 else []

    def get_catalog_by_name(self, name: str) -> Catalog | None:
        """Busca un catálogo por su nombre técnico."""
        for cat in self.catalogs:
            if cat.name == name:
                return cat
        return None

    def add_catalog(self, name: str, label: str) -> Catalog:
        """Agrega un nuevo catálogo (que automáticamente crea un dropdown)."""
        # Verificar que no exista
        if self.get_catalog_by_name(name):
            raise ValueError(f"Ya existe un catálogo con el nombre '{name}'")

        catalog = Catalog(
            name=name,
            label=label,
            order=len(self.catalogs)
        )
        self.catalogs.append(catalog)
        return catalog

    def remove_catalog(self, name: str) -> None:
        """Elimina un catálogo por nombre. No permite eliminar los dos primeros (base)."""
        if name in ("edificio", "tipo_equipo"):
            raise ValueError("No se pueden eliminar los catálogos base (Edificio y Tipo de Equipo)")

        self.catalogs = [c for c in self.catalogs if c.name != name]
        # Reordenar
        for i, cat in enumerate(self.catalogs):
            cat.order = i

    def to_dict(self) -> dict:
        """Serializa a diccionario."""
        return {
            "catalogs": [
                {
                    "name": c.name,
                    "label": c.label,
                    "items": c.items,
                    "order": c.order,
                    "parent_name": c.parent_name,
                    "parent_values": c.parent_values
                }
                for c in self.catalogs
            ]
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CatalogSystem":
        """Deserializa desde diccionario. Soporta formato antiguo y nuevo."""
        system = cls()
        system.catalogs = []

        catalogs_data = data.get("catalogs", [])

        # Manejar formato antiguo (dict) o nuevo (list)
        if isinstance(catalogs_data, dict):
            # Formato antiguo: convertir a lista
            for name, cat_data in catalogs_data.items():
                catalog = Catalog(
                    name=cat_data.get("name", name),
                    label=cat_data.get("label", name),
                    items=cat_data.get("items", []),
                    order=cat_data.get("order", 0),
                    parent_name=cat_data.get("parent_name"),
                    parent_values=cat_data.get("parent_values", [])
                )
                system.catalogs.append(catalog)
        elif isinstance(catalogs_data, list):
            # Formato nuevo
            for cat_data in catalogs_data:
                catalog = Catalog(
                    name=cat_data.get("name", ""),
                    label=cat_data.get("label", ""),
                    items=cat_data.get("items", []),
                    order=cat_data.get("order", 0),
                    parent_name=cat_data.get("parent_name"),
                    parent_values=cat_data.get("parent_values", [])
                )
                system.catalogs.append(catalog)

        # Si no hay catálogos, crear los base
        if not system.catalogs:
            system.catalogs = [
                Catalog(name="edificio", label="Edificio", order=0),
                Catalog(name="tipo_equipo", label="Tipo de Equipo", order=1),
            ]

        return system


@dataclass
class EvidencePhotoData:
    """Datos de entrada para generación de PDF de evidencias."""
    edificio: str
    tipo_equipo: str
    fecha: str  # Formato DD-MM-YYYY
    # Valores de catálogos dependientes: {catalog_name: valor_seleccionado}
    dependent_values: dict[str, str] = field(default_factory=dict)
    imagenes: list[str] = field(default_factory=list)

    def get_subfolder_path(self) -> str:
        """Genera ruta de subcarpetas: Edificio/TipoEquipo"""
        return f"{self.edificio}/{self.tipo_equipo}"

    def get_filename(self) -> str:
        """
        Genera nombre del archivo:
        TipoEquipo - Edificio - Dep1 - Dep2 - ... - [Fecha].pdf
        """
        parts = [self.tipo_equipo, self.edificio]

        # Agregar valores de catálogos dependientes en orden
        for value in self.dependent_values.values():
            if value:
                parts.append(value)

        parts.append(f"[{self.fecha}]")
        return " - ".join(parts) + ".pdf"

    def get_full_path(self, base_dir: str) -> str:
        """Genera ruta completa con subcarpetas y nombre."""
        import os
        subfolder = self.get_subfolder_path()
        full_dir = os.path.join(base_dir, subfolder)
        filename = self.get_filename()
        return os.path.join(full_dir, filename)
