from __future__ import annotations
import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path
from typing import Optional

from app.models.note import Note
from app.services.file_service import FileService
from app.services.markdown_highlighter import MarkdownHighlighter


class MainWindow(tk.Tk):
    """Main application window with a minimal editor and Save/Open actions."""

    def __init__(self, file_service: FileService) -> None:
        super().__init__()
        self.title("Markdown Notes")
        self.geometry("900x600")

        self.file_service = file_service
        self.current_note: Optional[Note] = Note(title="Untitled", body="")
        self.highlighter = MarkdownHighlighter(debounce_ms=20)
        self._highlight_after_id: Optional[str] = None

        self._build_menu()
        self._build_editor()
        self._bind_live_highlighting()

        # Focus the editor on start for immediate typing
        self.text_widget.focus_set()

    def _build_menu(self) -> None:
        menu_bar = tk.Menu(self)

        file_menu = tk.Menu(menu_bar, tearoff=0)
        file_menu.add_command(label="Open...", command=self.on_open)
        file_menu.add_command(label="Save", command=self.on_save)

        menu_bar.add_cascade(label="File", menu=file_menu)
        self.config(menu=menu_bar)

    def _build_editor(self) -> None:
        self.text_widget = tk.Text(self, wrap=tk.WORD, undo=True)
        self.text_widget.pack(fill=tk.BOTH, expand=True)
        self.text_widget.insert("1.0", self.current_note.body)

    def _bind_live_highlighting(self) -> None:
        # Bind to Tk's modified virtual event for edits/undo/redo/paste
        self.text_widget.bind("<<Modified>>", self._on_text_modified)
        # Initial highlight
        self._schedule_highlight()

    def _on_text_modified(self, _event=None) -> None:
        # Reset the modified flag or the event will not fire again
        try:
            self.text_widget.edit_modified(False)
        except Exception:
            pass
        self._schedule_highlight()

    def _schedule_highlight(self) -> None:
        if self._highlight_after_id is not None:
            try:
                self.after_cancel(self._highlight_after_id)
            except Exception:
                pass
        self._highlight_after_id = self.after(
            self.highlighter.debounce_ms, self._apply_highlighting
        )

    def _apply_highlighting(self) -> None:
        self.highlighter.highlight(self.text_widget)
        self._highlight_after_id = None

    def on_open(self) -> None:
        file_path = filedialog.askopenfilename(
            title="Open Markdown File",
            filetypes=[
                ("Markdown Files", "*.md"),
                ("Text Files", "*.txt"),
                ("All Files", "*.*"),
            ],
        )
        if not file_path:
            return
        try:
            note = self.file_service.read(Path(file_path))
        except Exception as exc:
            messagebox.showerror("Open Failed", f"Could not open file:\n{exc}")
            return

        self.current_note = note
        self.text_widget.delete("1.0", tk.END)
        self.text_widget.insert("1.0", note.body)
        self.title(f"Markdown Notes - {note.title}")
        self._schedule_highlight()

    def on_save(self) -> None:
        if self.current_note is None:
            self.current_note = Note(title="Untitled", body="")

        self.current_note.body = self.text_widget.get("1.0", tk.END).rstrip()

        try:
            # If no existing path, trigger Save As
            if not self.current_note.file_path:
                self.on_save_as()
                return
            self.file_service.write(self.current_note)
            messagebox.showinfo("Saved", "Note saved successfully.")
        except Exception as exc:
            messagebox.showerror("Save Failed", f"Could not save file:\n{exc}")

    def on_save_as(self) -> None:
        self.current_note.body = self.text_widget.get("1.0", tk.END).rstrip()
        initial_name = (
            self.current_note.file_path.name
            if self.current_note and self.current_note.file_path
            else (self.current_note.title if self.current_note else "Untitled")
        )

        file_path = filedialog.asksaveasfilename(
            title="Save Markdown File",
            initialfile=initial_name,
            defaultextension=".md",
            filetypes=[
                ("Markdown Files", "*.md"),
                ("Text Files", "*.txt"),
                ("All Files", "*.*"),
            ],
        )
        if not file_path:
            return
        try:
            target = self.file_service.write(self.current_note, Path(file_path))
            self.title(f"Markdown Notes - {self.current_note.title}")
            messagebox.showinfo("Saved", f"Saved to: {target}")
        except Exception as exc:
            messagebox.showerror("Save Failed", f"Could not save file:\n{exc}")
