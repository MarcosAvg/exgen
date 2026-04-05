#!/usr/bin/env bash
# Genera dist/exgen-<versión>-portable-linux.tar.gz: código + vendor/ (ReportLab, Pillow).
# Quien descomprima solo necesita Python 3, GTK 4 y PyGObject del sistema.
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
ROOT=$(cd "$SCRIPT_DIR/.." && pwd)
VERSION="${VERSION:-0.1.0}"
NAME="exgen-${VERSION}"
OUT="$ROOT/dist"
STAGE=$(mktemp -d)

cleanup() { rm -rf "$STAGE"; }
trap cleanup EXIT

die() { echo "error: $*" >&2; exit 1; }

command -v python3 >/dev/null || die "Se requiere python3."
command -v tar >/dev/null || die "Se requiere tar."

mkdir -p "$OUT" "$STAGE/$NAME"

echo "==> Copiando fuentes"
cp "$ROOT/main.py" "$STAGE/$NAME/"
cp -a "$ROOT/src" "$STAGE/$NAME/"
mkdir -p "$STAGE/$NAME/assets"
if [[ -d "$ROOT/assets" ]]; then
  cp -a "$ROOT/assets/." "$STAGE/$NAME/assets/" 2>/dev/null || true
fi
cp "$ROOT/requirements.txt" "$STAGE/$NAME/"
cp "$SCRIPT_DIR/pip-vendor.txt" "$STAGE/$NAME/"

echo "==> pip install → vendor/ (solo ReportLab y Pillow; no PyGObject)"
mkdir -p "$STAGE/$NAME/vendor"
python3 -m pip install --upgrade pip >/dev/null
python3 -m pip install --no-cache-dir --target "$STAGE/$NAME/vendor" -r "$SCRIPT_DIR/pip-vendor.txt"

cat > "$STAGE/$NAME/exgen" << 'EOS'
#!/bin/sh
ROOT="$(cd "$(dirname "$0")" && pwd)"
# Orden: proyecto primero, vendor después (gi siempre del sistema, no de vendor)
export PYTHONPATH="$ROOT:$ROOT/vendor${PYTHONPATH:+:$PYTHONPATH}"
cd "$ROOT" || exit 1

if ! python3 -c "import gi; gi.require_version('Gtk','4.0'); gi.require_version('Adw','1')" 2>/dev/null; then
  echo "Faltan dependencias de sistema (GTK 4, Libadwaita, PyGObject)." >&2
  echo "Consulta INSTALAR.txt en esta carpeta o el README del repositorio." >&2
  exit 1
fi

exec python3 "$ROOT/main.py" "$@"
EOS
chmod +x "$STAGE/$NAME/exgen"

cat > "$STAGE/$NAME/INSTALAR.txt" << 'EOF'
Generador de evidencia (Exgen) — paquete portable

Qué incluye este .tar.gz
-------------------------
- Código de la aplicación
- Librerías de pip (ReportLab, Pillow) en la carpeta vendor/

Qué debes instalar en el sistema (una vez)
-----------------------------------------
Son los mismos paquetes que para desarrollar: Python 3, GTK 4, Libadwaita y PyGObject.

Fedora:
  sudo dnf install python3 python3-pip python3-gobject gtk4 libadwaita

Debian / Ubuntu:
  sudo apt install python3 python3-pip python3-gi python3-gi-cairo gir1.2-gtk-4.0 gir1.2-adw-1

Cómo ejecutar
-------------
  tar -xzf exgen-*.tar.gz
  cd exgen-*
  ./exgen

No hace falta crear un venv ni ejecutar pip en la máquina destino (salvo que quieras actualizar dependencias).
EOF

find "$STAGE/$NAME/vendor" -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

ARCHIVE="$OUT/${NAME}-portable-linux.tar.gz"
echo "==> Generando $ARCHIVE"
tar -C "$STAGE" -czf "$ARCHIVE" "$NAME"
ls -la "$ARCHIVE"
echo "Listo. Distribuye ese archivo; quien lo use solo instala GTK/PyGObject del sistema y ejecuta ./exgen"
