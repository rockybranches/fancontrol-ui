from __future__ import annotations

import sys

from PyQt6.QtWidgets import QApplication

from fancontrol_ui.window import FanControlWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Fan Control UI")
    window = FanControlWindow()
    window.show()
    return app.exec()

