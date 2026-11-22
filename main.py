"""Scrcpy Deck desktop entry point."""
import os
import sys

from PySide6.QtCore import QCoreApplication, QLockFile, Qt, QTimer, QUrl, qWarning
from PySide6.QtGui import QFont, QFontDatabase, QGuiApplication, QIcon
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle

from assets import RESOURCES, VERSION, get_profile_dir, portable_profile_dir
from controller import Deck

if sys.platform == "win32":
    from window_caption import install_windows_caption


def create_engine(deck):
    """Load the same QML shell for source, packaged and UI test entry points."""
    engine = QQmlApplicationEngine()
    def log_warnings(errors):
        for error in errors:
            deck.logs.log("WARN", error.toString())
    engine.warnings.connect(log_warnings)
    engine.rootContext().setContextProperty("deck", deck)
    engine.rootContext().setContextProperty("consoleLog", deck.logs)
    engine.load(QUrl.fromLocalFile(str(RESOURCES / "qml/Main.qml")))
    if sys.platform == "win32" and engine.rootObjects():
        window = engine.rootObjects()[0]
        if window.property("captionHeight"):
            install_windows_caption(window)
    return engine


def run_app():
    portable = portable_profile_dir()
    if portable is not None:
        os.environ["QML_DISK_CACHE_PATH"] = str(portable / "qmlcache")
        QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_DisableShaderDiskCache)
    QQuickStyle.setStyle("Basic")
    app = QGuiApplication(sys.argv)
    app.setApplicationName("Scrcpy Deck")
    app.setApplicationVersion(VERSION)
    icon = QIcon(str(RESOURCES / "assets/icon.ico"))
    app.setWindowIcon(icon)
    missing_assets = ["assets/icon.ico"] if icon.pixmap(32, 32).isNull() else []
    for name in ("Inter-Regular", "Inter-SemiBold", "Inter-Bold", "CascadiaCode-Regular"):
        path = f"fonts/{name}.ttf"
        if QFontDatabase.addApplicationFont(str(RESOURCES / path)) == -1:
            missing_assets.append(path)
    app.setFont(QFont("Inter", 10))
    profile = get_profile_dir()
    profile.mkdir(parents=True, exist_ok=True)
    lock = QLockFile(str(profile / "desktop.lock"))
    if not lock.tryLock(0):
        if sys.platform == "win32":
            import ctypes
            ctypes.windll.user32.MessageBoxW(None, "Scrcpy Deck is already open or its profile is in use.",
                                              "Scrcpy Deck", 0x40)
        return 1
    deck = Deck(profile / "config.json")
    for path in missing_assets:
        deck.logs.log("WARN", f"Could not load {path}")

    def update_color_scheme():
        scheme = Qt.ColorScheme.Dark if deck.settings["appearance"] == "dark" else Qt.ColorScheme.Light
        app.styleHints().setColorScheme(scheme)

    update_color_scheme()
    deck.settingsChanged.connect(update_color_scheme)
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
    if portable == profile:
        try:
            (profile / "console.log").write_text(deck.logs.transcript(), encoding="utf-8")
        except OSError as exc:
            qWarning(f"Could not save the portable console log: {exc}")
    return result


if __name__ == "__main__":
    sys.exit(run_app())
