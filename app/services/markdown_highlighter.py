from __future__ import annotations
import re
import tkinter as tk
import tkinter.font as tkfont
from typing import List, Tuple

try:
    # Optional dependency; highlight gracefully if missing
    from pygments import lex
    from pygments.lexers import get_lexer_by_name, guess_lexer
    from pygments.token import Token

    _PYGMENTS_AVAILABLE = True
except Exception:
    _PYGMENTS_AVAILABLE = False
from app.services.link_handler import LinkHandler
from app.services.code_runner import CodeRunner
from app.ui.theme import ThemeColors, DARK_THEME


class MarkdownHighlighter:
    """Applies Markdown styling to a Tkinter Text widget using tags.

    This is regex-based and optimized for responsiveness over completeness.
    It highlights common constructs: headings, bold/italic/strikethrough,
    inline code, fenced code blocks, blockquotes, lists, and links.
    """

    # Output section markers (use these variables; do not hard-code elsewhere)
    OUTPUT_HEADER = "### Output: ----\n"
    OUTPUT_FOOTER = "--------------------\n"

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
        self._runner = CodeRunner()

        # Precompile patterns
        self._re_heading = re.compile(r"^(#{1,6})[\t ]+(.+)$", re.MULTILINE)
        self._re_bold = re.compile(r"(\*\*|__)([^\n]+?)\1")
        self._re_italic = re.compile(
            r"(?<!\*)\*([^\n*]+?)\*(?!\*)|(?<!_)_([^\n_]+?)_(?!_)"
        )
        self._re_bold_italic = re.compile(r"(\*\*\*|___)([^\n]+?)\1")
        self._re_strike = re.compile(r"~~([^\n]+?)~~")
        self._re_inline_code = re.compile(r"`([^`\n]+?)`")
        self._re_fenced_code = re.compile(
            r"^```(?P<lang>[^\n`]*)\n(?P<body>[\s\S]*?)^```",
            re.MULTILINE,
        )
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
            # Code token tags
            "md_code_kw",
            "md_code_name",
            "md_code_builtin",
            "md_code_str",
            "md_code_num",
            "md_code_cmt",
            "md_code_op",
            "md_code_punc",
            "md_code_func",
            "md_code_class",
            "md_code_deco",
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
        # Syntax token colors
        text.tag_config("md_code_kw", foreground=self.theme.code_kw_fg)
        text.tag_config("md_code_name", foreground=self.theme.code_name_fg)
        text.tag_config("md_code_builtin", foreground=self.theme.code_builtin_fg)
        text.tag_config("md_code_str", foreground=self.theme.code_str_fg)
        text.tag_config("md_code_num", foreground=self.theme.code_num_fg)
        text.tag_config("md_code_cmt", foreground=self.theme.code_cmt_fg)
        text.tag_config("md_code_op", foreground=self.theme.code_op_fg)
        text.tag_config("md_code_punc", foreground=self.theme.code_punc_fg)
        text.tag_config("md_code_func", foreground=self.theme.code_func_fg)
        text.tag_config("md_code_class", foreground=self.theme.code_class_fg)
        text.tag_config("md_code_deco", foreground=self.theme.code_deco_fg)

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
                name = str(tag)
                if (
                    name.startswith("md_link_target_")
                    or name.startswith("md_code_run_")
                    or name.startswith("md_code_block_")
                    or name.startswith("md_code_body_")
                    or name.startswith("md_code_lang_")
                ):
                    try:
                        text.tag_delete(tag)
                    except Exception:
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
        for idx, m in enumerate(self._re_fenced_code.finditer(content)):
            self._apply_span(text, "md_code_block", m.start(), m.end())
            # Unique tags to track this block + clickable lang
            block_tag = f"md_code_block_{idx}"
            body_tag = f"md_code_body_{idx}"
            lang_tag = f"md_code_lang_{idx}"
            text.tag_add(block_tag, self._idx(m.start()), self._idx(m.end()))
            body_start = m.start("body")
            body_end = m.end("body")
            if body_start is not None and body_end is not None:
                text.tag_add(body_tag, self._idx(body_start), self._idx(body_end))
            lang_start = m.start("lang")
            lang_end = m.end("lang")
            lang_raw = (m.group("lang") or "").strip()
            if lang_start is not None and lang_end is not None and lang_raw:
                # Narrow to trimmed span for nicer click target
                # Find trimmed bounds relative to lang group
                lang_full = m.group("lang")
                ltrim = len(lang_full) - len(lang_full.lstrip())
                rtrim = len(lang_full) - len(lang_full.rstrip())
                lang_s = lang_start + ltrim
                lang_e = lang_end - rtrim
                text.tag_add(lang_tag, self._idx(lang_s), self._idx(lang_e))
                # Make it look interactive
                try:
                    text.tag_config(lang_tag, underline=True)
                except Exception:
                    pass

            # Apply syntax tokens (pygments) inside the body if available
            try:
                self._highlight_code_block_tokens(text, content, m)
            except Exception:
                pass

            # Bind click for python blocks
            if (lang_raw.lower() in ("python", "py", "py3", "py2")) and (
                body_start is not None and body_end is not None
            ):
                run_tag = f"md_code_run_{idx}"
                # Click region: language tag if present; otherwise body
                try:
                    if lang_start is not None and lang_end is not None and lang_raw:
                        text.tag_add(run_tag, self._idx(lang_s), self._idx(lang_e))
                    else:
                        text.tag_add(
                            run_tag, self._idx(body_start), self._idx(body_end)
                        )
                except Exception:
                    text.tag_add(run_tag, self._idx(body_start), self._idx(body_end))

                def _on_enter(e):
                    try:
                        e.widget.configure(cursor="hand2")
                    except Exception:
                        pass

                def _on_leave(e):
                    try:
                        e.widget.configure(cursor="")
                    except Exception:
                        pass

                def _on_click(_e, i=idx, btag=block_tag, bdytag=body_tag):
                    try:
                        self._run_python_block(text, i, btag, bdytag)
                    except Exception:
                        pass

                text.tag_bind(run_tag, "<Enter>", _on_enter)
                text.tag_bind(run_tag, "<Leave>", _on_leave)
                text.tag_bind(run_tag, "<Button-1>", _on_click)

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

    # ---------- Code token highlighting ----------
    def _highlight_code_block_tokens(
        self, text: tk.Text, content: str, m: re.Match
    ) -> None:
        if not _PYGMENTS_AVAILABLE:
            return
        body_start = m.start("body")
        body_end = m.end("body")
        if body_start is None or body_end is None:
            return
        code_text = content[body_start:body_end]
        # Skip very large blocks for responsiveness
        if len(code_text) > 20000:
            return
        lang_raw = (m.group("lang") or "").strip()
        lexer = None
        try:
            if lang_raw:
                lexer = get_lexer_by_name(lang_raw, stripall=False)
        except Exception:
            lexer = None
        if lexer is None:
            try:
                # guess_lexer may be expensive; bound input size
                sample = code_text[:4000]
                lexer = guess_lexer(sample)
            except Exception:
                lexer = None
        if lexer is None:
            return

        # Map pygments token to our tag
        def tag_for(tok_type) -> str | None:
            # Use startswith semantics via in-tree hierarchy
            if tok_type in Token.Comment or str(tok_type).startswith("Token.Comment"):
                return "md_code_cmt"
            if tok_type in Token.Keyword or str(tok_type).startswith("Token.Keyword"):
                return "md_code_kw"
            if str(tok_type).startswith("Token.Name.Function"):
                return "md_code_func"
            if str(tok_type).startswith("Token.Name.Class"):
                return "md_code_class"
            if str(tok_type).startswith("Token.Name.Builtin"):
                return "md_code_builtin"
            if tok_type in Token.Name or str(tok_type).startswith("Token.Name"):
                return "md_code_name"
            if tok_type in Token.String or str(tok_type).startswith("Token.String"):
                return "md_code_str"
            if tok_type in Token.Number or str(tok_type).startswith("Token.Number"):
                return "md_code_num"
            if tok_type in Token.Operator or str(tok_type).startswith("Token.Operator"):
                return "md_code_op"
            if tok_type in Token.Punctuation or str(tok_type).startswith(
                "Token.Punctuation"
            ):
                return "md_code_punc"
            if str(tok_type).startswith("Token.Name.Decorator"):
                return "md_code_deco"
            return None

        offset = 0
        for tok_type, tok_text in lex(code_text, lexer):
            if not tok_text:
                continue
            tag = tag_for(tok_type)
            # Skip pure whitespace to reduce tag churn
            if tag and not tok_text.isspace():
                start = body_start + offset
                end = start + len(tok_text)
                self._apply_span(text, tag, start, end)
            offset += len(tok_text)

    # ---------- Running python code blocks ----------
    def _run_python_block(
        self, text: tk.Text, index: int, block_tag: str, body_tag: str
    ) -> None:
        # Get code text from the body tag
        ranges = text.tag_ranges(body_tag)
        if not ranges or len(ranges) < 2:
            return
        start_idx, end_idx = ranges[0], ranges[1]
        code = text.get(start_idx, end_idx)
        rc, out, err = self._runner.run_python(code)
        combined = (out or "") + (err or "")
        display = combined if combined.strip() else "none\n"
        header = self.OUTPUT_HEADER
        footer = self.OUTPUT_FOOTER
        payload = header + display + ("" if display.endswith("\n") else "\n") + footer

        # Where to insert: after the code block
        branges = text.tag_ranges(block_tag)
        if not branges or len(branges) < 2:
            return
        block_end = branges[1]

        # If an existing output section exists directly below, delete it first by scanning
        try:
            # Read a bounded window after the block to search for header/footer
            window = text.get(block_end, f"{block_end}+20000c")
            # Allow leading blank lines
            lead = 0
            while lead < len(window) and window[lead] in "\r\n":
                lead += 1
            if window[lead:].startswith(header):
                rel_footer = window[lead:].find(footer)
                if rel_footer != -1:
                    total = lead + rel_footer + len(footer)
                    text.delete(block_end, f"{block_end}+{total}c")
        except Exception:
            pass

        # Ensure a separating newline
        try:
            prev_char = text.get(f"{block_end}-1c", block_end)
        except Exception:
            prev_char = "\n"
        if prev_char != "\n":
            text.insert(block_end, "\n")
            block_end = f"{block_end}+1c"

        # Insert the new output
        text.insert(block_end, payload)
