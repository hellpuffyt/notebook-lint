"""Run every check over a set of notebooks and render the result."""

from __future__ import annotations

import json
from dataclasses import dataclass

from . import order, outputs, secrets, staleness
from .io import load
from .types import Finding, Severity

CHECKS = {
    "outputs": outputs.check,
    "secrets": secrets.check,
    "order": order.check,
    "staleness": staleness.check,
}


@dataclass(frozen=True)
class Run:
    """Findings for a whole invocation, across every notebook linted."""

    notebooks: int
    findings: list[Finding]

    def worst_severity(self) -> Severity | None:
        if not self.findings:
            return None
        return max((f.severity for f in self.findings), key=lambda s: s.rank)

    def to_dict(self) -> dict[str, object]:
        return {
            "notebooks": self.notebooks,
            "findings": [f.to_dict() for f in self.findings],
            "summary": {
                severity.value: sum(
                    1 for f in self.findings if f.severity is severity
                )
                for severity in Severity
            },
        }


def run(paths: list[str], checks: list[str] | None = None) -> Run:
    wanted = CHECKS if checks is None else {name: CHECKS[name] for name in checks}
    findings: list[Finding] = []
    for path in paths:
        notebook = load(path)
        for checker in wanted.values():
            findings.extend(checker(notebook))
    findings.sort(
        key=lambda f: (f.path, -f.severity.rank, f.cell if f.cell is not None else -1)
    )
    return Run(notebooks=len(paths), findings=findings)


def render_json(result: Run) -> str:
    return json.dumps(result.to_dict(), indent=2)


_MARK = {Severity.ERROR: "ERROR  ", Severity.WARNING: "warning", Severity.INFO: "info   "}


def render_text(result: Run) -> str:
    lines = [f"{result.notebooks} notebook(s) linted"]
    if not result.findings:
        lines.append("no findings: the checks this tool runs found nothing to report")
        return "\n".join(lines)
    current_path = None
    for finding in result.findings:
        if finding.path != current_path:
            current_path = finding.path
            lines.append("")
            lines.append(current_path)
        where = f" (cell {finding.cell})" if finding.cell is not None else ""
        lines.append(f"  {_MARK[finding.severity]} [{finding.check}]{where} {finding.message}")
        for item in finding.evidence:
            lines.append(f"            - {item}")
    return "\n".join(lines)
