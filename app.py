import os
import sys


def main() -> int:
    if getattr(sys, "frozen", False):
        app_root = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    else:
        app_root = os.path.abspath(os.path.dirname(__file__))
    if app_root not in sys.path:
        sys.path.insert(0, app_root)

    from PySide6.QtWidgets import QApplication

    from core.config_loader import get_app_root, load_commands
    from core.logger import AppLogger
    from ui.main_window import MainWindow

    app = QApplication([])
    app_root = get_app_root()
    commands = load_commands(app_root)
    logger = AppLogger(app_root)

    window = MainWindow(commands, logger, app_root)
    window.show()

    exit_code = app.exec()
    if exit_code == 1000:
        if getattr(sys, "frozen", False):
            os.execl(sys.executable, sys.executable)
        else:
            os.execl(sys.executable, sys.executable, *sys.argv)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
