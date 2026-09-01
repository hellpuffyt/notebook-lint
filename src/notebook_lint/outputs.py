"""Committed outputs: noise at best, a data leak at worst.

Severity scales with size because the failure modes differ: a stray text
output is churn in diffs, while megabytes of embedded base64 make the repo
grow forever (git keeps every version) and frequently contain rendered data
nobody meant to publish.
"""

from __future__ import annotations

from .types import Finding, Notebook, Severity

#: Above this many bytes of output, a notebook is bloating its repository.
LARGE_OUTPUT_BYTES = 256 * 1024


def check(notebook: Notebook) -> list[Finding]:
    dirty = [cell for cell in notebook.code_cells if cell.has_output]
    if not dirty:
        return []

    findings = []
    total = sum(cell.output_bytes for cell in dirty)
    severity = Severity.ERROR if total >= LARGE_OUTPUT_BYTES else Severity.WARNING
    message = (
        f"{len(dirty)} cell(s) have committed outputs totalling "
        f"{_human(total)}; every re-run rewrites them, so diffs and history "
        "carry rendering noise"
    )
    if severity is Severity.ERROR:
        message = (
            f"{len(dirty)} cell(s) carry {_human(total)} of committed output; "
            "git keeps every version of it forever, and rendered data has a "
            "way of containing what the code was careful not to print"
        )
    findings.append(
        Finding(
            check="outputs",
            severity=severity,
            message=message,
            path=notebook.path,
            evidence=tuple(
                f"cell {cell.index}: {_human(cell.output_bytes)}"
                f" ({', '.join(sorted(set(cell.output_types)))})"
                for cell in sorted(dirty, key=lambda c: -c.output_bytes)[:5]
            ),
        )
    )
    return findings


def _human(size: int) -> str:
    if size >= 1024 * 1024:
        return f"{size / (1024 * 1024):.1f} MB"
    if size >= 1024:
        return f"{size / 1024:.1f} kB"
    return f"{size} B"
