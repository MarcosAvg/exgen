_INVALID_FILENAME_CHARS = r'<>:"/\|?*'


def evidence_pdf_filename(concepto_numero: str, plantel: str) -> str:
    filename = f"{concepto_numero} - {plantel}.pdf"
    for char in _INVALID_FILENAME_CHARS:
        filename = filename.replace(char, "_")
    return filename
