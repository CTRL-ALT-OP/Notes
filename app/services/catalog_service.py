from __future__ import annotations
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set


@dataclass
class CatalogFile:
    path: str  # absolute path on disk


@dataclass
class CatalogFolder:
    id: str
    name: str
    files: List[CatalogFile]


class CatalogService:
    """Simple JSON-backed catalog of top-level folders and files.

    Notes:
        - Only a single level of folders is supported for simplicity.
        - File entries are stored as absolute path strings.
        - A special non-persisted "Drafts" folder should be rendered by the UI.
    """

    def __init__(self, storage_path: Optional[Path] = None) -> None:
        self.storage_path = storage_path or (
            Path.home() / "markdown_notes_catalog.json"
        )
        self._folders: Dict[str, CatalogFolder] = {}
        self._next_id: int = 1
        self._known_paths: Set[str] = set()
        self.load()

    # ---------- Persistence ----------
    def load(self) -> None:
        if not self.storage_path.exists():
            self._folders = {}
            self._next_id = 1
            self._known_paths = set()
            return
        try:
            data = json.loads(self.storage_path.read_text(encoding="utf-8"))
        except Exception:
            data = {"folders": [], "next_id": 1}
        self._folders = {}
        self._known_paths = set()
        self._next_id = int(data.get("next_id", 1))
        for f in data.get("folders", []):
            folder = CatalogFolder(
                id=str(f.get("id")),
                name=str(f.get("name", "Folder")),
                files=[CatalogFile(path=str(p)) for p in f.get("files", [])],
            )
            self._folders[folder.id] = folder
            for cf in folder.files:
                self._known_paths.add(cf.path)

    def save(self) -> None:
        payload = {
            "next_id": self._next_id,
            "folders": [
                {
                    "id": folder.id,
                    "name": folder.name,
                    "files": [f.path for f in folder.files],
                }
                for folder in self._folders.values()
            ],
        }
        try:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            self.storage_path.write_text(
                json.dumps(payload, indent=2), encoding="utf-8"
            )
        except Exception:
            # Best-effort; ignore failures to persist
            pass

    # ---------- Folder operations ----------
    def add_folder(self, name: str) -> CatalogFolder:
        folder_id = f"f{self._next_id}"
        self._next_id += 1
        folder = CatalogFolder(id=folder_id, name=name.strip() or "Folder", files=[])
        self._folders[folder_id] = folder
        self.save()
        return folder

    def remove_folder(self, folder_id: str) -> None:
        folder = self._folders.pop(folder_id, None)
        if folder is None:
            return
        # Remove paths from known set
        for cf in folder.files:
            self._known_paths.discard(cf.path)
        self.save()

    def list_folders(self) -> List[CatalogFolder]:
        # Stable order by id creation
        return [
            self._folders[k]
            for k in sorted(
                self._folders.keys(),
                key=lambda x: int(x[1:]) if x.startswith("f") else 0,
            )
        ]

    def get_folder(self, folder_id: str) -> Optional[CatalogFolder]:
        return self._folders.get(folder_id)

    # ---------- File operations ----------
    def add_files_to_folder(self, folder_id: str, paths: List[Path]) -> None:
        folder = self._folders.get(folder_id)
        if not folder:
            return
        changed = False
        for p in paths:
            abs_path = str(p.resolve())
            if abs_path in self._known_paths:
                continue
            folder.files.append(CatalogFile(path=abs_path))
            self._known_paths.add(abs_path)
            changed = True
        if changed:
            self.save()

    def move_file(self, file_path: Path, to_folder_id: str) -> None:
        target = self._folders.get(to_folder_id)
        if not target:
            return
        abs_path = str(file_path.resolve())
        if abs_path not in self._known_paths:
            # Unknown path; treat as add
            target.files.append(CatalogFile(path=abs_path))
            self._known_paths.add(abs_path)
            self.save()
            return
        # Remove from any existing folder
        removed = False
        for folder in self._folders.values():
            for i, cf in list(enumerate(folder.files)):
                if cf.path == abs_path:
                    del folder.files[i]
                    removed = True
                    break
            if removed:
                break
        # Add into target
        target.files.append(CatalogFile(path=abs_path))
        self.save()

    def remove_file(self, file_path: Path) -> None:
        abs_path = str(file_path.resolve())
        removed = False
        for folder in self._folders.values():
            for i, cf in list(enumerate(folder.files)):
                if cf.path == abs_path:
                    del folder.files[i]
                    removed = True
                    break
            if removed:
                break
        if removed:
            self._known_paths.discard(abs_path)
            self.save()
