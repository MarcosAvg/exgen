import os

from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate

from src.domain.models import EvidenciaData
from src.services.pdf.background import add_background
from src.services.pdf.image_blocks import build_image_flowables
from src.services.pdf.layout import build_title_and_data_table
from src.services.pdf.protocols import ProgressCallback


class ReportlabLetterEvidenciaGenerator:
    """Implementación actual: PDF carta con ReportLab y fondo personalizado."""

    def generate(
        self,
        data: EvidenciaData,
        output_path: str,
        progress_callback: ProgressCallback = None,
    ) -> str:
        _, height = letter
        header_flowables, normal_style = build_title_and_data_table(data)
        image_flowables, temp_files = build_image_flowables(
            data, normal_style, progress_callback
        )
        story = [*header_flowables, *image_flowables]
        doc = SimpleDocTemplate(
            output_path,
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=height * 0.12,
            bottomMargin=36,
        )
        if progress_callback:
            progress_callback(0.95, "Construyendo documento final...")
        doc.build(story, onFirstPage=add_background, onLaterPages=add_background)
        if progress_callback:
            progress_callback(1.0, "Limpiando...")
        for temp in temp_files:
            if os.path.exists(temp):
                try:
                    os.remove(temp)
                except Exception:
                    pass
        return os.path.abspath(output_path)
