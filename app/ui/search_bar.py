from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QLineEdit, QPushButton, QMenu, QCompleter
)
from PySide6.QtCore import Signal, Qt, QTimer, QStringListModel
from PySide6.QtGui import QAction, QKeySequence, QShortcut

class SearchBar(QWidget):
    """Barra de pesquisa com suporte a debounce, histórico e atalhos."""

    search_changed = Signal(str)      # Emitido quando o texto da busca muda
    reindex_requested = Signal()      # Emitido quando o usuário pede atualização

    def __init__(self, parent=None):
        super().__init__(parent)
        self._debounce_timer = QTimer(self)
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.setInterval(120)  # 120ms para digitação super responsiva
        self._debounce_timer.timeout.connect(self._on_timer_timeout)

        self._history: list[str] = []
        self._init_ui()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Input de Busca
        self.input = QLineEdit()
        self.input.setObjectName("search_input")
        self.input.setPlaceholderText("🔍  Digite o nome do arquivo, extensão (ex: .mp4) ou palavra-chave...")
        self.input.setClearButtonEnabled(True)
        self.input.textChanged.connect(self._on_text_changed)
        self.input.returnPressed.connect(self._on_return_pressed)
        layout.addWidget(self.input, 1)

        # Botão de Histórico
        self.btn_history = QPushButton("⏱️ Histórico")
        self.btn_history.setToolTip("Ver pesquisas recentes")
        self.btn_history.clicked.connect(self._show_history_menu)
        layout.addWidget(self.btn_history)

        # Botão de Reindexar / Atualizar
        self.btn_reindex = QPushButton("🔄 Atualizar")
        self.btn_reindex.setToolTip("Reescanear pastas configuradas")
        self.btn_reindex.clicked.connect(self.reindex_requested.emit)
        layout.addWidget(self.btn_reindex)

    def set_history(self, history: list[str]):
        """Atualiza a lista de histórico de buscas."""
        self._history = history

    def set_text(self, text: str):
        """Define o texto do campo de busca sem acionar debounce repetido."""
        self.input.setText(text)

    def get_text(self) -> str:
        return self.input.text().strip()

    def focus_input(self):
        self.input.setFocus()
        self.input.selectAll()

    def _on_text_changed(self, text: str):
        self._debounce_timer.start()

    def _on_timer_timeout(self):
        self.search_changed.emit(self.input.text().strip())

    def _on_return_pressed(self):
        self._debounce_timer.stop()
        self.search_changed.emit(self.input.text().strip())

    def _show_history_menu(self):
        if not self._history:
            menu = QMenu(self)
            action = menu.addAction("Nenhuma pesquisa recente")
            action.setEnabled(False)
            menu.exec(self.btn_history.mapToGlobal(self.btn_history.rect().bottomLeft()))
            return

        menu = QMenu(self)
        for term in self._history:
            action = menu.addAction(f"🔍 {term}")
            action.triggered.connect(lambda checked=False, t=term: self._apply_history_item(t))

        menu.addSeparator()
        action_clear = menu.addAction("🗑️ Limpar Histórico")
        action_clear.triggered.connect(lambda: self._history.clear())

        menu.exec(self.btn_history.mapToGlobal(self.btn_history.rect().bottomLeft()))

    def _apply_history_item(self, term: str):
        self.input.setText(term)
        self.search_changed.emit(term)
