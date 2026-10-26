import os
import sys
from typing import Optional, Dict, Any

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QFrame, QApplication, QStackedWidget, QWidget
)
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QPixmap, QImage, QDesktopServices

from app.core.streamer import TVCastManager, get_local_ip, get_tailscale_info, get_tailscale_ip


class RemoteAccessDialog(QDialog):
    """
    Diálogo para exibição do endereço de acesso remoto, QR Code e status do servidor local.
    Suporta acesso na rede local (Wi-Fi) e acesso externo seguro via Tailscale (4G/5G).
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Acesso Remoto Familiar - MediaFinder Mobile")
        self.setMinimumWidth(480)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        cast_mgr = TVCastManager.get_instance()
        self.stream_server = cast_mgr.stream_server
        self.port = self.stream_server.start()
        self.local_ip = self.stream_server.host_ip or get_local_ip()
        self.local_url = f"http://{self.local_ip}:{self.port}/"
        self.ip = self.local_ip
        self.url = self.local_url

        self.current_mode = "local"  # "local" ou "tailscale"
        self._init_ui()
        self._refresh_tailscale_state()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(24, 20, 24, 20)

        # Cabeçalho
        header_layout = QHBoxLayout()
        lbl_icon = QLabel("📱")
        lbl_icon.setStyleSheet("font-size: 32px;")
        header_layout.addWidget(lbl_icon)

        title_vbox = QVBoxLayout()
        lbl_title = QLabel("Acesso Remoto Familiar")
        lbl_title.setStyleSheet("font-size: 17px; font-weight: 700; color: #F8FAFC;")
        lbl_sub = QLabel("Acesse no celular ou tablet da família sem instalar servidores externos.")
        lbl_sub.setStyleSheet("font-size: 12px; color: #94A3B8;")
        title_vbox.addWidget(lbl_title)
        title_vbox.addWidget(lbl_sub)
        header_layout.addLayout(title_vbox, 1)

        layout.addLayout(header_layout)

        # Barra de Seleção de Modo (Pills)
        tabs_layout = QHBoxLayout()
        tabs_layout.setSpacing(8)

        self.btn_tab_local = QPushButton("🏠 Em Casa (Wi-Fi Local)")
        self.btn_tab_local.setCheckable(True)
        self.btn_tab_local.setChecked(True)
        self.btn_tab_local.setCursor(Qt.PointingHandCursor)
        self.btn_tab_local.clicked.connect(lambda: self._switch_tab("local"))

        self.btn_tab_tailscale = QPushButton("🚀 Fora de Casa (Tailscale 4G/5G)")
        self.btn_tab_tailscale.setCheckable(True)
        self.btn_tab_tailscale.setChecked(False)
        self.btn_tab_tailscale.setCursor(Qt.PointingHandCursor)
        self.btn_tab_tailscale.clicked.connect(lambda: self._switch_tab("tailscale"))

        tabs_layout.addWidget(self.btn_tab_local, 1)
        tabs_layout.addWidget(self.btn_tab_tailscale, 1)
        layout.addLayout(tabs_layout)

        # Stack de Telas (Aba Local x Aba Tailscale)
        self.stack = QStackedWidget()

        # --- ABA 1: WI-FI LOCAL ---
        self.view_local = self._create_local_view()
        self.stack.addWidget(self.view_local)

        # --- ABA 2: TAILSCALE ---
        self.view_tailscale = self._create_tailscale_view()
        self.stack.addWidget(self.view_tailscale)

        layout.addWidget(self.stack)

        # Rodapé com status e botões
        footer_layout = QHBoxLayout()

        self.lbl_status = QLabel(f"🟢 Servidor ativo na porta {self.port}")
        self.lbl_status.setStyleSheet("font-size: 11px; color: #10B981; font-weight: 500;")
        footer_layout.addWidget(self.lbl_status, 1)

        self.btn_open_browser = QPushButton("Abrir no Navegador")
        self.btn_open_browser.setStyleSheet("""
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
        self.btn_open_browser.clicked.connect(self._open_browser)
        footer_layout.addWidget(self.btn_open_browser)

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
        self._update_tab_styles()

    def _create_local_view(self) -> QWidget:
        widget = QWidget()
        vbox = QVBoxLayout(widget)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(12)

        # Caixa do QR Code
        qr_frame = QFrame()
        qr_frame.setStyleSheet("""
            QFrame {
                background-color: #0F172A;
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 16px;
                padding: 14px;
            }
        """)
        qr_vbox = QVBoxLayout(qr_frame)
        qr_vbox.setAlignment(Qt.AlignCenter)
        qr_vbox.setSpacing(8)

        self.lbl_qr_local = QLabel()
        self.lbl_qr_local.setAlignment(Qt.AlignCenter)
        self.lbl_qr_local.setFixedSize(164, 164)
        self.lbl_qr_local.setStyleSheet("""
            background-color: #FFFFFF;
            border-radius: 12px;
            padding: 6px;
        """)
        self._render_qr(self.local_url, self.lbl_qr_local)
        qr_vbox.addWidget(self.lbl_qr_local, 0, Qt.AlignCenter)

        lbl_scan_hint = QLabel("Aponte a câmera do celular para conectar")
        lbl_scan_hint.setStyleSheet("font-size: 12px; color: #38BDF8; font-weight: 600;")
        lbl_scan_hint.setAlignment(Qt.AlignCenter)
        qr_vbox.addWidget(lbl_scan_hint)

        vbox.addWidget(qr_frame)

        # Caixa de URL e Botão de Copiar
        url_vbox = QVBoxLayout()
        url_vbox.setSpacing(6)
        lbl_url_title = QLabel("Endereço na rede Wi-Fi local:")
        lbl_url_title.setStyleSheet("font-size: 12px; color: #94A3B8;")
        url_vbox.addWidget(lbl_url_title)

        url_hbox = QHBoxLayout()
        url_hbox.setSpacing(8)

        self.txt_url_local = QLineEdit(self.local_url)
        self.txt_url_local.setReadOnly(True)
        self.txt_url_local.setStyleSheet("""
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
        url_hbox.addWidget(self.txt_url_local, 1)

        self.btn_copy_local = QPushButton("Copiar")
        self.btn_copy_local.setStyleSheet(self._button_copy_style())
        self.btn_copy_local.clicked.connect(lambda: self._copy_text(self.local_url, self.btn_copy_local))
        url_hbox.addWidget(self.btn_copy_local)

        url_vbox.addLayout(url_hbox)
        vbox.addLayout(url_vbox)

        # Aliases para compatibilidade com a suite de testes e chamadas diretas
        self.lbl_qr = self.lbl_qr_local
        self.txt_url = self.txt_url_local
        self.btn_copy = self.btn_copy_local

        return widget

    def _copy_url(self):
        self._copy_text(self.local_url, self.btn_copy_local)

    def _create_tailscale_view(self) -> QWidget:
        self.widget_tailscale = QWidget()
        self.vbox_tailscale = QVBoxLayout(self.widget_tailscale)
        self.vbox_tailscale.setContentsMargins(0, 0, 0, 0)
        self.vbox_tailscale.setSpacing(12)

        # Stack interno para alternar entre "Conectado" e "Não Conectado / Como Configurar"
        self.stack_ts_state = QStackedWidget()

        # Estado A: Tailscale Ativo
        self.view_ts_active = QWidget()
        vbox_active = QVBoxLayout(self.view_ts_active)
        vbox_active.setContentsMargins(0, 0, 0, 0)
        vbox_active.setSpacing(12)

        qr_frame = QFrame()
        qr_frame.setStyleSheet("""
            QFrame {
                background-color: #0F172A;
                border: 1px solid rgba(56, 189, 248, 0.25);
                border-radius: 16px;
                padding: 14px;
            }
        """)
        qr_vbox = QVBoxLayout(qr_frame)
        qr_vbox.setAlignment(Qt.AlignCenter)
        qr_vbox.setSpacing(8)

        self.lbl_qr_ts = QLabel()
        self.lbl_qr_ts.setAlignment(Qt.AlignCenter)
        self.lbl_qr_ts.setFixedSize(164, 164)
        self.lbl_qr_ts.setStyleSheet("""
            background-color: #FFFFFF;
            border-radius: 12px;
            padding: 6px;
        """)
        qr_vbox.addWidget(self.lbl_qr_ts, 0, Qt.AlignCenter)

        self.lbl_ts_badge = QLabel("🟢 Conectado ao Tailscale (Rede Segura P2P)")
        self.lbl_ts_badge.setStyleSheet("font-size: 12px; color: #34D399; font-weight: 600;")
        self.lbl_ts_badge.setAlignment(Qt.AlignCenter)
        qr_vbox.addWidget(self.lbl_ts_badge)

        vbox_active.addWidget(qr_frame)

        url_vbox = QVBoxLayout()
        url_vbox.setSpacing(6)
        lbl_url_title = QLabel("Endereço Remoto Seguro (4G/5G ou Qualquer Lugar):")
        lbl_url_title.setStyleSheet("font-size: 12px; color: #94A3B8;")
        url_vbox.addWidget(lbl_url_title)

        url_hbox = QHBoxLayout()
        url_hbox.setSpacing(8)

        self.txt_url_ts = QLineEdit("")
        self.txt_url_ts.setReadOnly(True)
        self.txt_url_ts.setStyleSheet("""
            QLineEdit {
                background-color: #1E293B;
                border: 1px solid rgba(56, 189, 248, 0.3);
                border-radius: 8px;
                color: #38BDF8;
                padding: 8px 12px;
                font-size: 13px;
                font-family: monospace;
                font-weight: 600;
            }
        """)
        url_hbox.addWidget(self.txt_url_ts, 1)

        self.btn_copy_ts = QPushButton("Copiar")
        self.btn_copy_ts.setStyleSheet(self._button_copy_style())
        self.btn_copy_ts.clicked.connect(lambda: self._copy_text(self.txt_url_ts.text(), self.btn_copy_ts))
        url_hbox.addWidget(self.btn_copy_ts)

        url_vbox.addLayout(url_hbox)
        vbox_active.addLayout(url_vbox)

        lbl_ts_tip = QLabel("🔒 Abra o app Tailscale no celular e acesse este link de onde estiver.")
        lbl_ts_tip.setStyleSheet("font-size: 11px; color: #64748B;")
        vbox_active.addWidget(lbl_ts_tip)

        self.stack_ts_state.addWidget(self.view_ts_active)

        # Estado B: Tailscale Inativo / Guia de Configuração Rápida
        self.view_ts_setup = QWidget()
        vbox_setup = QVBoxLayout(self.view_ts_setup)
        vbox_setup.setContentsMargins(0, 0, 0, 0)
        vbox_setup.setSpacing(10)

        card_setup = QFrame()
        card_setup.setStyleSheet("""
            QFrame {
                background-color: #0F172A;
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 14px;
                padding: 16px;
            }
        """)
        vbox_card = QVBoxLayout(card_setup)
        vbox_card.setSpacing(10)

        lbl_setup_title = QLabel("🚀 Acesso Seguro de Qualquer Lugar com Tailscale")
        lbl_setup_title.setStyleSheet("font-size: 14px; font-weight: 700; color: #38BDF8;")
        vbox_card.addWidget(lbl_setup_title)

        lbl_setup_desc = QLabel(
            "O Tailscale cria uma rede privada criptografada (WireGuard) entre seu computador e celulares, "
            "sem abrir portas no roteador e com transmissão direta sem limites de dados."
        )
        lbl_setup_desc.setStyleSheet("font-size: 11px; color: #94A3B8; line-height: 1.4;")
        lbl_setup_desc.setWordWrap(True)
        vbox_card.addWidget(lbl_setup_desc)

        # Passo 1: Instalação
        lbl_step1 = QLabel("<b>Passo 1:</b> Instalar o Tailscale no computador:")
        lbl_step1.setStyleSheet("font-size: 12px; color: #F8FAFC;")
        vbox_card.addWidget(lbl_step1)

        cmd_layout = QHBoxLayout()
        txt_cmd = QLineEdit("curl -fsSL https://tailscale.com/install.sh | sh")
        txt_cmd.setReadOnly(True)
        txt_cmd.setStyleSheet("""
            QLineEdit {
                background-color: #1E293B;
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 6px;
                color: #38BDF8;
                padding: 6px 10px;
                font-size: 11px;
                font-family: monospace;
            }
        """)
        cmd_layout.addWidget(txt_cmd, 1)

        btn_copy_cmd = QPushButton("Copiar")
        btn_copy_cmd.setStyleSheet(self._button_copy_style())
        btn_copy_cmd.clicked.connect(lambda: self._copy_text(txt_cmd.text(), btn_copy_cmd))
        cmd_layout.addWidget(btn_copy_cmd)
        vbox_card.addLayout(cmd_layout)

        # Passo 2: Conectar
        lbl_step2 = QLabel("<b>Passo 2:</b> Ative no terminal com: <code style='color:#38BDF8;'>sudo tailscale up</code>")
        lbl_step2.setStyleSheet("font-size: 12px; color: #F8FAFC;")
        vbox_card.addWidget(lbl_step2)

        # Passo 3: Celular
        lbl_step3 = QLabel("<b>Passo 3:</b> Instale o app <b>Tailscale</b> no celular e faça login com a mesma conta.")
        lbl_step3.setStyleSheet("font-size: 12px; color: #F8FAFC;")
        vbox_card.addWidget(lbl_step3)

        vbox_setup.addWidget(card_setup)

        # Botão de verificar conexão
        btn_check_ts = QPushButton("🔄 Verificar Conexão do Tailscale")
        btn_check_ts.setStyleSheet("""
            QPushButton {
                background-color: #0284C7;
                color: #FFFFFF;
                border-radius: 8px;
                padding: 10px 16px;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #0369A1;
            }
        """)
        btn_check_ts.clicked.connect(self._refresh_tailscale_state)
        vbox_setup.addWidget(btn_check_ts)

        self.stack_ts_state.addWidget(self.view_ts_setup)
        self.vbox_tailscale.addWidget(self.stack_ts_state)

        return self.widget_tailscale

    def _switch_tab(self, mode: str):
        self.current_mode = mode
        if mode == "local":
            self.btn_tab_local.setChecked(True)
            self.btn_tab_tailscale.setChecked(False)
            self.stack.setCurrentIndex(0)
        else:
            self.btn_tab_local.setChecked(False)
            self.btn_tab_tailscale.setChecked(True)
            self.stack.setCurrentIndex(1)
            self._refresh_tailscale_state()
        self._update_tab_styles()

    def _update_tab_styles(self):
        active_style = """
            QPushButton {
                background-color: #0284C7;
                color: #FFFFFF;
                border: 1px solid #38BDF8;
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 12px;
                font-weight: 700;
            }
        """
        inactive_style = """
            QPushButton {
                background-color: #1E293B;
                color: #94A3B8;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 12px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #334155;
                color: #F8FAFC;
            }
        """
        self.btn_tab_local.setStyleSheet(active_style if self.btn_tab_local.isChecked() else inactive_style)
        self.btn_tab_tailscale.setStyleSheet(active_style if self.btn_tab_tailscale.isChecked() else inactive_style)

    def _refresh_tailscale_state(self):
        """Detecta se o Tailscale está ativo e atualiza a interface."""
        info = get_tailscale_info()
        ts_ip = info.get("ip")

        if ts_ip:
            self.stack_ts_state.setCurrentWidget(self.view_ts_active)
            ts_url = f"http://{ts_ip}:{self.port}/"
            self.txt_url_ts.setText(ts_url)
            self.lbl_ts_badge.setText(f"🟢 Tailscale Conectado (IP: {ts_ip})")
            self._render_qr(ts_url, self.lbl_qr_ts)
        else:
            self.stack_ts_state.setCurrentWidget(self.view_ts_setup)

    def _render_qr(self, target_url: str, target_label: QLabel):
        """Gera o QR Code da URL usando a biblioteca qrcode ou fallback elegante."""
        try:
            import qrcode
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_M,
                box_size=6,
                border=2,
            )
            qr.add_data(target_url)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")

            import io
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            qimg = QImage()
            qimg.loadFromData(buf.getvalue(), "PNG")
            pixmap = QPixmap.fromImage(qimg)
            target_label.setPixmap(pixmap.scaled(150, 150, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        except Exception:
            target_label.setText("🌐\nMediaFinder\nMobile")
            target_label.setStyleSheet("""
                background-color: #1E293B;
                color: #38BDF8;
                font-weight: bold;
                border-radius: 12px;
            """)

    def _copy_text(self, text: str, button: QPushButton):
        clipboard = QApplication.clipboard()
        clipboard.setText(text)
        button.setText("✓ Copiado!")
        button.setStyleSheet("""
            QPushButton {
                background-color: #059669;
                color: #FFFFFF;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 11px;
                font-weight: 600;
            }
        """)

    def _open_browser(self):
        target = self.local_url if self.current_mode == "local" else (self.txt_url_ts.text() or self.local_url)
        QDesktopServices.openUrl(QUrl(target))

    def _button_copy_style(self) -> str:
        return """
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
        """
