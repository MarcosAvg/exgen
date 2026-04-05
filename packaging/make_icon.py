#!/usr/bin/env python3
"""Genera un PNG cuadrado para un .desktop (solo biblioteca estándar)."""
from __future__ import annotations

import struct
import zlib
from pathlib import Path


def _chunk(chunk_type: bytes, data: bytes) -> bytes:
    crc = zlib.crc32(chunk_type + data) & 0xFFFFFFFF
    return struct.pack(">I", len(data)) + chunk_type + data + struct.pack(">I", crc)


def write_simple_png(
    path: Path,
    size: int = 256,
    rgb: tuple[int, int, int] = (0x35, 0x7D, 0xFF),
) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    r, g, b = rgb
    row = b"\x00" + bytes([r, g, b] * size)
    raw = row * size
    ihdr = struct.pack(">2I5B", size, size, 8, 2, 0, 0, 0)
    png = (
        b"\x89PNG\r\n\x1a\n"
        + _chunk(b"IHDR", ihdr)
        + _chunk(b"IDAT", zlib.compress(raw, 9))
        + _chunk(b"IEND", b"")
    )
    path.write_bytes(png)


if __name__ == "__main__":
    import sys

    out = Path(sys.argv[1] if len(sys.argv) > 1 else "icon.png")
    write_simple_png(out)
    print(out)
