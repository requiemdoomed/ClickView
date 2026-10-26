"""Native clipboard history with explicit opt-in capture."""

import os
import sys
from pathlib import Path
from datetime import datetime
from PySide6.QtCore import Qt, QSettings, QStandardPaths, QTimer
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPlainTextEdit,
    QComboBox,
    QCheckBox,
    QMessageBox,
    QInputDialog,
    QSplitter,
    QFileDialog,
    QMenu,
)
from .store import Store
from .privacy import foreground_app, allowed, DEFAULT_EXCLUSIONS, looks_sensitive
from .backup import decode_backup, write_backup, MAX_BACKUP

STYLE = """
QWidget {background:#101720;color:#e6edf4;font:14px 'Segoe UI';}
QLineEdit,QPlainTextEdit,QListWidget,QComboBox {background:#182330;border:1px solid #314151;border-radius:8px;padding:10px;selection-background-color:#315e60;}
QPushButton {background:#233542;border:1px solid #3e5461;border-radius:7px;padding:10px 16px;}
QPushButton:hover {background:#34515a;} QPushButton:disabled {color:#667788;}
QListWidget::item {padding:14px;border-bottom:1px solid #283746;}
QListWidget::item:selected {background:#264b4b;}
QLabel#title {font-size:28px;font-weight:700;color:#73e2c0;}
"""

LIGHT_STYLE = STYLE
for dark, light in [
    ("background:#101720;color:#e6edf4", "background:#f3f7f8;color:#172e38"),
    ("#182330", "#ffffff"),
    ("#314151", "#bacbd0"),
    ("#233542", "#e4efed"),
    ("#3e5461", "#acbfc5"),
    ("#34515a", "#cce9df"),
    ("#283746", "#d4e0e4"),
    ("#264b4b", "#d1ece3"),
    ("#73e2c0", "#146d59"),
]:
    LIGHT_STYLE = LIGHT_STYLE.replace(dark, light)


class Window(QMainWindow):
    def __init__(self, store, detector=foreground_app):
        super().__init__()
        self.store, self.detector = store, detector
        self.settings = QSettings("SwayamShakya", "ClipView")
        self.exclusions = str(
            self.settings.value("exclusions", ",".join(DEFAULT_EXCLUSIONS))
        ).split(",")
        self.paused = True
        self.restoring = False
        self.retention_days = int(self.settings.value("retention_days", 0))
        self.secret_guard = self.settings.value("secret_guard", True, type=bool)
        self.light = self.settings.value("light", False, type=bool)
        self.setStyleSheet(LIGHT_STYLE if self.light else STYLE)
        self.setWindowTitle("ClipView · Swayam Shakya")
        self.resize(1100, 720)
        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        title = QLabel("▣  ClipView")
        title.setObjectName("title")
        layout.addWidget(title)
        layout.addWidget(QLabel("A little space for everything worth keeping."))
        toolbar = QHBoxLayout()
        layout.addLayout(toolbar)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search your copied text…  Ctrl+F")
        toolbar.addWidget(self.search, 1)
        self.filter = QComboBox()
        self.filter.addItem("All categories", None)
        toolbar.addWidget(self.filter)
        self.only_pinned = QCheckBox("Pinned only")
        toolbar.addWidget(self.only_pinned)
        self.toggle = QPushButton("Start capture")
        self.toggle.clicked.connect(self.toggle_capture)
        toolbar.addWidget(self.toggle)
        options = QHBoxLayout()
        layout.addLayout(options)
        self.order = QComboBox()
        self.order.addItems(["Newest first", "Oldest first"])
        options.addWidget(self.order)
        self.summary = QLabel()
        options.addWidget(self.summary, 1)
        more = QPushButton("Tools && settings")
        menu = QMenu(more)
        for name, handler in [
            ("Export backup…", self.export_backup),
            ("Import backup…", self.import_backup),
            ("Retention…", self.retention),
            ("Switch light / dark", self.theme),
        ]:
            menu.addAction(name, lambda checked=False, fn=handler: self.safe(fn))
        guard = menu.addAction("Skip common secret patterns")
        guard.setCheckable(True)
        guard.setChecked(self.secret_guard)
        guard.toggled.connect(self.set_secret_guard)
        more.setMenu(menu)
        options.addWidget(more)
        splitter = QSplitter()
        layout.addWidget(splitter, 1)
        self.items = QListWidget()
        self.items.setTextElideMode(Qt.TextElideMode.ElideRight)
        self.items.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        splitter.addWidget(self.items)
        details = QWidget()
        right = QVBoxLayout(details)
        splitter.addWidget(details)
        splitter.setSizes([430, 570])
        self.meta = QLabel("Select a snippet")
        right.addWidget(self.meta)
        self.preview = QPlainTextEdit()
        self.preview.setReadOnly(True)
        right.addWidget(self.preview, 1)
        self.category = QLineEdit()
        self.category.setPlaceholderText("Category")
        self.category.setMaxLength(80)
        right.addWidget(self.category)
        self.pin = QCheckBox("Keep pinned")
        right.addWidget(self.pin)
        actions = QHBoxLayout()
        right.addLayout(actions)
        for label, callback in [
            ("Copy", self.copy),
            ("Edit text", self.edit_text),
            ("Save details", self.save_details),
            ("Delete", self.delete),
        ]:
            button = QPushButton(label)
            button.clicked.connect(lambda checked=False, fn=callback: self.safe(fn))
            actions.addWidget(button)
        footer = QHBoxLayout()
        layout.addLayout(footer)
        for label, callback in [
            ("Add text", self.add_manual),
            ("App exclusions", self.edit_exclusions),
            ("Clear history", self.clear),
        ]:
            button = QPushButton(label)
            button.clicked.connect(lambda checked=False, fn=callback: self.safe(fn))
            footer.addWidget(button)
        self.status = QLabel("Capture paused · start it when you are ready.")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.search.textChanged.connect(lambda: self.safe(self.refresh))
        self.filter.currentTextChanged.connect(lambda: self.safe(self.refresh))
        self.only_pinned.toggled.connect(lambda: self.safe(self.refresh))
        self.order.currentIndexChanged.connect(lambda: self.safe(self.refresh))
        self.items.currentItemChanged.connect(self.select)
        QShortcut(QKeySequence.StandardKey.Find, self, activated=self.search.setFocus)
        QShortcut(
            QKeySequence("Ctrl+N"), self, activated=lambda: self.safe(self.add_manual)
        )
        QApplication.clipboard().dataChanged.connect(self.capture)
        self.cleanup_timer = QTimer(self)
        self.cleanup_timer.setInterval(3600000)
        self.cleanup_timer.timeout.connect(lambda: self.safe(self.cleanup))
        self.cleanup_timer.start()
        self.safe(self.cleanup)

    def safe(self, callback):
        try:
            return callback()
        except ValueError as exc:
            self.status.setText(str(exc))
        except Exception:
            self.paused = True
            self.toggle.setText("Start capture")
            self.status.setText(
                "Operation failed; capture is paused. Check database or file access, then retry. No snippet content was logged."
            )

    def refresh(self):
        selected = self.current()
        category = self.filter.currentData()
        categories = sorted({x["category"] for x in self.store.search()})
        self.filter.blockSignals(True)
        self.filter.clear()
        self.filter.addItem("All categories", None)
        for name in categories:
            self.filter.addItem(name, name)
        self.filter.setCurrentIndex(max(0, self.filter.findData(category)))
        self.filter.blockSignals(False)
        self.items.clear()
        for clip in self.store.search(
            self.search.text(),
            self.filter.currentData(),
            self.only_pinned.isChecked(),
            "oldest" if self.order.currentIndex() else "newest",
        ):
            item = QListWidgetItem(
                ("★  " if clip["pinned"] else "")
                + clip["body"].replace("\n", " ")[:95]
                + "\n"
                + clip["category"]
            )
            item.setData(Qt.ItemDataRole.UserRole, clip)
            self.items.addItem(item)
            if selected and selected["id"] == clip["id"]:
                self.items.setCurrentItem(item)
        if not self.items.currentItem() and self.items.count():
            self.items.setCurrentRow(0)
        self.summary.setText(
            f"{self.items.count()} shown · {len(self.store.search())} saved"
        )

    def current(self):
        item = self.items.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def select(self, *args):
        clip = self.current()
        self.preview.setPlainText(clip["body"] if clip else "")
        self.category.setText(clip["category"] if clip else "")
        self.pin.setChecked(bool(clip and clip["pinned"]))
        self.meta.setText(
            datetime.fromtimestamp(clip["copied"]).strftime("Copied %b %d, %Y · %H:%M")
            if clip
            else "No snippets found"
        )

    def toggle_capture(self):
        self.paused = not self.paused
        self.toggle.setText("Start capture" if self.paused else "Pause capture")
        self.status.setText(
            "Capture paused."
            if self.paused
            else "Listening · excluded and unidentified apps are skipped."
        )

    def capture(self):
        if self.paused or self.restoring:
            return
        app = self.detector()
        if not allowed(app, self.exclusions):
            self.status.setText("Copy skipped: excluded or unidentified application.")
            return

        def save():
            text = QApplication.clipboard().text()
            if self.secret_guard and looks_sensitive(text):
                self.status.setText("Copy skipped: common secret pattern detected.")
                return
            if self.store.add(text):
                self.refresh()
                self.status.setText("Saved to your history.")

        self.safe(save)

    def copy(self):
        clip = self.current()
        if clip:
            self.restoring = True
            try:
                QApplication.clipboard().setText(clip["body"])
            finally:
                self.restoring = False
            self.status.setText("Copied. Paste it wherever you need it.")

    def save_details(self):
        clip = self.current()
        if clip:
            self.store.update(
                clip["id"], pinned=self.pin.isChecked(), category=self.category.text()
            )
            self.refresh()

    def delete(self):
        clip = self.current()
        if (
            clip
            and QMessageBox.question(
                self, "Delete snippet", "Delete this saved snippet?"
            )
            == QMessageBox.StandardButton.Yes
        ):
            self.store.delete(clip["id"])
            self.refresh()

    def add_manual(self):
        text, ok = QInputDialog.getMultiLineText(
            self, "Add text", "Paste or type a snippet:"
        )
        if ok:
            self.store.add(text)
            self.refresh()

    def edit_text(self):
        clip = self.current()
        if not clip:
            return
        text, ok = QInputDialog.getMultiLineText(
            self,
            "Edit snippet",
            "Changes keep this snippet’s date and category.",
            clip["body"],
        )
        if ok:
            self.store.update(
                clip["id"], pinned=clip["pinned"], category=clip["category"], body=text
            )
            self.refresh()

    def export_backup(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Export plain-text backup", "clipview-backup.json", "JSON (*.json)"
        )
        if path:
            write_backup(path, self.store.search())
            self.status.setText(
                "Backup saved. It contains plain text; keep it somewhere private."
            )

    def import_backup(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Import ClipView backup", "", "JSON (*.json)"
        )
        if not path:
            return
        with open(path, "rb") as source:
            raw = source.read(MAX_BACKUP + 1)
        if len(raw) > MAX_BACKUP:
            raise ValueError("Backup exceeds 10 MB.")
        try:
            records = decode_backup(raw.decode("utf-8"))
        except UnicodeError as exc:
            raise ValueError("Backup must be UTF-8 JSON.") from exc
        if (
            QMessageBox.question(
                self,
                "Import backup",
                f"Merge {len(records)} snippets? Existing text and categories will be kept. Automatic age cleanup applies.",
            )
            != QMessageBox.StandardButton.Yes
        ):
            return
        added, skipped = self.store.import_records(records)
        self.cleanup()
        self.status.setText(
            f"Imported {added}; skipped {skipped} duplicates. Age retention applied."
        )

    def retention(self):
        days, ok = QInputDialog.getInt(
            self,
            "History retention",
            "Delete unpinned snippets older than this many days.\n0 keeps them until the count limit is reached.",
            self.retention_days,
            0,
            3650,
        )
        if ok:
            if (
                days
                and QMessageBox.question(
                    self,
                    "Apply retention",
                    "Old unpinned snippets will be permanently deleted. Apply now?",
                )
                != QMessageBox.StandardButton.Yes
            ):
                return
            self.store.expire(days)
            self.retention_days = days
            self.settings.setValue("retention_days", days)
            self.refresh()

    def cleanup(self):
        self.store.expire(self.retention_days)
        self.refresh()

    def theme(self):
        self.light = not self.light
        self.settings.setValue("light", self.light)
        self.setStyleSheet(LIGHT_STYLE if self.light else STYLE)

    def set_secret_guard(self, enabled):
        self.secret_guard = enabled
        self.settings.setValue("secret_guard", enabled)

    def edit_exclusions(self):
        text, ok = QInputDialog.getText(
            self,
            "Excluded applications",
            "Comma-separated app-name fragments. Unknown apps are always skipped.\nBrowser tabs cannot be excluded individually.",
            text=",".join(self.exclusions),
        )
        if ok:
            self.exclusions = text.split(",")
            self.settings.setValue("exclusions", text)

    def clear(self):
        box = QMessageBox(self)
        box.setWindowTitle("Clear history")
        box.setText("Delete saved clipboard history? This cannot be undone.")
        include = QCheckBox("Also delete pinned snippets")
        box.setCheckBox(include)
        box.setStandardButtons(
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel
        )
        if box.exec() == QMessageBox.StandardButton.Yes:
            self.store.clear(include.isChecked())
            self.restoring = True
            try:
                QApplication.clipboard().clear()
            finally:
                self.restoring = False
            self.refresh()
            self.status.setText("History cleared. System clipboard cleared too.")

    def closeEvent(self, event):
        self.paused = True
        self.cleanup_timer.stop()
        QApplication.clipboard().dataChanged.disconnect(self.capture)
        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("ClipView")
    app.setStyleSheet(STYLE)
    folder = Path(
        QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.AppLocalDataLocation
        )
    )
    folder.mkdir(parents=True, exist_ok=True)
    try:
        folder.chmod(0o700)
        mysql = None
        if os.getenv("CLIPVIEW_DB") == "mysql":
            mysql = dict(
                host=os.getenv("CLIPVIEW_MYSQL_HOST", "127.0.0.1"),
                port=int(os.getenv("CLIPVIEW_MYSQL_PORT", "3306")),
                user=os.environ["CLIPVIEW_MYSQL_USER"],
                password=os.environ["CLIPVIEW_MYSQL_PASSWORD"],
                database=os.getenv("CLIPVIEW_MYSQL_DATABASE", "clipview"),
            )
        store = Store(folder / "history.sqlite3", mysql)
    except Exception:
        QMessageBox.critical(
            None,
            "ClipView",
            "Cannot open the database. Check your configuration and server availability.",
        )
        return
    window = Window(store)
    window.show()
    result = app.exec()
    store.close()
    sys.exit(result)
