from __future__ import annotations
import contextlib
import time
from typing import Callable, Optional

try:
    # Optional dependency; gracefully no-op if missing
    from pynput import keyboard

    _PYNPUT_AVAILABLE = True
except Exception:
    _PYNPUT_AVAILABLE = False


class GlobalPasteListener:
    """Listens for global paste key combos and invokes a callback.

    Uses a low-level Listener with HotKey press/release for reliability on Windows.
    """

    def __init__(self) -> None:
        self._listener: Optional["keyboard.Listener"] = None  # type: ignore[name-defined]
        self._hk_ctrl_v: Optional["keyboard.HotKey"] = None  # type: ignore[name-defined]
        self._hk_cmd_v: Optional["keyboard.HotKey"] = None  # type: ignore[name-defined]
        self._callback: Optional[Callable[[], None]] = None
        self._active = False
        self._last_invoke_ts: float | None = None

    def start(self, on_paste: Callable[[], None]) -> None:
        if not _PYNPUT_AVAILABLE:
            return
        self.stop()
        self._callback = on_paste
        self._active = True
        try:
            # Prepare hotkeys
            self._hk_ctrl_v = keyboard.HotKey(
                keyboard.HotKey.parse("<ctrl>+v"), self._invoke
            )
            # macOS support; harmless on Windows
            self._hk_cmd_v = keyboard.HotKey(
                keyboard.HotKey.parse("<cmd>+v"), self._invoke
            )

            def on_press(key):  # type: ignore[no-redef]
                with contextlib.suppress(Exception):
                    canonical = self._listener.canonical(key) if self._listener else key
                    if self._hk_ctrl_v:
                        self._hk_ctrl_v.press(canonical)
                    if self._hk_cmd_v:
                        self._hk_cmd_v.press(canonical)

            def on_release(key):  # type: ignore[no-redef]
                with contextlib.suppress(Exception):
                    canonical = self._listener.canonical(key) if self._listener else key
                    if self._hk_ctrl_v:
                        self._hk_ctrl_v.release(canonical)
                    if self._hk_cmd_v:
                        self._hk_cmd_v.release(canonical)

            self._listener = keyboard.Listener(on_press=on_press, on_release=on_release)
            self._listener.daemon = True
            self._listener.start()
        except Exception:
            self._listener = None
            self._hk_ctrl_v = None
            self._hk_cmd_v = None

    def stop(self) -> None:
        self._active = False
        with contextlib.suppress(Exception):
            if self._listener is not None:
                self._listener.stop()
        self._listener = None
        self._hk_ctrl_v = None
        self._hk_cmd_v = None
        self._last_invoke_ts = None

    def _invoke(self) -> None:
        if not (self._active and self._callback is not None):
            return
        with contextlib.suppress(Exception):
            self._callback()
