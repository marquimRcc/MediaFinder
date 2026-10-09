import os
import sys
from typing import Optional

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QFrame, QApplication
)
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QPixmap, QImage, QDesktopServices

from app.core.streamer import TVCastManager, get_local_ip


class RemoteAccessDialog(QDialog):
    """
    Diálogo para exibição do endereço de acesso remoto, QR Code e status do servidor local.
    Permite que Marcos, Esposa ou Filhos acessem o MediaFinder no smartphone sem instalar nada.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Acesso Remoto Familiar - MediaFinder Mobile")
        self.setMinimumWidth(440)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        cast_mgr = TVCastManager.get_instance()
        self.stream_server = cast_mgr.stream_server
        self.port = self.stream_server.start()
        self.ip = self.stream_server.host_ip or get_local_ip()
        self.url = f"http://{self.ip}:{self.port}/"

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        # Cabeçalho
        header_layout = QHBoxLayout()
        lbl_icon = QLabel("📱")
        lbl_icon.setStyleSheet("font-size: 32px;")
        header_layout.addWidget(lbl_icon)

        title_vbox = QVBoxLayout()
        lbl_title = QLabel("Acesso Remoto Familiar")
        lbl_title.setStyleSheet("font-size: 17px; font-weight: 700; color: #F8FAFC;")
        lbl_sub = QLabel("Use no smartphone ou tablet da família sem instalar nada.")
        lbl_sub.setStyleSheet("font-size: 12px; color: #94A3B8;")
        title_vbox.addWidget(lbl_title)
        title_vbox.addWidget(lbl_sub)
        header_layout.addLayout(title_vbox, 1)

        layout.addLayout(header_layout)

        # Caixa do QR Code
        qr_frame = QFrame()
        qr_frame.setStyleSheet("""
            QFrame {
                background-color: #0F172A;
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 16px;
                padding: 16px;
            }
        """)
        qr_vbox = QVBoxLayout(qr_frame)
        qr_vbox.setAlignment(Qt.AlignCenter)
        qr_vbox.setSpacing(10)

        self.lbl_qr = QLabel()
        self.lbl_qr.setAlignment(Qt.AlignCenter)
        self.lbl_qr.setFixedSize(180, 180)
        self.lbl_qr.setStyleSheet("""
            background-color: #FFFFFF;
            border-radius: 12px;
            padding: 8px;
        """)

        self._render_qr_code()
        qr_vbox.addWidget(self.lbl_qr, 0, Qt.AlignCenter)

        lbl_scan_hint = QLabel("Aponte a câmera do celular para conectar")
        lbl_scan_hint.setStyleSheet("font-size: 12px; color: #38BDF8; font-weight: 600;")
        lbl_scan_hint.setAlignment(Qt.AlignCenter)
        qr_vbox.addWidget(lbl_scan_hint)

        layout.addWidget(qr_frame)

        # Caixa de URL e Botão de Copiar
        url_vbox = QVBoxLayout()
        url_vbox.setSpacing(6)
        lbl_url_title = QLabel("Endereço na rede local (Wi-Fi):")
        lbl_url_title.setStyleSheet("font-size: 12px; color: #94A3B8;")
        url_vbox.addWidget(lbl_url_title)

        url_hbox = QHBoxLayout()
        url_hbox.setSpacing(8)

        self.txt_url = QLineEdit(self.url)
        self.txt_url.setReadOnly(True)
        self.txt_url.setStyleSheet("""
            QLineEdit {
                background-color: #1E293B;
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 8px;
                color: #F8FAFC;
                padding: 8px 12px;
                font-size: 13px;
                font-family: monospace;
            }
        """)
        url_hbox.addWidget(self.txt_url, 1)

        self.btn_copy = QPushButton("Copiar")
        self.btn_copy.setStyleSheet("""
            QPushButton {
                background-color: #334155;
                color: #F8FAFC;
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 8px;
                padding: 8px 14px;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #475569;
            }
        """)
        self.btn_copy.clicked.connect(self._copy_url)
        url_hbox.addWidget(self.btn_copy)

        url_vbox.addLayout(url_hbox)
        layout.addLayout(url_vbox)

        # Rodapé com ações e status
        footer_layout = QHBoxLayout()
        
        lbl_status = QLabel(f"🟢 Servidor ativo na porta {self.port}")
        lbl_status.setStyleSheet("font-size: 11px; color: #10B981; font-weight: 500;")
        footer_layout.addWidget(lbl_status, 1)

        btn_open_browser = QPushButton("Abrir no Navegador")
        btn_open_browser.setStyleSheet("""
            QPushButton {
                background-color: #2563EB;
                color: #FFFFFF;
                border-radius: 8px;
                padding: 8px 14px;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #1D4ED8;
            }
        """)
        btn_open_browser.clicked.connect(self._open_browser)
        footer_layout.addWidget(btn_open_browser)

        btn_close = QPushButton("Fechar")
        btn_close.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #94A3B8;
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 8px;
                padding: 8px 14px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.05);
                color: #F8FAFC;
            }
        """)
        btn_close.clicked.connect(self.accept)
        footer_layout.addWidget(btn_close)

        layout.addLayout(footer_layout)

    def _render_qr_code(self):
        """Gera o QR Code da URL usando a biblioteca qrcode ou fallback elegante."""
        try:
            import qrcode
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_M,
                box_size=6,
                border=2,
            )
            qr.add_data(self.url)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")

            import io
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            qimg = QImage()
            qimg.loadFromData(buf.getvalue(), "PNG")
            pixmap = QPixmap.fromImage(qimg)
            self.lbl_qr.setPixmap(pixmap.scaled(164, 164, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        except Exception:
            self.lbl_qr.setText("🌐\nMediaFinder\nMobile")
            self.lbl_qr.setStyleSheet("""
                background-color: #1E293B;
                color: #38BDF8;
                font-weight: bold;
                border-radius: 12px;
            """)

    def _copy_url(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(self.url)
        self.btn_copy.setText("✓ Copiado!")
        self.btn_copy.setStyleSheet("""
            QPushButton {
                background-color: #059669;
                color: #FFFFFF;
                border-radius: 8px;
                padding: 8px 14px;
                font-size: 12px;
                font-weight: 600;
            }
        """)

    def _open_browser(self):
        QDesktopServices.openUrl(QUrl(self.url))
