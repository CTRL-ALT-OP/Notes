from __future__ import annotations
from app.services.file_service import FileService
from app.services.draft_service import DraftService
from app.ui.main_window import MainWindow


def main() -> int:
    file_service = FileService()
    draft_service = DraftService()
    window = MainWindow(file_service=file_service, draft_service=draft_service)
    window.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
