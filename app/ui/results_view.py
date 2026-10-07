import os
from typing import List, Dict, Any, Optional
from PySide6.QtWidgets import (
    QTableWidget, QTableWidgetItem, QHeaderView, QMenu,
    QAbstractItemView, QApplication, QMessageBox
)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QColor, QFont, QKeyEvent

from app.utils.media_helpers import format_file_size, format_timestamp
from app.utils.system_ops import open_file, reveal_in_explorer

CATEGORY_ICONS = {
    "video": "🎬",
    "image": "🖼️",
    "audio": "🎵",
    "document": "📄",
    "other": "📦"
}

class ResultsTableView(QTableWidget):
    """Tabela de exibição de resultados com menu de contexto e alta fluidez."""

    item_selected = Signal(dict)       # Emitido ao selecionar uma linha (para o preview)
    file_activated = Signal(dict)      # Emitido ao dar duplo clique ou Enter
    delete_requested = Signal(list)    # Emitido ao solicitar exclusão de um ou mais arquivos selecionados

    COLUMNS = [
        ("Tipo", 44),
        ("Nome do Arquivo", 360),
        ("Ext", 60),
        ("Tamanho", 85),
        ("Unidade", 65),
        ("Modificado Em", 125),
        ("Caminho Completo", 300)
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_results: List[Dict[str, Any]] = []
        self._init_ui()

    def _init_ui(self):
        self.setColumnCount(len(self.COLUMNS))
        self.setHorizontalHeaderLabels([col[0] for col in self.COLUMNS])
        
        # Configurações de seleção e comportamento
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setAlternatingRowColors(True)
        self.setShowGrid(False)
        self.verticalHeader().setVisible(False)
        self.verticalHeader().setDefaultSectionSize(34)

        # Ajusta larguras iniciais
        header = self.horizontalHeader()
        header.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        
        for idx, (_, width) in enumerate(self.COLUMNS):
            self.setColumnWidth(idx, width)
            
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        header.setSectionResizeMode(1, QHeaderView.Stretch)       # Nome do Arquivo ganha espaço total
        header.setSectionResizeMode(2, QHeaderView.Interactive)
        header.setSectionResizeMode(3, QHeaderView.Interactive)
        header.setSectionResizeMode(4, QHeaderView.Interactive)
        header.setSectionResizeMode(5, QHeaderView.Interactive)
        header.setSectionResizeMode(6, QHeaderView.Interactive)

        # Sinais
        self.itemSelectionChanged.connect(self._on_selection_changed)
        self.itemDoubleClicked.connect(self._on_double_clicked)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

    def set_results(self, files: List[Dict[str, Any]]):
        """Carrega lista de arquivos na tabela."""
        self._current_results = files
        self.setRowCount(0)
        self.setRowCount(len(files))

        # Desativa atualização visual durante preenchimento em massa
        self.setUpdatesEnabled(False)

        for row, f in enumerate(files):
            cat = f.get("category", "other")
            ext = f.get("extension", "").upper()
            size = f.get("size", 0)
            mtime = f.get("mtime", 0)
            drive = f.get("drive", "").upper()
            name = f.get("name", "")
            path = f.get("path", "")

            icon_str = CATEGORY_ICONS.get(cat, "📦")

            # Coluna 0: Ícone/Tipo
            item_type = QTableWidgetItem(icon_str)
            item_type.setTextAlignment(Qt.AlignCenter)

            # Coluna 1: Nome do Arquivo
            item_name = QTableWidgetItem(name)
            item_name.setToolTip(f"📄 {name}\n📁 {path}\n💾 {format_file_size(size)} | 📅 {format_timestamp(mtime)}")

            # Coluna 2: Extensão com cor diferenciada
            item_ext = QTableWidgetItem(ext)
            item_ext.setTextAlignment(Qt.AlignCenter)
            if cat == "video":
                item_ext.setForeground(QColor("#60A5FA")) # Azul claro
            elif cat == "image":
                item_ext.setForeground(QColor("#34D399")) # Verde esmeralda
            elif cat == "audio":
                item_ext.setForeground(QColor("#FBBF24")) # Âmbar
            else:
                item_ext.setForeground(QColor("#94A3B8"))

            # Coluna 3: Tamanho formatado
            size_str = format_file_size(size)
            item_size = QTableWidgetItem(size_str)
            item_size.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            item_size.setForeground(QColor("#38BDF8"))

            # Coluna 4: HD / Drive com identificador visual
            item_drive = QTableWidgetItem(f"[{drive}]" if drive else "-")
            item_drive.setTextAlignment(Qt.AlignCenter)
            if "E:" in drive:
                item_drive.setForeground(QColor("#22D3EE")) # Ciano
            elif "F:" in drive:
                item_drive.setForeground(QColor("#818CF8")) # Índigo
            elif "H:" in drive:
                item_drive.setForeground(QColor("#C084FC")) # Roxo
            else:
                item_drive.setForeground(QColor("#E2E8F0"))

            # Coluna 5: Data Modificado
            date_str = format_timestamp(mtime)
            item_date = QTableWidgetItem(date_str)
            item_date.setForeground(QColor("#94A3B8"))

            # Coluna 6: Caminho Completo
            item_path = QTableWidgetItem(path)
            item_path.setForeground(QColor("#64748B"))
            item_path.setToolTip(path)

            self.setItem(row, 0, item_type)
            self.setItem(row, 1, item_name)
            self.setItem(row, 2, item_ext)
            self.setItem(row, 3, item_size)
            self.setItem(row, 4, item_drive)
            self.setItem(row, 5, item_date)
            self.setItem(row, 6, item_path)

        self.setUpdatesEnabled(True)

        # Seleciona primeira linha por padrão se houver itens
        if files:
            self.selectRow(0)


    def get_selected_file(self) -> Optional[Dict[str, Any]]:
        row = self.currentRow()
        if 0 <= row < len(self._current_results):
            return self._current_results[row]
        return None

    def get_selected_files(self) -> List[Dict[str, Any]]:
        """Retorna todos os arquivos selecionados atualmente na tabela."""
        selected_indexes = self.selectionModel().selectedRows()
        selected_items = []
        for idx in selected_indexes:
            row = idx.row()
            if 0 <= row < len(self._current_results):
                selected_items.append(self._current_results[row])
        return selected_items

    def _on_selection_changed(self):
        f = self.get_selected_file()
        if f:
            self.item_selected.emit(f)

    def _on_double_clicked(self, item):
        f = self.get_selected_file()
        if f:
            self.file_activated.emit(f)
            open_file(f.get("path", ""))

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            selected = self.get_selected_files()
            if selected:
                for f in selected:
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
        selected_files = self.get_selected_files()
        if not selected_files:
            return

        menu = QMenu(self)
        count = len(selected_files)

        if count == 1:
            f = selected_files[0]
            act_open = menu.addAction("🚀 Abrir Arquivo")
            act_open.triggered.connect(lambda: open_file(f.get("path", "")))

            act_explorer = menu.addAction("📂 Localizar no Windows Explorer")
            act_explorer.triggered.connect(lambda: reveal_in_explorer(f.get("path", "")))

            menu.addSeparator()

            act_copy_path = menu.addAction("📋 Copiar Caminho Completo")
            act_copy_path.triggered.connect(lambda: QApplication.clipboard().setText(f.get("path", "")))

            act_copy_name = menu.addAction("🏷️ Copiar Nome do Arquivo")
            act_copy_name.triggered.connect(lambda: QApplication.clipboard().setText(f.get("name", "")))

            act_copy_dir = menu.addAction("📁 Copiar Pasta do Arquivo")
            act_copy_dir.triggered.connect(lambda: QApplication.clipboard().setText(f.get("parent_dir", "")))

            menu.addSeparator()

            act_del = menu.addAction("🗑️ Excluir do Disco... (Delete)")
            act_del.triggered.connect(lambda: self.delete_requested.emit(selected_files))
        else:
            act_open_all = menu.addAction(f"🚀 Abrir Selecionados ({count} arquivos)")
            act_open_all.triggered.connect(lambda: [open_file(sf.get("path", "")) for sf in selected_files])

            act_explorer_first = menu.addAction("📂 Localizar 1º no Explorer")
            act_explorer_first.triggered.connect(lambda: reveal_in_explorer(selected_files[0].get("path", "")))

            menu.addSeparator()

            paths_joined = "\n".join(sf.get("path", "") for sf in selected_files)
            act_copy_all = menu.addAction(f"📋 Copiar {count} Caminhos")
            act_copy_all.triggered.connect(lambda: QApplication.clipboard().setText(paths_joined))

            menu.addSeparator()

            act_del = menu.addAction(f"🗑️ Excluir {count} Arquivos do Disco... (Delete)")
            act_del.triggered.connect(lambda: self.delete_requested.emit(selected_files))

        menu.exec(self.viewport().mapToGlobal(pos))
