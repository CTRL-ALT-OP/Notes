from __future__ import annotations
from datetime import datetime


class TagReplacer:
    """Replaces supported template tags in text.

    Currently supported tags:
    - {min}: two-digit current minute (00-59)
    """

    def replace(self, text: str) -> str:
        try:
            now = datetime.now()
            minute = now.strftime("%M")
            return text.replace("{min}", minute)
        except Exception:
            return text
