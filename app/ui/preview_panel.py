import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional
from PIL import Image

# Limite de segurança de descompressão de pixels para evitar DoS/OOM por imagens maliciosas
Image.MAX_IMAGE_PIXELS = 80_000_000

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QApplication, QMessageBox
)
from PySide6.QtCore import Qt, QSize, QThread, Signal
from PySide6.QtGui import QPixmap, QImage, QClipboard

from app.utils.system_ops import open_file, reveal_in_explorer
from app.utils.media_helpers import format_file_size, format_timestamp, resolve_poster_source


class ImageLoaderThread(QThread):
    """Carrega miniaturas de imagens e pôsteres em segundo plano com proteções de segurança."""
    image_loaded = Signal(str, QPixmap, str) # (path_or_url, pixmap, resolution_str)

    def __init__(self, target: str, max_size: QSize, parent=None):
        super().__init__(parent)
        self.target = target
        self.max_size = max_size

    def run(self):
        try:
            import io
            import urllib.request
            img = None

            if self.target.startswith(("http://", "https://")):
                req = urllib.request.Request(
                    self.target,
                    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) MediaFinder/1.0"}
                )
                with urllib.request.urlopen(req, timeout=6.0) as resp:
                    raw_data = resp.read()
                    img = Image.open(io.BytesIO(raw_data))
            elif os.path.isfile(self.target):
                img = Image.open(self.target)
            else:
                return

            with img:
                orig_w, orig_h = img.size
                res_str = f"{orig_w} × {orig_h} px"
                
                # Gera thumbnail mantendo proporção
                img.thumbnail((self.max_size.width(), self.max_size.height()), Image.Resampling.LANCZOS)
                
                # Converte para formato compatível com QImage
                if img.mode not in ("RGB", "RGBA"):
                    img = img.convert("RGBA")
                
                data = img.tobytes("raw", img.mode)
                qformat = QImage.Format_RGBA8888 if img.mode == "RGBA" else QImage.Format_RGB888
                qimg = QImage(data, img.width, img.height, img.width * (4 if img.mode == "RGBA" else 3), qformat)
                pixmap = QPixmap.fromImage(qimg)
                
                self.image_loaded.emit(self.target, pixmap, res_str)
        except (Image.DecompressionBombError, Image.DecompressionBombWarning):
            # Imagem excede os limites de segurança de memória
            pass
        except Exception:
            pass

class PreviewPanel(QFrame):
    """Painel lateral de prévia de imagem, metadados e ações rápidas."""

    close_requested = Signal()  # Emitido quando o usuário clica no ✕ do painel
    cast_requested = Signal(str)  # Emitido com o file_path para transmitir para TV

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("preview_panel")
        self.setMinimumWidth(220)  # Flexível para telas estreitas
        self.setMaximumWidth(420)
        
        self.current_file_data: Optional[Dict[str, Any]] = None
        self._loader_thread: Optional[ImageLoaderThread] = None

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # Header do Painel com Título e Botão Fechar
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)

        lbl_title = QLabel("👁️ Prévia & Detalhes")
        lbl_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #38BDF8;")
        header_layout.addWidget(lbl_title, 1)

        btn_close_panel = QPushButton("✕")
        btn_close_panel.setToolTip("Ocultar painel de prévia")
        btn_close_panel.setFixedSize(24, 24)
        btn_close_panel.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: #94A3B8;
                font-weight: bold;
                font-size: 13px;
                padding: 0;
            }
            QPushButton:hover {
                color: #EF4444;
                background-color: #1E293B;
                border-radius: 12px;
            }
        """)
        btn_close_panel.clicked.connect(self.close_requested.emit)
        header_layout.addWidget(btn_close_panel)
        layout.addLayout(header_layout)

        # Container da Imagem / Prévia Visual / Texto
        self.preview_stack_container = QWidget()
        stack_layout = QVBoxLayout(self.preview_stack_container)
        stack_layout.setContentsMargins(0, 0, 0, 0)

        # 1. Container de Imagem / Card
        self.img_container = QFrame()
        self.img_container.setObjectName("preview_img_container")
        self.img_container.setMinimumHeight(180)
        self.img_container.setMaximumHeight(230)
        img_layout = QVBoxLayout(self.img_container)
        img_layout.setContentsMargins(8, 8, 8, 8)
        
        self.lbl_preview = QLabel("Selecione um arquivo para ver a prévia")
        self.lbl_preview.setAlignment(Qt.AlignCenter)
        self.lbl_preview.setWordWrap(True)
        self.lbl_preview.setStyleSheet("color: #64748B; font-size: 13px;")
        img_layout.addWidget(self.lbl_preview)
        stack_layout.addWidget(self.img_container)

        # 2. Visualizador de Texto / NFO / Legendas
        from PySide6.QtWidgets import QTextEdit
        self.text_preview = QTextEdit()
        self.text_preview.setObjectName("preview_text_view")
        self.text_preview.setReadOnly(True)
        self.text_preview.setMinimumHeight(180)
        self.text_preview.setMaximumHeight(230)
        self.text_preview.setVisible(False)
        stack_layout.addWidget(self.text_preview)

        layout.addWidget(self.preview_stack_container)

        # Informações e Metadados
        self.info_container = QWidget()
        info_layout = QVBoxLayout(self.info_container)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(5)

        self.lbl_name = QLabel("-")
        self.lbl_name.setStyleSheet("font-size: 14px; font-weight: bold; color: #FFFFFF;")
        self.lbl_name.setWordWrap(True)
        info_layout.addWidget(self.lbl_name)

        self.lbl_size = QLabel("Tamanho: -")
        self.lbl_size.setStyleSheet("color: #94A3B8;")
        info_layout.addWidget(self.lbl_size)

        self.lbl_res = QLabel("Resolução: -")
        self.lbl_res.setStyleSheet("color: #34D399; font-weight: 500;")
        self.lbl_res.setVisible(False)
        info_layout.addWidget(self.lbl_res)

        self.lbl_date = QLabel("Modificado: -")
        self.lbl_date.setStyleSheet("color: #94A3B8;")
        info_layout.addWidget(self.lbl_date)

        self.lbl_drive = QLabel("Unidade: -")
        self.lbl_drive.setStyleSheet("color: #94A3B8;")
        info_layout.addWidget(self.lbl_drive)

        self.lbl_path = QLabel("Caminho: -")
        self.lbl_path.setStyleSheet("color: #64748B; font-size: 11px;")
        self.lbl_path.setWordWrap(True)
        info_layout.addWidget(self.lbl_path)

        layout.addWidget(self.info_container)
        layout.addStretch(1)

        actions_layout = QVBoxLayout()
        actions_layout.setSpacing(6)

        self.btn_open = QPushButton("🚀 Abrir Arquivo")
        self.btn_open.setObjectName("primary_action_btn")
        self.btn_open.setEnabled(False)
        self.btn_open.clicked.connect(self._on_open_file)
        actions_layout.addWidget(self.btn_open)

        self.btn_cast = QPushButton("📡 Transmitir para TV...")
        self.btn_cast.setObjectName("cast_action_btn")
        self.btn_cast.setEnabled(False)
        self.btn_cast.setToolTip("Transmitir este vídeo ou áudio para Smart TV (Chromecast, LG webOS, DLNA)")
        self.btn_cast.clicked.connect(self._on_cast_file)
        actions_layout.addWidget(self.btn_cast)

        expl_btn_label = "📂 Localizar no Explorer" if sys.platform == "win32" else "📂 Localizar na Pasta"
        self.btn_explorer = QPushButton(expl_btn_label)
        self.btn_explorer.setObjectName("explorer_action_btn")
        self.btn_explorer.setEnabled(False)
        self.btn_explorer.clicked.connect(self._on_reveal_explorer)
        actions_layout.addWidget(self.btn_explorer)


        copy_layout = QHBoxLayout()
        copy_layout.setSpacing(6)

        self.btn_copy_path = QPushButton("📋 Caminho")
        self.btn_copy_path.setToolTip("Copiar caminho completo")
        self.btn_copy_path.setEnabled(False)
        self.btn_copy_path.clicked.connect(self._on_copy_path)
        copy_layout.addWidget(self.btn_copy_path)

        self.btn_copy_folder = QPushButton("📁 Pasta")
        self.btn_copy_folder.setToolTip("Copiar pasta do arquivo")
        self.btn_copy_folder.setEnabled(False)
        self.btn_copy_folder.clicked.connect(self._on_copy_folder)
        copy_layout.addWidget(self.btn_copy_folder)

        actions_layout.addLayout(copy_layout)
        layout.addLayout(actions_layout)

    def set_file_data(self, file_data: Optional[Dict[str, Any]]):
        self.current_file_data = file_data

        if not file_data:
            self._reset_view()
            return

        file_path = file_data.get("path", "")
        name = file_data.get("name", "")
        cat = file_data.get("category", "")
        ext = file_data.get("extension", "").lower()
        size = file_data.get("size", 0)
        mtime = file_data.get("mtime", 0)
        drive = file_data.get("drive", "")

        self.lbl_name.setText(name)
        self.lbl_size.setText(f"Tamanho: {format_file_size(size)}")
        self.lbl_date.setText(f"Modificado: {format_timestamp(mtime)}")
        self.lbl_drive.setText(f"Origem / Unidade: {drive}")
        self.lbl_path.setText(f"Caminho:\n{file_path}")

        self.btn_open.setText("🚀 Abrir Arquivo")
        self.btn_open.setEnabled(True)
        self.btn_cast.setEnabled(cat in ("video", "audio", "pluto") or file_data.get("is_live_stream", False))
        self.btn_explorer.setEnabled(True)
        self.btn_copy_path.setEnabled(True)
        self.btn_copy_folder.setEnabled(True)
        self.lbl_res.setVisible(False)

        # Resolução de pôster / imagem
        source_path, is_remote = resolve_poster_source(file_data)

        if cat == "pluto" or file_data.get("is_live_stream"):
            ch_name = file_data.get("channel_name", name)
            self.lbl_name.setText(ch_name)
            ch_num = file_data.get("number")
            self.lbl_size.setText(f"Canal Nº: {ch_num if ch_num else '-'}")
            self.lbl_date.setText(f"Categoria: {file_data.get('pluto_category', 'Geral')}")
            self.lbl_drive.setText("Origem: Pluto TV Streaming")
            summary_txt = file_data.get("summary", "")
            self.lbl_path.setText(f"Sinopse:\n{summary_txt}" if summary_txt else f"Stream:\n{file_path}")

            self.btn_open.setText("▶️ Assistir Canal")
            self.btn_open.setEnabled(True)
            self.btn_cast.setEnabled(True)
            self.btn_explorer.setEnabled(False)
            self.btn_copy_folder.setEnabled(False)

            self.text_preview.setVisible(False)
            self.img_container.setVisible(True)

            if source_path:
                self.lbl_preview.setText("Carregando logo...")
                if self._loader_thread and self._loader_thread.isRunning():
                    self._loader_thread.terminate()
                self._loader_thread = ImageLoaderThread(source_path, QSize(260, 160), self)
                self._loader_thread.image_loaded.connect(self._on_image_loaded)
                self._loader_thread.start()
            else:
                self.lbl_preview.setPixmap(QPixmap())
                self.lbl_preview.setText(
                    f"<div style='text-align: center;'>"
                    f"<span style='font-size: 34px;'>🪐</span><br><br>"
                    f"<b style='font-size: 15px; color: #38BDF8;'>{ch_name}</b><br><br>"
                    f"<span style='background-color: #DC2626; color: #FFFFFF; font-weight: bold; font-size: 11px; padding: 3px 8px; border-radius: 4px;'>🔴 AO VIVO</span><br><br>"
                    f"<span style='color: #94A3B8; font-size: 11px;'>Pluto TV Brasil</span>"
                    f"</div>"
                )
            return

        text_extensions = {".txt", ".nfo", ".srt", ".vtt", ".sub", ".log", ".json", ".xml", ".ini", ".inf"}
        if ext in text_extensions:
            self.img_container.setVisible(False)
            self.text_preview.setVisible(True)
            try:
                if os.path.exists(file_path):
                    with open(file_path, "r", encoding="utf-8", errors="replace") as tf:
                        snippet = tf.read(2500)
                        self.text_preview.setPlainText(snippet if snippet.strip() else "(Arquivo vazio)")
                else:
                    self.text_preview.setPlainText("Arquivo inacessível ou unidade desconectada.")
            except Exception as e:
                self.text_preview.setPlainText(f"Não foi possível ler o arquivo: {e}")
            return

        self.text_preview.setVisible(False)
        self.img_container.setVisible(True)

        if cat == "image":
            self.lbl_preview.setText("Carregando miniatura...")
            if self._loader_thread and self._loader_thread.isRunning():
                self._loader_thread.terminate()
            
            target_img = source_path or file_path
            self._loader_thread = ImageLoaderThread(target_img, QSize(300, 200), self)
            self._loader_thread.image_loaded.connect(self._on_image_loaded)
            self._loader_thread.start()
        elif cat == "video":
            meta_title = file_data.get("meta_title")
            meta_year = file_data.get("meta_year")
            rating = file_data.get("imdb_rating")
            genre = file_data.get("meta_genre")

            if meta_title:
                title_disp = f"{meta_title} ({meta_year})" if meta_year else meta_title
                self.lbl_name.setText(title_disp)
                if rating:
                    self.lbl_size.setText(f"★ IMDb {rating:.1f} • {genre or 'Filme'} | {format_file_size(size)}")
                elif genre:
                    self.lbl_size.setText(f"Gênero: {genre} | {format_file_size(size)}")

            if source_path:
                self.lbl_preview.setText("Carregando pôster...")
                if self._loader_thread and self._loader_thread.isRunning():
                    self._loader_thread.terminate()
                self._loader_thread = ImageLoaderThread(source_path, QSize(260, 200), self)
                self._loader_thread.image_loaded.connect(self._on_image_loaded)
                self._loader_thread.start()
            else:
                self.lbl_preview.setPixmap(QPixmap())
                self.lbl_preview.setText(
                    f"<div style='text-align: center;'>"
                    f"<span style='font-size: 32px;'>🎬</span><br><br>"
                    f"<b style='font-size: 15px; color: #60A5FA;'>VÍDEO ({ext.upper()})</b><br>"
                    f"<span style='color: #94A3B8; font-size: 11px;'>Clique em 'Abrir Arquivo' ou aperte Enter</span>"
                    f"</div>"
                )
        elif cat == "audio":
            self.lbl_preview.setPixmap(QPixmap())
            self.lbl_preview.setText(
                f"<div style='text-align: center;'>"
                f"<span style='font-size: 32px;'>🎵</span><br><br>"
                f"<b style='font-size: 15px; color: #FBBF24;'>ÁUDIO ({ext.upper()})</b><br>"
                f"<span style='color: #94A3B8; font-size: 11px;'>Música / Trilha sonora</span>"
                f"</div>"
            )
        else:
            self.lbl_preview.setPixmap(QPixmap())
            self.lbl_preview.setText(
                f"<div style='text-align: center;'>"
                f"<span style='font-size: 32px;'>📦</span><br><br>"
                f"<b style='font-size: 14px; color: #E2E8F0;'>ARQUIVO ({ext.upper()})</b>"
                f"</div>"
            )

    def _on_image_loaded(self, path_or_url: str, pixmap: QPixmap, res_str: str):
        """Slot chamado quando o carregamento da imagem em segundo plano termina."""
        if not pixmap.isNull():
            self.lbl_preview.setText("")
            self.lbl_preview.setPixmap(pixmap)
            if res_str and self.current_file_data and self.current_file_data.get("category") == "image":
                self.lbl_res.setText(f"Resolução: {res_str}")
                self.lbl_res.setVisible(True)
        else:
            self.lbl_preview.setText("Não foi possível gerar miniatura.")

    def _reset_view(self):
        self.text_preview.setVisible(False)
        self.img_container.setVisible(True)
        self.lbl_preview.setPixmap(QPixmap())
        self.lbl_preview.setText("Selecione um arquivo para ver a prévia")
        self.lbl_name.setText("-")
        self.lbl_size.setText("Tamanho: -")
        self.lbl_res.setVisible(False)
        self.lbl_date.setText("Modificado: -")
        self.lbl_drive.setText("Unidade: -")
        self.lbl_path.setText("Caminho: -")
        self.btn_open.setEnabled(False)
        self.btn_cast.setEnabled(False)
        self.btn_explorer.setEnabled(False)
        self.btn_copy_path.setEnabled(False)
        self.btn_copy_folder.setEnabled(False)

    def _on_cast_file(self):
        if self.current_file_data:
            path = self.current_file_data.get("path", "")
            if path:
                self.cast_requested.emit(path)

    def _on_open_file(self):
        if self.current_file_data:
            path = self.current_file_data.get("path", "")
            if not open_file(path):
                QMessageBox.warning(self, "Aviso", f"Não foi possível abrir o arquivo ou a unidade está desconectada:\n{path}")

    def _on_reveal_explorer(self):
        if self.current_file_data:
            path = self.current_file_data.get("path", "")
            if not reveal_in_explorer(path):
                dest_name = "no Explorer" if sys.platform == "win32" else "no gerenciador de arquivos"
                QMessageBox.warning(self, "Aviso", f"Não foi possível localizar o arquivo {dest_name}:\n{path}")


    def _on_copy_path(self):
        if self.current_file_data:
            path = self.current_file_data.get("path", "")
            QApplication.clipboard().setText(path)

    def _on_copy_folder(self):
        if self.current_file_data:
            parent = self.current_file_data.get("parent_dir", "")
            QApplication.clipboard().setText(parent)
