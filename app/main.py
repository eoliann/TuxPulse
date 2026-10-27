# #!/usr/bin/env python3
# # app/main.py - wrapper simplu
# import sys
# from PyQt5.QtWidgets import QApplication
# from PyQt5.QtCore import QTimer

# from ui_main import MainWindow

# def main():
#     app = QApplication(sys.argv)
#     app.setApplicationName('TuxPulse')
#     app.setStyle('Fusion')

#     window = MainWindow()
#     window.show()

#     if hasattr(window, 'update_monitoring'):
#         timer = QTimer()
#         timer.timeout.connect(window.update_monitoring)
#         timer.start(1000)

#     sys.exit(app.exec_())

# if __name__ == '__main__':
#     main()


# app/main.py
import sys
from pathlib import Path
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication
from ui_main import MainWindow

APP_DESKTOP_ID = "tuxpulse-classic"   # trebuie să fie EXACT numele fișierului .desktop fără extensie
APP_ICON_PATHS = [
    Path(__file__).resolve().parent / "assets" / "tuxpulse.png",
    Path("/usr/share/icons/hicolor/256x256/apps/tuxpulse-classic.png"),
    Path("/usr/share/icons/hicolor/256x256/apps/tuxpulse.png"),
    Path("/usr/share/pixmaps/tuxpulse.png"),
]

def load_app_icon() -> QIcon:
    for path in APP_ICON_PATHS:
        if path.exists():
            return QIcon(str(path))
    return QIcon()

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("TuxPulse")
    app.setApplicationDisplayName("TuxPulse Classic")
    app.setDesktopFileName(APP_DESKTOP_ID)

    icon = load_app_icon()
    if not icon.isNull():
        app.setWindowIcon(icon)

    window = MainWindow()
    if not icon.isNull():
        window.setWindowIcon(icon)

    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()