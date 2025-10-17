from __future__ import annotations
import contextlib
import itertools
import re
import tkinter as tk
import tkinter.font as tkfont
from typing import List, Tuple
from dataclasses import dataclass

try:
    # Optional dependency; highlight gracefully if missing
    from pygments import lex
    from pygments.lexers import get_lexer_by_name, guess_lexer
    from pygments.token import Token

    _PYGMENTS_AVAILABLE = True
except Exception:
    _PYGMENTS_AVAILABLE = False
from app.ui.theme import ThemeColors, DARK_THEME


@dataclass(frozen=True)
class LinkInteraction:
    url: str
    tag: str


@dataclass(frozen=True)
class CodeRunInteraction:
    language: str
    block_tag: str
    body_tag: str
    run_tag: str
    index: int


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
    ) -> None:
        self.debounce_ms = debounce_ms
        self.theme: ThemeColors = theme or DARK_THEME
        self._configured_widget_id: int | None = None
        # Collected interactive regions from the last highlight pass
        self._link_interactions: List[LinkInteraction] = []
        self._code_run_interactions: List[CodeRunInteraction] = []

        # Precompile patterns
        self._re_heading = re.compile(r"^(#{1,6})[\t ]+(.+)$", re.MULTILINE)
        self._re_bold = re.compile(r"(\*\*|__)([^\n]+?)\1")
        self._re_italic = re.compile(r"(?<!\*)\*([^\n*]+?)\*(?!\*)")
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
        with contextlib.suppress(Exception):
            for lvl in range(7):
                indent_px = lvl * 20
                text.tag_config(
                    f"md_list_lvl_{lvl}",
                    lmargin1=0,
                    lmargin2=indent_px + 20,
                )
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

        # Ensure selection highlight appears over any markdown backgrounds
        with contextlib.suppress(Exception):
            text.tag_raise("sel")

        self._configured_widget_id = id(text)

    def clear(self, text: tk.Text) -> None:
        for tag in self._all_tags:
            text.tag_remove(tag, "1.0", tk.END)
        # Remove dynamically created link target tags
        with contextlib.suppress(Exception):
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

    def _apply_span(self, text: tk.Text, tag: str, start: int, end: int) -> None:
        if start < end:
            text.tag_add(tag, self._idx(start), self._idx(end))

    def _highlight_fenced_code_blocks(self, text: tk.Text, content: str) -> None:
        for idx, m in enumerate(self._re_fenced_code.finditer(content)):
            self._apply_span(text, "md_code_block", m.start(), m.end())
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
                lang_full = m.group("lang")
                ltrim = len(lang_full) - len(lang_full.lstrip())
                rtrim = len(lang_full) - len(lang_full.rstrip())
                lang_s = lang_start + ltrim
                lang_e = lang_end - rtrim
                text.tag_add(lang_tag, self._idx(lang_s), self._idx(lang_e))
                with contextlib.suppress(Exception):
                    text.tag_config(lang_tag, underline=True)
            with contextlib.suppress(Exception):
                self._highlight_code_block_tokens(text, content, m)
            if (lang_raw.lower() in ("python", "py", "py3", "py2")) and (
                body_start is not None and body_end is not None
            ):
                run_tag = f"md_code_run_{idx}"
                try:
                    if lang_start is not None and lang_end is not None and lang_raw:
                        text.tag_add(run_tag, self._idx(lang_s), self._idx(lang_e))
                    else:
                        text.tag_add(
                            run_tag, self._idx(body_start), self._idx(body_end)
                        )
                except Exception:
                    text.tag_add(run_tag, self._idx(body_start), self._idx(body_end))

                self._code_run_interactions.append(
                    CodeRunInteraction(
                        language=lang_raw.lower(),
                        block_tag=block_tag,
                        body_tag=body_tag,
                        run_tag=run_tag,
                        index=idx,
                    )
                )

    def _highlight_headings(
        self, text: tk.Text, content: str
    ) -> List[Tuple[int, int, int]]:
        heading_spans: List[Tuple[int, int, int]] = []
        for m in self._re_heading.finditer(content):
            hashes, heading_text = m.group(1), m.group(2)
            level = min(len(hashes), 6)
            tag = f"md_h{level}"
            text_start = m.start(2)
            text_end = m.end(2)
            self._apply_span(text, tag, text_start, text_end)
            heading_spans.append((text_start, text_end, level))
        return heading_spans

    def _highlight_emphasis(
        self, text: tk.Text, content: str
    ) -> Tuple[List[Tuple[int, int]], List[Tuple[int, int]]]:
        bold_spans: List[Tuple[int, int]] = []
        italic_spans: List[Tuple[int, int]] = []
        for m in self._re_bold_italic.finditer(content):
            start, end = m.start(2), m.end(2)
            self._apply_span(text, "md_bold_italic", start, end)
            bold_spans.append((start, end))
            italic_spans.append((start, end))
        for m in self._re_bold.finditer(content):
            start, end = m.start(2), m.end(2)
            self._apply_span(text, "md_bold", start, end)
            bold_spans.append((start, end))
        for m in self._re_italic.finditer(content):
            grp = 1 if m.group(1) is not None else 2
            start, end = m.start(grp), m.end(grp)
            self._apply_span(text, "md_italic", start, end)
            italic_spans.append((start, end))
        if bold_spans and italic_spans:
            for bs, is_ in itertools.product(bold_spans, italic_spans):
                s = max(bs[0], is_[0])
                e = min(bs[1], is_[1])
                if s < e:
                    self._apply_span(text, "md_bold_italic", s, e)
        return bold_spans, italic_spans

    def _highlight_misc_inline(self, text: tk.Text, content: str) -> None:
        for m in self._re_strike.finditer(content):
            self._apply_span(text, "md_strike", m.start(1), m.end(1))
        for m in self._re_inline_code.finditer(content):
            self._apply_span(text, "md_inline_code", m.start(1), m.end(1))
        for m in self._re_blockquote.finditer(content):
            self._apply_span(text, "md_blockquote", m.start(), m.end())

    def _highlight_lists(self, text: tk.Text, content: str) -> None:
        for m in self._re_ul.finditer(content):
            self._apply_span(text, "md_list_item", m.start(), m.end())
            indent_ws = m.group("indent") or ""
            level = self._indent_level(indent_ws)
            level = max(0, min(level, 6))
            self._apply_span(text, f"md_list_lvl_{level}", m.start(), m.end())
            self._apply_span(text, "md_ul_marker", m.start("marker"), m.end("marker"))
        for m in self._re_ol.finditer(content):
            self._apply_span(text, "md_list_item", m.start(), m.end())
            indent_ws = m.group("indent") or ""
            level = self._indent_level(indent_ws)
            level = max(0, min(level, 6))
            self._apply_span(text, f"md_list_lvl_{level}", m.start(), m.end())
            marker_start = m.start("num")
            marker_end = m.end("num")
            with contextlib.suppress(Exception):
                if content[marker_end : marker_end + 1] == ".":
                    marker_end += 1
            self._apply_span(text, "md_ol_marker", marker_start, marker_end)

    def _highlight_links(self, text: tk.Text, content: str) -> None:
        for idx, m in enumerate(self._re_link.finditer(content)):
            self._apply_span(text, "md_link_text", m.start(1), m.end(1))
            self._apply_span(text, "md_link_url", m.start(2), m.end(2))
            url = m.group(2)
            unique_tag = f"md_link_target_{idx}"
            text.tag_add(unique_tag, self._idx(m.start(1)), self._idx(m.end(1)))
            text.tag_add(unique_tag, self._idx(m.start(2)), self._idx(m.end(2)))
            self._link_interactions.append(LinkInteraction(url=url, tag=unique_tag))

    def highlight(self, text: tk.Text) -> None:
        self.configure_tags(text)
        self.clear(text)
        # reset interactions
        self._link_interactions.clear()
        self._code_run_interactions.clear()
        content = text.get("1.0", tk.END)
        # Order matters for visual stacking and composite tags
        self._highlight_fenced_code_blocks(text, content)
        heading_spans = self._highlight_headings(text, content)
        bold_spans, italic_spans = self._highlight_emphasis(text, content)
        if heading_spans and italic_spans:
            for h_start, h_end, level in heading_spans:
                for is_ in italic_spans:
                    s = max(h_start, is_[0])
                    e = min(h_end, is_[1])
                    if s < e:
                        self._apply_span(text, f"md_h{level}_italic", s, e)
        self._highlight_misc_inline(text, content)
        self._highlight_lists(text, content)
        self._highlight_links(text, content)

        # Ensure selection highlight remains visible over dynamic tags
        with contextlib.suppress(Exception):
            text.tag_raise("sel")

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
        lang_raw = (m["lang"] or "").strip()
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

    def get_link_interactions(self) -> List[LinkInteraction]:
        return list(self._link_interactions)

    def get_code_run_interactions(self) -> List[CodeRunInteraction]:
        return list(self._code_run_interactions)
