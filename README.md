Markdown Notes (Minimal)

Simple, modular, markdown-enabled note-taking app with a minimal GUI:
- Text editor area
- File menu with Open and Save

Structured into models, services, and UI for easy extensibility.

Requirements
- Python 3.9+
- tkinter (bundled on Windows; on some Linux distros install python3-tk)

Run
- From this directory, run: python main.py

Project Layout
- app/models/note.py
- app/services/file_service.py
- app/services/markdown_service.py
- app/ui/main_window.py
- main.py

Notes
- Files save as .md by default
- Title is derived from the filename when opening
- MarkdownService is a future-facing stub

Code highlighting
- Fenced code blocks are syntax highlighted using Pygments if installed.
- Use language-tagged fences like:

  ```
  ```python
  def hello(name: str) -> None:
      print(f"Hello {name}")
  ```
  ```

- If no language is provided, a best-effort guess is attempted on small blocks.
- Very large code blocks may skip detailed token coloring for responsiveness.


