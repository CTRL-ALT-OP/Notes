from __future__ import annotations
import os
import subprocess
import sys
import shlex
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

    def _command_exists(self, name: str) -> bool:
        for p in os.environ.get("PATH", "").split(os.pathsep):
            candidate = Path(p) / name
            if candidate.exists() and os.access(candidate, os.X_OK):
                return True
        return False

    def launch_in_terminal(
        self,
        command: Sequence[str],
        cwd: Path | None = None,
        keep_open: bool = True,
    ) -> subprocess.Popen[bytes]:
        """Open a new terminal window and run the provided command.

        The command should be provided as an argv-style sequence where the first
        element is the executable followed by its arguments.
        """
        if sys.platform == "win32":
            return self.windows_powershell(command, keep_open, cwd)
        # Build a bash/zsh-compatible script line
        script_cmd = " ".join(shlex.quote(part) for part in command)
        if keep_open:
            script_cmd += "; echo; read -n 1 -s -r -p 'Press any key to close'"

        if sys.platform == "darwin":
            # Escape backslashes and quotes for AppleScript double-quoted string
            escaped = script_cmd.replace("\\", "\\\\").replace('"', '\\"')
            as_script = f'tell application "Terminal" to do script "{escaped}"'
            return self.launch(["osascript", "-e", as_script], cwd=cwd)

        # Linux and other POSIX
        if self._command_exists("gnome-terminal"):
            return self.launch(
                ["gnome-terminal", "--", "bash", "-lc", script_cmd], cwd=cwd
            )
        if self._command_exists("xterm"):
            return self.launch(
                [
                    "xterm",
                    "-e",
                    f"bash -lc {shlex.quote(script_cmd)}",
                ],
                cwd=cwd,
            )

        # Fallback: run detached without opening a terminal
        return self.launch(list(command), cwd=cwd)

    def windows_powershell(self, command, keep_open, cwd):
        py_shell = (
            Path(os.environ.get("SystemRoot", r"C:\\Windows"))
            / "System32"
            / "WindowsPowerShell"
            / "v1.0"
            / "powershell.exe"
        )
        ps = str(py_shell)
        # & "exe" "arg1" "arg2"
        ps_command = "& " + " ".join(f'"{part}"' for part in command)
        args = [ps]
        if keep_open:
            args.append("-NoExit")
        args += [
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            ps_command,
        ]
        return self.launch(args, cwd=cwd)
