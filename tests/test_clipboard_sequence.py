from app.services.clipboard_sequence import (
    ClipboardSequenceManager,
    SequenceOptions,
)


def test_clipboard_sequence_basic_increment_and_tag(monkeypatch):
    mgr = ClipboardSequenceManager()

    # Freeze TagReplacer to return deterministic value for {min}
    from app.services import tag_service

    def fake_replace(s: str) -> str:
        return s.replace("{min}", "42")

    monkeypatch.setattr(
        tag_service.TagReplacer, "replace", lambda self, s: fake_replace(s)
    )

    opts = SequenceOptions(
        auto_increment=True, ordinal_only=True, replace_tags=True, incr_text=True
    )
    first = mgr.set_initial("Item 1 at {min}", opts)
    assert first == "Item 1 at 42"

    # First paste returns incremented version
    nxt = mgr.on_paste(first)
    assert nxt == "Item 2 at 43"

    # Second paste again
    nxt2 = mgr.on_paste(nxt)
    assert nxt2 == "Item 3 at 44"

    # If clipboard diverges, sequence stops
    assert mgr.on_paste("external change") is None


def test_clipboard_sequence_no_increment():
    mgr = ClipboardSequenceManager()
    opts = SequenceOptions(auto_increment=False, replace_tags=False)
    first = mgr.set_initial("Step 10", opts)
    assert first == "Step 10"
    # Without increment, next paste should equal last
    assert mgr.on_paste(first) == "Step 10"


def test_clipboard_sequence_reset_behavior():
    mgr = ClipboardSequenceManager()
    opts = SequenceOptions(auto_increment=True, replace_tags=False)

    first = mgr.set_initial("A 1", opts)
    assert mgr.last_generated == "A 1"
    assert mgr.on_paste(first) == "A 2"

    # Reset clears state and stops the sequence immediately
    mgr.reset()
    assert mgr.last_generated is None
    assert mgr.on_paste("anything") is None

    # New sequence after reset works independently of prior options
    first2 = mgr.set_initial(
        "B 10", SequenceOptions(auto_increment=False, replace_tags=False)
    )
    assert first2 == "B 10"
    assert mgr.on_paste(first2) == "B 10"


def test_clipboard_sequence_ordinal_only_textual_increment():
    mgr = ClipboardSequenceManager()
    opts = SequenceOptions(
        auto_increment=True, ordinal_only=True, replace_tags=False, incr_text=True
    )
    first = mgr.set_initial("one and first", opts)
    assert first == "one and first"

    nxt = mgr.on_paste(first)
    # With ordinal_only=True, textual ordinals increment, cardinals do not
    assert nxt == "one and second"


def test_clipboard_sequence_incr_text_false_numeric_only():
    mgr = ClipboardSequenceManager()
    opts = SequenceOptions(
        auto_increment=True, ordinal_only=False, replace_tags=False, incr_text=False
    )

    first = mgr.set_initial("first 1", opts)
    assert first == "first 1"

    nxt = mgr.on_paste(first)
    # Numeric part increments; textual part remains unchanged when incr_text=False
    assert nxt == "first 2"

    nxt2 = mgr.on_paste(nxt)
    assert nxt2 == "first 3"


def test_clipboard_sequence_stop_on_change_and_last_generated():
    mgr = ClipboardSequenceManager()
    opts = SequenceOptions(auto_increment=True, replace_tags=False)

    first = mgr.set_initial("Item 7", opts)
    assert mgr.last_generated == "Item 7"

    nxt = mgr.on_paste(first)
    assert nxt == "Item 8"
    assert mgr.last_generated == "Item 8"

    # External clipboard change stops the sequence and does not mutate last_generated
    assert mgr.on_paste("Item 999") is None
    assert mgr.last_generated == "Item 8"
