import os

from reportlab.lib import colors
from reportlab.platypus import Image as RLImage, Paragraph, Spacer, Table, TableStyle

from src.domain.models import EvidenciaData
from src.services.pdf.protocols import ProgressCallback
from src.utils.helpers import process_image_for_pdf


def build_image_flowables(
    data: EvidenciaData,
    normal_style,
    progress_callback: ProgressCallback,
    avail_height: float = 600.0,
):
    total_slots = 4
    total_img_w = 515
    cat_target_h = avail_height / 3.0
    
    temp_files: list[str] = []
    current_img_count = 0
    total_imgs = len(data.img_antes) + len(data.img_durante) + len(data.img_despues)

    def report_progress(msg: str):
        if progress_callback:
            fraction = (current_img_count / total_imgs) if total_imgs > 0 else 1.0
            progress_callback(fraction * 0.9, msg)

    def get_img_weight(path):
        """Retorna peso de imagen: 2 si es horizontal, 1 si es vertical."""
        try:
            from PIL import Image as PILImage, ImageOps
            with PILImage.open(path) as img:
                img = ImageOps.exif_transpose(img)
                w, h = img.size
                return 2 if w > h else 1
        except Exception:
            return 1

    def prep_img(path, slots, max_h):
        nonlocal current_img_count
        if not path or not os.path.exists(path):
            return Paragraph("Falta", normal_style)
        try:
            current_img_count += 1
            filename = os.path.basename(path)
            report_progress(f"Procesando {filename}...")
            
            # El ancho depende de cuántos slots ocupe
            target_w = (total_img_w / total_slots) * slots
            
            processed_path, w_fit, h_fit = process_image_for_pdf(path, target_w - 6, max_h - 6)
            if processed_path != path:
                temp_files.append(processed_path)
            return RLImage(processed_path, width=w_fit, height=h_fit)
        except Exception:
            return Paragraph("Error", normal_style)

    def build_category_block(title: str, path_list: list[str]):
        if not path_list:
            return None

        # Agrupar imágenes en filas basadas en su peso (slots)
        rows_data = []
        current_row_paths = []
        current_row_weights = []
        current_weight_sum = 0
        
        for path in path_list:
            weight = get_img_weight(path)
            if current_weight_sum + weight > total_slots:
                # Cerrar fila actual
                rows_data.append((current_row_paths, current_row_weights, current_weight_sum))
                current_row_paths = [path]
                current_row_weights = [weight]
                current_weight_sum = weight
            else:
                current_row_paths.append(path)
                current_row_weights.append(weight)
                current_weight_sum += weight
        
        if current_row_paths:
            rows_data.append((current_row_paths, current_row_weights, current_weight_sum))

        num_rows = len(rows_data)
        row_h = cat_target_h / num_rows
        
        row_tables = []
        for paths, weights, row_weight_sum in rows_data:
            # Calculamos anchos basados en slots. 
            # Si el peso total de la fila es menor a 5, los slots se expanden proporcionalmente
            # para llenar los total_img_w.
            actual_row_w = total_img_w
            col_widths = [(w / row_weight_sum) * actual_row_w for w in weights]
            
            row_images = [prep_img(p, (w/row_weight_sum)*total_slots, row_h) for p, w in zip(paths, weights)]
            
            row_t = Table([row_images], colWidths=col_widths, rowHeights=[row_h])
            row_t.setStyle(TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("LEFTPADDING", (0, 0), (-1, -1), 2),
                ("RIGHTPADDING", (0, 0), (-1, -1), 2),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ]))
            row_tables.append([row_t])
            
        header_text = f"<para align=center fontSize=8><b>{'<br/>'.join(list(title))}</b></para>"
        inner_content = Table(row_tables, colWidths=[total_img_w], rowHeights=[row_h] * num_rows)
        inner_content.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ]
            )
        )
        
        cat_outer_table = Table(
            [[Paragraph(header_text, normal_style), inner_content]],
            colWidths=[25, total_img_w],
            rowHeights=[cat_target_h]
        )
        cat_outer_table.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ]
            )
        )
        return cat_outer_table

    flowables = []
    if data.img_antes:
        flowables.append(build_category_block("ANTES", data.img_antes))
    if data.img_durante:
        flowables.append(build_category_block("DURANTE", data.img_durante))
    if data.img_despues:
        flowables.append(build_category_block("DESPUÉS", data.img_despues))
    return flowables, temp_files
