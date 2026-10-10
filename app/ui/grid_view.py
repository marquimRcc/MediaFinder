import os
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Any, Optional

from PySide6.QtWidgets import (
    QListWidget, QListWidgetItem, QStyledItemDelegate,
    QStyleOptionViewItem, QMenu, QApplication, QStyle
)
from PySide6.QtCore import Qt, Signal, QSize, QRect, QRectF, QObject
from PySide6.QtGui import (
    QPainter, QColor, QFont, QPen, QBrush, QPixmap, QImage,
    QPainterPath, QKeyEvent, QFontMetrics
)

from app.utils.system_ops import open_file, reveal_in_explorer


class ImageFetchSignal(QObject):
    loaded = Signal(str, QPixmap)


class MediaCardDelegate(QStyledItemDelegate):
    """Delegate para desenhar cada mídia como um cartão moderno com pôster, badges e metadados."""

    CARD_WIDTH = 164
    CARD_HEIGHT = 246
    POSTER_HEIGHT = 168

    def __init__(self, parent=None):
        super().__init__(parent)
        self.pixmap_cache: Dict[str, QPixmap] = {}
        self._loading_keys = set()
        self._executor = ThreadPoolExecutor(max_workers=3)
        self.signal_bridge = ImageFetchSignal()
        self.signal_bridge.loaded.connect(self._on_image_loaded)

    def _on_image_loaded(self, key: str, pixmap: QPixmap):
        self.pixmap_cache[key] = pixmap
        if self.parent():
            self.parent().viewport().update()

    def _load_image_async(self, key: str, url_or_path: str):
        if key in self.pixmap_cache or key in self._loading_keys:
            return
        self._loading_keys.add(key)

        def _fetch():
            try:
                pixmap = None
                if url_or_path.startswith(("http://", "https://")):
                    req = urllib.request.Request(
                        url_or_path,
                        headers={"User-Agent": "Mozilla/5.0 MediaFinder/1.0"}
                    )
                    with urllib.request.urlopen(req, timeout=5.0) as resp:
                        img_data = resp.read()
                        qimg = QImage.fromData(img_data)
                        if not qimg.isNull():
                            pixmap = QPixmap.fromImage(qimg)
                elif os.path.exists(url_or_path):
                    qimg = QImage(url_or_path)
                    if not qimg.isNull():
                        pixmap = QPixmap.fromImage(qimg)

                if pixmap and not pixmap.isNull():
                    scaled = pixmap.scaled(
                        self.CARD_WIDTH - 8,
                        self.POSTER_HEIGHT,
                        Qt.KeepAspectRatioByExpanding,
                        Qt.SmoothTransformation
                    )
                    self.signal_bridge.loaded.emit(key, scaled)
            except Exception:
                pass
            finally:
                self._loading_keys.discard(key)

        self._executor.submit(_fetch)

    def sizeHint(self, option: QStyleOptionViewItem, index) -> QSize:
        return QSize(self.CARD_WIDTH, self.CARD_HEIGHT)

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index):
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)

        rect = option.rect.adjusted(4, 4, -4, -4)
        data = index.data(Qt.UserRole) or {}

        is_selected = bool(option.state & QStyle.State_Selected)
        is_hover = bool(option.state & QStyle.State_MouseOver)

        # 1. Fundo do Card
        bg_color = QColor("#1E293B") if is_selected else (QColor("#1A202C") if is_hover else QColor("#141822"))
        border_color = QColor("#3B82F6") if is_selected else (QColor("#38BDF8") if is_hover else QColor("#222A38"))
        pen_width = 2 if (is_selected or is_hover) else 1

        path = QPainterPath()
        path.addRoundedRect(QRectF(rect), 8, 8)
        painter.fillPath(path, QBrush(bg_color))
        painter.setPen(QPen(border_color, pen_width))
        painter.drawPath(path)

        # 2. Área do Pôster / Imagem
        poster_rect = QRect(rect.x() + 4, rect.y() + 4, rect.width() - 8, self.POSTER_HEIGHT - 4)
        poster_path = QPainterPath()
        poster_path.addRoundedRect(QRectF(poster_rect), 6, 6)

        painter.save()
        painter.setClipPath(poster_path)

        # Fundo do Pôster
        painter.fillRect(poster_rect, QColor("#0B0E14"))

        # Determina a imagem (pôster local, pôster web, thumbnail ou logo)
        img_url = (
            data.get("poster_local")
            or data.get("poster_url")
            or data.get("logo")
            or data.get("thumbnail")
        )
        is_live = data.get("is_live_stream", False)

        cache_key = img_url or data.get("id", "")
        pixmap = self.pixmap_cache.get(cache_key)

        if pixmap and not pixmap.isNull():
            dx = poster_rect.x() + (poster_rect.width() - pixmap.width()) // 2
            dy = poster_rect.y() + (poster_rect.height() - pixmap.height()) // 2
            painter.drawPixmap(dx, dy, pixmap)
        else:
            if img_url:
                self._load_image_async(cache_key, img_url)

            icon_char = "🪐" if is_live else ("🎬" if data.get("category") == "video" else "📄")
            painter.setFont(QFont("Noto Color Emoji", 28))
            painter.setPen(QColor("#475569"))
            painter.drawText(poster_rect, Qt.AlignCenter, icon_char)

        painter.restore()

        # 3. Badges Sobrepostos no Pôster
        if is_live:
            # Badge "🔴 AO VIVO"
            badge_rect = QRect(poster_rect.x() + 6, poster_rect.y() + 6, 68, 20)
            bpath = QPainterPath()
            bpath.addRoundedRect(QRectF(badge_rect), 4, 4)
            painter.fillPath(bpath, QBrush(QColor("#DC2626")))
            painter.setFont(QFont("Segoe UI", 8, QFont.Bold))
            painter.setPen(QColor("#FFFFFF"))
            painter.drawText(badge_rect, Qt.AlignCenter, "AO VIVO")

            # Badge Número do Canal "CH 52"
            ch_num = data.get("number")
            if ch_num:
                num_text = f"CH {ch_num}"
                num_rect = QRect(poster_rect.right() - 50, poster_rect.y() + 6, 46, 20)
                npath = QPainterPath()
                npath.addRoundedRect(QRectF(num_rect), 4, 4)
                painter.fillPath(npath, QBrush(QColor(15, 23, 42, 220)))
                painter.setPen(QPen(QColor("#38BDF8"), 1))
                painter.drawPath(npath)
                painter.setFont(QFont("Segoe UI", 8, QFont.Bold))
                painter.setPen(QColor("#38BDF8"))
                painter.drawText(num_rect, Qt.AlignCenter, num_text)
        else:
            # Badge IMDb para filmes locais se disponível
            rating = data.get("imdb_rating")
            if rating:
                rate_text = f"★ {rating:.1f}"
                rate_rect = QRect(poster_rect.x() + 6, poster_rect.y() + 6, 48, 20)
                rpath = QPainterPath()
                rpath.addRoundedRect(QRectF(rate_rect), 4, 4)
                painter.fillPath(rpath, QBrush(QColor("#F59E0B")))
                painter.setFont(QFont("Segoe UI", 8, QFont.Bold))
                painter.setPen(QColor("#000000"))
                painter.drawText(rate_rect, Qt.AlignCenter, rate_text)

        # 4. Textos do Card (Título e Subtítulo)
        text_rect = QRect(
            rect.x() + 8,
            rect.y() + self.POSTER_HEIGHT + 4,
            rect.width() - 16,
            rect.height() - self.POSTER_HEIGHT - 8
        )

        name_text = data.get("meta_title") or data.get("channel_name") or data.get("name", "")
        if not is_live and "." in name_text:
            name_text = os.path.splitext(name_text)[0].replace(".", " ").replace("_", " ")

        painter.setFont(QFont("Segoe UI", 9, QFont.Bold))
        painter.setPen(QColor("#FFFFFF"))

        fm = QFontMetrics(painter.font())
        elided_title = fm.elidedText(name_text, Qt.ElideRight, text_rect.width())
        title_rect = QRect(text_rect.x(), text_rect.y() + 2, text_rect.width(), 20)
        painter.drawText(title_rect, Qt.AlignLeft | Qt.AlignVCenter, elided_title)

        if is_live:
            sub_text = f"Pluto TV • {data.get('pluto_category', 'Geral')}"
        else:
            year = data.get("meta_year")
            genre = data.get("meta_genre")
            ext = data.get("extension", "").upper().replace(".", "")
            if year and genre:
                first_genre = genre.split(",")[0].strip()
                sub_text = f"{year} • {first_genre}"
            elif year:
                sub_text = f"{year} • {ext}"
            else:
                sub_text = f"{ext} • {data.get('category', '').title()}"

        painter.setFont(QFont("Segoe UI", 8))
        painter.setPen(QColor("#94A3B8"))
        elided_sub = QFontMetrics(painter.font()).elidedText(sub_text, Qt.ElideRight, text_rect.width())
        sub_rect = QRect(text_rect.x(), text_rect.y() + 22, text_rect.width(), 18)
        painter.drawText(sub_rect, Qt.AlignLeft | Qt.AlignVCenter, elided_sub)

        painter.restore()


class MediaGridView(QListWidget):
    """Grade moderna e responsiva de cartões com miniaturas para filmes e canais."""

    item_selected = Signal(dict)
    file_activated = Signal(dict)
    delete_requested = Signal(list)
    cast_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("media_grid_view")
        self._current_results: List[Dict[str, Any]] = []

        self.setViewMode(QListWidget.IconMode)
        self.setResizeMode(QListWidget.Adjust)
        self.setMovement(QListWidget.Static)
        self.setSpacing(12)
        self.setWrapping(True)
        self.setSelectionMode(QListWidget.SingleSelection)
        self.setUniformItemSizes(True)
        self.setVerticalScrollMode(QListWidget.ScrollPerPixel)

        self.card_delegate = MediaCardDelegate(self)
        self.setItemDelegate(self.card_delegate)

        self.itemSelectionChanged.connect(self._on_selection_changed)
        self.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

    def set_results(self, files: List[Dict[str, Any]]):
        self._current_results = files
        self.clear()
        self.setUpdatesEnabled(False)

        for f in files:
            item = QListWidgetItem()
            item.setData(Qt.UserRole, f)
            item.setSizeHint(QSize(MediaCardDelegate.CARD_WIDTH, MediaCardDelegate.CARD_HEIGHT))
            item.setToolTip(f"{f.get('name', '')}\n{f.get('path', '')}")
            self.addItem(item)

        self.setUpdatesEnabled(True)
        if files:
            self.setCurrentRow(0)

    def get_selected_file(self) -> Optional[Dict[str, Any]]:
        cur = self.currentItem()
        if cur:
            return cur.data(Qt.UserRole)
        return None

    def get_selected_files(self) -> List[Dict[str, Any]]:
        sel = self.get_selected_file()
        return [sel] if sel else []

    def _on_selection_changed(self):
        f = self.get_selected_file()
        if f:
            self.item_selected.emit(f)

    def _on_item_double_clicked(self, item: QListWidgetItem):
        f = item.data(Qt.UserRole)
        if f:
            self.file_activated.emit(f)
            open_file(f.get("path", ""))

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            f = self.get_selected_file()
            if f:
                open_file(f.get("path", ""))
                event.accept()
                return
        elif event.key() == Qt.Key_Delete:
            selected = self.get_selected_files()
            if selected:
                self.delete_requested.emit(selected)
                event.accept()
                return
        super().keyPressEvent(event)

    def _show_context_menu(self, pos):
        f = self.get_selected_file()
        if not f:
            return

        menu = QMenu(self)
        is_live = f.get("is_live_stream", False) or f.get("category") == "pluto"

        open_title = "▶️ Assistir Canal Ao Vivo" if is_live else "🚀 Abrir Arquivo"
        act_open = menu.addAction(open_title)
        act_open.triggered.connect(lambda: open_file(f.get("path", "")))

        if is_live or f.get("category") in ("video", "audio"):
            act_cast = menu.addAction("📡 Transmitir para TV...")
            act_cast.triggered.connect(lambda: self.cast_requested.emit(f.get("path", "")))

        if not is_live:
            expl_label = "📂 Localizar no Windows Explorer" if sys.platform == "win32" else "📂 Localizar no Gerenciador de Arquivos"
            act_explorer = menu.addAction(expl_label)
            act_explorer.triggered.connect(lambda: reveal_in_explorer(f.get("path", "")))

        menu.addSeparator()

        copy_path_label = "📋 Copiar URL do Stream" if is_live else "📋 Copiar Caminho Completo"
        act_copy_path = menu.addAction(copy_path_label)
        act_copy_path.triggered.connect(lambda: QApplication.clipboard().setText(f.get("path", "")))

        copy_name_label = "🏷️ Copiar Nome do Canal" if is_live else "🏷️ Copiar Nome do Arquivo"
        act_copy_name = menu.addAction(copy_name_label)
        act_copy_name.triggered.connect(lambda: QApplication.clipboard().setText(f.get("name", "")))

        if not is_live:
            menu.addSeparator()
            act_del = menu.addAction("🗑️ Mover para a Lixeira... (Delete)")
            act_del.triggered.connect(lambda: self.delete_requested.emit([f]))

        menu.exec(self.viewport().mapToGlobal(pos))
