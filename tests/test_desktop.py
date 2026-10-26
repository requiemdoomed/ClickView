import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtWidgets import QApplication
from clipview.app import Window
from clipview.store import Store


def test_real_qt_clipboard_capture_and_restore():
    app = QApplication.instance() or QApplication([])
    store = Store()
    window = Window(store, detector=lambda: "Editor")
    window.toggle_capture()
    for text in ["first", "second", "third SELECT", "fourth", "fifth"]:
        app.clipboard().setText(text)
        app.processEvents()
    assert len(store.search()) == 5
    window.search.setText("third")
    app.processEvents()
    window.copy()
    assert app.clipboard().text() == "third SELECT"
    assert len(store.search()) == 5
    window.paused = True
    app.clipboard().setText("private")
    app.processEvents()
    assert not store.search("private")
    window.paused = False
    window.detector = lambda: "Bitwarden"
    app.clipboard().setText("excluded")
    app.processEvents()
    assert not store.search("excluded")
    window.detector = lambda: None
    app.clipboard().setText("unknown")
    app.processEvents()
    assert not store.search("unknown")
    window.detector = lambda: "Editor"
    window.secret_guard = True
    app.clipboard().setText("-----BEGIN PRIVATE KEY-----")
    app.processEvents()
    assert not store.search("PRIVATE KEY")
    window.close()
    store.close()
