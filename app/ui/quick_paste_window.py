from __future__ import annotations
import contextlib
import tkinter as tk
from typing import Callable

from app.services.clipboard_sequence import SequenceOptions


class QuickPasteWindow(tk.Toplevel):
    """Small sub-window overlay for quick sequence paste setup."""

    def __init__(
        self,
        parent: tk.Tk,
        initial_text: str,
        on_start: Callable[[str, SequenceOptions], None],
    ):
        super().__init__(parent)
        self.transient(parent)
        self.title("Quick Paste")
        self.resizable(False, False)
        self.attributes("-topmost", True)
        self.configure(
            bg=(
                getattr(parent, "theme", None).menubar_bg
                if hasattr(parent, "theme")
                else None
            )
        )

        self._on_start = on_start

        # Layout frame centered over the editor area
        container = tk.Frame(self, padx=8, pady=8)
        container.pack(fill=tk.BOTH, expand=True)

        # Entry row with clipboard button
        row = tk.Frame(container)
        row.pack(fill=tk.X)
        self.entry = tk.Entry(row)
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.entry.insert(0, initial_text)
        self.entry.icursor(tk.END)
        copy_btn = tk.Button(row, text="📋", width=3, command=self._on_submit)
        copy_btn.pack(side=tk.LEFT, padx=(6, 0))

        # Options
        opts = tk.Frame(container)
        opts.pack(fill=tk.X, pady=(8, 0))
        self.var_auto = tk.BooleanVar(value=True)
        self.var_ordinal_only = tk.BooleanVar(value=True)
        self.var_replace_tags = tk.BooleanVar(value=True)
        self.var_incr_text = tk.BooleanVar(value=True)
        tk.Checkbutton(opts, text="Auto-incr", variable=self.var_auto).pack(
            side=tk.LEFT
        )
        tk.Checkbutton(opts, text="Ordinal-only", variable=self.var_ordinal_only).pack(
            side=tk.LEFT, padx=(8, 0)
        )
        tk.Checkbutton(opts, text="Replace tags", variable=self.var_replace_tags).pack(
            side=tk.LEFT, padx=(8, 0)
        )
        tk.Checkbutton(opts, text="Incr text", variable=self.var_incr_text).pack(
            side=tk.LEFT, padx=(8, 0)
        )

        # Bindings
        self.entry.bind("<Return>", lambda _e: self._on_submit())

        # Size and position - center over parent text area
        self.update_idletasks()
        width = 420
        height = 110
        try:
            # place in the middle of the parent window
            px = parent.winfo_rootx()
            py = parent.winfo_rooty()
            pw = parent.winfo_width()
            ph = parent.winfo_height()
            x = px + (pw - width) // 2
            y = py + (ph - height) // 2
        except Exception:
            x, y = 200, 200
        self.geometry(f"{width}x{height}+{x}+{y}")

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
            self.destroy()
