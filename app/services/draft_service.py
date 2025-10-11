from __future__ import annotations
import contextlib
import os
from pathlib import Path
from typing import Optional


class DraftService:
    """Manages per-instance draft storage and simple instance slot locking.

    Each app process claims the lowest available instance index by creating a
    lock file. Draft text is stored in a file per instance index, so that
    multiple processes can persist independent drafts and restore them in a
    stable order across restarts.
    """

    def __init__(
        self, base_dir: Optional[Path] = None, max_instances: int = 50
    ) -> None:
        # Default to a user-home drafts directory so drafts persist regardless of CWD
        self.base_dir = base_dir or (Path.home() / "markdown_notes_drafts")
        self.max_instances = max_instances
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _lock_path(self, index: int) -> Path:
        return self.base_dir / f"instance_{index}.lock"

    def _draft_path(self, index: int) -> Path:
        return self.base_dir / f"draft_{index}.md"

    def claim_instance_index(self) -> int:
        """Claim the lowest available instance index by creating a lock file.

        Returns the claimed index starting at 1.
        """
        pid_str = str(os.getpid())
        for index in range(1, self.max_instances + 1):
            lock_path = self._lock_path(index)
            try:
                # 'x' ensures exclusive creation; fails if already exists
                with lock_path.open("x", encoding="utf-8") as f:
                    f.write(pid_str)
                return index
            except FileExistsError:
                continue
        # Fallback: if all slots are taken, use the last one non-exclusively
        # (very unlikely in typical usage). This ensures the app can still run.
        last_lock = self._lock_path(self.max_instances)
        with contextlib.suppress(Exception):
            with last_lock.open("a", encoding="utf-8") as f:
                f.write(f"\n{pid_str}")
        return self.max_instances

    def release_instance_index(self, index: int) -> None:
        """Release the lock for the given instance index if present."""
        with contextlib.suppress(Exception):
            self._lock_path(index).unlink(missing_ok=True)

    def load_draft(self, index: int, encoding: str = "utf-8") -> str:
        path = self._draft_path(index)
        if not path.exists():
            return ""
        try:
            return path.read_text(encoding=encoding)
        except Exception:
            return ""

    def save_draft(self, index: int, text: str, encoding: str = "utf-8") -> Path:
        path = self._draft_path(index)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding=encoding)
        return path

    def clear_draft(self, index: int) -> None:
        with contextlib.suppress(Exception):
            self._draft_path(index).unlink(missing_ok=True)
