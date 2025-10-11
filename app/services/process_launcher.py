from __future__ import annotations
import os
import subprocess
import sys
from pathlib import Path
from typing import Sequence


class DetachedProcessLauncher:
    """Launches processes fully detached from the current application.

    On Windows, uses CREATE_NEW_CONSOLE and DETACHED_PROCESS so that the child
    remains alive if the parent GUI app exits. On POSIX, uses start_new_session
    and devnull stdio redirection to fully detach.
    """

    def __init__(self) -> None:
        pass

    def launch(
        self, command: Sequence[str], cwd: Path | None = None
    ) -> subprocess.Popen[bytes]:
        if sys.platform == "win32":
            creationflags = 0x00000010  # CREATE_NEW_CONSOLE
            # Inherit environment; do not tie stdio to parent
            print(f"Launching command: {command}")
            return subprocess.Popen(
                list(command),
                cwd=str(cwd) if cwd else None,
                creationflags=creationflags,
                close_fds=False,
            )

        # POSIX: start new session and detach stdio
        with open(os.devnull, "rb") as devnull_in, open(
            os.devnull, "ab"
        ) as devnull_out:
            return subprocess.Popen(
                list(command),
                cwd=str(cwd) if cwd else None,
                stdin=devnull_in,
                stdout=devnull_out,
                stderr=devnull_out,
                start_new_session=True,
                close_fds=True,
            )
