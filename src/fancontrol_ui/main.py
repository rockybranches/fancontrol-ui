from __future__ import annotations

import sys

from PyQt6.QtWidgets import QApplication

from fancontrol_ui import __version__
from fancontrol_ui.window import FanControlWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Fan Control UI")
    app.setApplicationDisplayName("Fan Control UI")
    app.setApplicationVersion(__version__)
    app.setDesktopFileName("io.github.rockybranches.fancontrol-ui")
    app.setOrganizationName("RockyBranches")
    window = FanControlWindow()
    window.show()
    return app.exec()
