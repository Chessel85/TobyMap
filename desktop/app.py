"""Starting the desktop application."""
from __future__ import annotations

import sys
import time


def main(argv: list[str] | None = None) -> int:
    started = time.perf_counter()
    from PySide6.QtWidgets import QApplication

    from desktop.window import MainWindow

    app = QApplication.instance() or QApplication(argv if argv is not None else sys.argv)
    app.setApplicationName("TobyMap")
    window = MainWindow()
    window.session.startup_took((time.perf_counter() - started) * 1000)
    window.show()
    return app.exec()
