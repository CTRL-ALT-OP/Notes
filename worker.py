from __future__ import annotations
import argparse
import io
import json
import traceback
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path


def run_snippet(code_file: str, result_file: str | None) -> int:
    code_path = Path(code_file)
    out_buffer = io.StringIO()
    err_buffer = io.StringIO()

    exit_code = 0
    try:
        source = code_path.read_text(encoding="utf-8")
    except Exception as exc:
        err_buffer.write(f"[Worker error] failed to read code: {exc}\n")
        exit_code = 1
        source = ""

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
            pass

    return exit_code


def main() -> int:
    parser = argparse.ArgumentParser(prog="worker")
    parser.add_argument("code_file")
    parser.add_argument("--result", dest="result_file", default=None)
    args = parser.parse_args()
    return run_snippet(args.code_file, args.result_file)


if __name__ == "__main__":
    raise SystemExit(main())
