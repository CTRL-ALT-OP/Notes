import sys
from pathlib import Path

from app.services.code_runner import CodeRunner


def test_run_python_success(tmp_path: Path, monkeypatch):
    # Ensure non-frozen behavior
    monkeypatch.setattr(sys, "frozen", False, raising=False)
    rc, out, err = CodeRunner().run_python("print('hello')")
    assert rc == 0
    assert out.strip() == "hello"
    assert err.strip() == "" or err.strip() == "None"


def test_run_python_timeout(monkeypatch):
    monkeypatch.setattr(sys, "frozen", False, raising=False)
    # Busy wait loop to exceed small timeout
    code = "\nimport time\nwhile True: pass\n"
    rc, out, err = CodeRunner().run_python(code, timeout_seconds=0.1)
    assert rc == 124
    assert "Timed out" in err
