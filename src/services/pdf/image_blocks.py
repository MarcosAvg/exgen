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
):
    max_cols = 5
    total_img_w = 515
    img_max_h = 140
    temp_files: list[str] = []
    current_img_count = 0
    total_imgs = len(data.img_antes) + len(data.img_durante) + len(data.img_despues)

    def report_progress(msg: str):
        if progress_callback:
            fraction = (current_img_count / total_imgs) if total_imgs > 0 else 1.0
            progress_callback(fraction * 0.9, msg)

    def prep_img(path, custom_max_w=None):
        nonlocal current_img_count
        if not path or not os.path.exists(path):
            return Paragraph("Falta", normal_style)
        try:
            current_img_count += 1
            filename = os.path.basename(path)
            report_progress(f"Procesando {filename}...")
            target_w = custom_max_w if custom_max_w else 103
            processed_path, w_fit, h_fit = process_image_for_pdf(path, target_w, img_max_h)
            if processed_path != path:
                temp_files.append(processed_path)
            return RLImage(processed_path, width=w_fit, height=h_fit)
        except Exception:
            return Paragraph("Error", normal_style)

    def build_category_block(title: str, path_list: list[str]):
        if not path_list:
            return None
        chunks = [path_list[i : i + max_cols] for i in range(0, len(path_list), max_cols)]
        row_tables = []
        for chunk in chunks:
            n = len(chunk)
            cell_w = total_img_w / n
            row_data = [prep_img(p, custom_max_w=cell_w - 8) for p in chunk]
            row_t = Table([row_data], colWidths=[cell_w] * n)
            row_t_style = [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("LEFTPADDING", (0, 0), (-1, -1), 2),
                ("RIGHTPADDING", (0, 0), (-1, -1), 2),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ]
            if n > 1:
                row_t_style.append(("GRID", (0, 0), (-1, -1), 0.5, colors.grey))
            row_t.setStyle(TableStyle(row_t_style))
            row_tables.append([row_t])
        header_text = f"<para align=center fontSize=8><b>{'<br/>'.join(list(title))}</b></para>"
        inner_content = Table(row_tables, colWidths=[total_img_w])
        inner_content.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
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
        flowables.append(Spacer(1, 5))
    if data.img_durante:
        flowables.append(build_category_block("DURANTE", data.img_durante))
        flowables.append(Spacer(1, 5))
    if data.img_despues:
        flowables.append(build_category_block("DESPUÉS", data.img_despues))
        flowables.append(Spacer(1, 5))
    return flowables, temp_files
