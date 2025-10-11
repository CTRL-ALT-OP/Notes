from __future__ import annotations
import ast
import math
import tkinter as tk
from typing import Optional


class EquationAutoFormatter:
    """Auto-inserts the computed value after an equals sign on the current line.

    Behavior:
    - When the user types '=', the service attempts to parse the left-hand side of that
      line as a simple arithmetic expression and inserts its evaluated result right
      after the '='.
    - Parsing is done safely via AST; only numeric literals, parentheses, and
      arithmetic operators (+, -, *, /, %, **, unary +/-) are allowed.
    - If parsing or evaluation fails, nothing is inserted.
    """

    def attach(self, text_widget: tk.Text) -> None:
        # Bind after key release so '=' has been inserted before we read the line
        text_widget.bind(
            "<KeyRelease-=>", lambda e: self._on_equals(text_widget), add="+"
        )

    def _on_equals(self, text: tk.Text) -> None:
        try:
            insert_index = text.index("insert")
            line_number = insert_index.split(".")[0]
            line_start = f"{line_number}.0"
            # Read from line start to current cursor; includes the '=' we just typed
            left_segment = text.get(line_start, insert_index)
            if not left_segment or "=" not in left_segment:
                return
            # Take expression before the last '=' on the line
            expr = left_segment.rsplit("=", 1)[0].strip()
            if not expr:
                return

            # Optional: allow caret '^' as power by translating to Python '**'
            sanitized_expr = expr.replace("^", "**")

            value = self._safe_eval_expression(sanitized_expr)
            if value is None:
                return

            formatted = self._format_result(value)
            if not formatted:
                return

            # Insert at the current cursor position (right after '=')
            text.insert("insert", formatted)
        except Exception:
            # Do not disrupt typing on any error
            return

    # --- Safe evaluation helpers ---
    def _safe_eval_expression(self, expression: str) -> Optional[float | int]:
        if len(expression) > 200:
            return None
        try:
            node = ast.parse(expression, mode="eval")
            return self._eval_ast(node.body)
        except Exception:
            return None

    def _eval_ast(self, node: ast.AST) -> float | int:
        if isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float)):
                return node.value
            raise ValueError("Unsupported constant")
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            operand = self._eval_ast(node.operand)
            return +operand if isinstance(node.op, ast.UAdd) else -operand
        if isinstance(node, ast.BinOp) and isinstance(
            node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Mod, ast.Pow)
        ):
            left = self._eval_ast(node.left)
            right = self._eval_ast(node.right)
            if isinstance(node.op, ast.Add):
                return left + right
            if isinstance(node.op, ast.Sub):
                return left - right
            if isinstance(node.op, ast.Mult):
                return left * right
            if isinstance(node.op, ast.Div):
                return left / right
            if isinstance(node.op, ast.Mod):
                return left % right
            if isinstance(node.op, ast.Pow):
                return left**right
        # Disallow everything else for safety
        raise ValueError("Unsupported expression")

    def _format_result(self, value: float | int) -> str:
        if isinstance(value, bool):
            return ""
        if isinstance(value, int):
            return str(value)
        if not math.isfinite(value):
            return ""
        # Round to 6 decimals, strip trailing zeros
        s = f"{value:.6f}"
        if "." in s:
            s = s.rstrip("0").rstrip(".")
        return s
