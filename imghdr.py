"""
Compatibilidad local para el módulo imghdr eliminado en Python 3.13.
Este módulo detecta el tipo de imagen a partir de sus cabeceras.
"""

import os

def what(file, h=None):
    """
    Devuelve el tipo de imagen detectado ('jpeg', 'png', 'gif', 'bmp') o None.
    file: ruta o archivo en bytes.
    h: contenido binario opcional (primeros bytes del archivo).
    """
    if h is None:
        if isinstance(file, (str, bytes, os.PathLike)):
            try:
                with open(file, 'rb') as f:
                    h = f.read(32)
            except Exception:
                return None
        else:
            return None

    # JPEG
    if h.startswith(b'\xff\xd8'):
        return 'jpeg'

    # PNG
    if h.startswith(b'\x89PNG\r\n\x1a\n'):
        return 'png'

    # GIF
    if h.startswith(b'GIF8'):
        return 'gif'

    # BMP
    if h.startswith(b'BM'):
        return 'bmp'

    # WEBP
    if h.startswith(b'RIFF') and b'WEBP' in h[8:16]:
        return 'webp'

    # ICO
    if len(h) > 4 and h[0:4] == b'\x00\x00\x01\x00':
        return 'ico'

    return None
