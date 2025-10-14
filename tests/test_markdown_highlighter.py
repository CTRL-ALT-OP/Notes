from app.services.markdown_highlighter import MarkdownHighlighter


class FakeText:
    def __init__(self, content: str):
        self._content = content
        self.tags = []
        self._cfg = {}
        self._font = "TkDefaultFont"

    def cget(self, key):  # noqa: ANN001
        return self._font if key == "font" else None

    def tag_config(self, tag, **kw):  # noqa: ANN001, ANN003
        self._cfg[tag] = kw

    def tag_add(self, tag, s, e):  # noqa: ANN001, ANN002
        self.tags.append((tag, s, e))

    def tag_remove(self, tag, s, e):  # noqa: ANN001, ANN002
        return None

    def tag_names(self):
        return list({t for t, _, _ in self.tags})

    def tag_delete(self, tag):  # noqa: ANN001
        return None

    def tag_raise(self, tag):  # noqa: ANN001
        return None

    def get(self, s, e):  # noqa: ANN001, ANN002
        return self._content


def test_highlight_basic_tags():
    text = FakeText("""# Title\n\n- item\n\n`code` and [x](url)\n""")
    mh = MarkdownHighlighter()
    mh.highlight(text)  # type: ignore[arg-type]
    tag_names = {t for t, _, _ in text.tags}
    # Expect some common tags applied
    assert "md_h1" in tag_names
    assert "md_ul_marker" in tag_names or "md_list_item" in tag_names
    assert "md_inline_code" in tag_names
    assert "md_link_text" in tag_names and "md_link_url" in tag_names


def test_headings_and_emphasis_overlays():
    text = FakeText("""# Heading with *italic* and **bold** and ***both***\n""")
    mh = MarkdownHighlighter()
    mh.highlight(text)  # type: ignore[arg-type]
    tag_names = {t for t, _, _ in text.tags}
    assert "md_h1" in tag_names
    assert "md_italic" in tag_names
    assert "md_bold" in tag_names
    assert "md_bold_italic" in tag_names
    # Composite heading+italic tag should exist when italic falls within heading
    assert "md_h1_italic" in tag_names


def test_blockquote_and_strikethrough_and_inline_code():
    text = FakeText("> quote\n\nNormal with ~~strike~~ and `inline` code\n")
    mh = MarkdownHighlighter()
    mh.highlight(text)  # type: ignore[arg-type]
    tag_names = {t for t, _, _ in text.tags}
    assert "md_blockquote" in tag_names
    assert "md_strike" in tag_names
    assert "md_inline_code" in tag_names


def test_list_nesting_levels_and_ordered_markers():
    text = FakeText(
        """- top
  - level1
    - level2
\t- tab_as_level2
1. ordered
"""
    )
    mh = MarkdownHighlighter()
    mh.highlight(text)  # type: ignore[arg-type]
    tag_names = {t for t, _, _ in text.tags}
    # Unordered and ordered markers
    assert "md_ul_marker" in tag_names
    assert "md_ol_marker" in tag_names
    # Level tags capped and present
    assert "md_list_lvl_0" in tag_names
    assert "md_list_lvl_1" in tag_names
    assert "md_list_lvl_2" in tag_names


def test_fenced_code_block_tags_and_python_run_interaction():
    code = """```python\nprint('hi')\n```\n"""
    text = FakeText(code)
    mh = MarkdownHighlighter()
    mh.highlight(text)  # type: ignore[arg-type]
    tag_names = {t for t, _, _ in text.tags}
    # Code block and dynamic tags
    assert "md_code_block" in tag_names
    # Dynamic per-block tags exist
    assert any(t.startswith("md_code_block_") for t in tag_names)
    assert any(t.startswith("md_code_body_") for t in tag_names)
    assert any(t.startswith("md_code_lang_") for t in tag_names)
    # Python enables run-tag interactions
    run_tags = [t for t in tag_names if t.startswith("md_code_run_")]
    assert len(run_tags) == 1
    cis = mh.get_code_run_interactions()
    assert len(cis) == 1
    assert cis[0].language in ("python", "py")
    assert cis[0].block_tag.startswith("md_code_block_")
    assert cis[0].body_tag.startswith("md_code_body_")
    assert cis[0].run_tag == run_tags[0]


def test_language_tag_is_underlined_when_present():
    code = """``` py \npass\n```\n"""
    text = FakeText(code)
    mh = MarkdownHighlighter()
    mh.highlight(text)  # type: ignore[arg-type]
    # Find a lang tag config and ensure underline set via tag_config
    lang_tags = [t for t in text._cfg if str(t).startswith("md_code_lang_")]
    assert lang_tags, "expected language tag configs"
    assert any(text._cfg[t].get("underline") for t in lang_tags)


def test_link_interactions_collect_both_text_and_url_regions():
    text = FakeText("""See [Example](https://example.com) now\n""")
    mh = MarkdownHighlighter()
    mh.highlight(text)  # type: ignore[arg-type]
    tag_names = {t for t, _, _ in text.tags}
    assert "md_link_text" in tag_names and "md_link_url" in tag_names
    interactions = mh.get_link_interactions()
    assert len(interactions) == 1
    assert interactions[0].url.startswith("https://example.com")
    # Dynamic target tag is created and applied
    assert interactions[0].tag in tag_names


def test_repeated_highlight_resets_interactions():
    text = FakeText("""```python\nprint('x')\n``` and [x](url)\n""")
    mh = MarkdownHighlighter()
    mh.highlight(text)  # type: ignore[arg-type]
    # First pass should collect both kinds of interactions
    assert len(mh.get_code_run_interactions()) == 1
    assert len(mh.get_link_interactions()) == 1
    # Run again; counts should not grow
    mh.highlight(text)  # type: ignore[arg-type]
    assert len(mh.get_code_run_interactions()) == 1
    assert len(mh.get_link_interactions()) == 1


def test_constants_exposed():
    # Sanity: constants exist and contain expected markers
    assert MarkdownHighlighter.OUTPUT_HEADER.startswith("### Output:")
    assert MarkdownHighlighter.OUTPUT_FOOTER.strip("- ") == "\n"
