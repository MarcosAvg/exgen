from src.utils.helpers import get_image_aspect_ratio

def calculate_gallery_layout(path_list: list[str], img_area_w: float, cat_target_h: float) -> tuple[list[list[tuple[str, float]]], list[float]]:
    """
    Calcula el layout final óptimo evaluando diferentes particiones por filas (k).
    Busca maximizar el tamaño de las fotos penalizando los huecos (gaps) horizontales.
    Retorna: (rows, row_heights)
    """
    if not path_list:
        return [], []
        
    items = [(p, get_image_aspect_ratio(p)) for p in path_list]
    n = len(items)
    
    best_rows = []
    best_row_heights = []
    best_score = -1.0
    
    # Evaluar dividir las fotos desde 1 hasta n filas
    for k in range(1, n + 1):
        # Distribuir equitativamente
        rows = []
        items_per_row = n // k
        remainder = n % k
        
        idx = 0
        for i in range(k):
            count = items_per_row + (1 if i < remainder else 0)
            if count > 0:
                rows.append(items[idx : idx + count])
                idx += count
                
        # Calcular alturas naturales para que ocupen todo el ancho
        row_heights = []
        for row in rows:
            sum_ar = sum(ar for _, ar in row)
            natural_h = img_area_w / sum_ar if sum_ar > 0 else 100.0
            row_heights.append(natural_h)
            
        total_natural_h = sum(row_heights)
        
        # scale <= 1.0 evita que las imágenes se estiren verticalmente si sobran
        scale = min(1.0, cat_target_h / total_natural_h) if total_natural_h > 0 else 1.0
        
        # Altura efectiva promedio por fila
        effective_h = (total_natural_h * scale) / k
        
        # Penalizamos fuertemente layouts que dejen huecos horizontales enormes (scale < 1.0)
        score = effective_h * (scale ** 0.5) 
        
        if score > best_score:
            best_score = score
            best_rows = rows
            best_row_heights = [h * scale for h in row_heights]

    return best_rows, best_row_heights
