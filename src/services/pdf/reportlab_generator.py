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
        
        # Cálculo de espacio disponible aproximado
        # letter = (612, 792)
        total_h = height - 80 # Margen top(40) + bottom(40)
        header_h = 110 # Aproximación del espacio que ocupa la cabecera + spacers
        avail_h = total_h - header_h
        
        image_flowables, temp_files = build_image_flowables(
            data, normal_style, progress_callback, avail_height=avail_h
        )
        story = [*header_flowables, *image_flowables]
        doc = SimpleDocTemplate(
            output_path,
            pagesize=letter,
            rightMargin=30,
            leftMargin=30,
            topMargin=40, # Margen superior reducido al no haber fondo
            bottomMargin=40,
        )
        if progress_callback:
            progress_callback(0.95, "Construyendo documento final...")
        doc.build(story)
        if progress_callback:
            progress_callback(1.0, "Limpiando...")
        for temp in temp_files:
            if os.path.exists(temp):
                try:
                    os.remove(temp)
                except Exception:
                    pass
        return os.path.abspath(output_path)
