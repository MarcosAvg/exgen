import os
import tempfile
from PIL import Image, ImageOps

def get_asset_path(filename: str) -> str:
    """Returns the absolute path to an asset file assuming it's in the assets/ folder relative to project root."""
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base_dir, "assets", filename)

def process_image_for_pdf(img_path: str, max_width: float, max_height: float) -> tuple[str, float, float]:
    """
    Aplica rotación de metadatos EXIF (para problemas de rotación de celulares),
    calcula el ratio de aspecto y guarda una foto procesada UNICAMENTE si es necesario.
    """
    try:
        with Image.open(img_path) as img:
            orig_width, orig_height = img.size
            
            # Revisar si necesita transposición EXIF (rotación real)
            img_transposed = ImageOps.exif_transpose(img)
            
            # ¡IMPORTANTE! Actualizamos dimensiones DESPUÉS de la rotación para el cálculo de ratio
            orig_width, orig_height = img_transposed.size
            
            # Solo guardamos si hubo rotación real o si el modo no es RGB (ej. PNG con transparencia)
            needs_save = (img_transposed is not img) or (img.mode != 'RGB')
            
            if needs_save:
                fd, temp_path = tempfile.mkstemp(suffix=".jpg")
                os.close(fd)
                
                final_img = img_transposed
                if final_img.mode != 'RGB':
                    final_img = final_img.convert('RGB')
                
                # Calidad 85 es suficiente para un reporte y mucho más rápida que 95
                final_img.save(temp_path, format='JPEG', quality=85)
                res_path = temp_path
            else:
                res_path = img_path
            
    except Exception:
        return img_path, max_width, max_height
        
    ratio = min(max_width / orig_width, max_height / orig_height)
    return res_path, orig_width * ratio, orig_height * ratio
