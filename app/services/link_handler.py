from __future__ import annotations
import os
import sys
import webbrowser
import shlex
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
        print(f"Opening link from home: {link}")
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
        try:
            webbrowser.open(url, new=2)
        except Exception:
            # Best effort; ignore failures
            pass

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
            try:
                path = Path(expanded[7:])
            except Exception:
                pass

        if path.suffix.lower() == ".py":
            print(f"Running Python file in terminal: {path}")
            self._run_python_file_in_terminal(path)
            return

        self._open_with_default_app(path)

    def _open_with_default_app(self, path: Path) -> None:
        try:
            if sys.platform == "win32":
                os.startfile(str(path))  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                self.launcher.launch(["open", str(path)])
            else:
                self.launcher.launch(["xdg-open", str(path)])
        except Exception:
            pass

    def _run_python_file_in_terminal(self, path: Path) -> None:
        try:
            if sys.platform == "win32":
                # Launch a new PowerShell console that remains open after the script runs.
                # Using PowerShell avoids complex nested cmd quoting issues.
                py = sys.executable or "python"
                ps = (
                    Path(os.environ.get("SystemRoot", r"C:\\Windows"))
                    / "System32"
                    / "WindowsPowerShell"
                    / "v1.0"
                    / "powershell.exe"
                )
                ps_str = str(ps)
                ps_command = f'& "{py}" "{str(path)}"'
                command = [
                    ps_str,
                    "-NoExit",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-Command",
                    ps_command,
                ]
                self.launcher.launch(command, cwd=path.parent)
                return

            if sys.platform == "darwin":
                # Open Terminal.app and run; keep open on completion
                script = f"python {shlex.quote(str(path))}; echo; read -n 1 -s -r -p 'Press any key to close'"
                self.launcher.launch(
                    [
                        "osascript",
                        "-e",
                        f'tell application "Terminal" to do script "{script}"',
                    ]
                )
                return

            # Linux: try gnome-terminal, then xterm fallback
            script_cmd = f"python {shlex.quote(str(path))}; echo; read -n 1 -s -r -p 'Press any key to close'"
            if self._command_exists("gnome-terminal"):
                self.launcher.launch(
                    ["gnome-terminal", "--", "bash", "-lc", script_cmd], cwd=path.parent
                )
            elif self._command_exists("xterm"):
                self.launcher.launch(
                    ["xterm", "-e", f"bash -lc {shlex.quote(script_cmd)}"],
                    cwd=path.parent,
                )
            else:
                # Fallback: run detached in background without terminal
                self.launcher.launch([sys.executable, str(path)], cwd=path.parent)
        except Exception:
            pass

    def _command_exists(self, name: str) -> bool:
        for p in os.environ.get("PATH", "").split(os.pathsep):
            candidate = Path(p) / name
            if candidate.exists() and os.access(candidate, os.X_OK):
                return True
        return False
