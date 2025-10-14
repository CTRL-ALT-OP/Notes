from pathlib import Path
import json

from app.services.catalog_service import CatalogService


def test_catalog_persistence_and_basic_ops(tmp_path: Path):
    storage = tmp_path / "catalog.json"
    svc = CatalogService(storage)

    # Initially empty
    assert svc.list_folders() == []

    # Add folder and persist
    f1 = svc.add_folder("Work")
    assert f1.name == "Work"
    assert svc.get_folder(f1.id) is not None

    # Add files (dedup by absolute path)
    a = (tmp_path / "a.md").resolve()
    b = (tmp_path / "b.md").resolve()
    svc.add_files_to_folder(f1.id, [a, a, b])
    folder = svc.get_folder(f1.id)
    assert folder is not None
    assert sorted(x.path for x in folder.files) == sorted([str(a), str(b)])

    # Move file to another folder
    f2 = svc.add_folder("Personal")
    svc.move_file(a, f2.id)
    assert str(a) in {x.path for x in svc.get_folder(f2.id).files}  # type: ignore[union-attr]
    assert str(a) not in {x.path for x in svc.get_folder(f1.id).files}  # type: ignore[union-attr]

    # Update file path
    a2 = (tmp_path / "a2.md").resolve()
    svc.update_file_path(a, a2)
    assert str(a2) in {x.path for x in svc.get_folder(f2.id).files}  # type: ignore[union-attr]

    # Remove file
    svc.remove_file(a2)
    assert str(a2) not in {x.path for x in svc.get_folder(f2.id).files}  # type: ignore[union-attr]

    # Rename and remove folder
    svc.rename_folder(f2.id, "Home")
    assert svc.get_folder(f2.id).name == "Home"  # type: ignore[union-attr]
    svc.remove_folder(f2.id)
    assert svc.get_folder(f2.id) is None

    # File is saved as JSON with expected keys
    data = json.loads(storage.read_text(encoding="utf-8"))
    assert "folders" in data and "next_id" in data
