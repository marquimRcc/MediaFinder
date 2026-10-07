import os
import subprocess
import sys
from pathlib import Path

def open_file(file_path: str) -> bool:
    """Abre o arquivo no aplicativo padrão associado no Windows."""
    try:
        norm_path = os.path.normpath(file_path)
        if not os.path.exists(norm_path):
            return False
        os.startfile(norm_path)
        return True
    except Exception as e:
        print(f"Erro ao abrir arquivo: {e}")
        return False

def reveal_in_explorer(file_path: str) -> bool:
    """Abre o Windows Explorer com o arquivo específico selecionado/destacado."""
    try:
        norm_path = os.path.normpath(file_path)
        if not os.path.exists(norm_path):
            # Se o arquivo não existe, tenta abrir o diretório pai se existir
            parent_dir = os.path.dirname(norm_path)
            if os.path.exists(parent_dir):
                subprocess.Popen(["explorer", parent_dir])
                return True
            return False

        # explorer /select,"C:\caminho\do\arquivo.mp4"
        subprocess.Popen(f'explorer /select,"{norm_path}"')
        return True
    except Exception as e:
        print(f"Erro ao abrir explorer: {e}")
        return False

def is_path_accessible(path_str: str) -> bool:
    """Verifica se o caminho/unidade está acessível e online no momento."""
    try:
        return os.path.exists(path_str)
    except Exception:
        return False
