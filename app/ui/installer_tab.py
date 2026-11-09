from PyQt5.QtCore import QEasingCurve, QPropertyAnimation, pyqtSignal, Qt
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

CARD_COLOR_MAP = {
    "green": "#1f7a5c",
    "blue": "#10304d",
    "orange": "#7a4b00",
    "purple": "#2f1d46",
    "white": "#111827",
    "red": "#3a1212",
}


class SmoothScrollArea(QScrollArea):
    def __init__(self):
        super().__init__()
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.NoFrame)
        self.verticalScrollBar().setSingleStep(24)
        self._wheel_animation = QPropertyAnimation(self.verticalScrollBar(), b"value", self)
        self._wheel_animation.setDuration(140)
        self._wheel_animation.setEasingCurve(QEasingCurve.OutCubic)

    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        if delta == 0:
            super().wheelEvent(event)
            return

        bar = self.verticalScrollBar()
        steps = delta / 120.0
        distance = int(round(steps * bar.singleStep() * 3))
        target = bar.value() - distance
        target = max(bar.minimum(), min(bar.maximum(), target))

        self._wheel_animation.stop()
        self._wheel_animation.setStartValue(bar.value())
        self._wheel_animation.setEndValue(target)
        self._wheel_animation.start()
        event.accept()


class SelectButton(QPushButton):
    toggled_state = pyqtSignal(bool)

    def __init__(self):
        super().__init__("✓")
        self.setCheckable(True)
        self.setFixedSize(24, 24)
        self.setCursor(Qt.PointingHandCursor)
        self.toggled.connect(self._emit_and_refresh)
        self._refresh_style()

    def _emit_and_refresh(self, checked: bool):
        self._refresh_style()
        self.toggled_state.emit(checked)

    def _refresh_style(self):
        if self.isChecked():
            self.setStyleSheet(
                """
                QPushButton {
                    min-width: 24px;
                    max-width: 24px;
                    min-height: 24px;
                    max-height: 24px;
                    background: #22c55e;
                    color: white;
                    border: 2px solid #ffffff;
                    border-radius: 6px;
                    font-size: 14px;
                    font-weight: bold;
                    padding: 0px;
                }
                """
            )
        else:
            self.setStyleSheet(
                """
                QPushButton {
                    min-width: 24px;
                    max-width: 24px;
                    min-height: 24px;
                    max-height: 24px;
                    background: #ffffff;
                    color: transparent;
                    border: 2px solid #cbd5e1;
                    border-radius: 6px;
                    padding: 0px;
                }
                """
            )


class InstallerCard(QFrame):
    toggled = pyqtSignal(str, bool)
    install_requested = pyqtSignal(str)
    remove_requested = pyqtSignal(str)
    update_requested = pyqtSignal(str)
    source_changed = pyqtSignal(str, str)

    def __init__(self, app: dict):
        super().__init__()
        self.app = app
        self._texts = {}
        self.setObjectName("InstallerCard")

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        top = QHBoxLayout()
        top.setSpacing(10)

        self.check = SelectButton()
        self.check.toggled_state.connect(lambda checked: self.toggled.emit(self.app["id"], checked))
        top.addWidget(self.check, 0, Qt.AlignTop)

        icon_label = QLabel()
        icon = QIcon.fromTheme(app.get("icon") or "application-x-executable")
        icon_label.setPixmap(icon.pixmap(28, 28))
        top.addWidget(icon_label, 0, Qt.AlignTop)

        text_col = QVBoxLayout()
        text_col.setSpacing(4)
        self.name_label = QLabel(app["name"])
        self.name_label.setObjectName("SectionTitle")
        self.desc_label = QLabel(app.get("description", ""))
        self.desc_label.setWordWrap(True)
        self.meta_label = QLabel()
        self.meta_label.setObjectName("Subtitle")
        self.meta_label.setWordWrap(True)
        self.extra_label = QLabel()
        self.extra_label.setObjectName("Subtitle")
        self.extra_label.setWordWrap(True)
        text_col.addWidget(self.name_label)
        text_col.addWidget(self.desc_label)
        text_col.addWidget(self.meta_label)
        text_col.addWidget(self.extra_label)
        top.addLayout(text_col, 1)

        actions = QVBoxLayout()
        actions.setSpacing(6)

        self.status_label = QLabel()
        self.status_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.status_label.setMinimumWidth(180)

        btn_row = QHBoxLayout()
        self.install_btn = QPushButton("Install")
        self.remove_btn = QPushButton("Remove")
        self.update_btn = QPushButton("Update")
        self.install_btn.clicked.connect(lambda: self.install_requested.emit(self.app["id"]))
        self.remove_btn.clicked.connect(lambda: self.remove_requested.emit(self.app["id"]))
        self.update_btn.clicked.connect(lambda: self.update_requested.emit(self.app["id"]))
        btn_row.addWidget(self.install_btn)
        btn_row.addWidget(self.remove_btn)
        btn_row.addWidget(self.update_btn)

        actions.addWidget(self.status_label)
        actions.addLayout(btn_row)
        top.addLayout(actions)

        root.addLayout(top)

        source_row = QHBoxLayout()
        self.source_label = QLabel("Source:")
        source_row.addWidget(self.source_label)

        self.native_radio = QRadioButton("Native")
        self.flatpak_radio = QRadioButton("Flatpak")
        self.source_group = QButtonGroup(self)
        self.source_group.addButton(self.native_radio)
        self.source_group.addButton(self.flatpak_radio)

        self.native_radio.toggled.connect(self._emit_source_changed)
        self.flatpak_radio.toggled.connect(self._emit_source_changed)

        source_row.addWidget(self.native_radio)
        source_row.addWidget(self.flatpak_radio)
        source_row.addStretch(1)

        root.addLayout(source_row)
        self.update_data(app)

    def set_texts(self, texts: dict):
        self._texts = texts or {}
        self.install_btn.setText(self._texts.get("install", "Install"))
        self.remove_btn.setText(self._texts.get("remove", "Remove"))
        self.update_btn.setText(self._texts.get("update", "Update"))
        self.source_label.setText(self._texts.get("source", "Source:"))
        self.native_radio.setText(self._texts.get("native", "Native"))
        self.flatpak_radio.setText(self._texts.get("flatpak", "Flatpak"))
        self._apply_card_text_style()
        self._apply_state_label()

    def _status_text(self) -> str:
        ui = self.app.get("ui", {})
        key = ui.get("status_key")

        if key == "installer_update_available":
            return self._texts.get("update_available", "Update available")
        if key == "installer_installed_native":
            return self._texts.get("installed_native", "Installed (native)")
        if key == "installer_installed_flatpak":
            return self._texts.get("installed_flatpak", "Installed (Flatpak)")
        if key == "installer_available_flatpak":
            return self._texts.get("available_flatpak", "Available via Flatpak")
        if key == "installer_unavailable":
            return self._texts.get("unavailable", "Unavailable")
        return self._texts.get("available", "Available")

    def _apply_card_text_style(self):
        self.name_label.setStyleSheet(
            "color: #f8fafc; background: transparent; border: none; font-size: 16px; font-weight: bold;"
        )
        self.desc_label.setStyleSheet(
            "color: #e5e7eb; background: transparent; border: none;"
        )
        self.meta_label.setStyleSheet(
            "color: #cbd5e1; background: transparent; border: none;"
        )
        self.extra_label.setStyleSheet(
            "color: #fde68a; background: transparent; border: none; font-weight: bold;"
        )
        self.source_label.setStyleSheet(
            "color: #e5e7eb; background: transparent; border: none; font-weight: bold;"
        )
        self.native_radio.setStyleSheet(
            "QRadioButton { color: #f8fafc; background: transparent; }"
        )
        self.flatpak_radio.setStyleSheet(
            "QRadioButton { color: #f8fafc; background: transparent; }"
        )

    def _apply_state_label(self):
        ui = self.app.get("ui", {})
        color_name = ui.get("color_name", "white")
        status_text = self._status_text()
        badge = ui.get("badge", "")

        if color_name == "white":
            pill_bg = "#1f2937"
        else:
            pill_bg = {
                "green": "#166534",
                "orange": "#a16207",
                "red": "#b91c1c",
                "blue": "#1d4ed8",
                "purple": "#6d28d9",
            }.get(color_name, "#334155")

        self.status_label.setText(f"{badge} {status_text}".strip())
        self.status_label.setStyleSheet(
            f"""
            QLabel {{
                background: {pill_bg};
                color: white;
                border: 1px solid rgba(255,255,255,0.15);
                border-radius: 10px;
                padding: 6px 10px;
                font-weight: bold;
            }}
            """
        )

    def _emit_source_changed(self):
        if self.native_radio.isChecked():
            self.source_changed.emit(self.app["id"], "native")
        elif self.flatpak_radio.isChecked():
            self.source_changed.emit(self.app["id"], "flatpak")

    def _apply_card_style(self):
        ui = self.app.get("ui", {})
        color_name = ui.get("color_name", "white")
        bg = CARD_COLOR_MAP.get(color_name, "#111827")
        border = ui.get("border", "#1f2937")

        self.setStyleSheet(
            f"""
            QFrame#InstallerCard {{
                background: {bg};
                border: 2px solid {border};
                border-radius: 14px;
            }}
            """
        )
        self._apply_card_text_style()

    def update_data(self, app: dict):
        self.app = app
        self.name_label.setText(app["name"])
        self.desc_label.setText(app.get("description", ""))
        self._apply_card_style()

        native_text = app.get("native_package") if app.get("native_available") else self._texts.get("not_available", "not available")
        flatpak_text = app.get("flatpak") if app.get("flatpak_available") else self._texts.get("not_available", "not available")

        native_label = self._texts.get("meta_native", "Native")
        flatpak_label = self._texts.get("meta_flatpak", "Flatpak")
        self.meta_label.setText(f"{native_label}: {native_text}    |    {flatpak_label}: {flatpak_text}")

        repo_hint = ""
        if app.get("repo_missing"):
            repo_hint = self._texts.get("repo_missing", "External repo missing")
        self.extra_label.setText(repo_hint)
        self.extra_label.setVisible(bool(repo_hint))

        native_available = bool(app.get("native_available"))
        flatpak_available = bool(app.get("flatpak_available"))

        self.native_radio.setEnabled(native_available)
        self.flatpak_radio.setEnabled(flatpak_available)

        preferred = app.get("source", "native")
        if preferred == "flatpak" and flatpak_available:
            self.flatpak_radio.setChecked(True)
        elif preferred == "native" and native_available:
            self.native_radio.setChecked(True)
        elif native_available:
            self.native_radio.setChecked(True)
        elif flatpak_available:
            self.flatpak_radio.setChecked(True)
        else:
            self.native_radio.setAutoExclusive(False)
            self.flatpak_radio.setAutoExclusive(False)
            self.native_radio.setChecked(False)
            self.flatpak_radio.setChecked(False)
            self.native_radio.setAutoExclusive(True)
            self.flatpak_radio.setAutoExclusive(True)

        selected = bool(app.get("selected"))
        self.check.blockSignals(True)
        self.check.setChecked(selected)
        self.check.blockSignals(False)
        self.check._refresh_style()

        self._apply_state_label()

        ui = app.get("ui", {})
        self.check.setEnabled(any(ui.get(action) for action in ("can_install", "can_remove", "can_update")))
        self.install_btn.setEnabled(bool(ui.get("can_install")))
        self.remove_btn.setEnabled(bool(ui.get("can_remove")))
        self.update_btn.setEnabled(bool(ui.get("can_update")))
        self.update_btn.setText(self._texts.get("update", "Update"))


class InstallerTab(QWidget):
    search_changed = pyqtSignal(str)
    install_selected_requested = pyqtSignal()
    remove_selected_requested = pyqtSignal()
    update_selected_requested = pyqtSignal()
    install_one_requested = pyqtSignal(str)
    remove_one_requested = pyqtSignal(str)
    update_one_requested = pyqtSignal(str)
    source_changed = pyqtSignal(str, str)

    def __init__(self):
        super().__init__()
        self.cards = {}
        self._card_texts = {}
        self._stats_texts = {}
        self._grouped_apps = {}
        self._selection_state = {}
        self._app_cache = {}

        layout = QVBoxLayout(self)

        self.title = QLabel()
        self.title.setObjectName("SectionTitle")

        self.subtitle = QLabel()
        self.subtitle.setObjectName("Subtitle")
        self.subtitle.setWordWrap(True)

        toolbar = QHBoxLayout()
        self.search = QLineEdit()
        self.install_selected_btn = QPushButton()
        self.remove_selected_btn = QPushButton()
        self.update_selected_btn = QPushButton()
        toolbar.addWidget(self.search, 1)
        toolbar.addWidget(self.install_selected_btn)
        toolbar.addWidget(self.remove_selected_btn)
        toolbar.addWidget(self.update_selected_btn)

        self.status_label = QLabel()
        self.status_label.setObjectName("Subtitle")
        self.status_label.setWordWrap(True)

        self.stats_label = QLabel()
        self.stats_label.setObjectName("Subtitle")
        self.stats_label.setWordWrap(True)
        self.stats_label.setStyleSheet(
            """
            QLabel {
                background: #0b1220;
                border: 1px solid #243041;
                border-radius: 10px;
                padding: 8px 10px;
                color: #cbd5e1;
                font-weight: bold;
            }
            """
        )

        self.scroll = SmoothScrollArea()

        self.container = QWidget()
        self.cards_layout = QVBoxLayout(self.container)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        self.cards_layout.setSpacing(10)
        self.cards_layout.addStretch(1)

        self.scroll.setWidget(self.container)

        layout.addWidget(self.title)
        layout.addWidget(self.subtitle)
        layout.addLayout(toolbar)
        layout.addWidget(self.status_label)
        layout.addWidget(self.stats_label)
        layout.addWidget(self.scroll, 1)

        self.search.textChanged.connect(self.search_changed.emit)
        self.install_selected_btn.clicked.connect(self.install_selected_requested.emit)
        self.remove_selected_btn.clicked.connect(self.remove_selected_requested.emit)
        self.update_selected_btn.clicked.connect(self.update_selected_requested.emit)

    def set_texts(self, texts: dict):
        self.title.setText(texts.get("title", "Installer"))
        self.subtitle.setText(texts.get("subtitle", "Install software from native repositories or Flatpak."))
        self.search.setPlaceholderText(texts.get("search_placeholder", "Search applications..."))
        self.install_selected_btn.setText(texts.get("install_selected", "Install selected"))
        self.remove_selected_btn.setText(texts.get("remove_selected", "Remove selected"))
        self.update_selected_btn.setText(texts.get("update_selected", "Update selected"))

        if texts.get("status") is not None:
            self.status_label.setText(texts.get("status"))

        self._card_texts = {
            "install": texts.get("install", "Install"),
            "remove": texts.get("remove", "Remove"),
            "update": texts.get("update", "Update"),
            "source": texts.get("source", "Source:"),
            "native": texts.get("native", "Native"),
            "flatpak": texts.get("flatpak", "Flatpak"),
            "installed_native": texts.get("installed_native", "Installed (native)"),
            "installed_flatpak": texts.get("installed_flatpak", "Installed (Flatpak)"),
            "available": texts.get("available", "Available"),
            "not_available": texts.get("not_available", "not available"),
            "available_flatpak": texts.get("available_flatpak", "Available via Flatpak"),
            "unavailable": texts.get("unavailable", "Unavailable"),
            "update_available": texts.get("update_available", "Update available"),
            "repo_missing": texts.get("repo_missing", "External repo missing"),
            "meta_native": texts.get("meta_native", "Native"),
            "meta_flatpak": texts.get("meta_flatpak", "Flatpak"),
        }

        self._stats_texts = {
            "total": texts.get("stats_total", "Total"),
            "installed": texts.get("stats_installed", "Installed"),
            "not_installed": texts.get("stats_not_installed", "Not installed"),
            "selected": texts.get("stats_selected", "Selected"),
        }

        for card in self.cards.values():
            card.set_texts(self._card_texts)
            card.update_data(card.app)

        self._refresh_stats()
        self._refresh_update_button_label()

    def populate(self, grouped_apps: dict):
        self._grouped_apps = grouped_apps or {}
        self.container.setUpdatesEnabled(False)
        self.scroll.viewport().setUpdatesEnabled(False)

        try:
            while self.cards_layout.count() > 1:
                item = self.cards_layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()

            self.cards = {}

            for category, apps in grouped_apps.items():
                section = QLabel(category)
                section.setObjectName("SectionTitle")
                self.cards_layout.insertWidget(self.cards_layout.count() - 1, section)

                for raw_app in apps:
                    app = dict(raw_app)
                    app_id = app.get("id")
                    saved = self._selection_state.get(app_id, {})

                    if saved.get("source") in {"native", "flatpak"}:
                        app["source"] = saved["source"]
                    if saved.get("selected"):
                        app["selected"] = True

                    if app_id:
                        self._app_cache[app_id] = dict(app)

                    card = InstallerCard(app)
                    card.set_texts(self._card_texts)
                    card.toggled.connect(self._on_card_toggled)
                    card.install_requested.connect(self.install_one_requested.emit)
                    card.remove_requested.connect(self.remove_one_requested.emit)
                    card.update_requested.connect(self.update_one_requested.emit)
                    card.source_changed.connect(self._on_card_source_changed)

                    self.cards_layout.insertWidget(self.cards_layout.count() - 1, card)
                    self.cards[app["id"]] = card
        finally:
            self.container.setUpdatesEnabled(True)
            self.scroll.viewport().setUpdatesEnabled(True)

        self._refresh_stats()
        self._refresh_bulk_buttons()

    def _on_card_toggled(self, app_id: str, checked: bool):
        card = self.cards.get(app_id)
        if card is not None:
            card.app["selected"] = checked
            source = "flatpak" if card.flatpak_radio.isChecked() else "native"
            self._selection_state[app_id] = {
                "selected": checked,
                "source": source,
                "app": dict(card.app),
            }
            self._app_cache[app_id] = dict(card.app)
        elif app_id in self._selection_state:
            self._selection_state[app_id]["selected"] = checked

        self._refresh_stats()
        self._refresh_bulk_buttons()


    def _on_card_source_changed(self, app_id: str, source: str):
        card = self.cards.get(app_id)
        if card is not None:
            card.app["source"] = source
            current = self._selection_state.get(app_id, {})
            current["source"] = source
            current["selected"] = bool(card.check.isChecked())
            current["app"] = dict(card.app)
            self._selection_state[app_id] = current
            self._app_cache[app_id] = dict(card.app)
        self.source_changed.emit(app_id, source)

    def _selected_counts(self):
        installable = 0
        removable = 0
        updatable = 0

        for app in self.selected_apps():
            ui = app.get("ui", {})
            if ui.get("can_install"):
                installable += 1
            if ui.get("can_remove"):
                removable += 1
            if ui.get("can_update"):
                updatable += 1

        return installable, removable, updatable

    def _refresh_stats(self):
        total = len(self.cards)
        installed = 0
        selected = sum(1 for item in self._selection_state.values() if item.get("selected"))

        for card in self.cards.values():
            state = card.app.get("state", "")
            if state.startswith("installed"):
                installed += 1

        not_installed = max(0, total - installed)

        total_label = self._stats_texts.get("total", "Total")
        installed_label = self._stats_texts.get("installed", "Installed")
        not_installed_label = self._stats_texts.get("not_installed", "Not installed")
        selected_label = self._stats_texts.get("selected", "Selected")

        self.stats_label.setText(
            f"{total_label}: {total}    |    "
            f"{installed_label}: {installed}    |    "
            f"{not_installed_label}: {not_installed}    |    "
            f"{selected_label}: {selected}"
        )

    def _set_bulk_button_state(self, button: QPushButton, base_text: str, count: int):
        button.setEnabled(count > 0)
        button.setText(f"{base_text} ({count})" if count > 0 else base_text)

    def _refresh_bulk_buttons(self):
        install_count, remove_count, update_count = self._selected_counts()
        self._set_bulk_button_state(self.install_selected_btn, self.install_selected_btn.text().split(" (", 1)[0], install_count)
        self._set_bulk_button_state(self.remove_selected_btn, self.remove_selected_btn.text().split(" (", 1)[0], remove_count)
        self._set_bulk_button_state(self.update_selected_btn, self.update_selected_btn.text().split(" (", 1)[0], update_count)

    def _refresh_update_button_label(self):
        self._refresh_bulk_buttons()

    def selected_apps(self):
        apps = []
        for app_id, item in self._selection_state.items():
            if not item.get("selected"):
                continue

            app = dict(item.get("app") or self._app_cache.get(app_id) or {})
            if not app:
                continue

            source = item.get("source")
            if source in {"native", "flatpak"}:
                app["source"] = source

            app["selected"] = True
            apps.append(app)
        return apps
