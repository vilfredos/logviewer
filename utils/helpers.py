from datetime import datetime
import html
import re

def format_timestamp(timestamp, format="%Y-%m-%d %H:%M:%S"):
    """Formatea una marca de tiempo para mostrar"""
    if isinstance(timestamp, datetime):
        return timestamp.strftime(format)
    return "N/A"

def format_filesize(size_bytes, binary=True):
    """
    Formatea un tamaño en bytes a una representación legible
    
    Args:
        size_bytes: Tamaño en bytes
        binary: Si es True, usa base 1024 (KiB, MiB), si es False usa base 1000 (KB, MB)
    """
    if not isinstance(size_bytes, (int, float)) or size_bytes < 0:
        return "0 B"
        
    base = 1024 if binary else 1000
    suffixes = ['B', 'KiB', 'MiB', 'GiB', 'TiB', 'PiB', 'EiB', 'ZiB', 'YiB'] if binary else \
               ['B', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB']
               
    # Calcular el índice del sufijo
    magnitude = 0
    while size_bytes >= base and magnitude < len(suffixes) - 1:
        size_bytes /= base
        magnitude += 1
        
    return f"{size_bytes:.2f} {suffixes[magnitude]}"

def sanitize_input(input_str):
    """
    Sanitiza una cadena de entrada para prevenir XSS y SQL injection
    
    Args:
        input_str: Cadena a sanitizar
    """
    if not input_str:
        return ""
        
    # Escapar caracteres HTML
    escaped = html.escape(str(input_str))
    
    # Eliminar posibles intentos de SQL injection
    escaped = re.sub(r'(\s*([\"\;\'\=\-\#])\s*)', r' \2 ', escaped)
    
    # Limitar longitud
    max_length = 1000
    if len(escaped) > max_length:
        escaped = escaped[:max_length] + "..."
        
    return escaped