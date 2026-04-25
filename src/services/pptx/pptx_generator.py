import os
from typing import Optional

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.shapes import MSO_SHAPE
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.enum.text import MSO_ANCHOR

from src.domain.models import EvidenciaData
from src.domain.catalog_models import EvidencePhotoData
from src.services.pdf.protocols import ProgressCallback
from src.utils.helpers import get_asset_path


class PptxEvidenceGenerator:
    """ Generador de PPTX con diseño idéntico al PDF. """

    def generate(
        self,
        data: EvidenciaData | EvidencePhotoData,
        output_path: str,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> str:
        # Si el archivo existe, lo abrimos para anexar
        if os.path.exists(output_path):
            prs = Presentation(output_path)
        else:
            prs = Presentation()
            # Configurar tamaño de diapositiva a carta (Letter)
            # 8.5 x 11 inches
            prs.slide_width = Inches(8.5)
            prs.slide_height = Inches(11)

        total_images = self._get_total_images(data)

        if total_images == 0:
            self._add_empty_slide(prs, data)
            prs.save(output_path)
            return os.path.abspath(output_path)

        if isinstance(data, EvidenciaData):
            # Lógica para Pestaña "Reportes" (EvidenciaData) - TODO EN 1 SLIDE CON FLEXBOX
            self._add_slide_for_reporte(prs, data)
            if progress_callback:
                progress_callback(1.0, "Procesando PPTX Reporte...")
        else:
            # Lógica para Pestaña "Evidencias" (EvidencePhotoData) - GRID PAGINADO
            self._generate_pages_for_evidence(prs, data, progress_callback)

        prs.save(output_path)
        return os.path.abspath(output_path)

    def _get_total_images(self, data):
        if isinstance(data, EvidenciaData):
            return len(data.img_antes) + len(data.img_durante) + len(data.img_despues)
        return len(data.imagenes)

    def _add_empty_slide(self, prs, data):
        blank_slide_layout = prs.slide_layouts[6] # Blank
        slide = prs.slides.add_slide(blank_slide_layout)
        if isinstance(data, EvidencePhotoData):
            self._set_background(slide)

    def _set_background(self, slide):
        bg_path = get_asset_path("background_evidencia.jpg")
        if os.path.exists(bg_path):
            slide.shapes.add_picture(bg_path, 0, 0, width=Inches(8.5), height=Inches(11))

    # --- LÓGICA PARA PESTAÑA "REPORTES" (EvidenciaData) ---

    def _add_slide_for_reporte(self, prs, data: EvidenciaData):
        """ Recrea exactamente el layout del PDF Reportes en una sola diapositiva. """
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        
        # Base margins in inches (matched from layout.py reportlab constants)
        margin_x = 30 / 72.0
        margin_y = 40 / 72.0
        
        # 1. Título General
        title_box = slide.shapes.add_textbox(Inches(margin_x), Inches(margin_y), Inches(8.5 - margin_x*2), Inches(0.4))
        tf = title_box.text_frame
        tf.clear() # clear default paragraphs
        p = tf.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        run = p.add_run()
        run.text = "EVIDENCIA"
        run.font.bold = True
        run.font.size = Pt(16)
        run.font.name = "Helvetica"
        
        # 2. Tablas Encabezado
        y_tables = margin_y + 0.4
        self._add_header_tables_reportlab(slide, data, margin_x, y_tables)
        
        # 3. Categorías de Imágenes (Justified Gallery)
        y_images_start = y_tables + (110 / 72.0) - 0.4 # Aproximación espacio tabla
        avail_height_inches = 11.0 - y_images_start - (40 / 72.0) # Margen inferior
        
        self._build_report_categories(slide, data, margin_x, y_images_start, (612 - 60)/72.0, avail_height_inches)

    def _build_report_categories(self, slide, data: EvidenciaData, x_in: float, y_in: float, w_in: float, h_in: float):
        """ Recrea build_image_flowables usando tablas nativas de PPT """
        cat_target_h_in = h_in / 3.0
        
        header_w_pts = 25
        img_area_w_pts = w_in * 72.0 - header_w_pts
        cell_pad_pts = 3
        
        current_y_in = y_in

        categories = [
            ("ANTES", data.img_antes),
            ("DURANTE", data.img_durante),
            ("DESPUÉS", data.img_despues)
        ]

        for title, paths in categories:
            if not paths:
                current_y_in += cat_target_h_in
                continue
                
            # Calcular filas
            rows = self._build_justified_rows(paths, img_area_w_pts)
            rows = self._rebalance_last_rows(rows, img_area_w_pts)
            
            row_heights_pts = []
            for row in rows:
                sum_ar = sum(ar for _, ar in row)
                natural_h = img_area_w_pts / sum_ar if sum_ar > 0 else 100.0
                row_heights_pts.append(natural_h)
                
            total_natural_h_pts = sum(row_heights_pts)
            cat_target_h_pts = cat_target_h_in * 72.0
            
            # Scale para llenar exactamente la altura de la categoría (como en Reportlab)
            scale = cat_target_h_pts / total_natural_h_pts if total_natural_h_pts > 0 else 1.0
            scaled_row_heights_pts = [h * scale for h in row_heights_pts]
            
            # 1. Tabla exterior (Header + Contenedor general trasero)
            outer_shape = slide.shapes.add_table(
                1, 2, 
                Inches(x_in), Inches(current_y_in), 
                Inches(w_in), Inches(cat_target_h_in)
            )
            outer_table = outer_shape.table
            outer_table.columns[0].width = Pt(header_w_pts)
            outer_table.columns[1].width = Pt(img_area_w_pts)
            
            # Text for vertical title
            cell_title = outer_table.cell(0, 0)
            self._fill_cell(cell_title, "\n".join(list(title)), bold=True, align=PP_ALIGN.CENTER, valign=MSO_ANCHOR.MIDDLE)
            cell_title.text_frame.paragraphs[0].runs[0].font.size = Pt(8)
            
            cell_content = outer_table.cell(0, 1)
            self._fill_cell(cell_content, "", bold=False)
            self._add_borders(outer_table)

            # 2. Tablas internas (Una tabla por 'row' de imagenes)
            current_img_y_pts = current_y_in * 72.0
            
            for row_items, row_h_pts in zip(rows, scaled_row_heights_pts):
                sum_ar = sum(ar for _, ar in row_items)
                cols_count = len(row_items)
                
                # Crear tabla para la fila (dibujará las líneas / padding frame)
                row_shape = slide.shapes.add_table(
                    1, cols_count,
                    Inches(x_in + header_w_pts/72.0), Inches(current_img_y_pts / 72.0),
                    Inches(img_area_w_pts / 72.0), Inches(row_h_pts / 72.0)
                )
                row_table = row_shape.table
                self._add_borders(row_table)
                
                current_img_x_pts = x_in * 72.0 + header_w_pts
                
                for i, (path, ar) in enumerate(row_items):
                    col_w_pts = (ar / sum_ar) * img_area_w_pts
                    row_table.columns[i].width = Pt(col_w_pts)
                    self._fill_cell(row_table.cell(0, i), "", bold=False)
                    
                    # Dibujar Imagen real ajustada por padding sobre la tabla
                    cell_x_in = current_img_x_pts / 72.0
                    cell_y_in = current_img_y_pts / 72.0
                    cell_w_in = col_w_pts / 72.0
                    cell_h_in = row_h_pts / 72.0
                    
                    img_x = cell_x_in + (cell_pad_pts / 72.0)
                    img_y = cell_y_in + (cell_pad_pts / 72.0)
                    img_w = cell_w_in - (2 * cell_pad_pts / 72.0)
                    img_h = cell_h_in - (2 * cell_pad_pts / 72.0)
                    
                    if os.path.exists(path):
                        self._add_fitted_image(slide, path, img_x, img_y, img_w, img_h)
                    
                    current_img_x_pts += col_w_pts
                
                current_img_y_pts += row_h_pts
                
            current_y_in += cat_target_h_in

    def _add_fitted_image(self, slide, path, x_in, y_in, max_w_in, max_h_in):
        """ Escala la imagen para caber en la caja (x, y, w, h) manteniendo aspect ratio. """
        ar = self._get_aspect_ratio(path)
        
        target_w = max_w_in
        target_h = max_w_in / ar
        
        if target_h > max_h_in:
            target_h = max_h_in
            target_w = max_h_in * ar
        
        off_x = (max_w_in - target_w) / 2
        off_y = (max_h_in - target_h) / 2
        
        slide.shapes.add_picture(path, Inches(x_in + off_x), Inches(y_in + off_y), width=Inches(target_w), height=Inches(target_h))

    def _get_aspect_ratio(self, path: str) -> float:
        try:
            from PIL import Image as PILImage, ImageOps
            with PILImage.open(path) as img:
                img = ImageOps.exif_transpose(img)
                w, h = img.size
                return float(w) / h if h > 0 else 4 / 3
        except Exception:
            return 4 / 3

    def _build_justified_rows(self, path_list, img_area_w_pts, pack_row_h_pts=100):
        items = [(p, self._get_aspect_ratio(p)) for p in path_list]
        fill_threshold = img_area_w_pts / float(pack_row_h_pts)

        rows = []
        current_row = []
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

    def _rebalance_last_rows(self, rows, img_area_w_pts, max_row_height_ratio=1.8):
        if len(rows) < 2:
            return rows

        sum_ar_prev = sum(ar for _, ar in rows[-2])
        sum_ar_last = sum(ar for _, ar in rows[-1])

        h_prev = img_area_w_pts / sum_ar_prev if sum_ar_prev > 0 else 1.0
        h_last = img_area_w_pts / sum_ar_last if sum_ar_last > 0 else 1.0

        if h_last / h_prev <= max_row_height_ratio:
            return rows

        combined = rows[-2] + rows[-1]
        total_ar = sum(ar for _, ar in combined)
        half_ar = total_ar / 2.0

        best_split = 1
        best_diff = float("inf")
        cumsum = 0.0
        for i, (_, ar) in enumerate(combined[:-1]):
            cumsum += ar
            diff = abs(cumsum - half_ar)
            if diff < best_diff:
                best_diff = diff
                best_split = i + 1

        return rows[:-2] + [combined[:best_split], combined[best_split:]]

    def _add_header_tables_reportlab(self, slide, data, x_in, y_in):
        rows, cols = 1, 4
        table_width = Inches(540 / 72.0)
        table_height = Inches(0.4)
        
        # Centrar la tabla 540 pts (7.5 in) en 612 pts (8.5 in) -> x=36pts=0.5in
        # Pero reportlab usa rightMargin=30, leftMargin=30 para flowables.
        # Flowable width = 612 - 60 = 552. 
        # width of table Fila1 = 70+308+40+122 = 540pts.
        # En layout.py, se alinea al inicio (left). Asi que x = margin_x (30/72 in)
        
        shape = slide.shapes.add_table(rows, cols, Inches(x_in), Inches(y_in), table_width, table_height)
        table = shape.table
        
        table.columns[0].width = Pt(70)
        table.columns[1].width = Pt(308)
        table.columns[2].width = Pt(40)
        table.columns[3].width = Pt(122)
        
        self._fill_cell(table.cell(0, 0), "PLANTEL:", bold=True)
        self._fill_cell(table.cell(0, 1), data.plantel.upper())
        self._fill_cell(table.cell(0, 2), "CCT:", bold=True)
        self._fill_cell(table.cell(0, 3), data.cct.upper())
        
        self._add_borders(table)
        
        # Fila 2
        y_row2 = y_in + (table_height / Inches(1))
        shape2 = slide.shapes.add_table(1, 2, Inches(x_in), Inches(y_row2), table_width, table_height)
        table2 = shape2.table
        table2.columns[0].width = Pt(70)
        table2.columns[1].width = Pt(470)
        
        self._fill_cell(table2.cell(0, 0), f"# {data.concepto_numero}", bold=True, align=PP_ALIGN.CENTER)
        self._fill_cell(table2.cell(0, 1), data.concepto_texto.upper())
        
        self._add_borders(table2)


    # --- LÓGICA PARA PESTAÑA "EVIDENCIAS" (EvidencePhotoData) ---

    def _generate_pages_for_evidence(self, prs, data: EvidencePhotoData, progress_callback):
        """ Lógica normal de Grid (1 a 4 por página) """
        side_margin = 60 / 72.0
        top_margin = 100 / 72.0
        bottom_margin = 60 / 72.0
        gap = 20 / 72.0
        
        avail_width = 8.5 - (2 * side_margin)
        avail_height = 11.0 - top_margin - bottom_margin

        all_images = data.imagenes
        total = len(all_images)
        idx = 0
        
        while idx < total:
            remaining = total - idx
            per_page = 4 if remaining >= 4 else remaining
            
            group = all_images[idx : idx + per_page]
            self._add_slide_with_images_evidence(
                prs, data, group, per_page, side_margin, top_margin, avail_width, avail_height, gap
            )
            
            idx += per_page
            if progress_callback:
                progress_callback(idx / total, f"Procesando PPTX: {idx}/{total} imágenes...")

    def _add_slide_with_images_evidence(self, prs, data, image_paths, count, margin_x, margin_y, avail_w, avail_h, gap):
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        self._set_background(slide)
        self._add_header_tables_evidence(slide, data, margin_x, margin_y)
        
        header_height_pts = 140
        image_top_margin = margin_y + (header_height_pts / 72.0)
        actual_avail_h = avail_h - (header_height_pts / 72.0)

        if count == 1:
            self._add_fitted_image(slide, image_paths[0], margin_x, image_top_margin, avail_w, actual_avail_h)
        elif count == 2:
            cell_w = (avail_w - gap) / 2
            self._add_fitted_image(slide, image_paths[0], margin_x, image_top_margin, cell_w, actual_avail_h)
            self._add_fitted_image(slide, image_paths[1], margin_x + cell_w + gap, image_top_margin, cell_w, actual_avail_h)
        elif count == 3:
            cell_w = (avail_w - gap) / 2
            cell_h = (actual_avail_h - gap) / 2
            self._add_fitted_image(slide, image_paths[0], margin_x, image_top_margin, cell_w, cell_h)
            self._add_fitted_image(slide, image_paths[1], margin_x + cell_w + gap, image_top_margin, cell_w, cell_h)
            self._add_fitted_image(slide, image_paths[2], margin_x + (cell_w + gap) / 2, image_top_margin + cell_h + gap, cell_w, cell_h)
        elif count == 4:
            cell_w = (avail_w - gap) / 2
            cell_h = (actual_avail_h - gap) / 2
            self._add_fitted_image(slide, image_paths[0], margin_x, image_top_margin, cell_w, cell_h)
            self._add_fitted_image(slide, image_paths[1], margin_x + cell_w + gap, image_top_margin, cell_w, cell_h)
            self._add_fitted_image(slide, image_paths[2], margin_x, image_top_margin + cell_h + gap, cell_w, cell_h)
            self._add_fitted_image(slide, image_paths[3], margin_x + cell_w + gap, image_top_margin + cell_h + gap, cell_w, cell_h)

    def _add_header_tables_evidence(self, slide, data, x, y):
        rows, cols = 1, 4
        table_width = Inches(7.5)
        table_height = Inches(0.4)
        
        shape = slide.shapes.add_table(rows, cols, Inches(x), Inches(y), table_width, table_height)
        table = shape.table
        table.columns[0].width = Pt(100)
        table.columns[1].width = Pt(250)
        table.columns[2].width = Pt(50)
        table.columns[3].width = Pt(140)
        
        self._fill_cell(table.cell(0, 0), "EDIFICIO:", bold=True)
        self._fill_cell(table.cell(0, 1), data.edificio.upper())
        self._fill_cell(table.cell(0, 2), "FECHA:", bold=True)
        self._fill_cell(table.cell(0, 3), data.fecha)
        self._add_borders(table)
        
        y_row2 = y + (table_height / Inches(1))
        shape2 = slide.shapes.add_table(1, 2, Inches(x), Inches(y_row2), table_width, table_height)
        table2 = shape2.table
        table2.columns[0].width = Pt(100)
        table2.columns[1].width = Pt(440)
        self._fill_cell(table2.cell(0, 0), "EQUIPO:", bold=True)
        self._fill_cell(table2.cell(0, 1), data.tipo_equipo.upper())
        self._add_borders(table2)

        y_row3 = y_row2 + (table_height / Inches(1))
        if data.dependent_values:
            text = " | ".join([f"{k.upper()}: {v}" for k, v in data.dependent_values.items()])
            shape3 = slide.shapes.add_table(1, 1, Inches(x), Inches(y_row3), table_width, table_height)
            self._fill_cell(shape3.table.cell(0, 0), text, bold=False)
            self._add_borders(shape3.table)

    # --- UTILITARIOS ---

    def _fill_cell(self, cell, text, bold=False, align=PP_ALIGN.LEFT, valign=MSO_ANCHOR.MIDDLE):
        cell.fill.solid()
        cell.fill.fore_color.rgb = RGBColor(255, 255, 255)
        
        tf = cell.text_frame
        tf.clear() # Clear default
        tf.vertical_anchor = valign
        
        p = tf.paragraphs[0]
        p.alignment = align
        
        run = p.add_run()
        run.text = text
        run.font.size = Pt(10)
        run.font.bold = bold
        run.font.name = "Helvetica"
        run.font.color.rgb = RGBColor(0, 0, 0)
        
    def _add_borders(self, table):
        from pptx.oxml.xmlchemy import OxmlElement
        for row in table.rows:
            for cell in row.cells:
                tc = cell._tc
                tcPr = tc.get_or_add_tcPr()
                for border in ['a:lnL', 'a:lnR', 'a:lnT', 'a:lnB']:
                    ln = OxmlElement(border)
                    ln.set('w', '12700')
                    ln.set('cmpd', 'sng')
                    solidFill = OxmlElement('a:solidFill')
                    srgbClr = OxmlElement('a:srgbClr')
                    srgbClr.set('val', '000000')
                    solidFill.append(srgbClr)
                    ln.append(solidFill)
                    tcPr.append(ln)

