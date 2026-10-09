"""
Script para compilar o MediaFinder em um Executável (.exe) do Windows usando PyInstaller.
Execute: python build_exe.py
"""

import os
import sys
import subprocess
import shutil

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def build():
    is_windows = sys.platform == "win32"
    platform_name = "Windows (.exe)" if is_windows else "Linux"
    print("=" * 60)
    print(f"🚀 Iniciando compilação do MediaFinder para {platform_name}...")
    print("=" * 60)

    sep = ";" if is_windows else ":"
    icon_file = "assets/icon.ico" if is_windows else "assets/icon.png"

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name=MediaFinder",
        "--noconsole",
        "--onefile",
        "--noconfirm",
        f"--icon={icon_file}",
        f"--add-data=assets{sep}assets",
        # Inclui apenas os submódulos PySide6 utilizados pelo MediaFinder
        "--collect-submodules=PySide6.QtCore",
        "--collect-submodules=PySide6.QtGui",
        "--collect-submodules=PySide6.QtWidgets",
        "--collect-submodules=PySide6.QtMultimedia",
        "--collect-submodules=PySide6.QtMultimediaWidgets",
        # Exclui bibliotecas pesadas e desnecessárias para reduzir drasticamente o tamanho do binário
        "--exclude-module=PySide6.QtWebEngineCore",
        "--exclude-module=PySide6.QtWebEngineWidgets",
        "--exclude-module=PySide6.Qt3DCore",
        "--exclude-module=PySide6.Qt3DRender",
        "--exclude-module=PySide6.QtQuick",
        "--exclude-module=PySide6.QtQml",
        "--exclude-module=PySide6.QtDesigner",
        "--exclude-module=PySide6.QtSql",
        "--exclude-module=PySide6.QtTest",
        "--exclude-module=PySide6.QtPdf",
        "--collect-all=PIL",
        "main.py"
    ]

    print(f"Executando comando: {' '.join(cmd)}\n")
    result = subprocess.run(cmd)

    if result.returncode == 0:
        binary_name = "MediaFinder.exe" if is_windows else "MediaFinder"
        exe_path = os.path.abspath(os.path.join("dist", binary_name))
        print("\n" + "=" * 60)
        print("🎉 COMPILAÇÃO CONCLUÍDA COM SUCESSO!")
        print(f"📁 O binário foi gerado em: {exe_path}")
        print("=" * 60)
    else:
        print("\n❌ Ocorreu um erro durante a compilação.")


if __name__ == "__main__":
    build()
