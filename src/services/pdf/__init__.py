from src.domain.models import EvidenciaData
from src.services.pdf.protocols import EvidenceReportGenerator, ProgressCallback
from src.services.pdf.registry import (
    DEFAULT_EVIDENCE_BACKEND_ID,
    get_evidence_generator,
    list_evidence_backend_ids,
    register_evidence_backend,
)
from src.services.pdf.reportlab_generator import ReportlabLetterEvidenciaGenerator


def generar_pdf(
    data: EvidenciaData,
    output_path: str = "evidencia_output.pdf",
    progress_callback: ProgressCallback = None,
) -> str:
    return get_evidence_generator().generate(data, output_path, progress_callback)


__all__ = [
    "DEFAULT_EVIDENCE_BACKEND_ID",
    "EvidenceReportGenerator",
    "ProgressCallback",
    "ReportlabLetterEvidenciaGenerator",
    "generar_pdf",
    "get_evidence_generator",
    "list_evidence_backend_ids",
    "register_evidence_backend",
]
