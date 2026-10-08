import os
import subprocess
import sys
import shutil
from pathlib import Path

def open_file(file_path: str) -> bool:
    """Abre o arquivo no aplicativo padrão associado no sistema operacional (Linux/Windows/macOS)."""
    try:
        norm_path = os.path.normpath(file_path)
        if not os.path.exists(norm_path):
            return False

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
        print(f"Erro ao abrir arquivo: {e}")
        return False

def reveal_in_explorer(file_path: str) -> bool:
    """Abre o gerenciador de arquivos do sistema com o arquivo selecionado ou na pasta correspondente."""
    try:
        norm_path = os.path.normpath(file_path)
        parent_dir = os.path.dirname(norm_path)
        if not os.path.exists(norm_path) and not os.path.exists(parent_dir):
            return False

        if sys.platform == "win32":
            if os.path.exists(norm_path):
                subprocess.Popen(f'explorer /select,"{norm_path}"')
            elif os.path.exists(parent_dir):
                subprocess.Popen(["explorer", parent_dir])
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
        print(f"Erro ao abrir gerenciador de arquivos: {e}")
        return False

def is_path_accessible(path_str: str) -> bool:
    """Verifica se o caminho/unidade está acessível e online no momento."""
    try:
        return os.path.exists(path_str)
    except Exception:
        return False

