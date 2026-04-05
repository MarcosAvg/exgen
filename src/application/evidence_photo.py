"""
Lógica de aplicación para generación de PDFs de evidencias (solo imágenes).
"""
import os
from dataclasses import dataclass

from src.domain.catalog_models import EvidencePhotoData
from src.services.pdf import get_evidence_generator


@dataclass
class GenerateEvidenceSuccess:
    output_path: str


@dataclass
class GenerateEvidenceError:
    title: str
    message: str


def run_generate_evidence_pdf(
    data: EvidencePhotoData,
    base_output_directory: str,
    progress_callback=None,
) -> GenerateEvidenceSuccess | GenerateEvidenceError:
    """
    Genera PDF de evidencias con estructura de carpetas jerárquica.

    Args:
        data: Datos de evidencia incluyendo imágenes y selecciones
        base_output_directory: Carpeta base de configuración
        progress_callback: Callback de progreso opcional

    Returns:
        Resultado exitoso o error
    """
    # Validar datos mínimos
    if not data.edificio or not data.tipo_equipo:
        return GenerateEvidenceError(
            title="Faltan datos obligatorios",
            message="Por favor selecciona Edificio y Tipo de Equipo.",
        )

    if not data.imagenes:
        return GenerateEvidenceError(
            title="Sin imágenes",
            message="Por favor selecciona al menos una imagen.",
        )

    # Generar ruta completa con subcarpetas
    full_path = data.get_full_path(base_output_directory)

    # Crear subcarpetas si no existen
    output_dir = os.path.dirname(full_path)
    try:
        os.makedirs(output_dir, exist_ok=True)
    except OSError as e:
        return GenerateEvidenceError(
            title="Error al crear carpetas",
            message=f"No se pudo crear la estructura de carpetas: {e}",
        )

    # Generar PDF usando el backend de solo imágenes
    generator = get_evidence_generator("images_only")

    try:
        result_path = generator.generate(data, full_path, progress_callback)
        return GenerateEvidenceSuccess(output_path=result_path)
    except Exception as e:
        return GenerateEvidenceError(
            title="Error al generar PDF",
            message=f"Ocurrió un error: {e}",
        )
