"""
Script para criar o atalho do MediaFinder na Área de Trabalho do Windows.
"""

import os
import sys
import subprocess
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def create_shortcut():
    # Caminho do executável compilado ou fallback para o batch
    exe_path = os.path.abspath(os.path.join("dist", "MediaFinder.exe"))
    ico_path = os.path.abspath(os.path.join("assets", "icon.ico"))
    working_dir = os.path.abspath(".")

    # Detecta pasta da Área de Trabalho (suporte a OneDrive e local padrão)
    desktop_dirs = [
        os.path.join(os.path.expanduser("~"), "OneDrive", "Desktop"),
        os.path.join(os.path.expanduser("~"), "Desktop"),
        os.path.join(os.environ.get("USERPROFILE", ""), "Desktop")
    ]
    
    target_desktop = None
    for d in desktop_dirs:
        if os.path.exists(d):
            target_desktop = d
            break
            
    if not target_desktop:
        target_desktop = desktop_dirs[1] # fallback

    shortcut_path = os.path.join(target_desktop, "MediaFinder.lnk")

    # Script PowerShell para criar o arquivo .lnk nativo do Windows
    ps_command = f"""
    $WshShell = New-Object -ComObject WScript.Shell
    $Shortcut = $WshShell.CreateShortcut('{shortcut_path}')
    $Shortcut.TargetPath = '{exe_path}'
    $Shortcut.WorkingDirectory = '{working_dir}'
    $Shortcut.IconLocation = '{ico_path}, 0'
    $Shortcut.Description = 'MediaFinder — Buscador Rápido de Mídias Multi-HD'
    $Shortcut.Save()
    """

    try:
        subprocess.run(["powershell", "-NoProfile", "-Command", ps_command], check=True)
        print(f"✓ Atalho criado na Área de Trabalho com sucesso:")
        print(f"  👉 {shortcut_path}")
        return True
    except Exception as e:
        print(f"Erro ao criar atalho via PowerShell: {e}")
        return False

if __name__ == "__main__":
    create_shortcut()
