from __future__ import annotations
import contextlib
import multiprocessing
import sys
import threading
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
        # macOS subprocess listener (isolates potential SIGTRAPs from main app)
        self._proc: Optional[multiprocessing.Process] = None
        self._proc_conn: Optional[multiprocessing.connection.Connection] = None
        self._proc_reader: Optional[threading.Thread] = None

    def start(self, on_paste: Callable[[], None]) -> None:
        if not _PYNPUT_AVAILABLE:
            return
        self.stop()
        self._callback = on_paste
        self._active = True
        if sys.platform == "darwin":
            # Run the event tap in a helper process; macOS can send SIGTRAP to the
            # hosting process when creating the tap from certain environments.
            self._start_mac_subprocess()
            return
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
        # Stop macOS subprocess listener if present
        if sys.platform == "darwin":
            self._stop_mac_subprocess()
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

    # ---------- macOS subprocess listener ----------
    def _start_mac_subprocess(self) -> None:
        """Spawn a helper process to capture Cmd+V without risking main app crash."""
        self._stop_mac_subprocess()
        parent_conn, child_conn = multiprocessing.Pipe()
        proc = multiprocessing.Process(
            target=_mac_paste_worker, args=(child_conn,), daemon=True
        )
        try:
            proc.start()
        except Exception:
            return
        self._proc = proc
        self._proc_conn = parent_conn

        # Reader thread to forward paste events to main thread callback
        def _reader():
            while self._active and proc.is_alive():
                if parent_conn.poll(0.25):
                    try:
                        msg = parent_conn.recv()
                    except EOFError:
                        break
                    if msg == "paste":
                        self._invoke()
                    elif msg == "error":
                        break
            # If the helper died unexpectedly, stop list paste listener gracefully
            self._stop_mac_subprocess()

        t = threading.Thread(target=_reader, daemon=True)
        t.start()
        self._proc_reader = t

    def _stop_mac_subprocess(self) -> None:
        conn = self._proc_conn
        proc = self._proc
        self._proc_reader = None
        self._proc_conn = None
        self._proc = None
        with contextlib.suppress(Exception):
            if conn:
                conn.send("stop")
                conn.close()
        if proc:
            proc.join(timeout=0.5)
            if proc.is_alive():
                with contextlib.suppress(Exception):
                    proc.terminate()


def _mac_paste_worker(conn: multiprocessing.connection.Connection) -> None:
    """Isolated process to capture Cmd+V; communicates via Pipe."""
    try:
        from pynput import keyboard  # Import inside for process safety
    except Exception:
        with contextlib.suppress(Exception):
            conn.send("error")
        return

    hk_cmd_v: Optional["keyboard.HotKey"] = None  # type: ignore[name-defined]
    listener: Optional["keyboard.Listener"] = None  # type: ignore[name-defined]
    active = True

    def _invoke():
        with contextlib.suppress(Exception):
            conn.send("paste")

    try:
        hk_cmd_v = keyboard.HotKey(keyboard.HotKey.parse("<cmd>+v"), _invoke)

        def on_press(key):
            with contextlib.suppress(Exception):
                canonical = listener.canonical(key) if listener else key
                if hk_cmd_v:
                    hk_cmd_v.press(canonical)

        def on_release(key):
            with contextlib.suppress(Exception):
                canonical = listener.canonical(key) if listener else key
                if hk_cmd_v:
                    hk_cmd_v.release(canonical)

        listener = keyboard.Listener(on_press=on_press, on_release=on_release)
        listener.daemon = True
        listener.start()
    except Exception:
        with contextlib.suppress(Exception):
            conn.send("error")
        return

    # Heartbeat loop to detect stop signal
    try:
        while active:
            if conn.poll(0.25):
                msg = conn.recv()
                if msg == "stop":
                    active = False
                    break
            if listener and not listener.is_alive():
                break
    except Exception:
        pass
    finally:
        with contextlib.suppress(Exception):
            if listener:
                listener.stop()
        with contextlib.suppress(Exception):
            conn.close()
