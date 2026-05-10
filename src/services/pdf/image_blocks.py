import os

from reportlab.lib import colors
from reportlab.platypus import Image as RLImage, Paragraph, Spacer, Table, TableStyle

from src.domain.models import EvidenciaData
from src.services.pdf.protocols import ProgressCallback
from src.utils.helpers import process_image_for_pdf
from src.utils.gallery_layout import calculate_gallery_layout

# ─── Constantes de layout ────────────────────────────────────────────────────
HEADER_W = 25    # Ancho de la columna lateral de categoría (ANTES/DURANTE/DESPUÉS)
IMG_AREA_W = 515 # Ancho disponible para las imágenes dentro del bloque
CELL_PAD = 3     # Padding interior de cada celda de imagen (px por lado)

# Altura de referencia FIJA usada únicamente para decidir cuántas imágenes
# caben en una fila (no afecta la altura de visualización final).
# fill_threshold = IMG_AREA_W / PACK_ROW_H = 515/100 ≈ 5.15
# → una fila se cierra solo cuando su suma de aspect ratios supera 5.15,
#   lo que equivale a unas 3-4 imágenes landscape estándar por fila.
PACK_ROW_H = 100

# Si la altura natural de la última fila supera este factor respecto a la
# anterior, se redistribuyen imágenes entre las dos últimas filas.
MAX_ROW_HEIGHT_RATIO = 1.8


def build_image_flowables(
    data: EvidenciaData,
    normal_style,
    progress_callback: ProgressCallback,
    avail_height: float = 600.0,
):
    """
    Construye los flowables de imágenes para el PDF usando un algoritmo de
    "justified gallery": cada fila se llena horizontalmente de manera proporcional
    al aspect ratio real de cada imagen, sin gaps horizontales y con la menor
    cantidad posible de espacio vertical sobrante.
    """
    # Cada categoría ocupa 1/3 del espacio por defecto.
    # Si se solicita expandir, se divide entre el número de categorías presentes.
    num_cats = 3.0
    if data.expandir_espacio:
        present_cats = sum(1 for imgs in [data.img_antes, data.img_durante, data.img_despues] if imgs)
        if present_cats > 0:
            num_cats = float(present_cats)
            
    cat_target_h = avail_height / num_cats

    temp_files: list[str] = []
    current_img_count = 0
    total_imgs = len(data.img_antes) + len(data.img_durante) + len(data.img_despues)

    def report_progress(msg: str):
        if progress_callback:
            fraction = (current_img_count / total_imgs) if total_imgs > 0 else 1.0
            progress_callback(fraction * 0.9, msg)

    # ── Utilidades de imagen ──────────────────────────────────────────────────

    def prep_img(path: str, cell_w: float, cell_h: float) -> RLImage | Paragraph:
        """Procesa y escala la imagen para que encaje dentro de la celda dada."""
        nonlocal current_img_count
        if not path or not os.path.exists(path):
            return Paragraph("Falta", normal_style)
        try:
            current_img_count += 1
            report_progress(f"Procesando {os.path.basename(path)}...")
            processed_path, w_fit, h_fit = process_image_for_pdf(
                path,
                cell_w - CELL_PAD * 2,
                cell_h - CELL_PAD * 2,
            )
            if processed_path != path:
                temp_files.append(processed_path)
            return RLImage(processed_path, width=w_fit, height=h_fit)
        except Exception:
            return Paragraph("Error", normal_style)

    # ── Constructor de bloque de categoría ───────────────────────────────────

    def build_category_block(title: str, path_list: list[str]):
        if not path_list:
            return None

        rows, row_heights = calculate_gallery_layout(path_list, IMG_AREA_W, cat_target_h)
        total_natural_h = cat_target_h

        # Construir una Table por fila de imágenes
        row_tables = []
        for row_items, row_h in zip(rows, row_heights):
            sum_ar = sum(ar for _, ar in row_items)
            col_widths = [(ar / sum_ar) * IMG_AREA_W for _, ar in row_items]

            row_images = [
                prep_img(path, cw, row_h)
                for (path, _), cw in zip(row_items, col_widths)
            ]

            row_t = Table([row_images], colWidths=col_widths, rowHeights=[row_h])
            row_t.setStyle(TableStyle([
                ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
                ("LEFTPADDING",   (0, 0), (-1, -1), CELL_PAD),
                ("RIGHTPADDING",  (0, 0), (-1, -1), CELL_PAD),
                ("TOPPADDING",    (0, 0), (-1, -1), CELL_PAD),
                ("BOTTOMPADDING", (0, 0), (-1, -1), CELL_PAD),
            ]))
            row_tables.append([row_t])

        # Tabla interna: apila todas las filas verticalmente
        inner_content = Table(
            row_tables,
            colWidths=[IMG_AREA_W],
            rowHeights=row_heights,
        )
        inner_content.setStyle(TableStyle([
            ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING",   (0, 0), (-1, -1), 0),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
            ("TOPPADDING",    (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))

        # Tabla externa: encabezado lateral + contenido de imágenes
        header_text = (
            f"<para align=center fontSize=8>"
            f"<b>{'<br/>'.join(list(title))}</b>"
            f"</para>"
        )
        cat_outer_table = Table(
            [[Paragraph(header_text, normal_style), inner_content]],
            colWidths=[HEADER_W, IMG_AREA_W],
            rowHeights=[total_natural_h],
        )
        cat_outer_table.setStyle(TableStyle([
            ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
            ("GRID",          (0, 0), (-1, -1), 1, colors.black),
            ("LEFTPADDING",   (0, 0), (-1, -1), 0),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
            ("TOPPADDING",    (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))
        return cat_outer_table

    # ── Ensamblar flowables ───────────────────────────────────────────────────
    flowables = []
    
    # ANTES
    if data.img_antes:
        flowables.append(build_category_block("ANTES", data.img_antes))
    elif not data.expandir_espacio:
        flowables.append(Spacer(1, cat_target_h))
        
    # DURANTE
    if data.img_durante:
        flowables.append(build_category_block("DURANTE", data.img_durante))
    elif not data.expandir_espacio:
        flowables.append(Spacer(1, cat_target_h))
        
    # DESPUÉS
    if data.img_despues:
        flowables.append(build_category_block("DESPUÉS", data.img_despues))
    elif not data.expandir_espacio:
        flowables.append(Spacer(1, cat_target_h))
        
    return flowables, temp_files
