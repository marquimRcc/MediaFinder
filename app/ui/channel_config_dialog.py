import os
from typing import List, Dict, Any, Optional

from PySide6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QLineEdit, QComboBox, QSpinBox,
    QFileDialog, QFrame, QMessageBox, QGroupBox, QSplitter, QCheckBox,
    QScrollArea, QInputDialog
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon, QFont

from app.core.config import AppConfig
from app.core.database import MediaDatabase
from app.core.tv_schedule import TVChannel


class ChannelConfigDialog(QDialog):
    """Diálogo visual para criação, edição, exclusão e personalização de canais de TV e suas pastas/grupos."""

    channels_updated = Signal()

    def __init__(self, config: AppConfig, db: Optional[MediaDatabase] = None, parent=None):
        super().__init__(parent)
        self.config = config
        self.db = db
        self.setWindowTitle("⚙️ Gerenciador de Canais de TV — MediaFinder")
        self.resize(920, 620)
        self.setMinimumSize(780, 520)

        self.channels_data: List[Dict[str, Any]] = [dict(c) for c in self.config.get_tv_channels()]
        self.current_idx = 0
        self.group_checkboxes: Dict[str, QCheckBox] = {}

        self._init_ui()
        self._populate_channel_list()
        if self.channels_data:
            self.channel_list.setCurrentRow(0)

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(14, 14, 14, 14)
        main_layout.setSpacing(12)

        # Cabeçalho explicativo
        header_frame = QFrame()
        header_frame.setStyleSheet("background-color: #12151B; border: 1px solid #242A34; border-radius: 6px; padding: 6px;")
        h_layout = QVBoxLayout(header_frame)
        h_layout.setContentsMargins(10, 6, 10, 6)
        h_layout.setSpacing(2)

        lbl_title = QLabel("📡 Personalização de Canais & Origem das Mídias")
        lbl_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #38BDF8;")
        h_layout.addWidget(lbl_title)

        lbl_desc = QLabel("Crie canais, associe grupos de pastas e mídias (ex: Filmes ou Séries em múltiplos locais) e defina a ordem de transmissão (Aleatório ou Sequencial cronológico).")
        lbl_desc.setStyleSheet("font-size: 11px; color: #94A3B8;")
        lbl_desc.setWordWrap(True)
        h_layout.addWidget(lbl_desc)

        main_layout.addWidget(header_frame)

        # Splitter (Lista de Canais à esquerda, Editor à direita)
        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(4)

        # --- LADO ESQUERDO: Lista de Canais ---
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(8)

        lbl_list = QLabel("Canais Configurados:")
        lbl_list.setStyleSheet("font-weight: bold; font-size: 12px; color: #E2E8F0;")
        left_layout.addWidget(lbl_list)

        self.channel_list = QListWidget()
        self.channel_list.setStyleSheet("""
            QListWidget {
                background-color: #0E1014;
                border: 1px solid #1E242D;
                border-radius: 6px;
                color: #F8FAFC;
            }
            QListWidget::item {
                padding: 10px 8px;
                border-bottom: 1px solid #1A1F26;
                border-radius: 4px;
            }
            QListWidget::item:hover {
                background-color: #1A202C;
            }
            QListWidget::item:selected {
                background-color: #2563EB;
                color: #FFFFFF;
                font-weight: bold;
            }
        """)
        self.channel_list.currentRowChanged.connect(self._on_channel_selected)
        left_layout.addWidget(self.channel_list, 1)

        # Botões de ação da lista
        list_btns_layout = QHBoxLayout()
        list_btns_layout.setSpacing(4)

        self.btn_add = QPushButton("➕ Novo Canal")
        self.btn_add.setObjectName("primary_action_btn")
        self.btn_add.clicked.connect(self._add_new_channel)
        list_btns_layout.addWidget(self.btn_add)

        self.btn_remove = QPushButton("🗑️ Excluir")
        self.btn_remove.clicked.connect(self._remove_selected_channel)
        list_btns_layout.addWidget(self.btn_remove)

        self.btn_up = QPushButton("▲")
        self.btn_up.setToolTip("Mover para cima")
        self.btn_up.setFixedWidth(32)
        self.btn_up.clicked.connect(self._move_channel_up)
        list_btns_layout.addWidget(self.btn_up)

        self.btn_down = QPushButton("▼")
        self.btn_down.setToolTip("Mover para baixo")
        self.btn_down.setFixedWidth(32)
        self.btn_down.clicked.connect(self._move_channel_down)
        list_btns_layout.addWidget(self.btn_down)

        left_layout.addLayout(list_btns_layout)

        self.btn_restore = QPushButton("🔄 Restaurar Canais Padrão")
        self.btn_restore.setStyleSheet("color: #94A3B8; font-size: 11px; padding: 4px;")
        self.btn_restore.clicked.connect(self._restore_defaults)
        left_layout.addWidget(self.btn_restore)

        splitter.addWidget(left_widget)

        # --- LADO DIREITO: Editor do Canal Selecionado ---
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(6, 0, 0, 0)
        right_layout.setSpacing(8)

        form_group = QGroupBox("Propriedades do Canal Selecionado")
        form_group.setStyleSheet("""
            QGroupBox {
                border: 1px solid #242A34;
                border-radius: 6px;
                margin-top: 8px;
                padding-top: 12px;
                font-weight: bold;
                color: #38BDF8;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 4px;
            }
        """)
        form_layout = QVBoxLayout(form_group)
        form_layout.setSpacing(8)

        # Linha 1: Número, Ícone e Nome
        row1 = QHBoxLayout()
        row1.setSpacing(8)

        col_num = QVBoxLayout()
        lbl_num = QLabel("Número:")
        lbl_num.setStyleSheet("font-size: 11px; color: #94A3B8;")
        self.spin_number = QSpinBox()
        self.spin_number.setRange(1, 99)
        self.spin_number.valueChanged.connect(self._on_form_field_changed)
        col_num.addWidget(lbl_num)
        col_num.addWidget(self.spin_number)
        row1.addLayout(col_num)

        col_icon = QVBoxLayout()
        lbl_icon = QLabel("Ícone:")
        lbl_icon.setStyleSheet("font-size: 11px; color: #94A3B8;")
        self.combo_icon = QComboBox()
        self.combo_icon.setEditable(True)
        icons_presets = ["📺", "🎬", "🍿", "🌀", "🌸", "🔭", "🎙️", "⚡", "🎮", "🛸", "🪐", "🕹️", "⚽", "📚", "🎭", "🎸", "🎵"]
        for ic in icons_presets:
            self.combo_icon.addItem(ic)
        self.combo_icon.currentTextChanged.connect(self._on_form_field_changed)
        col_icon.addWidget(lbl_icon)
        col_icon.addWidget(self.combo_icon)
        row1.addLayout(col_icon)

        col_name = QVBoxLayout()
        lbl_name = QLabel("Nome do Canal:")
        lbl_name.setStyleSheet("font-size: 11px; color: #94A3B8;")
        self.txt_name = QLineEdit()
        self.txt_name.setPlaceholderText("Ex: Filmes Clássicos, Animes Shonen...")
        self.txt_name.textChanged.connect(self._on_form_field_changed)
        col_name.addWidget(lbl_name)
        col_name.addWidget(self.txt_name)
        row1.addLayout(col_name, 1)

        form_layout.addLayout(row1)

        # Linha 2: Modo de Exibição e Categoria
        row2 = QHBoxLayout()
        row2.setSpacing(8)

        col_mode = QVBoxLayout()
        lbl_mode = QLabel("Modo de Reprodução:")
        lbl_mode.setStyleSheet("font-size: 11px; color: #94A3B8;")
        self.combo_mode = QComboBox()
        self.combo_mode.addItem("🎲 Aleatório (Shuffle) — Filmes / Clipes / Variedades", "random")
        self.combo_mode.addItem("🔢 Sequencial (Cronológico) — Séries / Animes / Desenhos", "sequential")
        self.combo_mode.currentIndexChanged.connect(self._on_form_field_changed)
        col_mode.addWidget(lbl_mode)
        col_mode.addWidget(self.combo_mode)
        row2.addLayout(col_mode, 1)

        col_cat = QVBoxLayout()
        lbl_cat = QLabel("Categoria:")
        lbl_cat.setStyleSheet("font-size: 11px; color: #94A3B8;")
        self.combo_category = QComboBox()
        self.combo_category.addItem("Vídeos (Filmes, Séries, Clipes)", "video")
        self.combo_category.addItem("Áudios / Músicas", "audio")
        self.combo_category.addItem("Todos os Tipos", "all")
        self.combo_category.currentIndexChanged.connect(self._on_form_field_changed)
        col_cat.addWidget(lbl_cat)
        col_cat.addWidget(self.combo_category)
        row2.addLayout(col_cat)

        form_layout.addLayout(row2)

        # Linha 3: Grupos de Mídia Vinculados (Equivalências configuradas)
        lbl_groups_title = QLabel("🏷️ Grupos de Mídia Vinculados:")
        lbl_groups_title.setStyleSheet("font-size: 11px; font-weight: bold; color: #E2E8F0; margin-top: 4px;")
        form_layout.addWidget(lbl_groups_title)

        self.groups_container = QWidget()
        self.groups_layout = QHBoxLayout(self.groups_container)
        self.groups_layout.setContentsMargins(2, 2, 2, 2)
        self.groups_layout.setSpacing(8)
        self._build_group_checkboxes()
        form_layout.addWidget(self.groups_container)

        # Linha 4: Pastas Individuais / Específicas
        lbl_folders_title = QLabel("📁 Pastas Específicas / Individuais:")
        lbl_folders_title.setStyleSheet("font-size: 11px; font-weight: bold; color: #E2E8F0; margin-top: 4px;")
        form_layout.addWidget(lbl_folders_title)

        self.folders_list = QListWidget()
        self.folders_list.setStyleSheet("""
            QListWidget {
                background-color: #0E1014;
                border: 1px solid #1E242D;
                border-radius: 4px;
                color: #CBD5E1;
                font-size: 11px;
            }
            QListWidget::item {
                padding: 4px;
                border-bottom: 1px solid #15181E;
            }
        """)
        form_layout.addWidget(self.folders_list, 1)

        folder_btns_layout = QHBoxLayout()
        folder_btns_layout.setSpacing(6)

        self.btn_add_folder = QPushButton("📁 Adicionar Pasta do Windows...")
        self.btn_add_folder.clicked.connect(self._add_folder_to_channel)
        folder_btns_layout.addWidget(self.btn_add_folder)

        self.btn_import_sub = QPushButton("📑 Escolher Subpasta Indexada...")
        self.btn_import_sub.clicked.connect(self._import_subfolder_to_channel)
        folder_btns_layout.addWidget(self.btn_import_sub)

        self.btn_remove_folder = QPushButton("🗑️ Remover Pasta")
        self.btn_remove_folder.clicked.connect(self._remove_folder_from_channel)
        folder_btns_layout.addWidget(self.btn_remove_folder)

        folder_btns_layout.addStretch()
        form_layout.addLayout(folder_btns_layout)

        self.lbl_effective_count = QLabel("Total de Pastas Efetivas: 0")
        self.lbl_effective_count.setStyleSheet("font-size: 10px; color: #38BDF8; font-style: italic;")
        form_layout.addWidget(self.lbl_effective_count)

        right_layout.addWidget(form_group, 1)

        splitter.addWidget(right_widget)
        splitter.setStretchFactor(0, 35)
        splitter.setStretchFactor(1, 65)

        main_layout.addWidget(splitter, 1)

        # Botões de confirmação no rodapé
        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(8)
        bottom_layout.addStretch()

        self.btn_save = QPushButton("💾 Salvar e Aplicar Programação")
        self.btn_save.setObjectName("primary_action_btn")
        self.btn_save.setStyleSheet("padding: 8px 18px; font-weight: bold; font-size: 12px;")
        self.btn_save.clicked.connect(self._save_and_close)
        bottom_layout.addWidget(self.btn_save)

        self.btn_cancel = QPushButton("✕ Cancelar")
        self.btn_cancel.setStyleSheet("padding: 8px 14px; font-size: 12px;")
        self.btn_cancel.clicked.connect(self.reject)
        bottom_layout.addWidget(self.btn_cancel)

        main_layout.addLayout(bottom_layout)

    def _build_group_checkboxes(self):
        """Cria caixas de seleção dinâmicas para os grupos de pastas configurados no MediaFinder."""
        # Limpa layout existente
        for i in reversed(range(self.groups_layout.count())):
            w = self.groups_layout.itemAt(i).widget()
            if w:
                w.setParent(None)

        self.group_checkboxes.clear()
        available_groups = self.config.get_folder_groups()

        for grp_name, paths in available_groups.items():
            count_str = f"({len(paths)})" if paths else "(vazio)"
            chk = QCheckBox(f"{grp_name} {count_str}")
            chk.setStyleSheet("color: #CBD5E1; font-size: 11px;")
            chk.stateChanged.connect(self._on_group_checkbox_changed)
            self.groups_layout.addWidget(chk)
            self.group_checkboxes[grp_name] = chk

        self.groups_layout.addStretch()

    def _populate_channel_list(self):
        """Preenche a lista visual de canais com badges e contagens de pastas."""
        self.channel_list.clear()
        for ch in self.channels_data:
            num = ch.get("number", 1)
            icon = ch.get("icon", "📺")
            name = ch.get("name", "Canal")
            mode = ch.get("mode", "random")
            mode_tag = "🎲 Aleatório" if mode == "random" else "🔢 Sequencial"

            resolved = self.config.resolve_channel_folders(ch.get("folders", []), ch.get("folder_groups", []))
            folders_count = len(resolved)
            folder_info = f" ({folders_count} pasta{'s' if folders_count != 1 else ''})" if folders_count > 0 else " (Geral)"

            item_text = f"CH {num:02d} | {icon} {name} [{mode_tag}]{folder_info}"
            list_item = QListWidgetItem(item_text)
            self.channel_list.addItem(list_item)

    def _on_channel_selected(self, row: int):
        """Carrega os dados do canal selecionado nos campos de edição."""
        if row < 0 or row >= len(self.channels_data):
            return

        self.current_idx = row
        ch = self.channels_data[row]

        # Bloqueia sinais temporariamente para evitar loops
        self.spin_number.blockSignals(True)
        self.combo_icon.blockSignals(True)
        self.txt_name.blockSignals(True)
        self.combo_mode.blockSignals(True)
        self.combo_category.blockSignals(True)

        self.spin_number.setValue(ch.get("number", row + 1))
        self.combo_icon.setCurrentText(ch.get("icon", "📺"))
        self.txt_name.setText(ch.get("name", ""))

        mode_val = ch.get("mode", "random")
        mode_idx = 1 if mode_val == "sequential" else 0
        self.combo_mode.setCurrentIndex(mode_idx)

        cat_val = ch.get("category", "video")
        if cat_val == "audio":
            self.combo_category.setCurrentIndex(1)
        elif cat_val == "all":
            self.combo_category.setCurrentIndex(2)
        else:
            self.combo_category.setCurrentIndex(0)

        # Atualiza checkboxes de grupos
        active_groups = ch.get("folder_groups", [])
        for grp_name, chk in self.group_checkboxes.items():
            chk.blockSignals(True)
            chk.setChecked(grp_name in active_groups)
            chk.blockSignals(False)

        # Preenche lista de pastas específicas
        self.folders_list.clear()
        for folder in ch.get("folders", []):
            self.folders_list.addItem(folder)

        self._update_effective_count_label()

        self.spin_number.blockSignals(False)
        self.combo_icon.blockSignals(False)
        self.txt_name.blockSignals(False)
        self.combo_mode.blockSignals(False)
        self.combo_category.blockSignals(False)

    def _on_group_checkbox_changed(self):
        """Atualiza a lista de grupos vinculados do canal selecionado."""
        if self.current_idx < 0 or self.current_idx >= len(self.channels_data):
            return

        ch = self.channels_data[self.current_idx]
        selected_groups = [grp for grp, chk in self.group_checkboxes.items() if chk.isChecked()]
        ch["folder_groups"] = selected_groups
        self._on_form_field_changed()

    def _update_effective_count_label(self):
        if self.current_idx < 0 or self.current_idx >= len(self.channels_data):
            return
        ch = self.channels_data[self.current_idx]
        resolved = self.config.resolve_channel_folders(ch.get("folders", []), ch.get("folder_groups", []))
        grp_count = len(ch.get("folder_groups", []))
        ind_count = len(ch.get("folders", []))
        self.lbl_effective_count.setText(f"Total de Pastas Efetivas: {len(resolved)} ({grp_count} Grupos selecionados + {ind_count} Pastas individuais)")

    def _on_form_field_changed(self):
        """Atualiza os dados do canal na memória quando o usuário altera um campo."""
        if self.current_idx < 0 or self.current_idx >= len(self.channels_data):
            return

        ch = self.channels_data[self.current_idx]
        ch["number"] = self.spin_number.value()
        ch["icon"] = self.combo_icon.currentText() or "📺"
        ch["name"] = self.txt_name.text().strip() or f"Canal {ch['number']}"
        ch["mode"] = self.combo_mode.currentData() or "random"
        ch["category"] = self.combo_category.currentData() or "video"

        self._update_effective_count_label()

        # Atualiza o texto do item na lista visual
        num = ch["number"]
        icon = ch["icon"]
        name = ch["name"]
        mode_tag = "🎲 Aleatório" if ch["mode"] == "random" else "🔢 Sequencial"
        resolved = self.config.resolve_channel_folders(ch.get("folders", []), ch.get("folder_groups", []))
        folders_count = len(resolved)
        folder_info = f" ({folders_count} pasta{'s' if folders_count != 1 else ''})" if folders_count > 0 else " (Geral)"

        current_item = self.channel_list.item(self.current_idx)
        if current_item:
            current_item.setText(f"CH {num:02d} | {icon} {name} [{mode_tag}]{folder_info}")

    def _add_new_channel(self):
        """Cria um novo canal com numeração sequencial."""
        new_num = len(self.channels_data) + 1
        new_ch = {
            "id": f"ch_custom_{new_num}_{os.urandom(2).hex()}",
            "number": new_num,
            "name": f"Novo Canal {new_num}",
            "icon": "📺",
            "category": "video",
            "mode": "sequential",
            "folders": [],
            "folder_groups": [],
            "auto_filter_tag": None
        }
        self.channels_data.append(new_ch)
        self._populate_channel_list()
        self.channel_list.setCurrentRow(len(self.channels_data) - 1)

    def _remove_selected_channel(self):
        """Remove o canal selecionado após confirmação."""
        if not self.channels_data:
            return

        if len(self.channels_data) <= 1:
            QMessageBox.warning(self, "Aviso", "É necessário manter ao menos 1 canal configurado na TV.")
            return

        ch_name = self.channels_data[self.current_idx].get("name", "este canal")
        reply = QMessageBox.question(
            self,
            "Confirmar Exclusão",
            f"Deseja realmente remover o canal '{ch_name}'?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            del self.channels_data[self.current_idx]
            self._populate_channel_list()
            new_idx = min(self.current_idx, len(self.channels_data) - 1)
            self.channel_list.setCurrentRow(new_idx)

    def _move_channel_up(self):
        if self.current_idx > 0:
            idx = self.current_idx
            self.channels_data[idx], self.channels_data[idx - 1] = self.channels_data[idx - 1], self.channels_data[idx]
            self._populate_channel_list()
            self.channel_list.setCurrentRow(idx - 1)

    def _move_channel_down(self):
        if self.current_idx < len(self.channels_data) - 1:
            idx = self.current_idx
            self.channels_data[idx], self.channels_data[idx + 1] = self.channels_data[idx + 1], self.channels_data[idx]
            self._populate_channel_list()
            self.channel_list.setCurrentRow(idx + 1)

    def _add_folder_to_channel(self):
        """Abre seletor de pastas e adiciona ao canal ativo."""
        if self.current_idx < 0 or self.current_idx >= len(self.channels_data):
            return

        folder = QFileDialog.getExistingDirectory(self, "Selecionar Pasta para o Canal")
        if folder:
            norm_folder = os.path.normpath(folder)
            ch = self.channels_data[self.current_idx]
            folders = ch.get("folders", [])
            if norm_folder not in folders:
                folders.append(norm_folder)
                ch["folders"] = folders
                self.folders_list.addItem(norm_folder)
                self._on_form_field_changed()

    def _import_subfolder_to_channel(self):
        """Permite escolher facilmente entre as subpastas conhecidas indexadas no banco."""
        if self.current_idx < 0 or self.current_idx >= len(self.channels_data):
            return

        if not self.db:
            return

        known_subfolders = self.db.get_indexed_subfolders(limit=300)
        if not known_subfolders:
            QMessageBox.information(self, "Aviso", "Nenhuma subpasta indexada encontrada.")
            return

        item, ok = QInputDialog.getItem(
            self,
            "Escolher Subpasta Indexada",
            "Selecione uma subpasta indexada para este canal:",
            known_subfolders,
            0,
            False
        )
        if ok and item:
            norm = os.path.normpath(item)
            ch = self.channels_data[self.current_idx]
            folders = ch.get("folders", [])
            if norm not in folders:
                folders.append(norm)
                ch["folders"] = folders
                self.folders_list.addItem(norm)
                self._on_form_field_changed()

    def _remove_folder_from_channel(self):
        """Remove a pasta selecionada da lista do canal."""
        if self.current_idx < 0 or self.current_idx >= len(self.channels_data):
            return

        row = self.folders_list.currentRow()
        if row >= 0:
            ch = self.channels_data[self.current_idx]
            folders = ch.get("folders", [])
            if 0 <= row < len(folders):
                del folders[row]
                ch["folders"] = folders
                self.folders_list.takeItem(row)
                self._on_form_field_changed()

    def _restore_defaults(self):
        """Restaura a lista de canais padrão."""
        reply = QMessageBox.question(
            self,
            "Restaurar Padrões",
            "Deseja restaurar todos os canais para a grade temática padrão (7 canais)?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.channels_data = self.config.reset_tv_channels_to_default()
            self._populate_channel_list()
            self.channel_list.setCurrentRow(0)

    def _save_and_close(self):
        """Salva a configuração no disco e fecha."""
        # Garante números de canais consistentes
        for idx, ch in enumerate(self.channels_data):
            if not ch.get("number"):
                ch["number"] = idx + 1

        self.config.set_tv_channels(self.channels_data)
        self.channels_updated.emit()
        self.accept()
