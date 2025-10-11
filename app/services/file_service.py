from __future__ import annotations
from pathlib import Path
from typing import Optional

from app.models.note import Note


class FileService:
    """Handles reading and writing markdown notes to the filesystem."""

    def __init__(self, default_extension: str = ".md") -> None:
        self.default_extension = default_extension

    def ensure_extension(self, path: Path) -> Path:
        if path.suffix.lower() != self.default_extension:
            return path.with_suffix(self.default_extension)
        return path

    def read(self, path: Path, encoding: str = "utf-8") -> Note:
        text = path.read_text(encoding=encoding)
        return Note.from_file(path, text)

    def write(
        self, note: Note, path: Optional[Path] = None, encoding: str = "utf-8"
    ) -> Path:
        target = self.ensure_extension(path or (note.file_path or Path(note.title)))
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(note.to_text(), encoding=encoding)
        note.file_path = target
        return target
