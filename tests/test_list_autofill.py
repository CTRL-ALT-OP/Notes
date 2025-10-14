from app.services.list_autofill import ListAutoFill


class FakeText:
    def __init__(self, line: str):
        self.line = line
        self._insert = "1.%d" % len(line)
        self._inserted = ""
        self._deleted = []

    def index(self, what: str):  # noqa: ARG002
        return self._insert

    def get(self, start: str, end: str):  # noqa: ARG002
        if start.startswith("1.") and end == "1.end":
            return self.line
        return self.line if start == "1.0" and end == "1.end" else ""

    def insert(self, where: str, s: str):  # noqa: ARG002
        self._inserted += s

    def delete(self, start: str, end: str):  # noqa: ARG002
        self._deleted.append((start, end))

    def mark_set(self, *args, **kwargs):  # noqa: D401, ANN001, ANN002
        return None

    def bind(self, *args, **kwargs):  # noqa: D401, ANN001, ANN002
        return None

    def see(self, *args, **kwargs):  # noqa: D401, ANN001, ANN002
        return None


def test_ul_enter_adds_next_bullet():
    f = FakeText("- item")
    af = ListAutoFill()
    res = af._on_return(f)  # type: ignore[arg-type]
    assert res == "break"
    assert "\n- " in f._inserted


def test_ol_enter_adds_next_number_and_breaks_on_empty():
    f = FakeText("1. item")
    af = ListAutoFill()
    res = af._on_return(f)  # type: ignore[arg-type]
    assert res == "break"
    assert "\n2. " in f._inserted

    f2 = FakeText("2.   ")
    res2 = af._on_return(f2)  # type: ignore[arg-type]
    assert res2 == "break"
