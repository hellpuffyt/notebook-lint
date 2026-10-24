"""Cells that no longer run — judged statically, and honestly.

Executing the notebook would need its kernel, its packages and its data, none
of which a linter has. What *can* be established without running anything:

* a Python code cell that does not even parse cannot run, full stop;
* a cell whose names are defined by no earlier cell, no import, and no
  builtin depends on state the file no longer produces top-to-bottom —
  usually a deleted or moved cell.

The name analysis is deliberately conservative (assignments, imports, defs,
classes, loop and with targets, walrus, globals from earlier cells) and only
*reads* are flagged. When the language is not Python, the check reports
nothing rather than guessing at a grammar it does not know.
"""

from __future__ import annotations

import ast
import builtins

from .types import Finding, Notebook, Severity

#: Names Jupyter injects into every session.
JUPYTER_BUILTINS = frozenset({
    "get_ipython", "display", "In", "Out", "_", "__", "___", "_i", "_ii", "_iii",
})


#: Cell magics whose body is still Python (the first line is the magic).
PYTHON_BODY_CELL_MAGICS = frozenset({"time", "timeit", "capture", "prun"})


def strip_magics(source: str) -> str:
    """Blank out IPython magics and shell escapes, preserving line numbers.

    They are not Python and would otherwise turn every `%matplotlib inline`
    into a false syntax error. Blanking (not deleting) keeps positions
    meaningful for the findings.
    """
    lines = []
    first = source.lstrip().split("\n", 1)[0]
    if first.startswith("%%"):
        magic = first[2:].split(None, 1)[0] if first[2:].strip() else ""
        if magic not in PYTHON_BODY_CELL_MAGICS:
            # %%bash, %%writefile, %%html, %%sql ...: the body is not Python.
            return ""
    for line in source.splitlines():
        stripped = line.lstrip()
        if stripped.startswith(("%", "!", "?")) or stripped.endswith("?"):
            lines.append("")
        else:
            lines.append(line)
    return "\n".join(lines)


def defined_names(tree: ast.AST) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and isinstance(node.ctx, (ast.Store, ast.Del)):
            names.add(node.id)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                names.add((alias.asname or alias.name).split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.name != "*":
                    names.add(alias.asname or alias.name)
        elif isinstance(node, ast.ExceptHandler) and node.name:
            names.add(node.name)
        elif isinstance(node, (ast.Global, ast.Nonlocal)):
            names.update(node.names)
    return names


def read_names(tree: ast.AST) -> set[str]:
    """Names loaded at the top level of the cell (not inside defs/classes).

    A function body reading `df` only matters once the function is called;
    flagging it would drown the report in maybes. Top-level reads are what
    run immediately and fail immediately.
    """
    reads: set[str] = set()

    class TopLevel(ast.NodeVisitor):
        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            return  # do not descend

        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
            return

        def visit_ClassDef(self, node: ast.ClassDef) -> None:
            return

        def visit_Lambda(self, node: ast.Lambda) -> None:
            # Like a def: the body runs only when called, and its parameters
            # are not reads. Defaults are evaluated immediately, though.
            for default in (*node.args.defaults, *node.args.kw_defaults):
                if default is not None:
                    self.visit(default)

        def visit_Name(self, node: ast.Name) -> None:
            if isinstance(node.ctx, ast.Load):
                reads.add(node.id)

    TopLevel().visit(tree)
    return reads


def check(notebook: Notebook) -> list[Finding]:
    if notebook.language not in (None, "python"):
        return []

    findings: list[Finding] = []
    known: set[str] = set(dir(builtins)) | JUPYTER_BUILTINS
    star_imported = False

    for cell in notebook.code_cells:
        source = strip_magics(cell.source)
        if not source.strip():
            continue
        try:
            tree = ast.parse(source)
        except SyntaxError as err:
            findings.append(
                Finding(
                    check="staleness",
                    severity=Severity.ERROR,
                    message=(
                        f"cell {cell.index} is not valid Python "
                        f"(line {err.lineno}: {err.msg}); it cannot run in "
                        "any order"
                    ),
                    path=notebook.path,
                    cell=cell.index,
                )
            )
            continue

        # After `from x import *` the defined names are unknowable
        # statically, so undefined-name findings would be guesses.
        star_imported = star_imported or any(
            isinstance(node, ast.ImportFrom) and any(a.name == "*" for a in node.names)
            for node in ast.walk(tree)
        )
        undefined = [] if star_imported else sorted(
            name for name in read_names(tree)
            if name not in known and name not in defined_names(tree)
        )
        if undefined:
            findings.append(
                Finding(
                    check="staleness",
                    severity=Severity.WARNING,
                    message=(
                        f"cell {cell.index} reads {_names(undefined)} that no "
                        "earlier cell defines; it depends on a cell that was "
                        "deleted, moved below it, or run out of order"
                    ),
                    path=notebook.path,
                    cell=cell.index,
                    evidence=tuple(undefined[:5]),
                )
            )
        known |= defined_names(tree)
    return findings


def _names(names: list[str]) -> str:
    if len(names) == 1:
        return f"a name ({names[0]!r})"
    shown = ", ".join(repr(n) for n in names[:3])
    suffix = "…" if len(names) > 3 else ""
    return f"{len(names)} names ({shown}{suffix})"
