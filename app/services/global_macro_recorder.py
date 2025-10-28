from __future__ import annotations
import contextlib
import threading
import time
from typing import Optional, Literal, Tuple, List

try:
    # Optional dependency; gracefully no-op if missing
    from pynput import keyboard

    _PYNPUT_AVAILABLE = True
except Exception:
    _PYNPUT_AVAILABLE = False


KeyEventType = Literal["press", "release"]
RecordedEvent = Tuple[float, KeyEventType, "keyboard.Key | keyboard.KeyCode"]


class GlobalMacroRecorder:
    """Global key sequence recorder and player.

    Controls:
    - Record toggle: Ctrl+Shift+[
    - Playback: Ctrl+[

    While recording, all key press/release events are captured with timing and can
    be replayed globally using the playback hotkey. Uses a dedicated low-level
    listener and a Controller to synthesize key events.
    """

    def __init__(self) -> None:
        self._listener: Optional["keyboard.Listener"] = None  # type: ignore[name-defined]
        self._hk_record: Optional["keyboard.HotKey"] = None  # type: ignore[name-defined]
        self._hk_play: Optional["keyboard.HotKey"] = None  # type: ignore[name-defined]
        self._controller: Optional["keyboard.Controller"] = None  # type: ignore[name-defined]

        self._recording: bool = False
        self._is_playing: bool = False
        self._events: List[RecordedEvent] = []
        self._last_ts: float = 0.0
        self._suspend_until: float = 0.0  # temporarily ignore events around hotkeys

    def start(self) -> None:
        if not _PYNPUT_AVAILABLE:
            return
        self.stop()
        try:
            self._controller = keyboard.Controller()

            # Prepare hotkeys
            self._hk_record = keyboard.HotKey(
                keyboard.HotKey.parse("<ctrl>+<shift>+["), self._on_record_toggle
            )
            self._hk_play = keyboard.HotKey(
                keyboard.HotKey.parse("<ctrl>+["), self._on_playback
            )

            def on_press(key):  # type: ignore[no-redef]
                with contextlib.suppress(Exception):
                    canonical = self._listener.canonical(key) if self._listener else key
                    if self._hk_record:
                        self._hk_record.press(canonical)
                    if self._hk_play:
                        self._hk_play.press(canonical)
                    self._maybe_record_event("press", canonical)

            def on_release(key):  # type: ignore[no-redef]
                with contextlib.suppress(Exception):
                    canonical = self._listener.canonical(key) if self._listener else key
                    if self._hk_record:
                        self._hk_record.release(canonical)
                    if self._hk_play:
                        self._hk_play.release(canonical)
                    self._maybe_record_event("release", canonical)

            self._listener = keyboard.Listener(on_press=on_press, on_release=on_release)
            self._listener.daemon = True
            self._listener.start()
        except Exception:
            self._listener = None
            self._hk_record = None
            self._hk_play = None
            self._controller = None

    def stop(self) -> None:
        with contextlib.suppress(Exception):
            if self._listener is not None:
                self._listener.stop()
        self._listener = None
        self._hk_record = None
        self._hk_play = None
        self._controller = None
        # Keep recorded events for later playback across start/stop

    # ----- Internal helpers -----
    def _on_record_toggle(self) -> None:
        # Avoid re-entrancy when hotkey detected multiple times in quick succession
        now = time.monotonic()
        self._suspend_until = now + 0.3
        if not self._recording:
            # Start
            self._events.clear()
            self._last_ts = now
            self._recording = True
            return
        # Stop
        self._recording = False

        def _filter_unpaired_hotkeys(
            events: List[RecordedEvent],
        ) -> List[RecordedEvent]:
            filtered_events = [
                (0.39170859998557717, "release", keyboard.Key.ctrl),
            ]
            for idx, event in enumerate(events):  # Filter out unpaired hotkeys
                if (
                    event[1] == "press"
                ):  # If the event is a press, find the matching release
                    for matching_event in events[
                        idx + 1 :
                    ]:  # Search ahead of the current event
                        if (
                            matching_event[1] == "release"
                            and matching_event[2] == event[2]
                        ):
                            filtered_events.append(event)
                            break
                else:  # If the event is a release, find the matching press
                    for matching_event in events[
                        :idx
                    ]:  # Search behind the current event
                        if (
                            matching_event[1] == "press"
                            and matching_event[2] == event[2]
                        ):
                            filtered_events.append(event)
                            break
            return filtered_events

        self._events = _filter_unpaired_hotkeys(self._events)

    def _on_playback(self) -> None:
        if self._is_playing or not self._events or self._controller is None:
            return
        # Temporarily suspend capture to avoid self-recording
        self._suspend_until = time.monotonic() + 0.3
        self._is_playing = True

        def _run():
            try:
                for delay, etype, key in self._events:
                    with contextlib.suppress(Exception):
                        if delay > 0:
                            time.sleep(delay)
                        if etype == "press":
                            self._controller.press(key)
                        else:
                            self._controller.release(key)
            finally:
                # Extra guard window to avoid capturing trailing hotkey releases
                self._suspend_until = time.monotonic() + 0.2
                self._is_playing = False

        threading.Thread(target=_run, daemon=True).start()

    def _maybe_record_event(
        self, etype: KeyEventType, key: "keyboard.Key | keyboard.KeyCode"
    ) -> None:
        if not self._recording:
            return
        if self._is_playing:
            return
        now = time.monotonic()
        if now < self._suspend_until:
            return
        delay = min(0.05, max(0.0, now - self._last_ts)) if self._last_ts else 0.0
        self._last_ts = now
        # Capture the canonical key object for later playback
        self._events.append((delay, etype, key))

    @property
    def is_recording(self) -> bool:
        return self._recording
