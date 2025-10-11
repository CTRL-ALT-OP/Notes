from __future__ import annotations
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
from tkinter import ttk
from pathlib import Path
from typing import Optional, Dict

from app.models.note import Note
from app.services.file_service import FileService
from app.services.markdown_highlighter import MarkdownHighlighter
from app.services.equation_formatter import EquationAutoFormatter
from app.services.draft_service import DraftService
from app.services.catalog_service import CatalogService, CatalogFolder
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
        self.catalog = CatalogService()

        # Sidebar/Tree state
        self.sidebar_width = 150
        self._tree_item_to_payload: Dict[str, Dict[str, str]] = {}
        self._drag_item_id: Optional[str] = None
        self._drag_hover_id: Optional[str] = None

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
        self._build_body()
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

        # Key bindings
        self.bind("<Control-s>", lambda e: self.on_save())
        self.bind("<Control-o>", lambda e: self.on_open())
        self.bind("<Control-n>", lambda e: self.on_new())

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

    def _build_body(self) -> None:
        # Root body frame
        self.body = tk.Frame(self, bg=self.theme.background)
        self.body.pack(fill=tk.BOTH, expand=True)

        # Sidebar
        self.sidebar = tk.Frame(
            self.body, bg=self.theme.menubar_bg, width=self.sidebar_width
        )
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y)
        self.sidebar.pack_propagate(False)

        # Sidebar header with actions
        header = tk.Frame(
            self.sidebar,
            bg=self.theme.menubar_bg,
        )
        header.pack(fill=tk.X)
        add_folder_btn = tk.Button(
            header,
            text="+ Folder",
            command=self._on_add_folder,
            bg=self.theme.menu_active_bg,
            fg=self.theme.menu_active_fg,
            relief=tk.FLAT,
            padx=6,
        )
        add_folder_btn.pack(side=tk.LEFT, padx=6, pady=6)
        add_files_btn = tk.Button(
            header,
            text="+ Files",
            command=self._on_add_files,
            bg=self.theme.menu_active_bg,
            fg=self.theme.menu_active_fg,
            relief=tk.FLAT,
            padx=6,
        )
        add_files_btn.pack(side=tk.LEFT, padx=6, pady=6)

        # Treeview
        self._init_tree_style()
        tree_container = tk.Frame(self.sidebar, bg=self.theme.menubar_bg)
        tree_container.pack(fill=tk.BOTH, expand=True)
        self.tree = ttk.Treeview(
            tree_container,
            columns=("name",),
            show="tree",
            selectmode="browse",
        )
        self.tree.configure(style="Dark.Treeview")
        vsb = ttk.Scrollbar(
            tree_container,
            orient="vertical",
            command=self.tree.yview,
            style="Dark.Vertical.TScrollbar",
        )
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree.bind("<Double-1>", self._on_tree_double_click)
        self.tree.bind("<ButtonPress-1>", self._on_tree_button_press)
        self.tree.bind("<B1-Motion>", self._on_tree_drag_motion)
        self.tree.bind("<ButtonRelease-1>", self._on_tree_button_release)

        # Editor area
        editor_frame = tk.Frame(self.body, bg=self.theme.background)
        editor_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.text_widget = tk.Text(
            editor_frame,
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

        self._refresh_tree()

    def _init_tree_style(self) -> None:
        try:
            style = ttk.Style(self)
            # Use a theme that respects color configuration
            try:
                style.theme_use("clam")
            except Exception:
                pass
            style.configure(
                "Dark.Treeview",
                background=self.theme.menubar_bg,
                fieldbackground=self.theme.menubar_bg,
                foreground=self.theme.menubar_fg,
                borderwidth=0,
            )
            style.map(
                "Dark.Treeview",
                background=[("selected", self.theme.menu_active_bg)],
                foreground=[("selected", self.theme.menu_active_fg)],
            )
            style.configure(
                "Dark.Vertical.TScrollbar",
                background=self.theme.menubar_bg,
                troughcolor=self.theme.menubar_bg,
                bordercolor=self.theme.menubar_bg,
                arrowcolor=self.theme.menubar_fg,
            )
        except Exception:
            pass

    def _refresh_tree(self) -> None:
        self._tree_item_to_payload.clear()
        for item in self.tree.get_children(""):
            self.tree.delete(item)
        # Drafts root
        drafts_root = self.tree.insert("", "end", text="Drafts", open=True)
        self._tree_item_to_payload[drafts_root] = {"type": "drafts_root"}
        for draft_item, draft_index in self._list_drafts():
            node_id = self.tree.insert(drafts_root, "end", text=draft_item, open=False)
            self._tree_item_to_payload[node_id] = {
                "type": "draft",
                "index": str(draft_index),
            }
        # User folders
        for folder in self.catalog.list_folders():
            fid = self.tree.insert("", "end", text=folder.name, open=True)
            self._tree_item_to_payload[fid] = {"type": "folder", "id": folder.id}
            for f in folder.files:
                leaf = self.tree.insert(fid, "end", text=Path(f.path).name)
                self._tree_item_to_payload[leaf] = {"type": "file", "path": f.path}

    def _list_drafts(self):
        base = self.draft_service.base_dir
        results = []
        try:
            for p in sorted(base.glob("draft_*.md")):
                try:
                    idx = int(p.stem.split("_")[1])
                except Exception:
                    continue
                # Only list non-empty drafts
                try:
                    if p.read_text(encoding="utf-8").strip() == "":
                        continue
                except Exception:
                    continue
                results.append((f"Draft #{idx}", idx))
        except Exception:
            pass
        return results

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

    # ---------- Sidebar actions ----------
    def _on_add_folder(self) -> None:
        name = simpledialog.askstring("New Folder", "Folder name:", parent=self)
        if not name:
            return
        self.catalog.add_folder(name)
        self._refresh_tree()

    def _get_selected_folder_id(self) -> Optional[str]:
        sel = self.tree.selection()
        if not sel:
            return None
        payload = self._tree_item_to_payload.get(sel[0], {})
        if payload.get("type") == "folder":
            return payload.get("id")
        return None

    def _on_add_files(self) -> None:
        folder_id = self._get_selected_folder_id()
        if not folder_id:
            messagebox.showinfo("Select Folder", "Select a folder to add files to.")
            return
        paths = filedialog.askopenfilenames(title="Add Files to Folder")
        if not paths:
            return
        self.catalog.add_files_to_folder(folder_id, [Path(p) for p in paths])
        self._refresh_tree()

    # Drag from file -> folder
    def _on_tree_button_press(self, event) -> None:
        item = self.tree.identify_row(event.y)
        self._drag_item_id = item if item else None

    def _on_tree_drag_motion(self, event) -> None:
        if not self._drag_item_id:
            return
        src_payload = self._tree_item_to_payload.get(self._drag_item_id, {})
        if src_payload.get("type") != "file":
            return
        hover = self.tree.identify_row(event.y)
        self._drag_hover_id = hover if hover else None

    def _on_tree_button_release(self, _event) -> None:
        try:
            if not self._drag_item_id or not self._drag_hover_id:
                return
            src_payload = self._tree_item_to_payload.get(self._drag_item_id, {})
            dst_payload = self._tree_item_to_payload.get(self._drag_hover_id, {})
            if (
                src_payload.get("type") == "file"
                and dst_payload.get("type") == "folder"
            ):
                self.catalog.move_file(Path(src_payload["path"]), dst_payload["id"])
                self._refresh_tree()
        finally:
            self._drag_item_id = None
            self._drag_hover_id = None

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

    def on_new(self) -> None:
        self.current_note = Note(title="Untitled", body="")
        self.text_widget.delete("1.0", tk.END)
        self.text_widget.insert("1.0", "")
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

    # ---------- Tree interactions ----------
    def _on_tree_double_click(self, _event=None) -> None:
        sel = self.tree.selection()
        if not sel:
            return
        payload = self._tree_item_to_payload.get(sel[0], {})
        ptype = payload.get("type")
        if ptype == "file":
            path = Path(payload.get("path", ""))
            if not path.exists():
                messagebox.showerror("Missing File", f"File not found:\n{path}")
                return
            try:
                note = self.file_service.read(path)
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
        elif ptype == "draft":
            try:
                idx = int(payload.get("index", "0"))
            except Exception:
                return
            try:
                text = self.draft_service.load_draft(idx)
            except Exception:
                text = ""
            self.current_note = Note(title=f"Draft #{idx}", body=text)
            self.text_widget.delete("1.0", tk.END)
            self.text_widget.insert("1.0", text)
            self._update_title()
            self._schedule_highlight()
            self._schedule_draft_save()
            self._update_status()
