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
    max_cols = 5
    total_img_w = 515 # Ancho disponible para las imágenes (540 - 25 del título)
    img_max_h = 140   # Reducida para evitar saltos de página innecesarios
    
    temp_files = []
    
    def prep_img(path, custom_max_w=None):
        nonlocal current_img_count
        if not path or not os.path.exists(path):
            return Paragraph("Falta", normal_style)
        try:
            current_img_count += 1
            filename = os.path.basename(path)
            report_progress(f"Procesando {filename}...")
            
            target_w = custom_max_w if custom_max_w else 103 # Default 5 cols
            processed_path, w_fit, h_fit = process_image_for_pdf(path, target_w, img_max_h)
            if processed_path != path:
                temp_files.append(processed_path)
            return RLImage(processed_path, width=w_fit, height=h_fit)
        except Exception:
            return Paragraph("Error", normal_style)

    def build_category_block(title, path_list):
        if not path_list:
            return None
            
        chunks = [path_list[i:i+max_cols] for i in range(0, len(path_list), max_cols)]
        
        # Generar las filas de imágenes como tablas independientes ("Flexbox")
        row_tables = []
        for chunk in chunks:
            n = len(chunk)
            cell_w = total_img_w / n
            # Aumentamos el margen de seguridad a 8pts para evitar desbordamiento
            row_data = [prep_img(p, custom_max_w=cell_w-8) for p in chunk]
            
            # Tabla de una sola fila para este bloque de imágenes
            row_t = Table([row_data], colWidths=[cell_w] * n)
            row_t_style = [
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('LEFTPADDING', (0,0), (-1,-1), 2),
                ('RIGHTPADDING', (0,0), (-1,-1), 2),
                ('TOPPADDING', (0,0), (-1,-1), 2),
                ('BOTTOMPADDING', (0,0), (-1,-1), 2),
            ]
            # Solo añadir separadores verticales si hay más de una imagen
            if n > 1:
                row_t_style.append(('GRID', (0,0), (-1,-1), 0.5, colors.grey))
            
            row_t.setStyle(TableStyle(row_t_style))
            row_tables.append([row_t])
            
        # Tabla contenedora para la categoría (Título + Filas)
        header_text = f"<para align=center fontSize=8><b>{'<br/>'.join(list(title))}</b></para>"
        
        # El contenedor interno que apila las filas
        inner_content = Table(row_tables, colWidths=[total_img_w])
        inner_content.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey), # Separadores entre filas
            ('LEFTPADDING', (0,0), (-1,-1), 0),
            ('RIGHTPADDING', (0,0), (-1,-1), 0),
            ('TOPPADDING', (0,0), (-1,-1), 0),
            ('BOTTOMPADDING', (0,0), (-1,-1), 0),
        ]))

        cat_outer_table = Table([
            [Paragraph(header_text, normal_style), inner_content]
        ], colWidths=[25, total_img_w])
        
        cat_outer_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('GRID', (0,0), (-1,-1), 1, colors.black), # El borde exterior principal
            ('LEFTPADDING', (0,0), (-1,-1), 0),
            ('RIGHTPADDING', (0,0), (-1,-1), 0),
            ('TOPPADDING', (0,0), (-1,-1), 0),
            ('BOTTOMPADDING', (0,0), (-1,-1), 0),
        ]))
        
        return cat_outer_table

    # Ensamblar categorías
    if data.img_antes:
        story.append(build_category_block("ANTES", data.img_antes))
        story.append(Spacer(1, 5))
        
    if data.img_durante:
        story.append(build_category_block("DURANTE", data.img_durante))
        story.append(Spacer(1, 5))
        
    if data.img_despues:
        story.append(build_category_block("DESPUÉS", data.img_despues))
        story.append(Spacer(1, 5))
        
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
