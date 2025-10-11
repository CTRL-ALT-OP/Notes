from __future__ import annotations
import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path
from typing import Optional

from app.models.note import Note
from app.services.file_service import FileService
from app.services.markdown_highlighter import MarkdownHighlighter
from app.services.equation_formatter import EquationAutoFormatter
from app.services.draft_service import DraftService
from app.ui.theme import (
    DARK_THEME,
    ThemeColors,
    apply_theme_to_root,
    apply_windows_dark_title_bar,
)


class MainWindow(tk.Tk):
    """Main application window with a minimal editor and Save/Open actions."""

    def __init__(
        self,
        file_service: FileService,
        theme: ThemeColors = DARK_THEME,
        draft_service: Optional[DraftService] = None,
    ) -> None:
        super().__init__()
        self.title("Markdown Notes")
        self.geometry("900x600")

        self.file_service = file_service
        self.current_note: Optional[Note] = Note(title="Untitled", body="")
        self.draft_service = draft_service or DraftService()
        self.instance_index: int = self.draft_service.claim_instance_index()
        self.theme = theme
        self.highlighter = MarkdownHighlighter(debounce_ms=20, theme=self.theme)
        self.eq_formatter = EquationAutoFormatter()
        self._highlight_after_id: Optional[str] = None
        self._dropdown: Optional[tk.Toplevel] = None
        self._draft_after_id: Optional[str] = None

        # Apply theme to the root and attempt Windows dark title bar
        apply_theme_to_root(self, self.theme)
        apply_windows_dark_title_bar(self)

        # Load any existing draft for this instance before building the editor
        try:
            loaded = self.draft_service.load_draft(self.instance_index)
            if loaded:
                self.current_note.body = loaded
        except Exception:
            pass

        self._build_menu()
        self._build_editor()
        self._build_status_bar()
        # Attach auto-formatter bindings similar to the highlighter
        try:
            self.eq_formatter.attach(self.text_widget)
        except Exception:
            pass
        self._bind_live_highlighting()

        # Focus the editor on start for immediate typing
        self.text_widget.focus_set()

        # Update title to include instance index and current note title
        self._update_title()
        self._update_status()

        # Ensure we handle window close to persist draft and release index
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_menu(self) -> None:
        # Custom dark menu bar using a Frame + faux button that opens a custom dropdown
        self.menu_frame = tk.Frame(
            self, bg=self.theme.menubar_bg, height=30, highlightthickness=0, bd=0
        )
        self.menu_frame.pack(side=tk.TOP, fill=tk.X)

        self.file_btn = tk.Label(
            self.menu_frame,
            text="File",
            bg=self.theme.menubar_bg,
            fg=self.theme.menubar_fg,
            padx=8,
            pady=4,
        )
        self.file_btn.pack(side=tk.LEFT)
        self.file_btn.bind("<Button-1>", self._open_file_dropdown)
        self.file_btn.bind(
            "<Enter>", lambda e: self.file_btn.configure(bg=self.theme.menu_active_bg)
        )
        self.file_btn.bind(
            "<Leave>", lambda e: self.file_btn.configure(bg=self.theme.menubar_bg)
        )

        # Global click to dismiss dropdown if open
        self.bind("<Button-1>", self._on_global_click, add=True)

    def _open_file_dropdown(self, _event=None) -> None:
        # Toggle behavior
        if self._dropdown is not None and self._dropdown.winfo_exists():
            self._close_dropdown()
            return

        # Create borderless dropdown
        self._dropdown = tk.Toplevel(self)
        self._dropdown.overrideredirect(True)
        self._dropdown.configure(bg=self.theme.menubar_bg, highlightthickness=0, bd=0)

        # Position below the File button
        bx = self.file_btn.winfo_rootx()
        by = self.file_btn.winfo_rooty() + self.file_btn.winfo_height()
        self._dropdown.wm_geometry(f"220x110+{bx}+{by}")

        # Build menu items
        container = tk.Frame(
            self._dropdown, bg=self.theme.menubar_bg, bd=0, highlightthickness=0
        )
        container.pack(fill=tk.BOTH, expand=True)

        self._add_dropdown_item(container, "Open...", self.on_open)
        self._add_dropdown_item(container, "Save (Current File)", self.on_save_current)
        self._add_dropdown_item(container, "Save As...", self.on_save_as)

        # Esc closes
        self._dropdown.bind("<Escape>", lambda e: self._close_dropdown())
        try:
            self._dropdown.focus_force()
        except Exception:
            pass

    def _add_dropdown_item(self, parent: tk.Misc, label: str, command) -> None:
        item = tk.Frame(parent, bg=self.theme.menubar_bg, height=28)
        item.pack(fill=tk.X)
        txt = tk.Label(
            item,
            text=label,
            bg=self.theme.menubar_bg,
            fg=self.theme.menubar_fg,
            anchor="w",
            padx=10,
        )
        txt.pack(fill=tk.X)

        def on_click(_e=None):
            self._close_dropdown()
            command()

        item.bind("<Button-1>", on_click)
        txt.bind("<Button-1>", on_click)
        item.bind(
            "<Enter>",
            lambda e: (
                item.configure(bg=self.theme.menu_active_bg),
                txt.configure(bg=self.theme.menu_active_bg),
            ),
        )
        item.bind(
            "<Leave>",
            lambda e: (
                item.configure(bg=self.theme.menubar_bg),
                txt.configure(bg=self.theme.menubar_bg),
            ),
        )

    def _close_dropdown(self) -> None:
        if self._dropdown is not None:
            try:
                self._dropdown.destroy()
            except Exception:
                pass
            self._dropdown = None

    def _on_global_click(self, event) -> None:
        # Close if clicking outside the dropdown and outside the File button
        if self._dropdown is None:
            return
        widget = self.winfo_containing(event.x_root, event.y_root)
        if widget is None:
            self._close_dropdown()
            return
        if widget is self._dropdown or str(widget).startswith(str(self._dropdown)):
            return
        if widget is self.file_btn or str(widget).startswith(str(self.file_btn)):
            return
        self._close_dropdown()

    def _build_editor(self) -> None:
        # Apply window background
        self.configure(bg=self.theme.background)
        self.text_widget = tk.Text(
            self,
            wrap=tk.WORD,
            undo=True,
            bg=self.theme.background,
            fg=self.theme.foreground,
            insertbackground=self.theme.caret,
            selectbackground=self.theme.selection_bg,
            selectforeground=self.theme.selection_fg,
            highlightthickness=0,
            borderwidth=0,
        )
        self.text_widget.pack(fill=tk.BOTH, expand=True)
        self.text_widget.insert("1.0", self.current_note.body)

    def _build_status_bar(self) -> None:
        self.status_frame = tk.Frame(
            self, bg=self.theme.menubar_bg, height=22, highlightthickness=0, bd=0
        )
        self.status_frame.pack(side=tk.BOTTOM, fill=tk.X)
        self.status_label = tk.Label(
            self.status_frame,
            text="",
            bg=self.theme.menubar_bg,
            fg=self.theme.menubar_fg,
            anchor="w",
            padx=8,
        )
        self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

    def _bind_live_highlighting(self) -> None:
        # Bind to Tk's modified virtual event for edits/undo/redo/paste
        self.text_widget.bind("<<Modified>>", self._on_text_modified)
        # Initial highlight
        self._schedule_highlight()
        # Also schedule draft autosave on edits
        self._schedule_draft_save()

    def _on_text_modified(self, _event=None) -> None:
        # Reset the modified flag or the event will not fire again
        try:
            self.text_widget.edit_modified(False)
        except Exception:
            pass
        self._schedule_highlight()
        self._schedule_draft_save()

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

    def _update_status(self) -> None:
        path_text = (
            str(self.current_note.file_path)
            if (self.current_note and self.current_note.file_path)
            else None
        )
        if path_text:
            status = f"File: {path_text}"
        else:
            status = f"Draft slot: #{self.instance_index} (unsaved)"
        try:
            self.status_label.configure(text=status)
        except Exception:
            pass

    def _schedule_draft_save(self) -> None:
        if self._draft_after_id is not None:
            try:
                self.after_cancel(self._draft_after_id)
            except Exception:
                pass
        # Save drafts with a small debounce to avoid excessive disk writes
        self._draft_after_id = self.after(400, self._save_draft_now)

    def _save_draft_now(self) -> None:
        try:
            text = self.text_widget.get("1.0", tk.END).rstrip()
            self.draft_service.save_draft(self.instance_index, text)
        except Exception:
            pass
        self._draft_after_id = None

    def _update_title(self) -> None:
        title_part = (
            self.current_note.title
            if (self.current_note and self.current_note.title)
            else "Untitled"
        )
        self.title(f"Markdown Notes [#{self.instance_index}] - {title_part}")

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
        self._update_title()
        self._schedule_highlight()
        self._schedule_draft_save()
        self._update_status()

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
            # Clear draft upon successful save to a file
            try:
                self.draft_service.clear_draft(self.instance_index)
            except Exception:
                pass
            self._update_status()
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
            self._update_title()
            messagebox.showinfo("Saved", f"Saved to: {target}")
            # Clear draft after saving as a new file
            try:
                self.draft_service.clear_draft(self.instance_index)
            except Exception:
                pass
            self._update_status()
        except Exception as exc:
            messagebox.showerror("Save Failed", f"Could not save file:\n{exc}")

    def on_save_current(self) -> None:
        if self.current_note is None or not self.current_note.file_path:
            messagebox.showinfo(
                "No File",
                "No file is currently open. Use Save As... to choose a location.",
            )
            return
        self.current_note.body = self.text_widget.get("1.0", tk.END).rstrip()
        try:
            target = self.file_service.write(self.current_note)
            self._update_title()
            messagebox.showinfo("Saved", f"Saved to: {target}")
            try:
                self.draft_service.clear_draft(self.instance_index)
            except Exception:
                pass
            self._update_status()
        except Exception as exc:
            messagebox.showerror("Save Failed", f"Could not save file:\n{exc}")

    def _on_close(self) -> None:
        # Persist latest draft and release the instance lock before closing
        try:
            if self._draft_after_id is not None:
                try:
                    self.after_cancel(self._draft_after_id)
                except Exception:
                    pass
            self._save_draft_now()
        except Exception:
            pass
        try:
            self.draft_service.release_instance_index(self.instance_index)
        except Exception:
            pass
        try:
            self.destroy()
        except Exception:
            pass
