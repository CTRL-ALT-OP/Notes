import contextlib
import os
import sys
import webbrowser
from pathlib import Path
from typing import Optional

from app.services.process_launcher import DetachedProcessLauncher


class LinkHandler:
    """Handles opening of URLs and filesystem links.

    - http/https/mailto: opened via default system handler (webbrowser).
    - file paths: opened via OS default. If path ends with .py, run in a new
      terminal using a detached process so it outlives the notes app.
    """

    def __init__(self, launcher: Optional[DetachedProcessLauncher] = None) -> None:
        self.launcher = launcher or DetachedProcessLauncher()

    def open_link(self, link: str) -> None:
        link = link.strip()
        if not link:
            return

        if self._looks_like_url(link):
            self._open_url(link)
            return

        # Treat as filesystem path (allow quotes and spaces)
        self._open_path(link)

    def _looks_like_url(self, link: str) -> bool:
        lower = link.lower()
        return (
            lower.startswith("http://")
            or lower.startswith("https://")
            or lower.startswith("mailto:")
        )

    def _open_url(self, url: str) -> None:
        with contextlib.suppress(Exception):
            webbrowser.open(url, new=2)

    def _open_path(self, raw: str) -> None:
        # Remove surrounding quotes if user typed them in markdown
        cleaned = raw
        if (cleaned.startswith('"') and cleaned.endswith('"')) or (
            cleaned.startswith("'") and cleaned.endswith("'")
        ):
            cleaned = cleaned[1:-1]

        # Expand user and env vars
        expanded = os.path.expandvars(os.path.expanduser(cleaned))
        path = Path(expanded)

        # If it's a URI-like file://, convert
        if expanded.lower().startswith("file://"):
            with contextlib.suppress(Exception):
                path = Path(expanded[7:])
        if path.suffix.lower() == ".py":
            self._run_python_file_in_terminal(path)
            return

        self._open_with_default_app(path)

    def _open_with_default_app(self, path: Path) -> None:
        with contextlib.suppress(Exception):
            if sys.platform == "darwin":
                self.launcher.launch(["open", str(path)])
            elif sys.platform == "win32":
                os.startfile(str(path))  # type: ignore[attr-defined]
            else:
                self.launcher.launch(["xdg-open", str(path)])

    def _run_python_file_in_terminal(self, path: Path) -> None:
        with contextlib.suppress(Exception):
            py = sys.executable or "python"
            self.launcher.launch_in_terminal(
                [py, str(path)], cwd=path.parent, keep_open=True
            )
