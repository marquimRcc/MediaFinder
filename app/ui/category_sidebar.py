from typing import List, Dict, Any, Optional
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QListWidget,
    QListWidgetItem, QWidget, QAbstractItemView
)
from PySide6.QtCore import Qt, Signal, QSize


CATEGORY_ICONS = {
    "all": "🪐",
    "todas": "🪐",
    "filmes": "🎬",
    "séries": "📺",
    "series": "📺",
    "anime & geek": "⚡",
    "mtv": "🎸",
    "infantil": "🧸",
    "retrô": "📼",
    "retro": "📼",
    "esportes": "⚽",
    "nickelodeon": "🟧",
    "curiosidades": "💡",
    "estilo de vida": "✨",
    "notícias": "📰",
    "noticias": "📰",
    "comédia": "🎭",
    "comedia": "🎭",
    "reality": "🌟",
    "natureza": "🌿",
    "mistérios e sobrenatural": "🔮",
    "misterios e sobrenatural": "🔮",
    "investigação": "🕵️",
    "investigacao": "🕵️",
    "south park br": "🧢",
    "star trek": "🖖",
    "novelas": "💔",
    "música": "🎵",
    "musica": "🎵",
    "tv brasileira": "🇧🇷",
}


def get_category_icon(category_name: str) -> str:
    """Retorna um ícone temático correspondente à categoria."""
    cl = category_name.strip().lower()
    for k, icon in CATEGORY_ICONS.items():
        if k in cl or cl in k:
            return icon
    return "📺"


class CategoryItemWidget(QWidget):
    """Widget customizado para exibir ícone, nome da categoria e badge numérico."""

    def __init__(self, cat_id: str, title: str, count: int, icon: str, parent=None):
        super().__init__(parent)
        self.cat_id = cat_id
        self.setAttribute(Qt.WA_Hover, True)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(6)

        self.lbl_icon = QLabel(icon)
        self.lbl_icon.setStyleSheet("font-size: 13px; background: transparent;")
        layout.addWidget(self.lbl_icon)

        self.lbl_title = QLabel(title)
        self.lbl_title.setToolTip(title)
        self.lbl_title.setStyleSheet("font-size: 12px; font-weight: 500; color: #E2E8F0; background: transparent;")
        self.lbl_title.setWordWrap(False)
        layout.addWidget(self.lbl_title, 1)

        self.lbl_badge = QLabel(str(count))
        self.lbl_badge.setStyleSheet("""
            QLabel {
                font-size: 11px;
                font-weight: 700;
                color: #38BDF8;
                background-color: #1E293B;
                border: 1px solid #334155;
                border-radius: 9px;
                padding: 1px 6px;
            }
        """)
        layout.addWidget(self.lbl_badge)

    def set_active(self, active: bool):
        if active:
            self.lbl_title.setStyleSheet("font-size: 12px; font-weight: 700; color: #38BDF8; background: transparent;")
            self.lbl_badge.setStyleSheet("""
                QLabel {
                    font-size: 11px;
                    font-weight: 700;
                    color: #FFFFFF;
                    background-color: #0284C7;
                    border: 1px solid #38BDF8;
                    border-radius: 9px;
                    padding: 1px 6px;
                }
            """)
        else:
            self.lbl_title.setStyleSheet("font-size: 12px; font-weight: 500; color: #94A3B8; background: transparent;")
            self.lbl_badge.setStyleSheet("""
                QLabel {
                    font-size: 11px;
                    font-weight: 700;
                    color: #64748B;
                    background-color: #141A24;
                    border: 1px solid #1E293B;
                    border-radius: 9px;
                    padding: 1px 6px;
                }
            """)


class CategorySidebar(QFrame):
    """Barra lateral com categorias e contadores de canais da Pluto TV (Opção 4)."""

    category_selected = Signal(str)  # Emite o cat_id (ex: "all", "Filmes", "Séries")

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("category_sidebar")
        self.setMinimumWidth(215)
        self.setMaximumWidth(290)
        self._current_cat_id = "all"
        self._item_widgets: Dict[str, CategoryItemWidget] = {}

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 10, 8, 10)
        layout.setSpacing(8)

        # Header da Sidebar
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(6, 2, 6, 2)

        lbl_header = QLabel("CATEGORIAS")
        lbl_header.setStyleSheet("""
            font-size: 11px;
            font-weight: 700;
            color: #64748B;
            letter-spacing: 0.5px;
        """)
        header_layout.addWidget(lbl_header)
        header_layout.addStretch(1)

        self.lbl_total = QLabel("")
        self.lbl_total.setStyleSheet("font-size: 10px; color: #475569; font-weight: 600;")
        header_layout.addWidget(self.lbl_total)

        layout.addLayout(header_layout)

        # Lista de Categorias
        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QAbstractItemView.SingleSelection)
        self.list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.list_widget.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.list_widget.setStyleSheet("""
            QListWidget {
                background-color: transparent;
                border: none;
                outline: none;
            }
            QListWidget::item {
                background-color: transparent;
                border-radius: 8px;
                margin: 1px 0px;
                padding: 0px;
            }
            QListWidget::item:hover {
                background-color: #172033;
            }
            QListWidget::item:selected {
                background-color: #1E293B;
                border: 1px solid #0284C7;
            }
        """)
        self.list_widget.itemClicked.connect(self._on_item_clicked)
        layout.addWidget(self.list_widget, 1)

        # Estilo do frame da barra lateral
        self.setStyleSheet("""
            QFrame#category_sidebar {
                background-color: #0B0E14;
                border-right: 1px solid #1E293B;
            }
        """)

    def load_pluto_categories(self, channels: List[Dict[str, Any]]):
        """Carrega e agrupa categorias a partir dos canais da Pluto TV."""
        self.list_widget.clear()
        self._item_widgets.clear()

        # Contagem por categoria
        cat_counts: Dict[str, int] = {}
        for c in channels:
            cat = c.get("category", "Geral")
            cat_counts[cat] = cat_counts.get(cat, 0) + 1

        total_channels = len(channels)
        self.lbl_total.setText(f"{len(cat_counts)} seções")

        # Item Especial: Todas as Categorias
        self._add_category_item("all", "Todas as Categorias", total_channels, "🪐")

        # Ordena categorias por volume decrescente de canais
        sorted_cats = sorted(cat_counts.items(), key=lambda x: (-x[1], x[0]))
        for cat_name, count in sorted_cats:
            icon = get_category_icon(cat_name)
            self._add_category_item(cat_name, cat_name, count, icon)

        # Restaura ou inicializa seleção
        self.select_category(self._current_cat_id, emit_signal=False)

    def _add_category_item(self, cat_id: str, title: str, count: int, icon: str):
        item = QListWidgetItem(self.list_widget)
        item.setData(Qt.UserRole, cat_id)
        item.setSizeHint(QSize(180, 36))

        widget = CategoryItemWidget(cat_id, title, count, icon, self.list_widget)
        self.list_widget.addItem(item)
        self.list_widget.setItemWidget(item, widget)
        self._item_widgets[cat_id] = widget

    def select_category(self, cat_id: str, emit_signal: bool = False):
        """Seleciona programaticamente uma categoria na sidebar."""
        self._current_cat_id = cat_id or "all"
        target_item = None

        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            cid = item.data(Qt.UserRole)
            is_active = (cid == self._current_cat_id)
            widget = self._item_widgets.get(cid)
            if widget:
                widget.set_active(is_active)
            if is_active:
                target_item = item

        if target_item:
            self.list_widget.blockSignals(True)
            self.list_widget.setCurrentItem(target_item)
            self.list_widget.blockSignals(False)

        if emit_signal:
            self.category_selected.emit(self._current_cat_id)

    def _on_item_clicked(self, item: QListWidgetItem):
        cid = item.data(Qt.UserRole) or "all"
        self._current_cat_id = cid

        # Atualiza destaques visuais dos widgets
        for cat_id, widget in self._item_widgets.items():
            widget.set_active(cat_id == cid)

        self.category_selected.emit(cid)
