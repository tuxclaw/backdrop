"""Bounded, orientation-aware image decoding for background workers."""
from pathlib import Path

import gi

gi.require_version('GdkPixbuf', '2.0')
from gi.repository import GdkPixbuf

from backdrop.core import EXTENSIONS


def supported_extensions() -> frozenset[str]:
    available = {'.' + ext.lower() for fmt in GdkPixbuf.Pixbuf.get_formats() for ext in fmt.get_extensions()}
    return EXTENSIONS & available


def decode(path: Path, size: int) -> tuple[GdkPixbuf.Pixbuf, str]:
    info = GdkPixbuf.Pixbuf.get_file_info(str(path))
    if info is None or info[0] is None:
        raise ValueError('Unreadable image')
    _, width, height = info
    pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(str(path), size, size, True)
    orientation = pixbuf.get_option('orientation')
    if orientation in {'5', '6', '7', '8'}:
        width, height = height, width
    return pixbuf.apply_embedded_orientation(), f'{width:,} × {height:,}'
