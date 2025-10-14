import contextlib
import sys
from types import SimpleNamespace, ModuleType
from pathlib import Path


def _install_tkinter_mocks() -> None:
    # Build proper module objects so imports like `import tkinter.font as tkfont` work
    tk_mod = ModuleType("tkinter")

    class _DummyText:
        pass

    tk_mod.Text = _DummyText
    tk_mod.END = "end"
    tk_mod.Tk = object
    tk_mod.Toplevel = object

    # tkinter.font child module
    tkfont_mod = ModuleType("tkinter.font")

    class _Font:
        def __init__(self, font=None):
            self._size = 12
            self._family = "TkDefaultFont"
            self._weight = None
            self._slant = None

        def configure(self, **kwargs):
            if "size" in kwargs:
                self._size = kwargs["size"]
            if "family" in kwargs:
                self._family = kwargs["family"]
            if "weight" in kwargs:
                self._weight = kwargs["weight"]
            if "slant" in kwargs:
                self._slant = kwargs["slant"]

        def cget(self, key: str):
            if key == "size":
                return self._size
            return self._family if key == "family" else None

        def copy(self):
            f = _Font()
            f._size = self._size
            f._family = self._family
            f._weight = self._weight
            f._slant = self._slant
            return f

    def nametofont(name: str) -> _Font:  # noqa: ARG001
        return _Font()

    tkfont_mod.Font = _Font
    tkfont_mod.nametofont = nametofont

    # Register modules
    sys.modules["tkinter"] = tk_mod
    sys.modules["Tkinter"] = tk_mod
    sys.modules["tkinter.font"] = tkfont_mod
    sys.modules.setdefault("tkinter.filedialog", ModuleType("tkinter.filedialog"))
    sys.modules.setdefault("tkinter.messagebox", ModuleType("tkinter.messagebox"))
    sys.modules.setdefault("tkinter.ttk", ModuleType("tkinter.ttk"))


def pytest_configure(config):
    # Ensure repository root is importable as a package root (so 'app' works)
    with contextlib.suppress(Exception):
        root = Path(__file__).resolve().parents[1]
        sys.path.insert(0, str(root))
    _install_tkinter_mocks()
