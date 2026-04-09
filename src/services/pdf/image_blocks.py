import os

from reportlab.lib import colors
from reportlab.platypus import Image as RLImage, Paragraph, Table, TableStyle

from src.domain.models import EvidenciaData
from src.services.pdf.protocols import ProgressCallback
from src.utils.helpers import process_image_for_pdf

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
    cat_target_h = avail_height / 3.0  # Cada categoría ocupa 1/3 del espacio

    temp_files: list[str] = []
    current_img_count = 0
    total_imgs = len(data.img_antes) + len(data.img_durante) + len(data.img_despues)

    def report_progress(msg: str):
        if progress_callback:
            fraction = (current_img_count / total_imgs) if total_imgs > 0 else 1.0
            progress_callback(fraction * 0.9, msg)

    # ── Utilidades de imagen ──────────────────────────────────────────────────

    def get_aspect_ratio(path: str) -> float:
        """Retorna el aspect ratio (w/h) de la imagen después de corrección EXIF."""
        try:
            from PIL import Image as PILImage, ImageOps
            with PILImage.open(path) as img:
                img = ImageOps.exif_transpose(img)
                w, h = img.size
                return w / h if h > 0 else 4 / 3
        except Exception:
            return 4 / 3  # Fallback: landscape 4:3

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

    # ── Algoritmo justified gallery ───────────────────────────────────────────

    def build_justified_rows(path_list: list[str]):
        """
        Agrupa las imágenes en filas usando el algoritmo "justified gallery".

        Usa PACK_ROW_H como altura de referencia fija para calcular el umbral
        de llenado, desacoplado de cat_target_h. Así, 2-4 imágenes landscape
        siempre caben en la misma fila independientemente de cuánto espacio
        vertical haya disponible en el bloque.

        Retorna lista de filas: [[(path, ar), ...], ...].
        """
        items = [(p, get_aspect_ratio(p)) for p in path_list]
        fill_threshold = IMG_AREA_W / PACK_ROW_H  # ≋ 5.15 con los valores actuales

        rows: list[list[tuple[str, float]]] = []
        current_row: list[tuple[str, float]] = []
        current_sum = 0.0

        for path, ar in items:
            if current_row and current_sum + ar > fill_threshold:
                rows.append(current_row)
                current_row = [(path, ar)]
                current_sum = ar
            else:
                current_row.append((path, ar))
                current_sum += ar

        if current_row:
            rows.append(current_row)

        return rows

    def compute_row_heights(rows: list, target_row_h: float) -> list[float]:
        """
        Calcula la altura natural de cada fila.
        Fila completa: h = IMG_AREA_W / sum(ar)  → rellena el ancho exacto.
        La última fila incompleta usa la misma fórmula; el escalado final
        al cat_target_h se encarga de que todo encaje sin huecos.
        """
        heights = []
        for row in rows:
            sum_ar = sum(ar for _, ar in row)
            natural_h = IMG_AREA_W / sum_ar if sum_ar > 0 else target_row_h
            heights.append(natural_h)
        return heights

    # ── Constructor de bloque de categoría ───────────────────────────────────

    def rebalance_last_rows(rows: list) -> list:
        """
        Paso de post-proceso: si la última fila tiene una altura natural
        (IMG_AREA_W / sum_ar) más de MAX_ROW_HEIGHT_RATIO veces mayor que la
        penúltima, redistribuye imágenes entre las dos últimas filas buscando
        el punto de corte que minimiza la diferencia de alturas.

        Ejemplo:  3 imágenes landscape + 1 portrait en fila sola
                  → Greedy: [3 imgs] + [1 img]  (ratio alturas ≈ 3×)
                  → Rebalanceo: [2 imgs] + [2 imgs]  (ratio ≈ 1×)
        """
        if len(rows) < 2:
            return rows

        sum_ar_prev = sum(ar for _, ar in rows[-2])
        sum_ar_last = sum(ar for _, ar in rows[-1])

        h_prev = IMG_AREA_W / sum_ar_prev if sum_ar_prev > 0 else 1.0
        h_last = IMG_AREA_W / sum_ar_last if sum_ar_last > 0 else 1.0

        if h_last / h_prev <= MAX_ROW_HEIGHT_RATIO:
            return rows  # Proporción aceptable, no hace falta rebalancear

        # Combinar las dos últimas filas y encontrar el punto de corte que
        # minimiza |sum_ar_row1 - sum_ar_row2|
        combined = rows[-2] + rows[-1]
        total_ar = sum(ar for _, ar in combined)
        half_ar = total_ar / 2.0

        best_split = 1
        best_diff = float("inf")
        cumsum = 0.0
        for i, (_, ar) in enumerate(combined[:-1]):  # Al menos 1 en cada fila
            cumsum += ar
            diff = abs(cumsum - half_ar)
            if diff < best_diff:
                best_diff = diff
                best_split = i + 1

        return rows[:-2] + [combined[:best_split], combined[best_split:]]

    def build_category_block(title: str, path_list: list[str]):
        if not path_list:
            return None

        # 1. Agrupar en filas según aspect ratio (greedy)
        rows = build_justified_rows(path_list)
        # 2. Corregir última fila si queda desproporcionadamente grande
        rows = rebalance_last_rows(rows)

        row_heights = compute_row_heights(rows, cat_target_h)
        total_natural_h = sum(row_heights)

        # Siempre escalar (arriba o abajo) para ocupar exactamente cat_target_h.
        # Así no queda espacio vacío cuando el contenido natural es pequeño.
        scale = cat_target_h / total_natural_h
        row_heights = [h * scale for h in row_heights]
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
                ("GRID",          (0, 0), (-1, -1), 0.5, colors.grey),
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
    if data.img_antes:
        flowables.append(build_category_block("ANTES", data.img_antes))
    if data.img_durante:
        flowables.append(build_category_block("DURANTE", data.img_durante))
    if data.img_despues:
        flowables.append(build_category_block("DESPUÉS", data.img_despues))
    return flowables, temp_files
