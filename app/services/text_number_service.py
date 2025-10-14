from __future__ import annotations
import re
from typing import Iterable, Tuple


_CARDINALS = {
    "zero": 0,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
    "sixteen": 16,
    "seventeen": 17,
    "eighteen": 18,
    "nineteen": 19,
    "twenty": 20,
}

_ORDINALS = {
    "zeroth": 0,
    "first": 1,
    "second": 2,
    "third": 3,
    "fourth": 4,
    "fifth": 5,
    "sixth": 6,
    "seventh": 7,
    "eighth": 8,
    "ninth": 9,
    "tenth": 10,
    "eleventh": 11,
    "twelfth": 12,
    "thirteenth": 13,
    "fourteenth": 14,
    "fifteenth": 15,
    "sixteenth": 16,
    "seventeenth": 17,
    "eighteenth": 18,
    "nineteenth": 19,
    "twentieth": 20,
}


class TextNumberIncrementer:
    """Detects and increments numbers in text, including textual forms.

    - Increments Arabic numerals (e.g., 1, 23)
    - Increments ordinal suffix numerals (e.g., 1st, 2nd, 3rd, 4th)
    - Increments textual ordinals (e.g., first -> second)
    - Increments textual cardinals (e.g., one -> two) unless ordinal_only=True
    """

    _re_number = re.compile(r"\b(\d+)(st|nd|rd|th)?\b", flags=re.IGNORECASE)

    def increment(
        self, text: str, ordinal_only: bool = False, increment_text: bool = True
    ) -> str:
        # Increment numeric forms first
        text = self._increment_numeric(text, ordinal_only)
        # Then increment textual forms
        if increment_text:
            text = self._increment_textual(text, ordinal_only)
        return text

    def _increment_numeric(self, text: str, ordinal_only: bool) -> str:
        def repl(m: re.Match[str]) -> str:
            num = int(m.group(1))
            suffix = m.group(2)
            new_num = num + 1
            if suffix:
                return f"{new_num}{self._ordinal_suffix(new_num)}"
            return str(new_num) if ordinal_only else str(new_num)

        return self._re_number.sub(repl, text)

    def _increment_textual(self, text: str, ordinal_only: bool) -> str:
        # Single-pass ordinal word replacement (prevents cascading like first->second->third)
        if _ORDINALS:
            ordinal_words = sorted(_ORDINALS.keys(), key=len, reverse=True)
            ord_pattern = re.compile(
                r"\b(" + "|".join(map(re.escape, ordinal_words)) + r")\b",
                flags=re.IGNORECASE,
            )

            def ord_repl(m: re.Match[str]) -> str:
                word = m.group(0)
                base = _ORDINALS.get(word.lower())
                if base is None:
                    return word
                return self._case_like(word, self._ordinal_word(base + 1))

            text = ord_pattern.sub(ord_repl, text)

        # Single-pass cardinal replacement only when not ordinal-only
        if not ordinal_only and _CARDINALS:
            cardinal_words = sorted(_CARDINALS.keys(), key=len, reverse=True)
            car_pattern = re.compile(
                r"\b(" + "|".join(map(re.escape, cardinal_words)) + r")\b",
                flags=re.IGNORECASE,
            )

            def car_repl(m: re.Match[str]) -> str:
                word = m.group(0)
                base = _CARDINALS.get(word.lower())
                if base is None:
                    return word
                return self._case_like(word, self._cardinal_word(base + 1))

            text = car_pattern.sub(car_repl, text)

        return text

    @staticmethod
    def _ordinal_suffix(n: int) -> str:
        n_abs = abs(n)
        if 10 <= (n_abs % 100) <= 20:
            return "th"
        last = n_abs % 10
        if last == 1:
            return "st"
        if last == 2:
            return "nd"
        return "rd" if last == 3 else "th"

    @staticmethod
    def _cardinal_word(n: int) -> str:
        inv = {v: k for k, v in _CARDINALS.items()}
        return inv.get(n, str(n))

    @staticmethod
    def _ordinal_word(n: int) -> str:
        inv = {v: k for k, v in _ORDINALS.items()}
        base = inv.get(n)
        if base is not None:
            return base
        # Fallback: compose from numeric
        return f"{n}{TextNumberIncrementer._ordinal_suffix(n)}"

    @staticmethod
    def _case_like(sample: str, replacement: str) -> str:
        if sample.isupper():
            return replacement.upper()
        return replacement.capitalize() if sample[0].isupper() else replacement
