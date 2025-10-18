from __future__ import annotations
import contextlib
import tkinter as tk
from typing import Callable


class FindReplaceWindow(tk.Frame):
    """Overlay frame for Find/Replace, positioned at the top-right of the editor.

    Parent should be the editor widget/container. Uses place(..., anchor="ne").
    """

    def __init__(
        self,
        parent: tk.Misc,
        initial_find: str,
        on_change: Callable[[str, bool, bool], None],
        on_scrub_up: Callable[[], None],
        on_scrub_down: Callable[[], None],
        on_replace_next: Callable[[str], None],
        on_replace_all: Callable[[str], None],
        on_close: Callable[[], None],
    ) -> None:
        super().__init__(parent)

        # Resolve theme from the toplevel root if available
        with contextlib.suppress(Exception):
            root = self.winfo_toplevel()
        theme = getattr(root, "theme", None) if "root" in locals() else None

        bg_main = getattr(theme, "menubar_bg", "#222")
        fg_main = getattr(theme, "menubar_fg", "#eee")
        bg_active = getattr(theme, "menu_active_bg", "#333")
        fg_active = getattr(theme, "menu_active_fg", "#fff")
        entry_bg = getattr(theme, "background", "#111")
        entry_fg = getattr(theme, "foreground", "#eee")
        entry_caret = getattr(theme, "caret", "#fff")

        # Base container styling
        self.configure(
            bg=bg_main,
            highlightthickness=1,
            highlightbackground=bg_active,
            bd=0,
        )

        self._on_change = on_change
        self._on_scrub_up = on_scrub_up
        self._on_scrub_down = on_scrub_down
        self._on_replace_next = on_replace_next
        self._on_replace_all = on_replace_all
        self._on_close = on_close

        # Layout frame
        container = tk.Frame(
            self, padx=8, pady=8, bg=bg_main, bd=0, highlightthickness=0
        )
        container.pack(fill=tk.BOTH, expand=True)

        # Top row: Find entry + controls
        row1 = tk.Frame(container, bg=bg_main)
        row1.pack(fill=tk.X)

        tk.Label(row1, text="Find:", bg=bg_main, fg=fg_main).pack(
            side=tk.LEFT, padx=(0, 6)
        )
        self.find_entry = tk.Entry(
            row1,
            bg=entry_bg,
            fg=entry_fg,
            insertbackground=entry_caret,
            relief=tk.FLAT,
            width=28,
        )
        self.find_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.find_entry.insert(0, initial_find or "")
        self.find_entry.icursor(tk.END)

        up_btn = tk.Button(
            row1,
            text="▲",
            width=3,
            command=self._on_up,
            bg=bg_active,
            fg=fg_active,
            relief=tk.FLAT,
            padx=6,
        )
        up_btn.pack(side=tk.LEFT, padx=(6, 0))

        down_btn = tk.Button(
            row1,
            text="▼",
            width=3,
            command=self._on_down,
            bg=bg_active,
            fg=fg_active,
            relief=tk.FLAT,
            padx=6,
        )
        down_btn.pack(side=tk.LEFT, padx=(6, 0))

        close_btn = tk.Button(
            row1,
            text="✕",
            width=3,
            command=self._on_close_clicked,
            bg=bg_active,
            fg=fg_active,
            relief=tk.FLAT,
            padx=6,
        )
        close_btn.pack(side=tk.LEFT, padx=(6, 0))

        # Options
        opts = tk.Frame(container, bg=bg_main)
        opts.pack(fill=tk.X, pady=(6, 0))
        self.var_match_case = tk.BooleanVar(value=False)
        self.var_wildcards = tk.BooleanVar(value=True)
        tk.Checkbutton(
            opts,
            text="Match case",
            variable=self.var_match_case,
            bg=bg_main,
            fg=fg_main,
            activebackground=bg_active,
            activeforeground=fg_active,
            selectcolor=bg_active,
            command=self._notify_change,
        ).pack(side=tk.LEFT)
        tk.Checkbutton(
            opts,
            text="Wildcards (*, ?)",
            variable=self.var_wildcards,
            bg=bg_main,
            fg=fg_main,
            activebackground=bg_active,
            activeforeground=fg_active,
            selectcolor=bg_active,
            command=self._notify_change,
        ).pack(side=tk.LEFT, padx=(12, 0))

        # Replace row
        row2 = tk.Frame(container, bg=bg_main)
        row2.pack(fill=tk.X, pady=(6, 0))
        tk.Label(row2, text="Replace:", bg=bg_main, fg=fg_main).pack(
            side=tk.LEFT, padx=(0, 6)
        )
        self.replace_entry = tk.Entry(
            row2,
            bg=entry_bg,
            fg=entry_fg,
            insertbackground=entry_caret,
            relief=tk.FLAT,
            width=28,
        )
        self.replace_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        rnext_btn = tk.Button(
            row2,
            text="Replace next",
            command=self._on_replace_next_clicked,
            bg=bg_active,
            fg=fg_active,
            relief=tk.FLAT,
            padx=8,
        )
        rnext_btn.pack(side=tk.LEFT, padx=(6, 0))

        rall_btn = tk.Button(
            row2,
            text="Replace all",
            command=self._on_replace_all_clicked,
            bg=bg_active,
            fg=fg_active,
            relief=tk.FLAT,
            padx=8,
        )
        rall_btn.pack(side=tk.LEFT, padx=(6, 0))

        # Bindings
        self.find_entry.bind("<KeyRelease>", lambda _e: self._notify_change())
        self.find_entry.bind("<Return>", lambda _e: self._on_down())
        self.replace_entry.bind("<Return>", lambda _e: self._on_replace_next_clicked())
        self.bind("<Escape>", lambda _e: self._on_close_clicked())

        # Size and position: top-right
        with contextlib.suppress(Exception):
            self.update_idletasks()
        self.place(relx=1.0, x=-8, y=8, anchor="ne")
        with contextlib.suppress(Exception):
            self.lift()
        self.after(30, lambda: self.find_entry.focus_set())

        # Initial change notification to seed highlights
        self.after(0, self._notify_change)

    # ----- Callbacks -----
    def _notify_change(self) -> None:
        try:
            text = self.find_entry.get() or ""
            self._on_change(text, self.var_match_case.get(), self.var_wildcards.get())
        except Exception:
            pass

    def _on_up(self) -> None:
        with contextlib.suppress(Exception):
            self._on_scrub_up()

    def _on_down(self) -> None:
        with contextlib.suppress(Exception):
            self._on_scrub_down()

    def _on_replace_next_clicked(self) -> None:
        with contextlib.suppress(Exception):
            self._on_replace_next(self.replace_entry.get() or "")

    def _on_replace_all_clicked(self) -> None:
        with contextlib.suppress(Exception):
            self._on_replace_all(self.replace_entry.get() or "")

    def _on_close_clicked(self) -> None:
        try:
            self._on_close()
        finally:
            with contextlib.suppress(Exception):
                self.destroy()
