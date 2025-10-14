import sys
from pathlib import Path

from app.services.process_launcher import DetachedProcessLauncher


def test_launch_builds_command(monkeypatch, tmp_path: Path):
    dl = DetachedProcessLauncher()
    called = {"args": None, "cwd": None}

    def fake_popen(args=None, cwd=None, **kw):  # noqa: ANN001, ANN003
        called["args"] = list(args)
        called["cwd"] = cwd

        class _P:  # noqa: D401
            pass

        return _P()

    monkeypatch.setattr("subprocess.Popen", fake_popen)
    p = dl.launch(["echo", "hi"], cwd=tmp_path)
    assert called["args"] == ["echo", "hi"]
    assert str(called["cwd"]) == str(tmp_path)


def test_launch_in_terminal_fallbacks(monkeypatch, tmp_path: Path):
    dl = DetachedProcessLauncher()
    # Ensure command existence checks return False to hit fallback
    monkeypatch.setattr(dl, "_command_exists", lambda name: False)

    called = {"args": None}

    def fake_launch(args, cwd=None):  # noqa: ANN001, ANN002
        called["args"] = list(args)

        class _P:  # noqa: D401
            pass

        return _P()

    monkeypatch.setattr(dl, "launch", fake_launch)
    dl.launch_in_terminal(["python", "-V"], cwd=tmp_path)
    assert (
        called["args"][0] in ("osascript", "python", "gnome-terminal", "xterm")
        or sys.platform == "win32"
    )
