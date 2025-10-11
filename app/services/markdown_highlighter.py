from __future__ import annotations
import re
import tkinter as tk
import tkinter.font as tkfont
from typing import List, Tuple
from app.services.link_handler import LinkHandler
from app.ui.theme import ThemeColors, DARK_THEME


class MarkdownHighlighter:
    """Applies Markdown styling to a Tkinter Text widget using tags.

    This is regex-based and optimized for responsiveness over completeness.
    It highlights common constructs: headings, bold/italic/strikethrough,
    inline code, fenced code blocks, blockquotes, lists, and links.
    """

    def __init__(
        self,
        debounce_ms: int = 120,
        theme: ThemeColors | None = None,
        link_handler: LinkHandler | None = None,
    ) -> None:
        self.debounce_ms = debounce_ms
        self.theme: ThemeColors = theme or DARK_THEME
        self._configured_widget_id: int | None = None
        self._link_handler: LinkHandler = link_handler or LinkHandler()

        # Precompile patterns
        self._re_heading = re.compile(r"^(#{1,6})[\t ]+(.+)$", re.MULTILINE)
        self._re_bold = re.compile(r"(\*\*|__)([^\n]+?)\1")
        self._re_italic = re.compile(
            r"(?<!\*)\*([^\n*]+?)\*(?!\*)|(?<!_)_([^\n_]+?)_(?!_)"
        )
        self._re_bold_italic = re.compile(r"(\*\*\*|___)([^\n]+?)\1")
        self._re_strike = re.compile(r"~~([^\n]+?)~~")
        self._re_inline_code = re.compile(r"`([^`\n]+?)`")
        self._re_fenced_code = re.compile(r"^```[^\n]*\n[\s\S]*?^```", re.MULTILINE)
        self._re_blockquote = re.compile(r"^>[\t ]?.*$", re.MULTILINE)
        # Granular list patterns: unordered and ordered, with named groups
        self._re_ul = re.compile(
            r"^(?P<indent>[\t ]*)(?P<marker>[-*+])[\t ]+(?P<text>.+)$",
            re.MULTILINE,
        )
        self._re_ol = re.compile(
            r"^(?P<indent>[\t ]*)(?P<num>\d+)\.[\t ]+(?P<text>.+)$",
            re.MULTILINE,
        )
        self._re_link = re.compile(r"\[([^\]\n]+)\]\(([^)\n]+)\)")

        self._all_tags = [
            "md_h1",
            "md_h2",
            "md_h3",
            "md_h4",
            "md_h5",
            "md_h6",
            "md_h1_italic",
            "md_h2_italic",
            "md_h3_italic",
            "md_h4_italic",
            "md_h5_italic",
            "md_h6_italic",
            "md_bold",
            "md_italic",
            "md_bold_italic",
            "md_strike",
            "md_inline_code",
            "md_code_block",
            "md_blockquote",
            "md_list_item",
            "md_ul_marker",
            "md_ol_marker",
            # Predeclare several list level tags for clearing/config
            "md_list_lvl_0",
            "md_list_lvl_1",
            "md_list_lvl_2",
            "md_list_lvl_3",
            "md_list_lvl_4",
            "md_list_lvl_5",
            "md_list_lvl_6",
            "md_link_text",
            "md_link_url",
        ]

    def _idx(self, char_index: int) -> str:
        return f"1.0+{char_index}c"

    def configure_tags(self, text: tk.Text) -> None:
        """Configure fonts and tag styles. Call once per Text widget."""
        if self._configured_widget_id == id(text):
            return

        base_font = tkfont.nametofont(text.cget("font")).copy()
        base_size = int(base_font.cget("size"))

        def mk_font(
            weight: str | None = None,
            slant: str | None = None,
            size_delta: int = 0,
            family: str | None = None,
        ) -> tkfont.Font:
            f = tkfont.Font(font=base_font)
            if weight:
                f.configure(weight=weight)
            if slant:
                f.configure(slant=slant)
            if size_delta:
                f.configure(size=base_size + size_delta)
            if family:
                f.configure(family=family)
            return f

        # Headings
        text.tag_config(
            "md_h1",
            font=mk_font(weight="bold", size_delta=8),
            foreground=self.theme.heading_fg,
        )
        text.tag_config(
            "md_h2",
            font=mk_font(weight="bold", size_delta=6),
            foreground=self.theme.heading_fg,
        )
        text.tag_config(
            "md_h3",
            font=mk_font(weight="bold", size_delta=4),
            foreground=self.theme.heading_fg,
        )
        text.tag_config(
            "md_h4",
            font=mk_font(weight="bold", size_delta=2),
            foreground=self.theme.heading_fg,
        )
        text.tag_config(
            "md_h5",
            font=mk_font(weight="bold", size_delta=1),
            foreground=self.theme.heading_fg,
        )
        text.tag_config(
            "md_h6", font=mk_font(weight="bold"), foreground=self.theme.heading_fg
        )

        # Emphasis
        text.tag_config("md_bold", font=mk_font(weight="bold"))
        text.tag_config("md_italic", font=mk_font(slant="italic"))
        text.tag_config("md_bold_italic", font=mk_font(weight="bold", slant="italic"))
        text.tag_config("md_strike", overstrike=True)

        # Code
        code_font_family = "Consolas"
        text.tag_config(
            "md_inline_code",
            background=self.theme.inline_code_bg,
            font=mk_font(family=code_font_family),
        )
        text.tag_config(
            "md_code_block",
            background=self.theme.code_block_bg,
            lmargin1=20,
            lmargin2=20,
            spacing1=4,
            spacing3=4,
            font=mk_font(family=code_font_family),
        )

        # Block elements
        text.tag_config(
            "md_blockquote",
            foreground=self.theme.blockquote_fg,
            lmargin1=20,
            lmargin2=20,
        )
        text.tag_config("md_list_item", foreground=self.theme.list_item_fg)
        text.tag_config(
            "md_ul_marker",
            font=mk_font(weight="bold"),
            foreground=self.theme.heading_fg,
        )
        text.tag_config(
            "md_ol_marker",
            font=mk_font(weight="bold"),
            foreground=self.theme.heading_fg,
        )

        # List indentation levels (hanging indent): lmargin1 applies to first line,
        # lmargin2 to wrapped lines; indent increases by 20px per level.
        try:
            for lvl in range(0, 7):
                indent_px = lvl * 20
                text.tag_config(
                    f"md_list_lvl_{lvl}",
                    lmargin1=0,
                    lmargin2=indent_px + 20,
                )
        except Exception:
            # If platform rejects margin config, ignore gracefully
            pass

        # Links
        text.tag_config(
            "md_link_text", foreground=self.theme.link_text_fg, underline=True
        )
        text.tag_config("md_link_url", foreground=self.theme.link_url_fg)

        # Composite heading + italic fonts (created last for highest priority)
        text.tag_config(
            "md_h1_italic", font=mk_font(weight="bold", slant="italic", size_delta=8)
        )
        text.tag_config(
            "md_h2_italic", font=mk_font(weight="bold", slant="italic", size_delta=6)
        )
        text.tag_config(
            "md_h3_italic", font=mk_font(weight="bold", slant="italic", size_delta=4)
        )
        text.tag_config(
            "md_h4_italic", font=mk_font(weight="bold", slant="italic", size_delta=2)
        )
        text.tag_config(
            "md_h5_italic", font=mk_font(weight="bold", slant="italic", size_delta=1)
        )
        text.tag_config("md_h6_italic", font=mk_font(weight="bold", slant="italic"))

        self._configured_widget_id = id(text)

    def clear(self, text: tk.Text) -> None:
        for tag in self._all_tags:
            text.tag_remove(tag, "1.0", tk.END)
        # Remove dynamically created link target tags
        try:
            for tag in text.tag_names():
                if str(tag).startswith("md_link_target_"):
                    try:
                        text.tag_delete(tag)
                    except Exception:
                        # Fallback: at least remove range
                        text.tag_remove(tag, "1.0", tk.END)
        except Exception:
            pass

    def _apply_span(self, text: tk.Text, tag: str, start: int, end: int) -> None:
        if start < end:
            text.tag_add(tag, self._idx(start), self._idx(end))

    def highlight(self, text: tk.Text) -> None:
        self.configure_tags(text)
        self.clear(text)
        content = text.get("1.0", tk.END)

        # Fenced code blocks: apply whole block styling first to avoid conflicting highlights
        for m in self._re_fenced_code.finditer(content):
            self._apply_span(text, "md_code_block", m.start(), m.end())

        # Track spans for composing nested styles
        bold_spans: List[Tuple[int, int]] = []
        italic_spans: List[Tuple[int, int]] = []
        heading_spans: List[Tuple[int, int, int]] = []  # (start, end, level)

        # Headings
        for m in self._re_heading.finditer(content):
            hashes, heading_text = m.group(1), m.group(2)
            level = min(len(hashes), 6)
            tag = f"md_h{level}"
            # Apply to the heading text only (exclude leading # and space)
            text_start = m.start(2)
            text_end = m.end(2)
            self._apply_span(text, tag, text_start, text_end)
            heading_spans.append((text_start, text_end, level))

        # Bold-italic (*** or ___) first
        for m in self._re_bold_italic.finditer(content):
            start, end = m.start(2), m.end(2)
            self._apply_span(text, "md_bold_italic", start, end)
            # Treat as both bold and italic for overlap logic
            bold_spans.append((start, end))
            italic_spans.append((start, end))

        # Bold then italic
        for m in self._re_bold.finditer(content):
            start, end = m.start(2), m.end(2)
            self._apply_span(text, "md_bold", start, end)
            bold_spans.append((start, end))

        for m in self._re_italic.finditer(content):
            # pattern has two alternatives; choose the matched group
            grp = 1 if m.group(1) is not None else 2
            start, end = m.start(grp), m.end(grp)
            self._apply_span(text, "md_italic", start, end)
            italic_spans.append((start, end))

        # Enable stacking: apply md_bold_italic over intersections of bold and italic
        if bold_spans and italic_spans:
            for bs in bold_spans:
                for is_ in italic_spans:
                    s = max(bs[0], is_[0])
                    e = min(bs[1], is_[1])
                    if s < e:
                        self._apply_span(text, "md_bold_italic", s, e)

        # Preserve heading size while allowing italic inside headings
        if heading_spans and italic_spans:
            for hs in heading_spans:
                h_start, h_end, level = hs
                for is_ in italic_spans:
                    s = max(h_start, is_[0])
                    e = min(h_end, is_[1])
                    if s < e:
                        self._apply_span(text, f"md_h{level}_italic", s, e)

        # Strikethrough
        for m in self._re_strike.finditer(content):
            self._apply_span(text, "md_strike", m.start(1), m.end(1))

        # Inline code
        for m in self._re_inline_code.finditer(content):
            self._apply_span(text, "md_inline_code", m.start(1), m.end(1))

        # Blockquote lines
        for m in self._re_blockquote.finditer(content):
            self._apply_span(text, "md_blockquote", m.start(), m.end())

        # List items
        # Unordered list items (bulleted)
        for m in self._re_ul.finditer(content):
            # Whole line styled as list item
            self._apply_span(text, "md_list_item", m.start(), m.end())
            # Apply indentation level
            indent_ws = m.group("indent") or ""
            level = self._indent_level(indent_ws)
            level = max(0, min(level, 6))
            self._apply_span(text, f"md_list_lvl_{level}", m.start(), m.end())
            # Emphasize the bullet marker itself
            self._apply_span(text, "md_ul_marker", m.start("marker"), m.end("marker"))

        # Ordered list items (numbered)
        for m in self._re_ol.finditer(content):
            # Whole line styled as list item
            self._apply_span(text, "md_list_item", m.start(), m.end())
            # Apply indentation level
            indent_ws = m.group("indent") or ""
            level = self._indent_level(indent_ws)
            level = max(0, min(level, 6))
            self._apply_span(text, f"md_list_lvl_{level}", m.start(), m.end())
            # Emphasize the numeric marker including the trailing period
            marker_start = m.start("num")
            marker_end = m.end("num")
            # Include the dot if present right after the number
            try:
                if content[marker_end : marker_end + 1] == ".":
                    marker_end += 1
            except Exception:
                pass
            self._apply_span(text, "md_ol_marker", marker_start, marker_end)

        # Links: style link text and show URL in subtle color; also bind clickable actions
        for idx, m in enumerate(self._re_link.finditer(content)):
            self._apply_span(text, "md_link_text", m.start(1), m.end(1))
            self._apply_span(text, "md_link_url", m.start(2), m.end(2))

            url = m.group(2)
            unique_tag = f"md_link_target_{idx}"
            # Make the clickable region be both the link-text and the URL
            text.tag_add(unique_tag, self._idx(m.start(1)), self._idx(m.end(1)))
            text.tag_add(unique_tag, self._idx(m.start(2)), self._idx(m.end(2)))

            def _open(_event=None, u=url):
                print(f"Opening link: {u}")
                try:
                    self._link_handler.open_link(u)
                except Exception:
                    pass

            text.tag_bind(unique_tag, "<Button-1>", _open)

            # Change cursor on hover using enter/leave bindings
            def _enter(e):
                try:
                    e.widget.configure(cursor="hand2")
                except Exception:
                    pass

            def _leave(e):
                try:
                    e.widget.configure(cursor="")
                except Exception:
                    pass

            text.tag_bind(unique_tag, "<Enter>", _enter)
            text.tag_bind(unique_tag, "<Leave>", _leave)

    def _indent_level(self, whitespace: str) -> int:
        """Estimate list nesting level from leading whitespace.

        Tabs count as 4 spaces. Each 2 spaces yields one level.
        """
        if not whitespace:
            return 0
        spaces = 0
        for ch in whitespace:
            if ch == "\t":
                spaces += 4
            elif ch == " ":
                spaces += 1
        return spaces // 2
