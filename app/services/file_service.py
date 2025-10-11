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

    def delete(self, path: Path) -> None:
        """Delete a note file from disk if it exists."""
        try:
            path.unlink(missing_ok=True)
        except Exception:
            # Propagate minimal surface; caller may show a message
            raise

    def rename(self, old_path: Path, new_path: Path) -> Path:
        """Rename/move a note file on disk. Returns the new path.

        Ensures the target path uses the default extension.
        """
        target = self.ensure_extension(new_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            old_path.rename(target)
        except Exception:
            # If rename fails, surface the error for the UI to handle
            raise
        return target
