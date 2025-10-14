Markdown Notes (Minimal)

Dark‑themed Tkinter markdown editor with live highlighting, drafts, a simple catalog sidebar, and runnable Python code blocks.

### Requirements
- Python 3.9+
- tkinter (bundled on Windows; on some Linux distros install python3-tk)
- Optional: Pygments (for code token coloring)
  - Install: `pip install -r requirements.txt`

### Run
- From this directory: `python main.py`

### Features
- Live Markdown styling: headings, bold/italic/strike, blockquotes, lists, inline and fenced code, clickable links.
    - Quick markdown tips:
    - `*text*` makes it italics
    - `**text**` makes it bold
    - `# text` makes it a heading, additional hashtags make incrementally smaller headings
    - `[Text](link)` to display links
    - Code blocks are enclosed in \`\`\`.
    - Unordered lists use dashes (-) or asterixes (*) and must be at the beginning of the line, followed by a space and some text, with optional whitespace to determine the indentation
    - Ordered lists follow the same format, but with "1." or etc instead of a dash.
- Code blocks: Pygments-based syntax colors (if installed). Python blocks are runnable. Click the language tag to execute; output is injected below between `### Output: ----` and `--------------------`. This output is replaced on re-running.
- Lists: Enter continues the current item; Tab/Shift‑Tab indent/outdent; ordered lists auto‑renumber; pressing Enter on an empty marker ends the list.
- Quick math: typing `=` after an arithmetic expression inserts its evaluated result (supports +, -, *, /, %, ** and caret ^ for power).
- Drafts: per‑window autosave to `~/markdown_notes_drafts`, restored on launch; status bar shows the draft slot. Drafts are also listed in the sidebar.
- Sidebar catalog: create folders, add files, drag files between folders, rename/delete items; persisted to `~/markdown_notes_catalog.json`.
- File operations: Open, Save, Save As; rename/delete from sidebar. Files default to `.md`; titles derive from filenames.
- Links: `http/https/mailto` open via a browser; filesystem paths open in the OS. `.py` files open and run in a new terminal.
- Shortcuts: Ctrl+S save, Ctrl+O open, Ctrl+N new, Ctrl+B toggle sidebar.
  - Ctrl+Q opens Quick Paste overlay: seed text, then paste repeatedly anywhere.
    - Options: Auto-incr, Ordinal-only, Replace tags, Incr text (all on by default)
      - Replaces tags like `{min}` (current minute)
      - Auto-incr increments numbers each paste; with Ordinal-only, skips cardinal words
      - Incr text toggles whether textual numbers (e.g., one/first) are incremented
  - Ctrl+L toggles List paste: select lines, then paste each line on Ctrl+V.
    - Splits selection by line, strips leading list markers (e.g., `1.`, `-`) and whitespace
    - Seeds clipboard with the first cleaned line; advances to the next on each paste
    - Auto-stops at the end and removes the “List paste” label shown at bottom-right
    - Press Ctrl+L again to stop early and remove the label

### Project layout (key modules)
- `app/ui/main_window.py` — main window, editor, sidebar, menus
- `app/ui/theme.py` — dark theme and Windows title bar best‑effort
- `app/services/markdown_highlighter.py` — regex Markdown + optional Pygments; runnable Python blocks
- `app/services/list_autofill.py` — list continuation/indent/outdent and auto‑renumber
- `app/services/equation_formatter.py` — inline arithmetic result on `=`
- `app/services/file_service.py` — read/write/rename/delete notes
- `app/services/catalog_service.py` — JSON‑backed sidebar catalog
- `app/services/link_handler.py`, `app/services/process_launcher.py` — link/file opening and detached process launch
- `app/services/code_runner.py` — execute Python snippets
- `app/models/note.py` — note model
- `main.py` — app entrypoint

Notes
- Very large code blocks may skip detailed token coloring for responsiveness.
