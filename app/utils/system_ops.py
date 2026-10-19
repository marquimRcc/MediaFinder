import os
import subprocess
import sys
import shutil
import logging
from pathlib import Path
from typing import Optional, List

logger = logging.getLogger("MediaFinder.SystemOps")

DANGEROUS_EXECUTABLE_EXTENSIONS = {
    # Windows
    ".exe", ".bat", ".cmd", ".com", ".scr", ".pif", ".msi", ".msp", ".vbs",
    ".vbe", ".js", ".jse", ".wsf", ".wsh", ".ps1", ".ps1xml", ".ps2", ".ps2xml",
    ".psc1", ".psc2", ".msc", ".hta", ".cpl", ".reg",
    # Linux / Unix
    ".sh", ".bash", ".zsh", ".csh", ".ksh", ".bin", ".run", ".appimage",
    ".desktop", ".service", ".apk", ".deb", ".rpm"
}

def is_dangerous_file(file_path: str) -> bool:
    """Verifica se a extensão do arquivo representa risco de execução de código no SO."""
    ext = os.path.splitext(file_path)[1].lower()
    return ext in DANGEROUS_EXECUTABLE_EXTENSIONS

def open_file(file_path: str, fallback_urls: Optional[List[str]] = None, title: Optional[str] = None) -> bool:
    """
    Abre o arquivo no aplicativo padrão associado no sistema operacional (Linux/Windows/macOS),
    ou reproduz fluxos de rede (HTTP/HTTPS/HLS) com suporte a failover de múltiplas fontes.
    Bloqueia a execução direta de binários e scripts potencialmente perigosos por segurança,
    redirecionando para o gerenciador de arquivos (reveal_in_explorer).
    """
    try:
        # Suporte a URLs de streaming e transmissões ao vivo
        if file_path.startswith(("http://", "https://")):
            all_urls = [file_path]
            if fallback_urls:
                for u in fallback_urls:
                    if u and u not in all_urls:
                        all_urls.append(u)

            # MPV suporta passar múltiplos links sequenciais para failover automático
            if shutil.which("mpv"):
                args = ["mpv"]
                if title:
                    args.append(f"--title={title}")
                args.extend(all_urls)
                subprocess.Popen(args)
                return True

            # VLC suporta abrir playlist temporária com múltiplas fontes
            if shutil.which("vlc"):
                if len(all_urls) > 1:
                    import tempfile
                    with tempfile.NamedTemporaryFile("w", suffix=".m3u8", delete=False, encoding="utf-8") as f:
                        f.write("#EXTM3U\n")
                        ch_title = title or "Canal Ao Vivo"
                        for i, u in enumerate(all_urls, 1):
                            f.write(f"#EXTINF:-1,{ch_title} (Fonte {i})\n{u}\n")
                        tmp_playlist = f.name
                    subprocess.Popen(["vlc", tmp_playlist])
                    return True
                else:
                    subprocess.Popen(["vlc", file_path])
                    return True

            if sys.platform == "win32":
                os.startfile(file_path)
                return True
            elif sys.platform == "darwin":
                subprocess.Popen(["open", file_path])
                return True
            else:
                subprocess.Popen(["xdg-open", file_path])
                return True

        norm_path = os.path.normpath(file_path)
        if not os.path.exists(norm_path):
            return False

        if is_dangerous_file(norm_path):
            # Por segurança, nunca executa binários/scripts diretamente do buscador
            return reveal_in_explorer(norm_path)

        if sys.platform == "win32":
            os.startfile(norm_path)
            return True
        elif sys.platform == "darwin":
            subprocess.Popen(["open", norm_path])
            return True
        else:
            # Linux / Regata OS / BSD
            subprocess.Popen(["xdg-open", norm_path])
            return True
    except Exception as e:
        logger.error(f"Erro ao abrir arquivo: {e}")
        return False

def reveal_in_explorer(file_path: str) -> bool:
    """Abre o gerenciador de arquivos do sistema com o arquivo selecionado ou na pasta correspondente."""
    try:
        norm_path = os.path.normpath(file_path)
        parent_dir = os.path.dirname(norm_path)
        if not os.path.exists(norm_path) and not os.path.exists(parent_dir):
            return False

        if sys.platform == "win32":
            clean_path = norm_path.replace('"', '')
            if os.path.exists(clean_path):
                subprocess.Popen(["explorer", f'/select,{clean_path}'])
            elif os.path.exists(parent_dir):
                subprocess.Popen(["explorer", parent_dir.replace('"', '')])
            return True
        elif sys.platform == "darwin":
            if os.path.exists(norm_path):
                subprocess.Popen(["open", "-R", norm_path])
            elif os.path.exists(parent_dir):
                subprocess.Popen(["open", parent_dir])
            return True
        else:
            # Linux / Regata OS (KDE Dolphin, GNOME Nautilus, etc.)
            if os.path.exists(norm_path):
                if shutil.which("dolphin"):
                    subprocess.Popen(["dolphin", "--select", norm_path])
                    return True
                elif shutil.which("nautilus"):
                    subprocess.Popen(["nautilus", "--select", norm_path])
                    return True
                elif shutil.which("nemo"):
                    subprocess.Popen(["nemo", norm_path])
                    return True
                elif shutil.which("thunar"):
                    subprocess.Popen(["thunar", parent_dir])
                    return True

            target_dir = parent_dir if os.path.exists(parent_dir) else norm_path
            subprocess.Popen(["xdg-open", target_dir])
            return True
    except Exception as e:
        logger.error(f"Erro ao abrir gerenciador de arquivos: {e}")
        return False

def is_path_accessible(path_str: str) -> bool:
    """Verifica se o caminho/unidade está acessível e online no momento."""
    try:
        return os.path.exists(path_str)
    except Exception:
        return False

