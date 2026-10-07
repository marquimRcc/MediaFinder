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
    print("=" * 60)
    print("🚀 Iniciando compilação do MediaFinder para Windows (.exe)...")
    print("=" * 60)

    # Comando PyInstaller com ícone personalizado
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name=MediaFinder",
        "--noconsole",          # Sem janela preta de terminal
        "--onefile",            # Gera um único arquivo .exe independente
        "--noconfirm",          # Sobrescreve sem perguntar
        "--icon=assets/icon.ico", # Ícone personalizado do executável
        "--add-data=assets;assets",
        "--collect-all=PySide6",
        "--collect-all=PIL",
        "main.py"
    ]



    print(f"Executando comando: {' '.join(cmd)}\n")
    result = subprocess.run(cmd)

    if result.returncode == 0:
        exe_path = os.path.abspath(os.path.join("dist", "MediaFinder.exe"))
        print("\n" + "=" * 60)
        print("🎉 COMPILAÇÃO CONCLUÍDA COM SUCESSO!")
        print(f"📁 O executável foi gerado em: {exe_path}")
        print("=" * 60)
    else:
        print("\n❌ Ocorreu um erro durante a compilação.")

if __name__ == "__main__":
    build()
