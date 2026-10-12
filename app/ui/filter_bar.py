import sys
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QComboBox,
    QLabel, QButtonGroup, QScrollArea, QFrame, QSizePolicy
)
from PySide6.QtCore import Signal, Qt


class FilterBar(QWidget):
    """Barra de filtros por tipo de mídia, unidade/origem e ordenação responsiva."""

    filters_changed = Signal(str, str, str)  # (categoria, drive_ou_subcat, ordenacao)
    view_mode_changed = Signal(str)          # ("grid" ou "table")

    CATEGORIES = [
        ("video", "🎬 Filmes"),
        ("pluto", "🪐 Pluto TV"),
        ("iptv", "📺 Canais FAST"),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_category = "video"
        self._init_ui()

    def _populate_pluto_categories(self):
        try:
            from app.core.pluto_tv import PlutoTVService
            cats = PlutoTVService.get_instance().get_categories()
            for c in cats:
                icon = "🎬 " if "Filmes" in c else ("📺 " if "Séries" in c else ("🦁 " if "Infantil" in c or "Nickelodeon" in c else ("⚡ " if "Anime" in c else "")))
                self.combo_pluto_cat.addItem(f"{icon}{c}", c)
        except Exception:
            pass

    def _populate_iptv_sources(self):
        self.combo_iptv_source.blockSignals(True)
        self.combo_iptv_source.clear()
        try:
            from app.core.iptv import IPTVService
            svc = IPTVService.get_instance()
            active = svc.get_active_source()
            for src in svc.get_sources():
                self.combo_iptv_source.addItem(src["name"], src["id"])
            idx = self.combo_iptv_source.findData(active)
            if idx >= 0:
                self.combo_iptv_source.setCurrentIndex(idx)
        except Exception:
            pass
        self.combo_iptv_source.blockSignals(False)

    def _populate_iptv_categories(self):
        self.combo_iptv_cat.blockSignals(True)
        self.combo_iptv_cat.clear()
        self.combo_iptv_cat.addItem("📺 Todas as Categorias", "all")
        try:
            from app.core.iptv import IPTVService
            cats = IPTVService.get_instance().get_categories()
            for c in cats:
                icon = "🎬 " if "Filmes" in c else ("📺 " if "Séries" in c else ("📰 " if "Notícias" in c else ("🎭 " if "Cultura" in c else ("⚽ " if "Esportes" in c else ("🧸 " if "Infantil" in c else "")))))
                self.combo_iptv_cat.addItem(f"{icon}{c}", c)
        except Exception:
            pass
        self.combo_iptv_cat.blockSignals(False)

    def _init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 2, 0, 2)
        main_layout.setSpacing(8)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setStyleSheet("background: transparent;")
        scroll_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        chips_container = QWidget()
        chips_container.setStyleSheet("background: transparent;")
        chips_layout = QHBoxLayout(chips_container)
        chips_layout.setContentsMargins(0, 0, 0, 0)
        chips_layout.setSpacing(6)

        self.btn_group = QButtonGroup(self)
        self.btn_group.setExclusive(True)

        self.chip_buttons = {}
        for cat_id, cat_label in self.CATEGORIES:
            btn = QPushButton(cat_label)
            btn.setProperty("class", "filter_chip")
            btn.setCheckable(True)
            btn.setChecked(cat_id == self.current_category)
            btn.clicked.connect(lambda checked=False, cid=cat_id: self._on_category_clicked(cid))
            self.btn_group.addButton(btn)
            self.chip_buttons[cat_id] = btn
            chips_layout.addWidget(btn)

        chips_layout.addStretch(1)
        scroll_area.setWidget(chips_container)
        main_layout.addWidget(scroll_area, 1)

        dropdowns_widget = QWidget()
        dropdowns_widget.setStyleSheet("background: transparent;")
        dropdowns_layout = QHBoxLayout(dropdowns_widget)
        dropdowns_layout.setContentsMargins(0, 0, 0, 0)
        dropdowns_layout.setSpacing(6)

        # Seletor de Categorias da Pluto TV
        self.combo_pluto_cat = QComboBox()
        self.combo_pluto_cat.addItem("🪐 Todas as Categorias", "all")
        self._populate_pluto_categories()
        self.combo_pluto_cat.currentIndexChanged.connect(self._emit_changes)
        self.combo_pluto_cat.setVisible(self.current_category == "pluto")
        dropdowns_layout.addWidget(self.combo_pluto_cat)

        # Seletor de Lista / Fonte IPTV (GitHub Brasil, Filmes 24h, FAST, Customizada)
        self.combo_iptv_source = QComboBox()
        self.combo_iptv_source.setMaximumWidth(230)
        self.combo_iptv_source.setToolTip("Selecione a playlist de canais: Comunidade GitHub, Filmes ou Lista Própria")
        self._populate_iptv_sources()
        self.combo_iptv_source.currentIndexChanged.connect(self._on_iptv_source_changed)
        self.combo_iptv_source.setVisible(self.current_category == "iptv")
        dropdowns_layout.addWidget(self.combo_iptv_source)

        # Botão para importar ou gerenciar lista M3U customizada
        self.btn_iptv_config = QPushButton("⚙️ Lista")
        self.btn_iptv_config.setMaximumWidth(75)
        self.btn_iptv_config.setToolTip("Configurar lista M3U personalizada (URL externa ou arquivo local)")
        self.btn_iptv_config.setStyleSheet("padding: 4px 8px; font-weight: bold;")
        self.btn_iptv_config.clicked.connect(self._open_iptv_dialog)
        self.btn_iptv_config.setVisible(self.current_category == "iptv")
        dropdowns_layout.addWidget(self.btn_iptv_config)

        # Seletor de Categorias de Canais FAST / IPTV
        self.combo_iptv_cat = QComboBox()
        self.combo_iptv_cat.setMaximumWidth(170)
        self.combo_iptv_cat.addItem("📺 Todas as Categorias", "all")
        self._populate_iptv_categories()
        self.combo_iptv_cat.currentIndexChanged.connect(self._emit_changes)
        self.combo_iptv_cat.setVisible(self.current_category == "iptv")
        dropdowns_layout.addWidget(self.combo_iptv_cat)

        self.combo_drive = QComboBox()
        self.combo_drive.addItem("Todas as Unidades", "all")
        self.combo_drive.currentIndexChanged.connect(self._emit_changes)
        self.combo_drive.setVisible(self.current_category not in ("pluto", "iptv"))
        dropdowns_layout.addWidget(self.combo_drive)

        self.combo_sort = QComboBox()
        self.combo_sort.addItem("Nome (A-Z)", "name_asc")
        self.combo_sort.addItem("Nome (Z-A)", "name_desc")
        self.combo_sort.addItem("Tamanho (Maior)", "size_desc")
        self.combo_sort.addItem("Tamanho (Menor)", "size_asc")
        self.combo_sort.addItem("Mais Recentes", "mtime_desc")
        self.combo_sort.currentIndexChanged.connect(self._emit_changes)
        dropdowns_layout.addWidget(self.combo_sort)

        # Botões de alternância Grade / Lista
        self.view_btn_group = QButtonGroup(self)
        self.btn_view_grid = QPushButton("⊞ Grade")
        self.btn_view_grid.setCheckable(True)
        self.btn_view_grid.setChecked(True)
        self.btn_view_grid.setToolTip("Visualização em Grade com miniaturas de filmes e canais")
        self.btn_view_grid.clicked.connect(lambda: self.view_mode_changed.emit("grid"))
        self.view_btn_group.addButton(self.btn_view_grid)
        dropdowns_layout.addWidget(self.btn_view_grid)

        self.btn_view_table = QPushButton("☰ Lista")
        self.btn_view_table.setCheckable(True)
        self.btn_view_table.setToolTip("Visualização clássica em lista/tabela detalhada")
        self.btn_view_table.clicked.connect(lambda: self.view_mode_changed.emit("table"))
        self.view_btn_group.addButton(self.btn_view_table)
        dropdowns_layout.addWidget(self.btn_view_table)

        main_layout.addWidget(dropdowns_widget)

    def _on_iptv_source_changed(self):
        src_id = self.combo_iptv_source.currentData()
        if not src_id:
            return
        from app.core.iptv import IPTVService
        svc = IPTVService.get_instance()
        if src_id == "custom":
            url, _ = svc.get_custom_config()
            if not url:
                self._open_iptv_dialog()
                return

        svc.set_active_source(src_id)
        self._populate_iptv_categories()
        self._update_iptv_chip()
        self._emit_changes()

    def _open_iptv_dialog(self):
        from app.ui.iptv_dialog import ImportM3UDialog
        dlg = ImportM3UDialog(self.window())
        dlg.playlist_updated.connect(self._on_playlist_imported)
        dlg.exec()

    def _on_playlist_imported(self, source_id: str):
        self._populate_iptv_sources()
        idx = self.combo_iptv_source.findData("custom")
        if idx >= 0:
            self.combo_iptv_source.setCurrentIndex(idx)
        else:
            self._on_iptv_source_changed()

    def _update_iptv_chip(self):
        btn = self.chip_buttons.get("iptv")
        if not btn:
            return
        from app.core.iptv import IPTVService
        channels = IPTVService.get_instance().get_channels()
        count = len(channels)
        text = f"📺 Canais FAST ({count})" if count > 0 else "📺 Canais FAST"
        btn.setText(text)

    def update_category_counts(self, stats: dict):
        """Atualiza os contadores em parênteses em cada chip de categoria."""
        total_files = stats.get("total_files", 0)
        cat_counts = stats.get("categories", {})

        def format_count(n: int) -> str:
            if n >= 10000:
                return f"{n/1000:.1f}k"
            elif n >= 1000:
                return f"{n:,}".replace(",", ".")
            return str(n)

        for cat_id, cat_label in self.CATEGORIES:
            btn = self.chip_buttons.get(cat_id)
            if not btn:
                continue

            if cat_id == "pluto":
                from app.core.pluto_tv import PlutoTVService
                service = PlutoTVService.get_instance()
                pluto_count = len(service._cached_channels) if service._cached_channels else 0
                count_str = format_count(pluto_count) if pluto_count > 0 else ""
            elif cat_id == "iptv":
                from app.core.iptv import IPTVService
                channels = IPTVService.get_instance().get_channels()
                iptv_count = len(channels)
                count_str = format_count(iptv_count) if iptv_count > 0 else ""
            elif cat_id == "video":
                c = cat_counts.get("video", 0)
                count_str = format_count(c) if c > 0 else ""
            else:
                c = cat_counts.get(cat_id, 0)
                count_str = format_count(c) if c > 0 else ""

            text = f"{cat_label} ({count_str})" if count_str else cat_label
            btn.setText(text)

    def set_available_drives(self, drives: list[str]):
        """Atualiza a lista de unidades no combobox dinamicamente."""
        current_data = self.combo_drive.currentData()
        self.combo_drive.blockSignals(True)
        self.combo_drive.clear()
        self.combo_drive.addItem("Todas as Unidades", "all")

        for d in sorted(drives):
            if d:
                if sys.platform == "win32" or (len(d) <= 2 and d.endswith(":")):
                    label = f"Drive {d}"
                else:
                    label = f"Unidade: {d}"
                self.combo_drive.addItem(label, d)

        idx = self.combo_drive.findData(current_data)
        if idx >= 0:
            self.combo_drive.setCurrentIndex(idx)
        self.combo_drive.blockSignals(False)

    def set_category(self, cat_id: str):
        """Seleciona programaticamente a categoria."""
        target = cat_id if cat_id in self.chip_buttons else "video"
        if target in self.chip_buttons:
            self.chip_buttons[target].setChecked(True)
            self.current_category = target

    def set_drive(self, drive_str: str):
        """Seleciona programaticamente o drive."""
        idx = self.combo_drive.findData(drive_str)
        if idx >= 0:
            self.combo_drive.setCurrentIndex(idx)

    def _on_category_clicked(self, cat_id: str):
        self.current_category = cat_id
        is_pluto = (cat_id == "pluto")
        is_iptv = (cat_id == "iptv")
        self.combo_pluto_cat.setVisible(is_pluto)
        self.combo_iptv_source.setVisible(is_iptv)
        self.btn_iptv_config.setVisible(is_iptv)
        self.combo_iptv_cat.setVisible(is_iptv)
        self.combo_drive.setVisible(not is_pluto and not is_iptv)
        self._emit_changes()

    def set_view_mode(self, mode: str):
        """Seleciona programaticamente o modo de visualização (grade ou tabela)."""
        self.view_btn_group.blockSignals(True)
        if mode == "table":
            self.btn_view_table.setChecked(True)
        else:
            self.btn_view_grid.setChecked(True)
        self.view_btn_group.blockSignals(False)

    def _emit_changes(self):
        if self.current_category == "pluto":
            sub_filter = self.combo_pluto_cat.currentData() or "all"
        elif self.current_category == "iptv":
            sub_filter = self.combo_iptv_cat.currentData() or "all"
        else:
            sub_filter = self.combo_drive.currentData() or "all"
        sort_by = self.combo_sort.currentData() or "name_asc"
        self.filters_changed.emit(self.current_category, sub_filter, sort_by)
