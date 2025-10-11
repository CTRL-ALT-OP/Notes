from __future__ import annotations
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional, Tuple


class CodeRunner:
    """Runs code snippets and captures stdout/stderr reliably.

    Currently supports Python via the active interpreter.
    """

    def __init__(self) -> None:
        pass

    def run_python(
        self,
        code: str,
        cwd: Optional[Path] = None,
        timeout_seconds: float = 5.0,
    ) -> Tuple[int, str, str]:
        """Run the given Python code in a subprocess.

        Returns (exit_code, stdout, stderr).
        """
        # Write to a temporary file so multi-line code executes as-is
        with tempfile.NamedTemporaryFile(
            "w", suffix=".py", delete=False, encoding="utf-8"
        ) as tmp:
            code_path = Path(tmp.name)
            tmp.write(code)
            tmp.flush()

        # In frozen apps, re-invoking sys.executable runs the GUI again.
        # Use the app's worker mode to execute code and capture results.
        is_frozen = bool(getattr(sys, "frozen", False))
        result_path: Path | None = None
        try:
            if is_frozen:
                with tempfile.NamedTemporaryFile(
                    "w", suffix=".json", delete=False, encoding="utf-8"
                ) as rtmp:
                    result_path = Path(rtmp.name)
                    rtmp.write("")
                    rtmp.flush()

                cmd = [
                    sys.executable,
                    "--worker-run",
                    str(code_path),
                    "--result",
                    str(result_path),
                ]

                creationflags = 0
                startupinfo = None
                if sys.platform == "win32":
                    # CREATE_NO_WINDOW to avoid flashing a console or new window
                    creationflags = 0x08000000  # CREATE_NO_WINDOW

                completed = subprocess.run(
                    cmd,
                    cwd=str(cwd) if cwd else None,
                    capture_output=True,
                    text=True,
                    timeout=timeout_seconds,
                    creationflags=creationflags,
                    startupinfo=startupinfo,
                )

                # Prefer structured result file written by the worker
                try:
                    data = json.loads(result_path.read_text(encoding="utf-8"))
                    rc = int(data.get("returncode", completed.returncode))
                    out = str(data.get("stdout", ""))
                    err = str(data.get("stderr", ""))
                    return rc, out, err
                except Exception:
                    # Fallback to captured stdio if JSON missing/invalid
                    return (
                        completed.returncode,
                        completed.stdout or "",
                        completed.stderr or "",
                    )
            else:
                # Dev mode: invoke the current interpreter directly
                completed = subprocess.run(
                    [sys.executable, str(code_path)],
                    cwd=str(cwd) if cwd else None,
                    capture_output=True,
                    text=True,
                    timeout=timeout_seconds,
                )
                return completed.returncode, completed.stdout, completed.stderr
        except subprocess.TimeoutExpired as exc:
            out = exc.stdout or ""
            err = (exc.stderr or "") + "\n[Timed out]"
            return 124, out, err
        except Exception as exc:
            return 1, "", f"[Runner error] {exc}"
        finally:
            try:
                code_path.unlink(missing_ok=True)  # type: ignore[arg-type]
            except Exception:
                pass
            if result_path is not None:
                try:
                    result_path.unlink(missing_ok=True)  # type: ignore[arg-type]
                except Exception:
                    pass
