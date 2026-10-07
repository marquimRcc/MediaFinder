import os
from typing import List, Dict, Any, Optional

from PySide6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QFileDialog, QMessageBox, QGroupBox, QTabWidget,
    QInputDialog, QSplitter, QFrame
)
from PySide6.QtCore import Signal, Qt

from app.core.config import AppConfig
from app.core.database import MediaDatabase
from app.utils.media_helpers import format_file_size


class SettingsDialog(QDialog):
    """Diálogo de gerenciamento de HDs, indexação e grupos de equivalência de mídia multi-HD."""

    reindex_requested = Signal()
    folder_groups_updated = Signal()

    def __init__(self, config: AppConfig, db: MediaDatabase, parent=None):
        super().__init__(parent)
        self.config = config
        self.db = db
        self.setWindowTitle("Configurações do MediaFinder — Pastas, HDs & Grupos")
        self.resize(720, 540)
        self.setMinimumSize(640, 460)
        self.setModal(True)

        self.groups_data: Dict[str, List[str]] = dict(self.config.get_folder_groups())
        self.current_group_name: Optional[str] = None

        self._init_ui()
        self._load_data()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(14, 14, 14, 14)
        main_layout.setSpacing(12)

        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #242A34;
                border-radius: 6px;
                background-color: #161A21;
            }
            QTabBar::tab {
                background-color: #0E1014;
                color: #94A3B8;
                padding: 8px 16px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                margin-right: 2px;
                font-weight: bold;
            }
            QTabBar::tab:selected {
                background-color: #161A21;
                color: #38BDF8;
                border-bottom: 2px solid #38BDF8;
            }
        """)

        # Aba 1: HDs & Pastas Globais
        tab_global = self._build_global_folders_tab()
        self.tabs.addTab(tab_global, "📁 HDs & Pastas Monitoradas")

        # Aba 2: Grupos de Mídia (Equivalência Multi-HD)
        tab_groups = self._build_folder_groups_tab()
        self.tabs.addTab(tab_groups, "🏷️ Grupos de Mídia & Categorias Multi-HD")

        main_layout.addWidget(self.tabs, 1)

        # Barra Inferior de Botões
        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(8)

        self.btn_reindex = QPushButton("🔄 Reindexar Tudo Agora")
        self.btn_reindex.setObjectName("primary_action_btn")
        self.btn_reindex.clicked.connect(self._on_reindex_clicked)
        bottom_layout.addWidget(self.btn_reindex)

        self.btn_clear_db = QPushButton("🗑️ Limpar Banco")
        self.btn_clear_db.clicked.connect(self._on_clear_db_clicked)
        bottom_layout.addWidget(self.btn_clear_db)

        bottom_layout.addStretch(1)

        self.btn_save_close = QPushButton("💾 Salvar e Fechar")
        self.btn_save_close.setObjectName("primary_action_btn")
        self.btn_save_close.clicked.connect(self._on_save_and_close)
        bottom_layout.addWidget(self.btn_save_close)

        main_layout.addLayout(bottom_layout)

    def _build_global_folders_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        lbl_desc = QLabel("Selecione as raízes dos HDs ou pastas que o MediaFinder deve varrer e indexar:")
        lbl_desc.setStyleSheet("color: #94A3B8; font-size: 11px;")
        layout.addWidget(lbl_desc)

        self.list_folders = QListWidget()
        self.list_folders.setStyleSheet("""
            QListWidget {
                background-color: #0E1014;
                border: 1px solid #1E242D;
                border-radius: 6px;
                color: #F8FAFC;
                padding: 4px;
            }
            QListWidget::item {
                padding: 6px;
                border-bottom: 1px solid #15181E;
            }
        """)
        layout.addWidget(self.list_folders, 1)

        btn_layout = QHBoxLayout()
        self.btn_add_watched = QPushButton("➕ Adicionar Pasta / HD...")
        self.btn_add_watched.clicked.connect(self._add_watched_folder)
        btn_layout.addWidget(self.btn_add_watched)

        self.btn_remove_watched = QPushButton("➖ Remover Selecionada")
        self.btn_remove_watched.clicked.connect(self._remove_watched_folder)
        btn_layout.addWidget(self.btn_remove_watched)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # Estatísticas
        group_stats = QGroupBox("📊 Estatísticas da Base de Dados")
        group_stats.setStyleSheet("""
            QGroupBox {
                border: 1px solid #242A34;
                border-radius: 6px;
                margin-top: 8px;
                padding-top: 10px;
                color: #38BDF8;
                font-weight: bold;
            }
        """)
        stats_layout = QVBoxLayout(group_stats)
        stats_layout.setSpacing(4)

        self.lbl_stats = QLabel("Total de Arquivos: - | Tamanho Total: -")
        self.lbl_stats.setStyleSheet("color: #38BDF8; font-weight: bold; font-size: 12px;")
        stats_layout.addWidget(self.lbl_stats)

        self.lbl_drives_detail = QLabel("Drives: -")
        self.lbl_drives_detail.setStyleSheet("color: #94A3B8; font-size: 11px;")
        stats_layout.addWidget(self.lbl_drives_detail)

        layout.addWidget(group_stats)

        return widget

    def _build_folder_groups_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        lbl_desc = QLabel("Crie categorias e equivalências para unir pastas de múltiplos HDs (ex: 'Filmes' contendo pastas do E:, F: e H:). Esses grupos alimentam o buscador e o Modo TV automaticamente:")
        lbl_desc.setStyleSheet("color: #94A3B8; font-size: 11px;")
        lbl_desc.setWordWrap(True)
        layout.addWidget(lbl_desc)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(4)

        # Lado Esquerdo: Lista de Grupos
        left_box = QWidget()
        left_layout = QVBoxLayout(left_box)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(6)

        lbl_grp_title = QLabel("Categorias / Grupos:")
        lbl_grp_title.setStyleSheet("font-weight: bold; color: #E2E8F0; font-size: 11px;")
        left_layout.addWidget(lbl_grp_title)

        self.list_groups = QListWidget()
        self.list_groups.setStyleSheet("""
            QListWidget {
                background-color: #0E1014;
                border: 1px solid #1E242D;
                border-radius: 6px;
                color: #F8FAFC;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #15181E;
            }
            QListWidget::item:selected {
                background-color: #2563EB;
                color: #FFFFFF;
                font-weight: bold;
            }
        """)
        self.list_groups.currentTextChanged.connect(self._on_group_selected)
        left_layout.addWidget(self.list_groups, 1)

        grp_btns = QHBoxLayout()
        self.btn_new_group = QPushButton("➕ Novo Grupo")
        self.btn_new_group.clicked.connect(self._add_new_group)
        grp_btns.addWidget(self.btn_new_group)

        self.btn_del_group = QPushButton("🗑️ Excluir")
        self.btn_del_group.clicked.connect(self._delete_group)
        grp_btns.addWidget(self.btn_del_group)

        left_layout.addLayout(grp_btns)
        splitter.addWidget(left_box)

        # Lado Direito: Pastas do Grupo Selecionado
        right_box = QWidget()
        right_layout = QVBoxLayout(right_box)
        right_layout.setContentsMargins(6, 0, 0, 0)
        right_layout.setSpacing(6)

        self.lbl_selected_group = QLabel("Pastas Vinculadas a este Grupo:")
        self.lbl_selected_group.setStyleSheet("font-weight: bold; color: #38BDF8; font-size: 11px;")
        right_layout.addWidget(self.lbl_selected_group)

        self.list_group_folders = QListWidget()
        self.list_group_folders.setStyleSheet("""
            QListWidget {
                background-color: #0E1014;
                border: 1px solid #1E242D;
                border-radius: 6px;
                color: #CBD5E1;
                font-size: 11px;
            }
            QListWidget::item {
                padding: 6px;
                border-bottom: 1px solid #15181E;
            }
        """)
        right_layout.addWidget(self.list_group_folders, 1)

        f_btns = QHBoxLayout()
        self.btn_add_folder_to_grp = QPushButton("📁 Adicionar Pasta...")
        self.btn_add_folder_to_grp.clicked.connect(self._add_folder_to_group)
        f_btns.addWidget(self.btn_add_folder_to_grp)

        self.btn_import_subfolder = QPushButton("📑 Escolher das Subpastas dos HDs...")
        self.btn_import_subfolder.clicked.connect(self._import_subfolder_to_group)
        f_btns.addWidget(self.btn_import_subfolder)

        self.btn_del_folder_from_grp = QPushButton("🗑️ Remover")
        self.btn_del_folder_from_grp.clicked.connect(self._remove_folder_from_group)
        f_btns.addWidget(self.btn_del_folder_from_grp)

        right_layout.addLayout(f_btns)
        splitter.addWidget(right_box)

        splitter.setStretchFactor(0, 35)
        splitter.setStretchFactor(1, 65)

        layout.addWidget(splitter, 1)
        return widget

    def _load_data(self):
        """Carrega pastas monitoradas, grupos e estatísticas."""
        # 1. Pastas monitoradas
        self.list_folders.clear()
        folders = self.config.get_watched_folders()
        for f in folders:
            self.list_folders.addItem(f)

        # 2. Grupos de pastas
        self.groups_data = dict(self.config.get_folder_groups())
        self._populate_groups_list()

        # 3. Estatísticas
        stats = self.db.get_stats()
        total_files = stats.get("total_files", 0)
        total_size = stats.get("total_size", 0)
        drives = stats.get("drives", {})

        self.lbl_stats.setText(f"Total Indexado: {total_files:,} arquivos ({format_file_size(total_size)})")
        drives_str = ", ".join([f"{k} ({v} arquivos)" for k, v in drives.items() if k])
        self.lbl_drives_detail.setText(f"Drives Ativos: {drives_str if drives_str else 'Nenhum'}")

    def _populate_groups_list(self):
        self.list_groups.clear()
        for grp in self.groups_data.keys():
            self.list_groups.addItem(grp)
        if self.groups_data:
            self.list_groups.setCurrentRow(0)

    def _on_group_selected(self, group_name: str):
        self.current_group_name = group_name
        self.list_group_folders.clear()
        if not group_name or group_name not in self.groups_data:
            self.lbl_selected_group.setText("Selecione um grupo à esquerda")
            return

        self.lbl_selected_group.setText(f"Pastas vinculadas ao grupo '{group_name}':")
        for f in self.groups_data[group_name]:
            self.list_group_folders.addItem(f)

    def _add_new_group(self):
        name, ok = QInputDialog.getText(self, "Novo Grupo de Mídia", "Nome da categoria ou grupo (ex: Cursos, Novelas, Filmes 4K):")
        if ok and name.strip():
            clean_name = name.strip()
            if clean_name in self.groups_data:
                QMessageBox.warning(self, "Aviso", "Já existe um grupo com este nome.")
                return
            self.groups_data[clean_name] = []
            self._populate_groups_list()
            # Seleciona o recém-criado
            items = self.list_groups.findItems(clean_name, Qt.MatchExactly)
            if items:
                self.list_groups.setCurrentItem(items[0])

    def _delete_group(self):
        if not self.current_group_name or self.current_group_name not in self.groups_data:
            return

        reply = QMessageBox.question(
            self,
            "Excluir Grupo",
            f"Deseja realmente remover o grupo '{self.current_group_name}'?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            del self.groups_data[self.current_group_name]
            self._populate_groups_list()

    def _add_folder_to_group(self):
        if not self.current_group_name or self.current_group_name not in self.groups_data:
            return

        folder = QFileDialog.getExistingDirectory(self, f"Selecionar Pasta para '{self.current_group_name}'")
        if folder:
            norm = os.path.normpath(folder)
            if norm not in self.groups_data[self.current_group_name]:
                self.groups_data[self.current_group_name].append(norm)
                self.list_group_folders.addItem(norm)

    def _import_subfolder_to_group(self):
        """Permite escolher uma das subpastas conhecidas indexadas no banco com facilidade."""
        if not self.current_group_name or self.current_group_name not in self.groups_data:
            return

        known_subfolders = self.db.get_indexed_subfolders(limit=300)
        if not known_subfolders:
            QMessageBox.information(self, "Aviso", "Nenhuma subpasta indexada encontrada no banco de dados.")
            return

        item, ok = QInputDialog.getItem(
            self,
            "Escolher Subpasta Indexada",
            "Selecione uma pasta indexada para vincular a este grupo:",
            known_subfolders,
            0,
            False
        )
        if ok and item:
            norm = os.path.normpath(item)
            if norm not in self.groups_data[self.current_group_name]:
                self.groups_data[self.current_group_name].append(norm)
                self.list_group_folders.addItem(norm)

    def _remove_folder_from_group(self):
        if not self.current_group_name or self.current_group_name not in self.groups_data:
            return

        row = self.list_group_folders.currentRow()
        if row >= 0:
            del self.groups_data[self.current_group_name][row]
            self.list_group_folders.takeItem(row)

    def _add_watched_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Selecionar Pasta ou Drive para Monitorar")
        if folder:
            norm = os.path.normpath(folder)
            folders = self.config.get_watched_folders()
            if norm not in folders:
                folders.append(norm)
                self.config.set_watched_folders(folders)
                self._load_data()

    def _remove_watched_folder(self):
        current_item = self.list_folders.currentItem()
        if not current_item:
            return
        
        folder = current_item.text()
        folders = self.config.get_watched_folders()
        if folder in folders:
            folders.remove(folder)
            self.config.set_watched_folders(folders)
            self._load_data()

    def _on_reindex_clicked(self):
        self._on_save_and_close()
        self.reindex_requested.emit()

    def _on_clear_db_clicked(self):
        reply = QMessageBox.question(
            self,
            "Confirmar",
            "Deseja realmente limpar todos os registros indexados do banco de dados?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.db.clear_database()
            self._load_data()
            QMessageBox.information(self, "Sucesso", "Banco de dados limpo com sucesso.")

    def _on_save_and_close(self):
        self.config.set_folder_groups(self.groups_data)
        self.folder_groups_updated.emit()
        self.accept()
