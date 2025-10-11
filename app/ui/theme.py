from __future__ import annotations
from dataclasses import dataclass
import sys
from ctypes import byref, sizeof, c_int
from typing import Any


@dataclass(frozen=True)
class ThemeColors:
    """Defines a set of colors for the application UI and markdown tags."""

    # App and editor
    background: str
    foreground: str
    caret: str
    selection_bg: str
    selection_fg: str

    # Menu
    menubar_bg: str
    menubar_fg: str
    menu_active_bg: str
    menu_active_fg: str

    # Markdown tags
    heading_fg: str
    inline_code_bg: str
    code_block_bg: str
    blockquote_fg: str
    list_item_fg: str
    link_text_fg: str
    link_url_fg: str

    # Code syntax colors
    code_kw_fg: str
    code_name_fg: str
    code_builtin_fg: str
    code_str_fg: str
    code_num_fg: str
    code_cmt_fg: str
    code_op_fg: str
    code_punc_fg: str
    code_func_fg: str
    code_class_fg: str
    code_deco_fg: str


# Slightly muted dark theme
DARK_THEME = ThemeColors(
    background="#111827",  # gray-900
    foreground="#e5e7eb",  # gray-200
    caret="#f3f4f6",  # gray-100
    selection_bg="#374151",  # gray-700
    selection_fg="#f9fafb",  # gray-50
    menubar_bg="#0f172a",  # slate-900
    menubar_fg="#e5e7eb",  # gray-200
    menu_active_bg="#1f2937",  # gray-800
    menu_active_fg="#f3f4f6",  # gray-100
    heading_fg="#93c5fd",  # blue-300
    inline_code_bg="#1f2937",  # gray-800
    code_block_bg="#111827",  # gray-900
    blockquote_fg="#9ca3af",  # gray-400
    list_item_fg="#d1d5db",  # gray-300
    link_text_fg="#93c5fd",  # blue-300
    link_url_fg="#9ca3af",  # gray-400
    # Code syntax
    code_kw_fg="#c084fc",  # purple-400
    code_name_fg="#e5e7eb",  # gray-200 (default text)
    code_builtin_fg="#60a5fa",  # blue-400
    code_str_fg="#34d399",  # emerald-400
    code_num_fg="#fbbf24",  # amber-400
    code_cmt_fg="#6b7280",  # gray-500
    code_op_fg="#f472b6",  # pink-400
    code_punc_fg="#9ca3af",  # gray-400
    code_func_fg="#93c5fd",  # blue-300
    code_class_fg="#fca5a5",  # red-300
    code_deco_fg="#d8b4fe",  # purple-300
)


def apply_theme_to_root(root: Any, theme: ThemeColors) -> None:
    """Apply base colors to the Tk root and menu defaults.

    Uses option database for menus so popups and cascades inherit dark colors.
    """
    try:
        root.configure(bg=theme.background)
        # Menu defaults
        root.option_add("*Menu.background", theme.menubar_bg)
        root.option_add("*Menu.foreground", theme.menubar_fg)
        root.option_add("*Menu.activeBackground", theme.menu_active_bg)
        root.option_add("*Menu.activeForeground", theme.menu_active_fg)
        root.option_add("*Menu.relief", "flat")
    except Exception:
        # Best-effort; on some platforms option db keys may vary
        pass


def apply_windows_dark_title_bar(root: Any) -> None:
    """Attempt to set a dark title bar on Windows 10/11 via DWM attribute.

    This is best-effort and silently ignored on failure or non-Windows.
    """
    if sys.platform != "win32":
        return
    try:
        from ctypes import windll  # type: ignore

        hwnd = root.winfo_id()
        DWMWA_USE_IMMERSIVE_DARK_MODE = 20
        DWMWA_USE_IMMERSIVE_DARK_MODE_BEFORE_20H1 = 19
        value = c_int(1)

        # Try modern attribute first
        hr = windll.dwmapi.DwmSetWindowAttribute(
            c_int(hwnd),
            c_int(DWMWA_USE_IMMERSIVE_DARK_MODE),
            byref(value),
            sizeof(value),
        )
        if hr != 0:
            # Fall back to older attribute id
            windll.dwmapi.DwmSetWindowAttribute(
                c_int(hwnd),
                c_int(DWMWA_USE_IMMERSIVE_DARK_MODE_BEFORE_20H1),
                byref(value),
                sizeof(value),
            )
    except Exception:
        # Ignore if not supported
        pass
