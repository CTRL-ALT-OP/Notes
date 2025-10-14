from app.services import global_paste_listener as gpl_mod
from app.services.global_paste_listener import GlobalPasteListener


def test_global_paste_listener_noop_when_pynput_missing(monkeypatch):
    # Force optional dependency flag off
    monkeypatch.setattr(gpl_mod, "_PYNPUT_AVAILABLE", False, raising=True)

    called = {"count": 0}

    def cb():
        called["count"] += 1

    gl = GlobalPasteListener()
    gl.start(cb)  # Should be a no-op
    gl._invoke()  # Should not call when inactive
    assert called["count"] == 0
