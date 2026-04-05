"""
Generador de PDF para evidencias - solo imágenes sin bordes ni tablas.
Distribución adaptativa: 1-4 imágenes por página con background.
"""
import os
from typing import Optional

from PIL import Image as PILImage
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.platypus import Image as RLImage, PageBreak, SimpleDocTemplate, Table, Spacer

from src.domain.catalog_models import EvidencePhotoData
from src.services.pdf.protocols import ProgressCallback
from src.utils.helpers import get_asset_path


def add_evidence_background(canvas, doc):
    """Agrega el background de evidencia a cada página."""
    canvas.saveState()
    bg_path = get_asset_path("background_evidencia.jpg")
    if os.path.exists(bg_path):
        try:
            canvas.drawImage(bg_path, 0, 0, width=letter[0], height=letter[1])
        except Exception:
            pass
    canvas.restoreState()


class EvidenceImagesOnlyGenerator:
    """
    Generador de PDF con solo imágenes, sin bordes ni tablas.
    Distribución inteligente según cantidad de imágenes.
    """

    def generate(
        self,
        data: EvidencePhotoData,
        output_path: str,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> str:
        """
        Genera PDF con solo imágenes.

        Args:
            data: Datos de evidencia incluyendo lista de imágenes
            output_path: Ruta completa donde guardar el PDF
            progress_callback: Callback opcional de progreso

        Returns:
            Ruta absoluta del archivo generado
        """
        width, height = letter

        # Nuevos márgenes solicitados (más grandes)
        side_margin = 60   # Aprox 0.83 pulgadas
        top_margin = 100   # Margen superior prominente
        bottom_margin = 60
        gap = 20           # Gap equidistante ampliado

        # Área disponible dinámica basada en los nuevos márgenes con buffer de seguridad
        safe_buffer = 20
        avail_width = width - (2 * side_margin) - safe_buffer
        avail_height = height - top_margin - bottom_margin - safe_buffer

        doc = SimpleDocTemplate(
            output_path,
            pagesize=letter,
            rightMargin=side_margin,
            leftMargin=side_margin,
            topMargin=top_margin,
            bottomMargin=bottom_margin,
        )

        story = []
        images = data.imagenes
        total = len(images)

        if total == 0:
            # PDF vacío
            doc.build(story, onFirstPage=add_evidence_background, onLaterPages=add_evidence_background)
            return os.path.abspath(output_path)

        # Procesar imágenes en grupos según la distribución óptima
        idx = 0
        page_num = 0

        while idx < total:
            remaining = total - idx

            # Determinar cuántas imágenes en esta página
            if remaining >= 4:
                per_page = 4
            else:
                per_page = remaining

            # Procesar el grupo
            group_images = images[idx:idx + per_page]
            flowables = self._layout_images(
                group_images,
                per_page,
                avail_width,
                avail_height,
                gap,
                progress_callback,
                idx,
                total,
            )
            story.extend(flowables)

            idx += per_page
            page_num += 1

            # Agregar salto de página si quedan más imágenes
            if idx < total:
                story.append(PageBreak())

        if progress_callback:
            progress_callback(0.95, "Construyendo documento final...")

        # Construir PDF con background en cada página
        doc.build(story, onFirstPage=add_evidence_background, onLaterPages=add_evidence_background)

        if progress_callback:
            progress_callback(1.0, "Completado")

        return os.path.abspath(output_path)

    def _layout_images(
        self,
        image_paths: list[str],
        count: int,
        avail_width: float,
        avail_height: float,
        gap: float,
        progress_callback: Optional[ProgressCallback],
        current_idx: int,
        total: int,
    ) -> list:
        """
        Distribuye las imágenes en la página según la cantidad.
        Retorna lista de flowables de ReportLab.
        """
        flowables = []

        if count == 1:
            # Una imagen - ocupa máximo espacio manteniendo aspect ratio
            img = self._create_single_image(
                image_paths[0], avail_width, avail_height, gap
            )
            flowables.append(img)

        elif count == 2:
            # Dos imágenes - lado a lado en una tabla
            flowables.append(self._create_table_row(
                image_paths, avail_width, avail_height, gap, cols=2
            ))

        elif count == 3:
            # Tres imágenes - arriba 2, abajo 1 centrado
            flowables.append(self._create_three_images_table(
                image_paths, avail_width, avail_height, gap
            ))

        elif count == 4:
            # Cuatro imágenes - grid 2x2
            flowables.append(self._create_table_row(
                image_paths, avail_width, avail_height, gap, cols=2
            ))

        # Reportar progreso
        if progress_callback:
            for i, _ in enumerate(image_paths):
                progress = (current_idx + i + 1) / total * 0.9
                progress_callback(progress, f"Procesando imagen {current_idx + i + 1}/{total}...")

        return flowables

    def _create_table_row(
        self,
        paths: list[str],
        avail_width: float,
        avail_height: float,
        gap: float,
        cols: int,
    ):
        """Crea una tabla con las imágenes distribuidas en columnas."""
        rows = (len(paths) + cols - 1) // cols  # Ceiling division
        cell_w = (avail_width - gap * (cols - 1)) / cols
        cell_h = (avail_height - gap * (rows - 1)) / rows

        # Crear celdas con imágenes
        cells = []
        for i, path in enumerate(paths):
            final_w, final_h = self._calculate_constrained_size(
                path, cell_w - gap, cell_h - gap
            )
            img = RLImage(path, width=final_w, height=final_h)
            cells.append(img)

        # Organizar en filas
        table_data = []
        for row_idx in range(rows):
            row_data = []
            for col_idx in range(cols):
                idx = row_idx * cols + col_idx
                if idx < len(cells):
                    row_data.append(cells[idx])
                else:
                    row_data.append('')  # Celda vacía
            table_data.append(row_data)

        # Crear tabla
        table = Table(table_data, colWidths=[cell_w] * cols, rowHeights=[cell_h] * rows)
        table.setStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            # Gap entre imágenes mediante padding
            ('LEFTPADDING', (0, 0), (-1, -1), gap / 2),
            ('RIGHTPADDING', (0, 0), (-1, -1), gap / 2),
            ('TOPPADDING', (0, 0), (-1, -1), gap / 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), gap / 2),
        ])

        return table

    def _create_three_images_table(
        self,
        paths: list[str],
        avail_width: float,
        avail_height: float,
        gap: float,
    ):
        """Distribución de 3 imágenes: 2 arriba, 1 abajo centrado."""
        cell_w = (avail_width - gap) / 2
        cell_h = (avail_height - gap) / 2

        # Crear imágenes
        imgs = []
        for path in paths:
            final_w, final_h = self._calculate_constrained_size(
                path, cell_w - gap, cell_h - gap
            )
            img = RLImage(path, width=final_w, height=final_h)
            imgs.append(img)

        # Organizar: [img0, img1], ['', img2] (con espaciado para centrar)
        table_data = [
            [imgs[0], imgs[1]],
            ['', imgs[2]] if len(imgs) > 2 else ['', '']
        ]

        table = Table(table_data, colWidths=[cell_w, cell_w], rowHeights=[cell_h, cell_h])
        table.setStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            # Gap entre imágenes mediante padding
            ('LEFTPADDING', (0, 0), (-1, -1), gap / 2),
            ('RIGHTPADDING', (0, 0), (-1, -1), gap / 2),
            ('TOPPADDING', (0, 0), (-1, -1), gap / 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), gap / 2),
        ])

        return table

    def _create_single_image(
        self,
        path: str,
        avail_width: float,
        avail_height: float,
        gap: float,
    ):
        """Crea una imagen única ocupando máximo espacio."""
        target_w = avail_width - gap
        target_h = avail_height - gap

        # Obtener dimensiones originales
        img_w, img_h = self._get_image_dimensions(path)

        if img_w and img_h:
            aspect = img_w / img_h
            avail_aspect = target_w / target_h

            if aspect > avail_aspect:
                # Imagen más ancha que disponible - limitar por ancho
                final_w = target_w
                final_h = target_w / aspect
            else:
                # Imagen más alta - limitar por alto
                final_h = target_h
                final_w = target_h * aspect
        else:
            final_w = target_w
            final_h = target_h

        return RLImage(path, width=final_w, height=final_h)

    def _calculate_constrained_size(
        self,
        path: str,
        max_w: float,
        max_h: float,
    ) -> tuple[float, float]:
        """Calcula dimensiones manteniendo aspect ratio dentro de constraints."""
        img_w, img_h = self._get_image_dimensions(path)

        if not img_w or not img_h:
            return max_w, max_h

        aspect = img_w / img_h
        avail_aspect = max_w / max_h

        if aspect > avail_aspect:
            # Limitar por ancho
            final_w = max_w
            final_h = max_w / aspect
        else:
            # Limitar por alto
            final_h = max_h
            final_w = max_h * aspect

        return final_w, final_h

    def _get_image_dimensions(self, path: str) -> tuple[Optional[float], Optional[float]]:
        """Obtiene dimensiones de una imagen."""
        try:
            with PILImage.open(path) as img:
                return float(img.width), float(img.height)
        except Exception:
            return None, None
