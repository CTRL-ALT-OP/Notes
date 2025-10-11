from __future__ import annotations
from dataclasses import dataclass


@dataclass
class MarkdownService:
    """Stub for future markdown processing (e.g., preview to HTML).

    Keeping this as a separate service makes the app modular and allows
    easy replacement with a richer implementation later (like python-markdown).
    """

    def to_html(self, markdown_text: str) -> str:
        # Minimal stub: escape angle brackets and wrap in <pre>.
        # Replace with real markdown conversion in the future.
        escaped = (
            markdown_text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )
        return f"<pre>{escaped}</pre>"
