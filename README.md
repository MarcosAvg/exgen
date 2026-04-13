# Generador de Evidencia (Exgen)

Aplicación de escritorio nativa usando **Python + GTK 4 + Libadwaita** diseñada para generar reportes de inspección fotográfica en formato PDF y mantener un registro estructurado en Excel.

Utiliza **ReportLab** como motor de generación PDF y **Pillow** para el procesamiento y corrección de orientación de las imágenes.

## Características Principales

- **Interfaz Nativa y Profesional**: Componentes alineados a las guías de diseño de GNOME (GTK 4 y Libadwaita) con un flujo de trabajo optimizado y validación de UI.
- **Catálogos Dinámicos**: Sistema de dependencias que oculta o muestra campos de información jerárquica (Edificio -> Tipo de Equipo -> Zonas, etc.).
- **Base de Datos en Excel**: La aplicación actúa sincronizada con un archivo `Registros.xlsx` de forma local, identificando combinaciones ya completadas para evitar duplicaciones o sobrescrituras accidentales.
- **Manejo de Evidencias Mejorado Drag-and-Drop**: Una zona interactiva para arrastrar imágenes; se encarga automáticamente del aspecto en el PDF final aplicando formato de grilla ajustado al tamaño esperado (70/30 para títulos).

## Requisitos

| Componente                    | Notas                                                                                         |
| ----------------------------- | --------------------------------------------------------------------------------------------- |
| **Python**                    | 3.10+ recomendado                                                                             |
| **GTK 4 + Libadwaita**        | Dependencias nativas para la interfaz gráfica.                                                |
| **PyGObject + introspección** | Suele instalarse por el sistema (`python3-gi`, `gir1.2-gtk-4.0`, `gir1.2-adw-1`).             |
| **ReportLab, Pillow, openpyxl**| Librerías necesarias de Python. Ver `requirements.txt`.                                      |

Es recomendable instalar las librerías `Pillow`, `reportlab` y `openpyxl` vía local pero enlazar los bindings base del sistema (`--system-site-packages` en caso de usar `venv`).

## Instalación y Arranque Rápido

1. Teniendo instaladas las bases GTK en el sistema:
```bash
git clone <url-de-tu-repositorio> exgen
cd exgen
```

2. Ejecutar directamente (si tienes entorno pip del usuario):
```bash
pip install --user -r requirements.txt
python3 main.py
```

### Notas sobre dependencias del sistema operativo:

*   **Ubuntu/Debian**: `sudo apt install python3-gi gir1.2-gtk-4.0 gir1.2-adw-1`
*   **Fedora**: `sudo dnf install python3-gobject gtk4 libadwaita`
*   **Arch Linux**: `sudo pacman -S python-gobject gtk4 libadwaita`

## Empaquetado y Compilación (Flatpak)

Asegúrate de tener instalada la herramienta constructora y los SDKs base correspondientes:

1. Instalar dependencias GNOME necesarias:
```bash
flatpak install flathub org.gnome.Sdk//49 org.gnome.Platform//49
```

2. Compilar e instalar localmente:
```bash
flatpak-builder build-dir com.github.marcosavg.Exgen.json --force-clean --user --install
```

Tras la compilación, "Exgen" estará disponible en tu menú de aplicaciones o podrá ser ejecutada vía terminal:
```bash
flatpak run com.github.marcosavg.Exgen
```

## Uso de la aplicación

1. **Configurar Catálogos:** Ve al menú principal y configura tus Edificios, Equipos y sus respectivos detalles, estableciendo sus reglas de visibilidad (por ejemplo: "Solo muestra Piso si Edificio es Torre").
2. **Seleccionar Ubicación Destino:** Define la "Carpeta de Guardado" donde se ubicarán los PDFs y donde se generará o leerá la bitácora `Registros.xlsx`.
3. **Selección Activa:** Elige las opciones de tu reporte. Si esta captura ya existe, observarás una etiqueta en verde indicando "COMPLETADO".
4. **Evidencias Gráficas:** Añade las imágenes necesarias desde el explorador o arrastrándolas.
5. **Generación:** Al pulsar "Generar PDF", se creará el documento final en la carpeta correspondiente al Edificio y Equipo y se dará de alta el evento como completado en tu hoja de Excel general.
