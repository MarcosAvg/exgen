from dataclasses import dataclass, field

@dataclass
class EvidenciaData:
    plantel: str
    cct: str
    direccion: str
    municipio: str
    concepto_numero: str
    concepto_texto: str
    img_antes: list[str] = field(default_factory=list)
    img_durante: list[str] = field(default_factory=list)
    img_despues: list[str] = field(default_factory=list)
