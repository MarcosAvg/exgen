"""
Sistema simplificado de catálogos - cada catálogo es automáticamente un dropdown.
"""
from dataclasses import dataclass, field


@dataclass
class CatalogDependency:
    """Representa una condición para que un catálogo sea visible."""
    parent_name: str
    values: list[str] = field(default_factory=list)

@dataclass
class Catalog:
    """
    Un catálogo representa tanto los valores disponibles como un dropdown en la UI.
    Los dos primeros catálogos son Edificio y Tipo de Equipo (fijos).
    Los siguientes son dependientes y aparecen dinámicamente si se cumplen todas sus dependencias.
    """
    name: str  # identificador técnico
    label: str  # etiqueta visible en la UI
    items: list[str] = field(default_factory=list)
    order: int = 0  # orden de aparición en la UI
    dependencies: list[CatalogDependency] = field(default_factory=list)

    @property
    def parent_name(self) -> str | None:
        """Propiedad de conveniencia para compatibilidad con código que usa un solo padre."""
        return self.dependencies[0].parent_name if self.dependencies else None

    @property
    def parent_values(self) -> list[str]:
        """Propiedad de conveniencia para compatibilidad con código que usa un solo padre."""
        return self.dependencies[0].values if self.dependencies else []


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

    def rename_item(self, catalog_name: str, old_value: str, new_value: str) -> None:
        """Cambia el nombre de un item y propaga el cambio a todas las dependencias."""
        cat = self.get_catalog_by_name(catalog_name)
        if not cat:
            return

        if old_value not in cat.items:
            return
            
        # 1. Renombrar en el propio catálogo
        idx = cat.items.index(old_value)
        cat.items[idx] = new_value
        
        # 2. Propagar a todas las dependencias de otros catálogos
        for other_cat in self.catalogs:
            for dep in other_cat.dependencies:
                if dep.parent_name == catalog_name:
                    if old_value in dep.values:
                        val_idx = dep.values.index(old_value)
                        dep.values[val_idx] = new_value

    def to_dict(self) -> dict:
        """Serializa a diccionario."""
        return {
            "catalogs": [
                {
                    "name": c.name,
                    "label": c.label,
                    "items": c.items,
                    "order": c.order,
                    "dependencies": [
                        {"parent_name": d.parent_name, "values": d.values}
                        for d in c.dependencies
                    ]
                }
                for c in self.catalogs
            ]
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CatalogSystem":
        """Deserializa desde diccionario. Soporta formato antiguo y nuevo (multi-dependencia)."""
        system = cls()
        system.catalogs = []

        catalogs_data = data.get("catalogs", [])

        # Manejar formato antiguo (dict) o nuevo (list)
        if isinstance(catalogs_data, dict):
            # Muy antiguo
            for name, cat_data in catalogs_data.items():
                cat = Catalog(
                    name=cat_data.get("name", name),
                    label=cat_data.get("label", name),
                    items=cat_data.get("items", []),
                    order=cat_data.get("order", 0)
                )
                # Migrar dependencia simple
                p_name = cat_data.get("parent_name")
                if p_name:
                    cat.dependencies.append(CatalogDependency(p_name, cat_data.get("parent_values", [])))
                system.catalogs.append(cat)
        elif isinstance(catalogs_data, list):
            # Formato intermedio y nuevo
            for cat_data in catalogs_data:
                cat = Catalog(
                    name=cat_data.get("name", ""),
                    label=cat_data.get("label", ""),
                    items=cat_data.get("items", []),
                    order=cat_data.get("order", 0)
                )
                
                # Cargar dependencias nuevas
                deps_data = cat_data.get("dependencies")
                if deps_data and isinstance(deps_data, list):
                    for d in deps_data:
                        cat.dependencies.append(CatalogDependency(d["parent_name"], d.get("values", [])))
                else:
                    # Migrar dependencia única (formato intermedio)
                    p_name = cat_data.get("parent_name")
                    if p_name:
                        cat.dependencies.append(CatalogDependency(p_name, cat_data.get("parent_values", [])))
                
                system.catalogs.append(cat)

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
    # Etiquetas de los catálogos para el nombre del archivo: {catalog_name: etiqueta}
    labels: dict[str, str] = field(default_factory=dict)
    imagenes: list[str] = field(default_factory=list)

    def get_subfolder_path(self) -> str:
        """Genera ruta de subcarpetas: Edificio/TipoEquipo"""
        return f"{self.edificio}/{self.tipo_equipo}"

    def get_filename(self) -> str:
        """
        Genera nombre del archivo:
        TipoEquipo - Edificio - [Label] Dep1 - [Label] Dep2 - ... - [DD-MM-YY].pdf
        """
        parts = [self.tipo_equipo, self.edificio]

        # Agregar valores de catálogos dependientes en orden, incluyendo su etiqueta
        for name, value in self.dependent_values.items():
            if value:
                label = self.labels.get(name)
                if label:
                    parts.append(f"{label} {value}")
                else:
                    parts.append(value)

        # Formatear fecha a 2 dígitos para el año [DD-MM-YY]
        fecha_partes = self.fecha.split("-")
        if len(fecha_partes) == 3:
            d, m, y = fecha_partes
            if len(y) == 4:
                y = y[2:]  # 2026 -> 26
            fecha_short = f"{d}-{m}-{y}"
        else:
            fecha_short = self.fecha

        parts.append(f"[{fecha_short}]")
        return " - ".join(parts) + ".pdf"

    def get_full_path(self, base_dir: str) -> str:
        """Genera ruta completa con subcarpetas y nombre."""
        import os
        subfolder = self.get_subfolder_path()
        full_dir = os.path.join(base_dir, subfolder)
        filename = self.get_filename()
        return os.path.join(full_dir, filename)
