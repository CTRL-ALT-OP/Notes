from __future__ import annotations
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
            tmp_path = Path(tmp.name)
            tmp.write(code)
            tmp.flush()
        try:
            completed = subprocess.run(
                [sys.executable, str(tmp_path)],
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
                tmp_path.unlink(missing_ok=True)  # type: ignore[arg-type]
            except Exception:
                pass
