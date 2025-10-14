from __future__ import annotations
import contextlib
import re
import tkinter as tk


class ListAutoFill:
    """Auto-extends unordered and ordered lists when pressing Enter.

    Behavior:
    - Detects the current line's list marker. If it's a UL ( -, *, + ) or OL (1., 2., ...),
      inserts a newline followed by the same indentation and the next marker.
    - For UL: repeats the bullet. For OL: increments the number.
    - If the line contains only the marker and whitespace, pressing Enter will remove
      the marker (like finishing the list in many editors).
    """

    _re_ul = re.compile(r"^(?P<indent>[\t ]*)(?P<marker>[-*+])[\t ]+(?P<rest>.*)$")
    _re_ol = re.compile(r"^(?P<indent>[\t ]*)(?P<num>\d+)\.[\t ]+(?P<rest>.*)$")

    def attach(self, text_widget: tk.Text) -> None:
        # Intercept Return before default inserts newline, so we can control insertion
        text_widget.bind("<Return>", lambda e: self._on_return(text_widget), add="+")
        # Handle indent / outdent on Tab / Shift-Tab
        text_widget.bind("<Tab>", lambda e: self._on_tab(text_widget), add="+")
        text_widget.bind(
            "<Shift-Tab>", lambda e: self._on_shift_tab(text_widget), add="+"
        )
        # Some platforms send ISO_Left_Tab for Shift-Tab
        text_widget.bind(
            "<ISO_Left_Tab>", lambda e: self._on_shift_tab(text_widget), add="+"
        )
        # After deletion/backspace, renumber ordered lists if needed (post-edit)
        text_widget.bind(
            "<KeyRelease-BackSpace>",
            lambda e: self._on_post_delete(text_widget),
            add="+",
        )
        text_widget.bind(
            "<KeyRelease-Delete>",
            lambda e: self._on_post_delete(text_widget),
            add="+",
        )

    def _on_return(self, text: tk.Text) -> str | None:
        try:
            insert_index = text.index("insert")
            line_no = insert_index.split(".")[0]
            line_start = f"{line_no}.0"
            line_end = f"{line_no}.end"
            line = text.get(line_start, line_end)

            # Determine if current line is a UL/OL item
            mul = self._re_ul.match(line)
            mol = self._re_ol.match(line)
            if not mul and not mol:
                return None  # allow default behavior

            # If line is just a marker (no rest or only spaces), break the list
            if mul:
                indent = mul.group("indent")
                marker = mul.group("marker")
                rest = mul.group("rest").rstrip()
                if rest == "":
                    # Replace current line with a blank line at same indent
                    text.delete(line_start, line_end)
                    text.insert(line_start, indent)
                    text.mark_set("insert", f"{line_no}.{len(indent)}")
                    return "break"
                next_prefix = f"\n{indent}{marker} "
            else:
                indent = mol.group("indent")
                num = mol.group("num")
                rest = mol.group("rest").rstrip()
                if rest == "":
                    text.delete(line_start, line_end)
                    text.insert(line_start, indent)
                    text.mark_set("insert", f"{line_no}.{len(indent)}")
                    return "break"
                try:
                    n = int(num)
                except Exception:
                    n = 1
                next_prefix = f"\n{indent}{n+1}. "

            # Default: insert newline + next marker from caret position
            text.insert("insert", next_prefix)
            # If we inserted an ordered-list item, renumber following same-level items
            if mol:
                with contextlib.suppress(Exception):
                    self._renumber_ordered_block(text, int(line_no) + 1)
            return "break"
        except Exception:
            return None

    def _on_tab(self, text: tk.Text) -> str | None:
        try:
            insert_index = text.index("insert")
            line_no = insert_index.split(".")[0]
            line_start = f"{line_no}.0"
            line_end = f"{line_no}.end"
            line = text.get(line_start, line_end)
            mul = self._re_ul.match(line)
            mol = self._re_ol.match(line)
            if not mul and not mol:
                return None

            indent = (mul or mol).group("indent") if (mul or mol) else ""
            add_ws = "\t" if ("\t" in indent and indent.strip(" ") == indent) else "  "

            # Insert indent before current leading whitespace
            text.insert(line_start, add_ws)

            # Adjust caret position by the amount inserted if on this line
            with contextlib.suppress(Exception):
                col = int(insert_index.split(".")[1])
                new_col = col + len(add_ws)
                text.mark_set("insert", f"{line_no}.{new_col}")
            # Renumber ordered list block if applicable
            self._renumber_ordered_block(text, int(line_no))
            return "break"
        except Exception:
            return None

    def _on_post_delete(self, text: tk.Text) -> None:
        """Post-delete handler to keep ordered lists renumbered.

        Tries current line, then next, then previous to find an ordered item
        and renumbers the contiguous same-level block.
        """
        try:
            insert_index = text.index("insert")
            line_no = int(insert_index.split(".")[0])
            candidates = (line_no, line_no + 1, max(1, line_no - 1))
            for ln in candidates:
                line = text.get(f"{ln}.0", f"{ln}.end")
                if self._re_ol.match(line):
                    self._renumber_ordered_block(text, ln)
                    break
        except Exception:
            return

    def _on_shift_tab(self, text: tk.Text) -> str | None:
        try:
            insert_index = text.index("insert")
            line_no = insert_index.split(".")[0]
            line_start = f"{line_no}.0"
            line_end = f"{line_no}.end"
            line = text.get(line_start, line_end)
            mul = self._re_ul.match(line)
            mol = self._re_ol.match(line)
            if not mul and not mol:
                return None

            # Determine existing leading whitespace
            indent = (mul or mol).group("indent") if (mul or mol) else ""
            remove_len = 0
            if indent.startswith("\t"):
                remove_len = 1
            elif indent.startswith("  "):
                remove_len = 2
            elif indent.startswith(" "):
                # Single space before marker: remove it to normalize
                remove_len = 1
            else:
                remove_len = 0

            if remove_len <= 0:
                return "break"

            # Delete from line start
            text.delete(line_start, f"{line_no}.{remove_len}")

            # Adjust caret position
            with contextlib.suppress(Exception):
                col = int(insert_index.split(".")[1])
                new_col = max(0, col - remove_len)
                text.mark_set("insert", f"{line_no}.{new_col}")
            # Renumber ordered list block if applicable
            self._renumber_ordered_block(text, int(line_no))
            return "break"
        except Exception:
            return None

    def _renumber_ordered_block(self, text: tk.Text, line_number: int) -> None:
        """Renumber a contiguous ordered-list block at the current indentation level.

        Keeps the first item's number and adjusts following items sequentially.
        """
        try:
            # Fetch current line and its indentation length
            line_start = f"{line_number}.0"
            line = text.get(line_start, f"{line_number}.end")
            m = self._re_ol.match(line)
            if not m:
                return
            indent = m.group("indent")
            indent_len = len(indent.replace("\t", "    "))  # approximate

            # Find block start by scanning upwards while same-level ordered items
            start = line_number
            while start > 1:
                prev_line = text.get(f"{start-1}.0", f"{start-1}.end")
                pm = self._re_ol.match(prev_line)
                if not pm:
                    break
                prev_indent_len = len(pm.group("indent").replace("\t", "    "))
                if prev_indent_len != indent_len:
                    break
                start -= 1

            # Determine starting number from the first line in block
            first_line = text.get(f"{start}.0", f"{start}.end")
            fm = self._re_ol.match(first_line)
            if not fm:
                return
            current_num = int(fm.group("num"))

            # Scan downward, renumbering subsequent items at the same level
            ln = start + 1
            while True:
                cur = text.get(f"{ln}.0", f"{ln}.end")
                if cur == "":
                    break
                cm = self._re_ol.match(cur)
                if not cm:
                    break
                cur_indent_len = len(cm.group("indent").replace("\t", "    "))
                if cur_indent_len != indent_len:
                    break
                current_num += 1
                # Replace number token on this line
                num_start_col = len(cm.group("indent"))
                num_end_col = num_start_col + len(cm.group("num")) + 1  # include '.'
                text.delete(f"{ln}.{num_start_col}", f"{ln}.{num_end_col}")
                text.insert(f"{ln}.{num_start_col}", f"{current_num}.")
                ln += 1
        except Exception:
            return
