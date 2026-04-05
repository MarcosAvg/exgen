# Generador de evidencia (Exgen)

Aplicación de escritorio **Python + GTK 4 + Libadwaita** para generar **PDFs** de inspección con datos del plantel y fotografías por fase (antes / durante / después). El motor de PDF usa **ReportLab**; las imágenes se preparan con **Pillow** (incluye corrección de orientación EXIF).

## Características

- Interfaz alineada con **GNOME** (GTK 4 y Adwaita).
- Varias imágenes por categoría (antes, durante, después), con previsualización y arrastrar y soltar.
- PDF en tamaño carta, tabla de datos de inspección y bloques de fotos; fondo opcional desde `assets/background.jpg`.
- **Persistencia** de carpeta de destino y de la última carpeta usada al elegir imágenes (`~/.config/evidencia_app/`).
- Arquitectura por capas (`domain` / `application` / `services`) y **backends de PDF registrables** para cambiar o añadir formatos.

## Requisitos

| Componente                    | Notas                                                                                         |
| ----------------------------- | --------------------------------------------------------------------------------------------- |
| **Python**                    | 3.10+ recomendado                                                                             |
| **GTK 4 + Libadwaita**        | Interfaz                                                                                      |
| **PyGObject + introspección** | Suele instalarse con paquetes del sistema (`python3-gi`, `gir1.2-gtk-4.0`, `gir1.2-adw-1`, …) |
| **ReportLab, Pillow**         | `pip install -r requirements.txt`                                                             |

En la práctica, **GTK y `gi` deben coincidir con el intérprete** que uses. Si un `venv` no ve `gi`, crea el entorno con `--system-site-packages` o instala solo ReportLab/Pillow en el usuario y ejecuta con el `python3` del sistema (véase abajo).

## Clonar

```bash
git clone <url-de-tu-repositorio> exgen
cd exgen
```

## Dependencias del sistema

### Fedora / RHEL / derivados

```bash
sudo dnf install python3 python3-pip \
  python3-gobject gtk4 libadwaita \
  cairo-gobject gobject-introspection-devel
```

Si falta algún módulo en tiempo de ejecución, instala también los paquetes `gir1.2-*` o `-devel` que sugiera el gestor para GTK 4 / Adwaita.

### Debian / Ubuntu

```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv \
  python3-gi python3-gi-cairo gir1.2-gtk-4.0 gir1.2-adw-1
```

### Arch Linux

```bash
sudo pacman -S python python-pip gtk4 libadwaita python-gobject
```

## Dependencias de Python (`pip`)

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
```

Si `import gi` falla dentro del `.venv`:

```bash
deactivate
rm -rf .venv
python3 -m venv --system-site-packages .venv
source .venv/bin/activate
pip install -r requirements.txt
```

O bien: usa **solo** `pip install --user -r requirements.txt` con el `python3` del sistema y no uses `venv`.

## Fondo del PDF (opcional)

Si existe `assets/background.jpg`, se usa como fondo de página. Puedes generar un placeholder:

```bash
python3 generate_bg.py
```

La carpeta `assets/` está en el repo; el JPEG puedes ignorarlo en git si lo indicas en `.gitignore`.

## Ejecutar

Desde la raíz del clon:

```bash
python3 main.py
```

(con el entorno activado si usas `venv`).

## Uso

1. Rellena **Detalles de inspección** (el campo **Plantel** es obligatorio para generar).
2. En **Ajustes**, define **Guardar en…**.
3. Añade fotos en **Antes / Durante / Después** (clic o arrastrar).
4. Pulsa **Generar PDF**.

## Estructura del proyecto

| Ruta                | Contenido                                           |
| ------------------- | --------------------------------------------------- |
| `main.py`           | Entrada de la aplicación                            |
| `src/domain/`       | Modelo, validación, nombres de archivo              |
| `src/application/`  | Caso de uso de generación del informe               |
| `src/services/pdf/` | Protocolo, registro y backend ReportLab             |
| `src/ui/`           | Ventana, estilos, widgets                           |
| `src/utils/`        | Config, rutas a `assets/`, imagen para PDF          |
| `packaging/`        | `make-tarball.sh`, `pip-vendor.txt`, `make_icon.py` |

## Empaquetado para distribuir (Linux)

Genera `dist/exgen-<versión>-portable-linux.tar.gz` con el código, `vendor/` (ReportLab y Pillow) y el script `./exgen`:

```bash
chmod +x packaging/make-tarball.sh
./packaging/make-tarball.sh
# opcional: VERSION=1.0.0 ./packaging/make-tarball.sh
```

Quien reciba el `.tar.gz` instala GTK 4 + PyGObject en el sistema (como en [Dependencias del sistema](#dependencias-del-sistema)), descomprime y ejecuta `./exgen`. No hace falta `pip` en la máquina destino.

## Acceso directo (`.desktop`)

No hay archivo `.desktop` en el repo: suele llevar rutas absolutas de tu máquina. Para un lanzador en el menú mientras desarrollas, crea por ejemplo `~/.local/share/applications/exgen.desktop` con:

```ini
[Desktop Entry]
Type=Application
Name=Generador de Evidencia
Comment=Ejecución desde el repositorio
Path=/ruta/absoluta/al/clon/exgen
Exec=python3 main.py
Icon=folder-documents
Terminal=false
Categories=Office;Utility;
```

Icono PNG de ejemplo (stdlib):

```bash
python3 packaging/make_icon.py ~/.local/share/icons/hicolor/256x256/apps/exgen.png
```

Luego en el `.desktop` usa `Icon=exgen` (si instalaste el PNG en `hicolor/.../apps/`) o la ruta absoluta al archivo.
