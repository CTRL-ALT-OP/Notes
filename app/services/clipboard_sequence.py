from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

from app.services.tag_service import TagReplacer
from app.services.text_number_service import TextNumberIncrementer


@dataclass
class SequenceOptions:
    auto_increment: bool = True
    ordinal_only: bool = True
    replace_tags: bool = True
    incr_text: bool = True


class ClipboardSequenceManager:
    """Manages a clipboard-driven text sequence with optional transforms.

    Life cycle:
    - set_initial(...) to establish the first clipboard value
    - on_paste(current_clipboard) -> Optional[str]
        If current_clipboard matches last_generated, compute next and return it.
        If it does not match, return None to signal termination.
    """

    def __init__(self) -> None:
        self._tagger = TagReplacer()
        self._incr = TextNumberIncrementer()
        self._options: SequenceOptions = SequenceOptions()
        self._base_text: str = ""
        self._last_generated: Optional[str] = None

    @property
    def last_generated(self) -> Optional[str]:
        return self._last_generated

    def reset(self) -> None:
        self._base_text = ""
        self._last_generated = None
        self._options = SequenceOptions()

    def set_initial(self, selected_text: str, options: SequenceOptions) -> str:
        self._base_text = selected_text
        self._options = options
        first = selected_text
        if options.replace_tags:
            first = self._tagger.replace(first)
        self._last_generated = first
        return first

    def on_paste(self, current_clipboard: str) -> Optional[str]:
        # Stop if clipboard was changed externally
        if self._last_generated is None or current_clipboard != self._last_generated:
            return None

        next_text = self._last_generated
        if self._options.auto_increment:
            next_text = self._incr.increment(
                next_text,
                ordinal_only=self._options.ordinal_only,
                increment_text=self._options.incr_text,
            )
        if self._options.replace_tags:
            next_text = self._tagger.replace(next_text)

        self._last_generated = next_text
        return next_text
