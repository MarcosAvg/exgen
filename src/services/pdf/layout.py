from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle

from src.domain.models import EvidenciaData


def build_title_and_data_table(data: EvidenciaData):
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "TitleStyle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=16,
        alignment=1,
    )
    normal_style = styles["Normal"]
    flowables = [
        Paragraph("EVIDENCIA", title_style),
        Spacer(1, 15),
    ]
    
    # Tabla Fila 1: Plantel (70% total) y CCT (30% total)
    # Distribuido en 4 celdas: [Etiqueta, Valor, Etiqueta, Valor]
    row1_table = Table(
        [[
            Paragraph("<b>PLANTEL:</b>", normal_style),
            Paragraph(data.plantel.upper(), normal_style),
            Paragraph("<b>CCT:</b>", normal_style),
            Paragraph(data.cct.upper(), normal_style)
        ]],
        colWidths=[70, 308, 40, 122] # Proporciones aproximadas de 70% y 30%
    )
    row1_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 1, colors.black),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    
    # Tabla Fila 2: Concepto Num y Texto
    row2_table = Table(
        [[
            Paragraph(f"<b># {data.concepto_numero}</b>", normal_style),
            Paragraph(data.concepto_texto.upper(), normal_style)
        ]],
        colWidths=[70, 470] # Alineado con la primera celda de la fila 1 (70pt)
    )
    row2_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 1, colors.black),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("ALIGN", (0, 0), (0, 0), "CENTER"), # Número centrado
    ]))
    
    flowables.append(row1_table)
    flowables.append(row2_table)
    flowables.append(Spacer(1, 20))
    return flowables, normal_style
