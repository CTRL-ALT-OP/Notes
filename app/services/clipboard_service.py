from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from app.services.clipboard_sequence import (
    ClipboardSequenceManager,
    SequenceOptions,
)


@dataclass
class NextClipboardDecision:
    """Represents what to do after a global paste event.

    - next_text: If provided, set the clipboard to this text for the next paste.
    - should_stop_listener: If True, the caller should stop listening for global pastes.
    """

    next_text: Optional[str]
    should_stop_listener: bool


class ClipboardService:
    """Orchestrates clipboard-driven flows such as sequence paste and list paste.

    This service contains no UI code. The UI is responsible for reading/writing the
    actual OS clipboard and starting/stopping any global keyboard listeners. The
    service provides pure logic and state transitions.
    """

    def __init__(self) -> None:
        self._sequence: Optional[ClipboardSequenceManager] = None
        self._list_items: list[str] = []
        self._list_index: int = 0
        self._list_active: bool = False

    # ---------- List paste helpers ----------
    @staticmethod
    def parse_list_items(selected: str) -> list[str]:
        """Extract plain items from a markdown-like list selection.

        Strips leading markers like '-', '*', '+', or numeric markers like '1.'/'2)'.
        """
        results: list[str] = []
        marker_pattern = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+")
        for raw in selected.splitlines():
            stripped = raw.strip()
            if not stripped:
                continue
            if cleaned := marker_pattern.sub("", stripped).strip():
                results.append(cleaned)
        return results

    def start_list_paste(self, items: list[str]) -> Optional[str]:
        """Begin a list paste session. Returns the first item to seed the clipboard."""
        self._list_items = items[:]
        self._list_index = 0
        self._list_active = len(self._list_items) > 0
        return self._list_items[0] if self._list_active else None

    def stop_list_paste(self) -> None:
        self._list_active = False
        self._list_items = []
        self._list_index = 0

    @property
    def list_paste_active(self) -> bool:
        return self._list_active

    # ---------- Sequence helpers ----------
    def start_sequence(self, initial: str, options: SequenceOptions) -> str:
        """Begin a sequence paste session. Returns the first clipboard value."""
        self._sequence = ClipboardSequenceManager()
        return self._sequence.set_initial(initial, options)

    def clear_sequence(self) -> None:
        self._sequence = None

    @property
    def sequence_active(self) -> bool:
        return self._sequence is not None

    # ---------- Global paste event handling ----------
    def compute_next_clipboard(self, current_clipboard: str) -> NextClipboardDecision:
        """Given the current clipboard contents, decide the next action.

        Priority:
        1) If list paste is active, advance to the next item.
        2) Else if a sequence is active, compute the next sequence value.
        3) Otherwise, request that the listener stop.
        """
        # 1) List paste mode takes precedence
        if self._list_active:
            self._list_index += 1
            if self._list_index >= len(self._list_items):
                # Completed; stop list mode. Keep listener only if a sequence continues.
                self.stop_list_paste()
                return NextClipboardDecision(
                    next_text=None, should_stop_listener=self._sequence is None
                )
            nxt = self._list_items[self._list_index]
            return NextClipboardDecision(next_text=nxt, should_stop_listener=False)

        # 2) Sequence mode
        if not self._sequence:
            return NextClipboardDecision(next_text=None, should_stop_listener=True)

        nxt = self._sequence.on_paste(current_clipboard)
        if nxt is None:
            # Clipboard diverged; stop sequence
            self._sequence = None
            return NextClipboardDecision(
                next_text=None, should_stop_listener=not self._list_active
            )

        return NextClipboardDecision(next_text=nxt, should_stop_listener=False)
