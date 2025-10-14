import sys
from pathlib import Path

from app.services.link_handler import LinkHandler


class FakeLauncher:
    def __init__(self):
        self.calls = []

    def launch(self, args, cwd=None):  # noqa: ANN001
        self.calls.append(("launch", tuple(args), cwd))
        return None

    def launch_in_terminal(self, args, cwd=None, keep_open=True):  # noqa: ANN001
        self.calls.append(("launch_in_terminal", tuple(args), cwd, keep_open))
        return None


def test_open_url(monkeypatch):
    opened = {"count": 0, "url": None}

    def fake_open(url, new=0):  # noqa: ANN001
        opened["count"] += 1
        opened["url"] = url
        return True

    import webbrowser

    monkeypatch.setattr(webbrowser, "open", fake_open)
    lh = LinkHandler(launcher=FakeLauncher())
    lh.open_link("https://example.com/path")
    assert opened["count"] == 1 and opened["url"].startswith("https://example.com")


def test_open_path_python_runs_in_terminal(tmp_path: Path, monkeypatch):
    launcher = FakeLauncher()
    lh = LinkHandler(launcher=launcher)
    pyfile = tmp_path / "script.py"
    pyfile.write_text("print('ok')", encoding="utf-8")
    lh.open_link(str(pyfile))
    assert any(call[0] == "launch_in_terminal" for call in launcher.calls)


def test_open_path_quotes_and_env_expand(tmp_path: Path, monkeypatch):
    launcher = FakeLauncher()
    lh = LinkHandler(launcher=launcher)
    f = tmp_path / "file.txt"
    f.write_text("x", encoding="utf-8")
    quoted = f'"{f}"'
    if sys.platform == "win32":
        # Prevent calling real os.startfile during test
        import os

        called = {"path": None}

        def fake_startfile(p):  # noqa: ANN001
            called["path"] = p

        monkeypatch.setattr(os, "startfile", fake_startfile, raising=True)
        lh.open_link(quoted)
        assert called["path"]
    else:
        lh.open_link(quoted)
        assert any(call[0] == "launch" for call in launcher.calls)


def test_open_link_ignores_empty_and_whitespace(monkeypatch):
    import webbrowser

    calls = {"web": 0, "start": 0}

    def fake_open(url, new=0):  # noqa: ANN001
        calls["web"] += 1
        return True

    monkeypatch.setattr(webbrowser, "open", fake_open)
    launcher = FakeLauncher()
    lh = LinkHandler(launcher=launcher)

    if sys.platform == "win32":
        import os as _os

        def fake_startfile(_p):  # noqa: ANN001
            calls["start"] += 1

        monkeypatch.setattr(_os, "startfile", fake_startfile, raising=True)

    lh.open_link("")
    lh.open_link("   ")

    assert calls["web"] == 0
    if sys.platform == "win32":
        assert calls["start"] == 0
    assert launcher.calls == []


def test_open_mailto_calls_webbrowser(monkeypatch):
    import webbrowser

    opened = {"url": None}

    def fake_open(url, new=0):  # noqa: ANN001
        opened["url"] = url
        return True

    monkeypatch.setattr(webbrowser, "open", fake_open)
    lh = LinkHandler(launcher=FakeLauncher())
    lh.open_link("mailto:user@example.com")
    assert opened["url"] and opened["url"].startswith("mailto:")


def test_open_url_case_insensitive(monkeypatch):
    import webbrowser

    opened = {"url": None}

    def fake_open(url, new=0):  # noqa: ANN001
        opened["url"] = url
        return True

    monkeypatch.setattr(webbrowser, "open", fake_open)
    lh = LinkHandler(launcher=FakeLauncher())
    lh.open_link("HTTP://Example.com/Path")
    assert opened["url"] and opened["url"].lower().startswith("http://example.com")


def test_open_url_with_surrounding_spaces(monkeypatch):
    import webbrowser

    opened = {"url": None}

    def fake_open(url, new=0):  # noqa: ANN001
        opened["url"] = url
        return True

    monkeypatch.setattr(webbrowser, "open", fake_open)
    lh = LinkHandler(launcher=FakeLauncher())
    lh.open_link("  https://example.org/test  ")
    assert opened["url"] == "https://example.org/test"


def test_file_uri_non_py_opens_default_app(tmp_path: Path, monkeypatch):
    f = tmp_path / "file_uri.txt"
    f.write_text("x", encoding="utf-8")
    if sys.platform == "win32":
        import os

        called = {"path": None}

        def fake_startfile(p):  # noqa: ANN001
            called["path"] = p

        monkeypatch.setattr(os, "startfile", fake_startfile, raising=True)
        lh = LinkHandler(launcher=FakeLauncher())
        lh.open_link(f"file://{f}")
        assert called["path"] == str(f)
    else:
        launcher = FakeLauncher()
        lh = LinkHandler(launcher=launcher)
        lh.open_link(f"file://{f}")
        assert any(
            call[0] == "launch" and str(f) in call[1][-1] for call in launcher.calls
        )


def test_file_uri_py_uses_terminal_and_sys_executable(tmp_path: Path, monkeypatch):
    launcher = FakeLauncher()
    lh = LinkHandler(launcher=launcher)
    pyfile = tmp_path / "run_me.py"
    pyfile.write_text("print('ok')", encoding="utf-8")
    monkeypatch.setattr(sys, "executable", "SENTINEL_PY")
    lh.open_link(f"file://{pyfile}")
    term_calls = [c for c in launcher.calls if c[0] == "launch_in_terminal"]
    assert term_calls and term_calls[0][1][0] == "SENTINEL_PY"


def test_single_quotes_and_env_expand(tmp_path: Path, monkeypatch):
    target = tmp_path / "env.txt"
    target.write_text("x", encoding="utf-8")
    if sys.platform == "win32":
        import os

        monkeypatch.setenv("MYDIR", str(tmp_path))
        called = {"path": None}

        def fake_startfile(p):  # noqa: ANN001
            called["path"] = p

        monkeypatch.setattr(os, "startfile", fake_startfile, raising=True)
        lh = LinkHandler(launcher=FakeLauncher())
        lh.open_link(f"'%MYDIR%\\env.txt'")
        assert called["path"] and called["path"].endswith("env.txt")
    else:
        launcher = FakeLauncher()
        monkeypatch.setenv("MYDIR", str(tmp_path))
        lh = LinkHandler(launcher=launcher)
        lh.open_link("'$MYDIR/env.txt'")
        assert any(call[0] == "launch" for call in launcher.calls)
