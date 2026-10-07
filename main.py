import sys
import os

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QFont

from app.ui.main_window import MainWindow
from app.ui.styles import DARK_THEME_QSS

def main():
    # Habilita suporte a High-DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("MediaFinder")
    app.setApplicationDisplayName("MediaFinder — Buscador Rápido de Mídias")

    # Define ícone da aplicação
    icon_path = os.path.join(os.path.dirname(__file__), "assets", "icon.png")
    if os.path.exists(icon_path):
        app_icon = QIcon(icon_path)
        app.setWindowIcon(app_icon)

    # Fonte padrão moderna
    font = QFont("Segoe UI", 10)
    app.setFont(font)

    # Aplica tema escuro
    app.setStyleSheet(DARK_THEME_QSS)

    window = MainWindow()
    if os.path.exists(icon_path):
        window.setWindowIcon(QIcon(icon_path))
    window.show()


    sys.exit(app.exec())

if __name__ == "__main__":
    main()
