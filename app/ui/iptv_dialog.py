import os
from typing import Optional

from PySide6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QFileDialog, QFrame, QMessageBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon

from app.core.iptv import IPTVService


class ImportM3UDialog(QDialog):
    """Diálogo moderno para importação e configuração de lista M3U personalizada (URL ou arquivo local)."""

    playlist_updated = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("📺 Configurar Lista IPTV Personalizada — MediaFinder")
        self.resize(580, 360)
        self.setMinimumSize(500, 320)

        self.service = IPTVService.get_instance()
        current_url, current_name = self.service.get_custom_config()

        self._init_ui(current_url, current_name)

    def _init_ui(self, current_url: str, current_name: str):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(18, 18, 18, 18)
        main_layout.setSpacing(14)

        # Cabeçalho
        header_frame = QFrame()
        header_frame.setStyleSheet(
            "background-color: #12151B; border: 1px solid #242A34; border-radius: 8px; padding: 8px;"
        )
        h_layout = QVBoxLayout(header_frame)
        h_layout.setContentsMargins(10, 8, 10, 8)
        h_layout.setSpacing(4)

        lbl_title = QLabel("📡 Importar Playlist IPTV / M3U")
        lbl_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #38BDF8;")
        h_layout.addWidget(lbl_title)

        lbl_desc = QLabel(
            "Cole a URL de uma lista M3U externa (GitHub, servidor Xtream Codes) ou escolha um arquivo .m3u / .m3u8 local no seu computador."
        )
        lbl_desc.setStyleSheet("font-size: 12px; color: #94A3B8;")
        lbl_desc.setWordWrap(True)
        h_layout.addWidget(lbl_desc)
        main_layout.addWidget(header_frame)

        # Campo: Nome da Lista
        lbl_name = QLabel("Nome de Identificação da Lista:")
        lbl_name.setStyleSheet("font-size: 12px; font-weight: bold; color: #E2E8F0;")
        main_layout.addWidget(lbl_name)

        self.txt_name = QLineEdit()
        self.txt_name.setPlaceholderText("Ex: Minha Lista de Filmes & Séries")
        self.txt_name.setText(current_name or "Minha Lista M3U")
        self.txt_name.setStyleSheet(
            "background-color: #1A1F29; color: #F8FAFC; border: 1px solid #334155; border-radius: 6px; padding: 8px;"
        )
        main_layout.addWidget(self.txt_name)

        # Campo: URL ou Arquivo Local
        lbl_source = QLabel("URL Web ou Arquivo Local (.m3u / .m3u8):")
        lbl_source.setStyleSheet("font-size: 12px; font-weight: bold; color: #E2E8F0;")
        main_layout.addWidget(lbl_source)

        source_row = QHBoxLayout()
        source_row.setSpacing(8)

        self.txt_url_path = QLineEdit()
        self.txt_url_path.setPlaceholderText("https://.../lista.m3u ou /home/usuario/minha_lista.m3u")
        self.txt_url_path.setText(current_url)
        self.txt_url_path.setStyleSheet(
            "background-color: #1A1F29; color: #F8FAFC; border: 1px solid #334155; border-radius: 6px; padding: 8px;"
        )
        source_row.addWidget(self.txt_url_path, 1)

        btn_browse = QPushButton("📁 Procurar...")
        btn_browse.setStyleSheet(
            "background-color: #334155; color: #F8FAFC; font-weight: bold; padding: 8px 14px; border-radius: 6px;"
        )
        btn_browse.clicked.connect(self._browse_file)
        source_row.addWidget(btn_browse)
        main_layout.addLayout(source_row)

        # Label de status / resultado
        self.lbl_status = QLabel("")
        self.lbl_status.setStyleSheet("font-size: 12px; padding: 4px;")
        self.lbl_status.setWordWrap(True)
        main_layout.addWidget(self.lbl_status)

        main_layout.addStretch(1)

        # Botões de Ação
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        btn_row.addStretch(1)

        btn_cancel = QPushButton("Cancelar")
        btn_cancel.setStyleSheet(
            "background-color: #1E293B; color: #94A3B8; padding: 8px 16px; border-radius: 6px;"
        )
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_cancel)

        self.btn_save = QPushButton("💾 Salvar e Carregar Lista")
        self.btn_save.setStyleSheet(
            "background-color: #0284C7; color: #FFFFFF; font-weight: bold; padding: 8px 18px; border-radius: 6px;"
        )
        self.btn_save.clicked.connect(self._save_and_load)
        btn_row.addWidget(self.btn_save)

        main_layout.addLayout(btn_row)

    def _browse_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Selecionar Arquivo de Playlist M3U",
            "",
            "Listas M3U (*.m3u *.m3u8 *.txt);;Todos os Arquivos (*.*)"
        )
        if file_path:
            self.txt_url_path.setText(file_path)
            if not self.txt_name.text() or self.txt_name.text() == "Minha Lista M3U":
                base_name = os.path.splitext(os.path.basename(file_path))[0]
                self.txt_name.setText(base_name.capitalize())

    def _save_and_load(self):
        url_or_path = self.txt_url_path.text().strip()
        name = self.txt_name.text().strip() or "Minha Lista M3U"

        if not url_or_path:
            self.lbl_status.setStyleSheet("color: #F87171; font-weight: bold;")
            self.lbl_status.setText("⚠️ Por favor, insira uma URL ou selecione um arquivo.")
            return

        self.btn_save.setEnabled(False)
        self.lbl_status.setStyleSheet("color: #38BDF8;")
        self.lbl_status.setText("⏳ Processando e carregando canais da lista...")
        self.repaint()

        ok, count, msg = self.service.set_custom_source(url_or_path, name)
        self.btn_save.setEnabled(True)

        if ok:
            self.lbl_status.setStyleSheet("color: #4ADE80; font-weight: bold;")
            self.lbl_status.setText(f"✓ {msg}")
            self.playlist_updated.emit("custom")
            QMessageBox.information(
                self,
                "Lista IPTV Carregada",
                f"A lista '{name}' foi configurada com sucesso!\nForam carregados {count} canais ao vivo."
            )
            self.accept()
        else:
            self.lbl_status.setStyleSheet("color: #F87171; font-weight: bold;")
            self.lbl_status.setText(f"❌ {msg}")
