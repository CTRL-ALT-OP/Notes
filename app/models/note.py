from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class Note:
    """Represents a markdown note.

    Attributes:
        title: The user-visible title of the note (derived from filename if absent).
        body: The markdown content of the note.
        file_path: Optional filesystem path where the note is saved.
    """

    title: str
    body: str
    file_path: Optional[Path] = None

    @staticmethod
    def derive_title_from_path(path: Path) -> str:
        stem = path.stem.strip()
        return stem or "Untitled"

    @classmethod
    def from_file(cls, path: Path, content: str) -> "Note":
        return cls(title=cls.derive_title_from_path(path), body=content, file_path=path)

    def to_text(self) -> str:
        """Returns the markdown body suitable for writing to disk."""
        return self.body
