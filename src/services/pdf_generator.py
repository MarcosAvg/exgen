import os
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Image as RLImage, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from src.models.data_models import EvidenciaData
from src.utils.helpers import get_asset_path, process_image_for_pdf

def add_background(canvas, doc):
    canvas.saveState()
    bg_path = get_asset_path("background.jpg")
    if os.path.exists(bg_path):
        try:
            canvas.drawImage(bg_path, 0, 0, width=letter[0], height=letter[1])
        except Exception as e:
            pass
    canvas.restoreState()

def generar_pdf(data: EvidenciaData, output_path: str = "evidencia_output.pdf", progress_callback=None):
    width, height = letter
    
    total_imgs = len(data.img_antes) + len(data.img_durante) + len(data.img_despues)
    current_img_count = 0

    def report_progress(msg):
        if progress_callback:
            fraction = (current_img_count / total_imgs) if total_imgs > 0 else 1.0
            # Reservamos el último 10% para el build del PDF
            progress_callback(fraction * 0.9, msg)

    # Configuramos el documento
    doc = SimpleDocTemplate(
        output_path, 
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=height * 0.12,
        bottomMargin=36
    )
    
    story = []
    
    # 1. Título
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=16,
        alignment=1 # Center
    )
    story.append(Paragraph("EVIDENCIA:", title_style))
    story.append(Spacer(1, 10))
    
    # 2. Tabla Datos Generales y Concepto
    normal_style = styles["Normal"]
    
    table_data = [
        [Paragraph("<b>PLANTEL:</b>", normal_style), Paragraph(data.plantel.upper(), normal_style)],
        [Paragraph("<b>CCT:</b>", normal_style), Paragraph(data.cct.upper(), normal_style)],
        [Paragraph("<b>DIRECCIÓN:</b>", normal_style), Paragraph(data.direccion.upper(), normal_style)],
        [Paragraph("<b>MUNICIPIO:</b>", normal_style), Paragraph(data.municipio.upper(), normal_style)],
        [Paragraph("<para align=center><b>CONCEPTO:</b></para>", normal_style), ""],
        [Paragraph(f"<para align=center>{data.concepto_numero}</para>", normal_style), Paragraph(data.concepto_texto.upper(), normal_style)]
    ]
    
    t_style = TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('GRID', (0,0), (-1,-1), 1, colors.black),
        ('SPAN', (0,4), (1,4)), 
        ('ALIGN', (0,4), (1,4), 'CENTER'),
        ('ALIGN', (0,5), (0,5), 'CENTER'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('TOPPADDING', (0,0), (-1,-1), 4),
    ])
    
    # Width total disponible: 612 - 72 = 540 pts.
    t = Table(table_data, colWidths=[130, 410])
    t.setStyle(t_style)
    story.append(t)
    story.append(Spacer(1, 10))
    
    # 3. Sección Imágenes Múltiples (Horizontal con título vertical)
    max_cols = 3
    img_max_w = 160  
    img_max_h = 140 
    
    temp_files = []
    
    def prep_img(path):
        nonlocal current_img_count
        if not path or not os.path.exists(path):
            return Paragraph("Falta", normal_style)
        try:
            current_img_count += 1
            filename = os.path.basename(path)
            report_progress(f"Procesando {filename}...")
            
            processed_path, w_fit, h_fit = process_image_for_pdf(path, img_max_w, img_max_h)
            if processed_path != path:
                temp_files.append(processed_path)
            return RLImage(processed_path, width=w_fit, height=h_fit)
        except Exception:
            return Paragraph("Error", normal_style)

    def build_category_table(title, path_list):
        if not path_list:
            return []
            
        header_text = f"<para align=center fontSize=8><b>{'<br/>'.join(list(title))}</b></para>"
        chunks = [path_list[i:i+max_cols] for i in range(0, len(path_list), max_cols)]
        
        cat_rows = []
        for row_idx, chunk in enumerate(chunks):
            row_data = []
            if row_idx == 0:
                row_data.append(Paragraph(header_text, normal_style))
            else:
                row_data.append("") 
                
            for img_path in chunk:
                row_data.append(prep_img(img_path))
                
            while len(row_data) < max_cols + 1:
                row_data.append("")
                
            cat_rows.append(row_data)
            
        return cat_rows

    all_img_rows = []
    antes_rows = build_category_table("ANTES", data.img_antes)
    durante_rows = build_category_table("DURANTE", data.img_durante)
    despues_rows = build_category_table("DESPUÉS", data.img_despues)
    
    all_img_rows.extend(antes_rows)
    all_img_rows.extend(durante_rows)
    all_img_rows.extend(despues_rows)
    
    if all_img_rows:
        img_styles = [
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('GRID', (0,0), (-1,-1), 1, colors.black),
            ('BOTTOMPADDING', (0,0), (-1,-1), 2),
            ('TOPPADDING', (0,0), (-1,-1), 2),
            ('LEFTPADDING', (0,0), (0,-1), 2),
            ('RIGHTPADDING', (0,0), (0,-1), 2),
        ]
        
        current_idx = 0
        for cat_rows_set in [antes_rows, durante_rows, despues_rows]:
            n_rows = len(cat_rows_set)
            if n_rows > 1:
                img_styles.append(('SPAN', (0, current_idx), (0, current_idx + n_rows - 1)))
            current_idx += n_rows
            
        t_imgs = Table(all_img_rows, colWidths=[30, 170, 170, 170])
        t_imgs.setStyle(TableStyle(img_styles))
        story.append(t_imgs)
        
    if progress_callback:
        progress_callback(0.95, "Construyendo documento final...")
    
    doc.build(story, onFirstPage=add_background, onLaterPages=add_background)
    
    if progress_callback:
        progress_callback(1.0, "Limpiando...")

    # Clean up standard temp files
    for temp in temp_files:
        if os.path.exists(temp):
            try:
                os.remove(temp)
            except Exception:
                pass
                
    return os.path.abspath(output_path)
