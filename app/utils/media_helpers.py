import os
import datetime
from pathlib import Path

# Extensões suportadas por categoria
VIDEO_EXTENSIONS = {
    ".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm", ".m4v",
    ".3gp", ".ts", ".mts", ".m2ts", ".vob", ".ogv", ".rmvb"
}

IMAGE_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tiff", ".tif",
    ".svg", ".ico", ".raw", ".cr2", ".nef", ".arw", ".psd", ".ai", ".eps",
    ".heic", ".heif", ".avif"
}

AUDIO_EXTENSIONS = {
    ".mp3", ".wav", ".flac", ".aac", ".ogg", ".wma", ".m4a", ".opus",
    ".aiff", ".alac", ".mid", ".midi"
}

DOC_EXTENSIONS = {
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    ".txt", ".srt", ".vtt", ".sub", ".zip", ".rar", ".7z", ".tar", ".gz"
}

ALL_MEDIA_EXTENSIONS = VIDEO_EXTENSIONS | IMAGE_EXTENSIONS | AUDIO_EXTENSIONS | DOC_EXTENSIONS

def get_category_for_extension(ext: str) -> str:
    """Retorna a categoria correspondente à extensão."""
    ext = ext.lower()
    if not ext.startswith("."):
        ext = "." + ext
    if ext in VIDEO_EXTENSIONS:
        return "video"
    elif ext in IMAGE_EXTENSIONS:
        return "image"
    elif ext in AUDIO_EXTENSIONS:
        return "audio"
    elif ext in DOC_EXTENSIONS:
        return "document"
    return "other"

def format_file_size(size_bytes: int) -> str:
    """Converte tamanho em bytes para representação legível (KB, MB, GB, TB)."""
    if size_bytes is None or size_bytes < 0:
        return "0 B"
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}" if unit != "B" else f"{int(size_bytes)} B"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"

def format_timestamp(ts: float) -> str:
    """Formata timestamp UNIX para data/hora legível."""
    try:
        dt = datetime.datetime.fromtimestamp(ts)
        return dt.strftime("%d/%m/%Y %H:%M")
    except Exception:
        return "-"

def get_drive_letter(path_str: str) -> str:
    """Retorna a letra do drive em maiúsculo (ex: 'E:', 'F:')."""
    try:
        drive, _ = os.path.splitdrive(path_str)
        return drive.upper() if drive else ""
    except Exception:
        return ""
