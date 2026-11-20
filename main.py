"""Scrcpy Deck desktop entry point."""
import os
import sys
from pathlib import Path

from PySide6.QtCore import QLockFile, QStandardPaths, QTimer, QUrl
from PySide6.QtGui import QFont, QFontDatabase, QGuiApplication, QIcon
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle

from assets import RESOURCES, VERSION
from controller import Deck


def create_engine(deck):
    """Load the same QML shell for source, packaged and UI test entry points."""
    engine = QQmlApplicationEngine()
    engine.warnings.connect(lambda errors: [deck.logs.log("WARN", e.toString()) for e in errors])
    engine.rootContext().setContextProperty("deck", deck)
    engine.rootContext().setContextProperty("consoleLog", deck.logs)
    engine.load(QUrl.fromLocalFile(str(RESOURCES / "qml/Main.qml")))
    return engine


def run_app():
    QQuickStyle.setStyle("Basic")
    app = QGuiApplication(sys.argv)
    app.setApplicationName("Scrcpy Deck")
    app.setApplicationVersion(VERSION)
    app.setWindowIcon(QIcon(str(RESOURCES / "assets/icon.ico")))
    for name in ("Nunito-Regular", "Nunito-Bold", "CascadiaCode-Regular"):
        QFontDatabase.addApplicationFont(str(RESOURCES / f"fonts/{name}.ttf"))
    app.setFont(QFont("Nunito", 10))
    profile = Path(os.environ.get("SCRCPY_DECK_PROFILE_DIR") or
                   QStandardPaths.writableLocation(QStandardPaths.AppLocalDataLocation))
    profile.mkdir(parents=True, exist_ok=True)
    lock = QLockFile(str(profile / "desktop.lock"))
    if not lock.tryLock(0):
        if sys.platform == "win32":
            import ctypes
            ctypes.windll.user32.MessageBoxW(None, "Scrcpy Deck is already open or its profile is in use.",
                                              "Scrcpy Deck", 0x40)
        return 1
    deck = Deck(profile / "config.json")
    engine = create_engine(deck)
    if not engine.rootObjects():
        deck.logs.flush()
        message = deck.logs.transcript() or "The Qt Quick window could not be loaded."
        (profile / "startup-error.log").write_text(message, encoding="utf-8")
        if sys.platform == "win32":
            import ctypes
            ctypes.windll.user32.MessageBoxW(None, message[-2000:], "Scrcpy Deck startup error", 0x10)
        return 1
    app.aboutToQuit.connect(deck.shutdown)
    QTimer.singleShot(0, deck.startup)
    result = app.exec()
    del engine
    return result


if __name__ == "__main__":
    sys.exit(run_app())
