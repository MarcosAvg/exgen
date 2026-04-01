# Generador de Evidencias (GTK 4 + Libadwaita)

Una aplicación de escritorio moderna escrita en Python para la generación estructurada de reportes de evidencia en formato PDF, diseñada específicamente para el entorno de escritorio GNOME.

## Características

- **Interfaz Moderna**: Construida con GTK 4 y Libadwaita siguiendo las pautas de diseño de GNOME.
- **Responsiva**: Diseño adaptativo que se ajusta a ventanas estrechas y de escritorio (dos columnas).
- **Generación de PDF**: Reportes profesionales en tamaño carta con encabezados personalizados y logos de fondo.
- **Soporte de Imágenes Múltiples**: Permite adjuntar múltiples fotografías por categoría (Antes, Durante y Después).
- **9 Imágenes por Hoja**: Distribución optimizada para que quepan hasta 9 fotos por página con encabezados laterales.
- **Paginación Automática**: Crea hojas adicionales automáticamente si el contenido excede una página.
- **Corrección de Orientación**: Detecta metadatos EXIF de cámaras de celular para rotar las fotos correctamente.
- **Persistencia**: Recuerda la carpeta de destino entre reinicios.

## Requisitos

- Python 3.10+
- GTK 4 y Libadwaita 1.x
- ReportLab (para la generación de PDF)
- Pillow (para el procesamiento de imágenes)

## Instalación

1.  **Clonar el repositorio**:
    ```bash
    git clone https://github.com/tu-usuario/Exgen.git
    cd Exgen
    ```

2.  **Instalar dependencias del sistema** (Ubuntu/Debian):
    ```bash
    sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-4.0 gir1.2-adw-1
    ```

3.  **Configurar entorno virtual e instalar librerías de Python**:
    ```bash
    python -m venv .venv
    source .venv/bin/activate
    pip install reportlab Pillow
    ```

## Uso

Para iniciar la aplicación:
```bash
python main.py
```

1.  Completa los campos de **Datos Generales** y **Concepto**.
2.  Define la **Carpeta de Destino** donde se guardarán tus archivos.
3.  Selecciona las imágenes para cada categoría (puedes seleccionar varias a la vez).
4.  Haz clic en **Generar PDF**.

## Estructura del Proyecto

- `src/ui/`: Lógica de la interfaz gráfica.
- `src/services/`: Motor de generación de PDF.
- `src/utils/`: Funciones de apoyo y gestión de configuración.
- `src/models/`: Estructuras de datos.
- `assets/`: Recursos gráficos (fondos, iconos).
