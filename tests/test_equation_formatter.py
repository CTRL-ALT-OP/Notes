from types import SimpleNamespace

from app.services.equation_formatter import EquationAutoFormatter


class FakeText:
    def __init__(self, content: str, insert_index: str) -> None:
        self._content = content
        self._insert_index = insert_index
        self.inserted = ""

    # Minimal subset used by EquationAutoFormatter
    def index(self, what: str) -> str:  # noqa: ARG002
        return self._insert_index

    def get(self, start: str, end: str) -> str:  # noqa: ARG002
        # Only support reading from line start to current insert
        line_no = int(self._insert_index.split(".")[0])
        if start == f"{line_no}.0":
            # Return content up to the position referenced by _insert_index
            col = int(self._insert_index.split(".")[1])
            # Support multi-line content
            lines = self._content.splitlines()
            line = lines[line_no - 1] if 0 <= line_no - 1 < len(lines) else ""
            return line[:col]
        return ""

    def insert(self, where: str, s: str) -> None:  # noqa: ARG002
        self.inserted += s

    def bind(self, *args, **kwargs):  # noqa: D401, ANN001, ANN002
        return None


def test_equation_inserts_result_after_equals(monkeypatch):
    # Ensure tkinter Text and constants exist via conftest mocks
    fmt = EquationAutoFormatter()
    # Simulate typing "3+4=" on line 1 at column 4
    fake = FakeText("3+4=", "1.4")
    fmt._on_equals(fake)  # type: ignore[arg-type]
    assert fake.inserted.strip() == "7"

    # caret '^' works as power
    fake2 = FakeText("2^3=", "1.4")
    fmt._on_equals(fake2)  # type: ignore[arg-type]
    assert fake2.inserted.strip() == "8"
