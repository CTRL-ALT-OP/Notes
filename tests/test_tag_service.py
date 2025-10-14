from app.services.tag_service import TagReplacer


def test_tag_replacer_minute_pass_through(monkeypatch):
    # Freeze time to ensure deterministic replacement
    from datetime import datetime

    class FakeDT(datetime):
        @classmethod
        def now(cls, tz=None):  # noqa: ANN001
            return cls(2020, 1, 1, 12, 34, 56)

    monkeypatch.setattr("app.services.tag_service.datetime", FakeDT)
    tr = TagReplacer()
    assert tr.replace("at {min}") == "at 34"
