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
    """Retorna a letra da unidade (Windows, ex: 'E:') ou o rótulo do ponto de montagem (Linux)."""
    try:
        norm_p = os.path.normpath(path_str)
        
        # Detecção de letra de unidade estilo Windows (mesmo se executado no Linux)
        if len(norm_p) >= 2 and norm_p[1] == ":" and norm_p[0].isalpha():
            return norm_p[:2].upper()

        drive, _ = os.path.splitdrive(norm_p)
        if drive:
            return drive.upper()

        # Detecção de discos e partições montadas no Linux / Regata OS
        parts = Path(norm_p).parts
        if len(parts) >= 5 and parts[1] == "run" and parts[2] == "media":
            # /run/media/usuario/NOME_DO_DISCO
            return parts[4]
        elif len(parts) >= 3 and parts[1] == "media":
            # /media/usuario/DISCO ou /media/DISCO
            return parts[3] if len(parts) >= 4 else parts[2]
        elif len(parts) >= 3 and parts[1] == "mnt":
            return parts[2]
        elif len(parts) >= 3 and parts[1] == "home":
            return "Home"
        elif len(parts) >= 2:
            return "/"
        return ""
    except Exception:
        return ""


def resolve_poster_source(data: dict) -> tuple:
    """
    Identifica a origem da imagem do pôster ou logo para uma mídia.
    Retorna (caminho_ou_url, is_remote).
    Se for arquivo local existente no disco, is_remote será False.
    Se for URL remota (http/https), is_remote será True.
    Se não houver pôster, retorna (None, False).
    """
    if not data or not isinstance(data, dict):
        return None, False

    import re
    from app.core.metadata import get_posters_dir

    posters_dir = get_posters_dir()

    # 1. Pôster salvo em disco pelo ID do arquivo (numérico ou alfanumérico como pluto_xxx/iptv_xxx)
    file_id = data.get("id") or data.get("file_id")
    if file_id is not None:
        cand = posters_dir / f"{file_id}.jpg"
        if cand.is_file() and cand.stat().st_size > 0:
            return str(cand), False

    # 2. poster_local (rota /api/media/{id}/poster ou caminho absoluto)
    poster_local = data.get("poster_local")
    if poster_local and isinstance(poster_local, str):
        match = re.search(r"/api/media/(\d+)/poster", poster_local)
        if match:
            cand = posters_dir / f"{match.group(1)}.jpg"
            if cand.is_file() and cand.stat().st_size > 0:
                return str(cand), False
        elif os.path.isfile(poster_local) and os.path.getsize(poster_local) > 0:
            return poster_local, False

    # 3. Arquivo de imagem do usuário (fotos/wallpapers)
    if data.get("category") == "image":
        img_path = data.get("path")
        if img_path and os.path.isfile(img_path) and os.path.getsize(img_path) > 0:
            return img_path, False

    # 4. URLs remotas ou caminhos específicos (prioridade para thumbnail e poster_url antes de logo)
    for key in ("poster_url", "thumbnail", "featured_image", "logo", "backdrop_url"):
        val = data.get(key)
        if val and isinstance(val, str):
            val_clean = val.strip()
            if val_clean.startswith(("http://", "https://")):
                return val_clean, True
            elif os.path.isfile(val_clean) and os.path.getsize(val_clean) > 0:
                return val_clean, False

    return None, False

