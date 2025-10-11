from __future__ import annotations
import sys
import io
import json
import traceback
from pathlib import Path
from contextlib import redirect_stdout, redirect_stderr

from app.services.file_service import FileService
from app.services.draft_service import DraftService
from app.ui.main_window import MainWindow


def _run_snippet_worker(code_file: str, result_file: str | None) -> int:
    code_path = Path(code_file)
    out_buffer = io.StringIO()
    err_buffer = io.StringIO()

    exit_code = 0
    try:
        source = code_path.read_text(encoding="utf-8")
    except Exception as exc:
        # Could not read code; report error
        err_buffer.write(f"[Worker error] failed to read code: {exc}\n")
        exit_code = 1
        source = ""

    # Execute code with isolated globals and captured stdio
    exec_globals: dict[str, object] = {"__name__": "__main__"}
    try:
        with redirect_stdout(out_buffer), redirect_stderr(err_buffer):
            try:
                compiled = compile(source, str(code_path), "exec")
                exec(compiled, exec_globals)
                exit_code = 0
            except SystemExit as e:
                try:
                    exit_code = int(e.code)  # type: ignore[arg-type]
                except Exception:
                    exit_code = 1
            except Exception:
                # Print full traceback into stderr buffer
                traceback.print_exc()
                exit_code = 1
    except Exception as exc:
        err_buffer.write(f"[Worker error] {exc}\n")
        exit_code = 1

    if result_file:
        try:
            Path(result_file).write_text(
                json.dumps(
                    {
                        "returncode": exit_code,
                        "stdout": out_buffer.getvalue(),
                        "stderr": err_buffer.getvalue(),
                    }
                ),
                encoding="utf-8",
            )
        except Exception:
            # Best-effort; ignore write failures
            pass

    return exit_code


def main() -> int:
    # Worker mode: run a snippet and exit without starting the GUI
    if "--worker-run" in sys.argv:
        try:
            idx = sys.argv.index("--worker-run")
            code_file = sys.argv[idx + 1]
        except Exception:
            return 2
        result_path: str | None = None
        if "--result" in sys.argv:
            try:
                ridx = sys.argv.index("--result")
                result_path = sys.argv[ridx + 1]
            except Exception:
                result_path = None
        return _run_snippet_worker(code_file, result_path)

    file_service = FileService()
    draft_service = DraftService()
    window = MainWindow(file_service=file_service, draft_service=draft_service)
    window.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
