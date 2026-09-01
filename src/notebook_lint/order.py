"""Execution order: does the file tell the story of how it actually ran?

`execution_count` is the notebook's own record. When the numbers are not
strictly increasing top to bottom, the committed results were produced in a
different order than a reader (or `jupyter execute`) will run them — the
classic "restart and run all gives different answers" trap.
"""

from __future__ import annotations

from .types import Cell, Finding, Notebook, Severity


def executed_cells(notebook: Notebook) -> list[Cell]:
    return [c for c in notebook.code_cells if c.execution_count is not None]


def out_of_order_pairs(cells: list[Cell]) -> list[tuple[Cell, Cell]]:
    """Adjacent executed cells whose counts run backwards."""
    pairs = []
    for earlier, later in zip(cells, cells[1:], strict=False):
        assert earlier.execution_count is not None
        assert later.execution_count is not None
        if later.execution_count <= earlier.execution_count:
            pairs.append((earlier, later))
    return pairs


def check(notebook: Notebook) -> list[Finding]:
    cells = executed_cells(notebook)
    findings: list[Finding] = []

    pairs = out_of_order_pairs(cells)
    if pairs:
        findings.append(
            Finding(
                check="order",
                severity=Severity.WARNING,
                message=(
                    f"{len(pairs)} place(s) where execution counts run "
                    "backwards; the committed results were produced in a "
                    "different order than the file reads, so a clean "
                    "run-all may not reproduce them"
                ),
                path=notebook.path,
                evidence=tuple(
                    f"cell {a.index} ran as [{a.execution_count}] but "
                    f"cell {b.index} below it ran as [{b.execution_count}]"
                    for a, b in pairs[:5]
                ),
            )
        )

    unexecuted = [
        c for c in notebook.code_cells
        if c.execution_count is None and c.source.strip() and c.has_output
    ]
    if unexecuted:
        findings.append(
            Finding(
                check="order",
                severity=Severity.WARNING,
                message=(
                    f"{len(unexecuted)} cell(s) carry outputs but no "
                    "execution count; their results cannot have come from "
                    "the code as committed"
                ),
                path=notebook.path,
                evidence=tuple(f"cell {c.index}" for c in unexecuted[:5]),
            )
        )
    return findings
