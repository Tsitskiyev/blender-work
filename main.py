from __future__ import annotations

import sys
from pathlib import Path

from PyQt6.QtWidgets import QApplication

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.gui import MainWindow


def main() -> None:
    application = QApplication(sys.argv)
    application.setApplicationName("Zero-Template House Generator")
    application.setOrganizationName("ArchGen")
    window = MainWindow()
    window.show()
    sys.exit(application.exec())


if __name__ == "__main__":
    main()
