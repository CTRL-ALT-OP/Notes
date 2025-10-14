from pathlib import Path

from app.models.note import Note
from app.services.file_service import FileService


def test_file_service_read_write_rename_delete(tmp_path: Path):
    svc = FileService(default_extension=".md")

    note = Note(title="My Note", body="# Hello")
    out = svc.write(note, tmp_path / "note")
    assert out.suffix == ".md"
    assert out.exists()
    assert note.file_path == out

    # Read back
    read = svc.read(out)
    assert read.title == "note"
    assert read.body == "# Hello"

    # Rename
    new_path = tmp_path / "renamed.md"
    moved = svc.rename(out, new_path)
    assert moved == new_path
    assert moved.exists()
    assert not out.exists()

    # Delete
    svc.delete(moved)
    assert not moved.exists()
