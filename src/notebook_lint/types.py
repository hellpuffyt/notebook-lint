"""Core model: a parsed notebook and the findings the checks produce."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Severity(Enum):
    """How much a finding should worry the reader."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"

    @property
    def rank(self) -> int:
        """Ordering for --fail-on comparisons; higher is worse."""
        return {"info": 0, "warning": 1, "error": 2}[self.value]


@dataclass(frozen=True)
class Finding:
    """One concrete problem, anchored to a cell so it can be checked."""

    check: str
    severity: Severity
    message: str
    #: Path of the notebook the finding is about.
    path: str
    #: Zero-based cell index, or None for notebook-level findings.
    cell: int | None = None
    evidence: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "check": self.check,
            "severity": self.severity.value,
            "message": self.message,
            "path": self.path,
            "cell": self.cell,
            "evidence": list(self.evidence),
        }


@dataclass(frozen=True)
class Cell:
    """One notebook cell, reduced to what the checks need."""

    index: int
    cell_type: str
    source: str
    execution_count: int | None
    #: Rendered sizes of each output, in bytes of JSON — enough to reason
    #: about bloat without keeping the payloads themselves in memory.
    output_sizes: tuple[int, ...] = ()
    output_types: tuple[str, ...] = ()

    @property
    def is_code(self) -> bool:
        return self.cell_type == "code"

    @property
    def has_output(self) -> bool:
        return bool(self.output_sizes)

    @property
    def output_bytes(self) -> int:
        return sum(self.output_sizes)


@dataclass(frozen=True)
class Notebook:
    """A parsed .ipynb, plus the metadata the checks consult."""

    path: str
    cells: tuple[Cell, ...]
    language: str | None
    kernel_name: str | None
    nbformat: int

    @property
    def code_cells(self) -> tuple[Cell, ...]:
        return tuple(cell for cell in self.cells if cell.is_code)


@dataclass
class CheckContext:
    """Mutable bag passed through a run, for cross-notebook state later."""

    findings: list[Finding] = field(default_factory=list)

    def add(self, finding: Finding) -> None:
        self.findings.append(finding)
