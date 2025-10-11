from __future__ import annotations
import sys
from pathlib import Path

from app.services.file_service import FileService
from app.ui.main_window import MainWindow


def main() -> int:
    file_service = FileService()
    window = MainWindow(file_service=file_service)
    window.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
