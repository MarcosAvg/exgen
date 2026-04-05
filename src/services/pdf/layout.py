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
        Paragraph("EVIDENCIA:", title_style),
        Spacer(1, 10),
    ]
    table_data = [
        [Paragraph("<b>PLANTEL:</b>", normal_style), Paragraph(data.plantel.upper(), normal_style)],
        [Paragraph("<b>CCT:</b>", normal_style), Paragraph(data.cct.upper(), normal_style)],
        [Paragraph("<b>DIRECCIÓN:</b>", normal_style), Paragraph(data.direccion.upper(), normal_style)],
        [Paragraph("<b>MUNICIPIO:</b>", normal_style), Paragraph(data.municipio.upper(), normal_style)],
        [Paragraph("<para align=center><b>CONCEPTO:</b></para>", normal_style), ""],
        [
            Paragraph(f"<para align=center>{data.concepto_numero}</para>", normal_style),
            Paragraph(data.concepto_texto.upper(), normal_style),
        ],
    ]
    t_style = TableStyle(
        [
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("GRID", (0, 0), (-1, -1), 1, colors.black),
            ("SPAN", (0, 4), (1, 4)),
            ("ALIGN", (0, 4), (1, 4), "CENTER"),
            ("ALIGN", (0, 5), (0, 5), "CENTER"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
        ]
    )
    t = Table(table_data, colWidths=[130, 410])
    t.setStyle(t_style)
    flowables.append(t)
    flowables.append(Spacer(1, 10))
    return flowables, normal_style
