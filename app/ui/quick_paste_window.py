from __future__ import annotations
import contextlib
import tkinter as tk
from typing import Callable

from app.services.clipboard_sequence import SequenceOptions


class QuickPasteWindow(tk.Frame):
    """Overlay frame for quick sequence paste setup.

    Designed to be placed over the editor area using place(..., anchor="center").
    """

    def __init__(
        self,
        parent: tk.Misc,
        initial_text: str,
        on_start: Callable[[str, SequenceOptions], None],
    ):
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

        self._on_start = on_start

        # Layout frame
        container = tk.Frame(
            self, padx=8, pady=8, bg=bg_main, bd=0, highlightthickness=0
        )
        container.pack(fill=tk.BOTH, expand=True)

        # Entry row with clipboard button
        row = tk.Frame(container, bg=bg_main)
        row.pack(fill=tk.X)
        self.entry = tk.Entry(
            row,
            bg=entry_bg,
            fg=entry_fg,
            insertbackground=entry_caret,
            relief=tk.FLAT,
        )
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.entry.insert(0, initial_text)
        self.entry.icursor(tk.END)
        copy_btn = tk.Button(
            row,
            text="📋",
            width=3,
            command=self._on_submit,
            bg=bg_active,
            fg=fg_active,
            relief=tk.FLAT,
            padx=6,
        )
        copy_btn.pack(side=tk.LEFT, padx=(6, 0))

        # Options
        opts = tk.Frame(container, bg=bg_main)
        opts.pack(fill=tk.X, pady=(8, 0))
        self.var_auto = tk.BooleanVar(value=True)
        self.var_ordinal_only = tk.BooleanVar(value=True)
        self.var_replace_tags = tk.BooleanVar(value=True)
        self.var_incr_text = tk.BooleanVar(value=True)
        tk.Checkbutton(
            opts,
            text="Auto-incr",
            variable=self.var_auto,
            bg=bg_main,
            fg=fg_main,
            activebackground=bg_active,
            activeforeground=fg_active,
            selectcolor=bg_active,
        ).pack(side=tk.LEFT)
        tk.Checkbutton(
            opts,
            text="Ordinal-only",
            variable=self.var_ordinal_only,
            bg=bg_main,
            fg=fg_main,
            activebackground=bg_active,
            activeforeground=fg_active,
            selectcolor=bg_active,
        ).pack(side=tk.LEFT, padx=(8, 0))
        tk.Checkbutton(
            opts,
            text="Replace tags",
            variable=self.var_replace_tags,
            bg=bg_main,
            fg=fg_main,
            activebackground=bg_active,
            activeforeground=fg_active,
            selectcolor=bg_active,
        ).pack(side=tk.LEFT, padx=(8, 0))
        tk.Checkbutton(
            opts,
            text="Incr text",
            variable=self.var_incr_text,
            bg=bg_main,
            fg=fg_main,
            activebackground=bg_active,
            activeforeground=fg_active,
            selectcolor=bg_active,
        ).pack(side=tk.LEFT, padx=(8, 0))

        # Bindings
        self.entry.bind("<Return>", lambda _e: self._on_submit())
        self.bind("<Escape>", lambda _e: self.destroy())

        # Size to content and center over parent
        with contextlib.suppress(Exception):
            self.update_idletasks()
        self.place(relx=0.5, rely=0.5, anchor="center")
        with contextlib.suppress(Exception):
            self.lift()
        self.after(50, lambda: self.entry.focus_set())

    def _on_submit(self) -> None:
        initial = self.entry.get() or ""
        options = SequenceOptions(
            auto_increment=self.var_auto.get(),
            ordinal_only=self.var_ordinal_only.get(),
            replace_tags=self.var_replace_tags.get(),
            incr_text=self.var_incr_text.get(),
        )
        # Pass initial and options back to parent to manage the sequence and clipboard
        try:
            self._on_start(initial, options)
        finally:
            with contextlib.suppress(Exception):
                self.destroy()
