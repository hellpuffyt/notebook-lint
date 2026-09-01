from __future__ import annotations

from notebook_lint import order
from notebook_lint.types import Severity

from .conftest import code_cell, notebook


class TestOutOfOrder:
    def test_strictly_increasing_counts_are_fine(self) -> None:
        nb = notebook(
            code_cell(0, "a = 1", execution_count=1),
            code_cell(1, "b = a", execution_count=2),
            code_cell(2, "c = b", execution_count=5),  # gaps are fine: re-runs
        )
        assert order.check(nb) == []

    def test_backwards_counts_warn_with_both_cells_named(self) -> None:
        nb = notebook(
            code_cell(0, "late", execution_count=7),
            code_cell(1, "early", execution_count=3),
        )
        findings = order.check(nb)
        assert [f.severity for f in findings] == [Severity.WARNING]
        assert "cell 0 ran as [7]" in findings[0].evidence[0]
        assert "cell 1 below it ran as [3]" in findings[0].evidence[0]

    def test_equal_counts_also_warn(self) -> None:
        nb = notebook(
            code_cell(0, "a", execution_count=2),
            code_cell(1, "b", execution_count=2),
        )
        assert order.check(nb)

    def test_unexecuted_cells_between_executed_ones_are_ignored(self) -> None:
        nb = notebook(
            code_cell(0, "a", execution_count=1),
            code_cell(1, "never ran"),
            code_cell(2, "b", execution_count=2),
        )
        assert order.check(nb) == []

    def test_every_backwards_pair_is_evidence(self) -> None:
        nb = notebook(
            code_cell(0, "a", execution_count=9),
            code_cell(1, "b", execution_count=4),
            code_cell(2, "c", execution_count=2),
        )
        findings = order.check(nb)
        assert len(findings) == 1
        assert len(findings[0].evidence) == 2


class TestOutputsWithoutExecution:
    def test_output_but_no_count_warns(self) -> None:
        nb = notebook(code_cell(0, "print(1)", output_sizes=(20,)))
        findings = order.check(nb)
        assert [f.severity for f in findings] == [Severity.WARNING]
        assert "cannot have come from the code as committed" in findings[0].message

    def test_empty_source_with_output_is_not_flagged_here(self) -> None:
        nb = notebook(code_cell(0, "   ", output_sizes=(20,)))
        assert order.check(nb) == []
