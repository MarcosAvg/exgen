from dataclasses import dataclass

from src.domain.models import EvidenciaData


@dataclass
class ValidationResult:
    ok: bool
    missing_labels: list[str]


def validate_evidence_for_export(data: EvidenciaData) -> ValidationResult:
    missing: list[str] = []
    if not (data.plantel or "").strip():
        missing.append("Plantel")
    return ValidationResult(ok=len(missing) == 0, missing_labels=missing)
