import os
from typing import List, Optional
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QRadioButton, QButtonGroup,
    QComboBox, QFileDialog, QFrame, QMessageBox
)
from PySide6.QtCore import Qt, Signal

from app.core.config import AppConfig
from app.core.database import MediaDatabase
from app.utils.system_ops import open_file


class RandomMediaDialog(QDialog):
    """Diálogo de configuração e disparo do Modo Aleatório Rápido."""

    random_triggered = Signal(dict) # Emite dados do arquivo sorteado

    def __init__(self, config: AppConfig, db: MediaDatabase, parent=None):
        super().__init__(parent)
        self.config = config
        self.db = db

        self.setWindowTitle("🎲 Configuração do Modo Aleatório Rápido")
        self.resize(560, 480)
        self.setModal(True)

        self._init_ui()
        self._load_saved_settings()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        # Cabeçalho
        title_label = QLabel("🎲 Sorteador Rápido de Mídia")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #A855F7;")
        layout.addWidget(title_label)

        desc_label = QLabel(
            "Escolha quais pastas ou categorias devem entrar no sorteio.\n"
            "Ao disparar, a mídia é sorteada e aberta instantaneamente no seu reprodutor padrão."
        )
        desc_label.setStyleSheet("color: #94A3B8; font-size: 12px;")
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)

        # Modo de Origem
        source_frame = QFrame()
        source_frame.setStyleSheet("background-color: #161A21; border-radius: 8px; padding: 6px;")
        source_layout = QVBoxLayout(source_frame)
        source_layout.setSpacing(6)

        lbl_source = QLabel("Origem do Sorteio:")
        lbl_source.setStyleSheet("font-weight: 600; color: #E2E8F0;")
        source_layout.addWidget(lbl_source)

        self.bg_source = QButtonGroup(self)
        self.rb_custom_folders = QRadioButton("Pastas marcadas na lista abaixo (ex: Filmes, Séries, Desenhos)")
        self.rb_current_results = QRadioButton("Mídias dos resultados da busca/filtros atuais na tela")
        self.bg_source.addButton(self.rb_custom_folders, 1)
        self.bg_source.addButton(self.rb_current_results, 2)
        self.rb_custom_folders.setChecked(True)

        source_layout.addWidget(self.rb_custom_folders)
        source_layout.addWidget(self.rb_current_results)
        layout.addWidget(source_frame)

        # Categoria
        cat_layout = QHBoxLayout()
        lbl_cat = QLabel("Tipo de Mídia:")
        lbl_cat.setStyleSheet("font-weight: 600; color: #E2E8F0;")
        cat_layout.addWidget(lbl_cat)

        self.combo_category = QComboBox()
        self.combo_category.addItem("🎬 Vídeos (Filmes, Séries, Animes)", "video")
        self.combo_category.addItem("🎵 Músicas / Áudios", "audio")
        self.combo_category.addItem("🖼️ Imagens / Fotos", "image")
        self.combo_category.addItem("📁 Qualquer Mídia / Tudo", "all")
        cat_layout.addWidget(self.combo_category, 1)
        layout.addLayout(cat_layout)

        # Lista de Pastas
        lbl_folders = QLabel("Pastas Selecionadas para o Sorteio:")
        lbl_folders.setStyleSheet("font-weight: 600; color: #E2E8F0;")
        layout.addWidget(lbl_folders)

        self.list_folders = QListWidget()
        self.list_folders.setStyleSheet("background-color: #15181E; border: 1px solid #242A34; border-radius: 8px;")
        layout.addWidget(self.list_folders, 1)

        # Botões da Lista de Pastas
        btn_folders_layout = QHBoxLayout()
        self.btn_add_folder = QPushButton("➕ Adicionar Pasta...")
        self.btn_add_folder.clicked.connect(self._add_custom_folder)
        btn_folders_layout.addWidget(self.btn_add_folder)

        self.btn_select_all = QPushButton("Marcar Todas")
        self.btn_select_all.clicked.connect(lambda: self._set_all_checked(True))
        btn_folders_layout.addWidget(self.btn_select_all)

        self.btn_unselect_all = QPushButton("Desmarcar Todas")
        self.btn_unselect_all.clicked.connect(lambda: self._set_all_checked(False))
        btn_folders_layout.addWidget(self.btn_unselect_all)

        btn_folders_layout.addStretch()
        layout.addLayout(btn_folders_layout)

        # Rodapé de Ações
        footer_layout = QHBoxLayout()
        footer_layout.setSpacing(10)

        self.btn_test_shuffle = QPushButton("🎲 Sortear e Reproduzir Agora")
        self.btn_test_shuffle.setStyleSheet("""
            QPushButton {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #9333EA, stop:1 #A855F7);
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                padding: 10px 18px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #7E22CE, stop:1 #9333EA);
            }
        """)
        self.btn_test_shuffle.clicked.connect(self._shuffle_and_play)
        footer_layout.addWidget(self.btn_test_shuffle)

        footer_layout.addStretch()

        self.btn_save = QPushButton("Salvar Preferências")
        self.btn_save.setObjectName("primary_action_btn")
        self.btn_save.clicked.connect(self._save_and_close)
        footer_layout.addWidget(self.btn_save)

        self.btn_cancel = QPushButton("Fechar")
        self.btn_cancel.clicked.connect(self.reject)
        footer_layout.addWidget(self.btn_cancel)

        layout.addLayout(footer_layout)

        # Alternar habilitação da lista conforme opção de origem
        self.rb_custom_folders.toggled.connect(self._on_source_toggled)

    def _on_source_toggled(self, checked: bool):
        self.list_folders.setEnabled(checked)
        self.btn_add_folder.setEnabled(checked)
        self.btn_select_all.setEnabled(checked)
        self.btn_unselect_all.setEnabled(checked)

    def _load_saved_settings(self):
        source = self.config.get("random_mode_source", "custom")
        if source == "current_results":
            self.rb_current_results.setChecked(True)
        else:
            self.rb_custom_folders.setChecked(True)

        saved_cat = self.config.get("random_mode_category", "video")
        idx = self.combo_category.findData(saved_cat)
        if idx >= 0:
            self.combo_category.setCurrentIndex(idx)

        # Povoar pastas: combina pastas monitoradas gerais + pastas do random salvas + subpastas indexadas
        watched = set(self.config.get_watched_folders())
        saved_random_folders = set(self.config.get("random_mode_folders", []))
        all_candidate_folders = list(watched.union(saved_random_folders))

        # Adiciona subpastas conhecidas para facilitar marcação (ex: Filmes, Séries, etc.)
        subfolders = self.db.get_indexed_subfolders(limit=50)
        for sf in subfolders:
            if sf not in all_candidate_folders and len(sf.split(os.sep)) <= 4:
                all_candidate_folders.append(sf)

        all_candidate_folders.sort()

        self.list_folders.clear()
        for folder in all_candidate_folders:
            item = QListWidgetItem(folder)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            # Se não há nada salvo ainda, seleciona todas por padrão; se há salvo, checa as salvas
            if not saved_random_folders:
                item.setCheckState(Qt.Checked)
            else:
                item.setCheckState(Qt.Checked if folder in saved_random_folders else Qt.Unchecked)
            self.list_folders.addItem(item)

    def _add_custom_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Selecionar Pasta para Modo Aleatório")
        if folder:
            norm = os.path.normpath(folder)
            # Verifica se já existe
            for i in range(self.list_folders.count()):
                if self.list_folders.item(i).text() == norm:
                    self.list_folders.item(i).setCheckState(Qt.Checked)
                    return
            item = QListWidgetItem(norm)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked)
            self.list_folders.addItem(item)

    def _set_all_checked(self, checked: bool):
        state = Qt.Checked if checked else Qt.Unchecked
        for i in range(self.list_folders.count()):
            self.list_folders.item(i).setCheckState(state)

    def get_selected_folders(self) -> List[str]:
        folders = []
        for i in range(self.list_folders.count()):
            item = self.list_folders.item(i)
            if item.checkState() == Qt.Checked:
                folders.append(item.text())
        return folders

    def _save_settings(self):
        source = "current_results" if self.rb_current_results.isChecked() else "custom"
        self.config.set("random_mode_source", source)
        self.config.set("random_mode_category", self.combo_category.currentData())
        self.config.set("random_mode_folders", self.get_selected_folders())

    def _save_and_close(self):
        self._save_settings()
        self.accept()

    def _shuffle_and_play(self):
        self._save_settings()
        cat = self.combo_category.currentData()
        categories = [cat] if cat != "all" else None
        folders = self.get_selected_folders() if self.rb_custom_folders.isChecked() else None

        item = self.db.get_random_file(categories=categories, folders=folders)
        if item:
            open_file(item["path"])
            self.random_triggered.emit(item)
            QMessageBox.information(
                self,
                "🎲 Mídia Sorteada",
                f"Reproduzindo no player padrão:\n\n{item['name']}\n\nLocal: {item['path']}"
            )
        else:
            QMessageBox.warning(
                self,
                "Nenhuma Mídia Encontrada",
                "Não encontramos nenhum arquivo compatível com as pastas e categorias selecionadas."
            )
