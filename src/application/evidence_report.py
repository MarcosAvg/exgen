import os
from dataclasses import dataclass

from src.domain.filenames import evidence_pdf_filename
from src.domain.models import EvidenciaData
from src.domain.validation import validate_evidence_for_export
from src.services.pdf import ProgressCallback, get_evidence_generator


@dataclass
class GenerateReportSuccess:
    output_path: str


@dataclass
class GenerateReportError:
    title: str
    message: str


def run_generate_evidence_report(
    data: EvidenciaData,
    output_directory: str,
    *,
    backend_id: str | None = None,
    progress_callback: ProgressCallback = None,
) -> GenerateReportSuccess | GenerateReportError:
    validation = validate_evidence_for_export(data)
    if not validation.ok:
        return GenerateReportError(
            title="Faltan datos obligatorios",
            message="Por favor completa al menos el campo Plantel.",
        )
    filename = evidence_pdf_filename(data.concepto_numero, data.plantel)
    full_path = os.path.join(output_directory, filename)
    generator = get_evidence_generator(backend_id)
    try:
        out_path = generator.generate(data, full_path, progress_callback)
        return GenerateReportSuccess(output_path=out_path)
    except Exception as e:
        return GenerateReportError(
            title="Error",
            message=f"Ocurrió un error al generar PDF: {e}",
        )
