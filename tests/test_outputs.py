from __future__ import annotations

from notebook_lint import outputs
from notebook_lint.types import Severity

from .conftest import code_cell, notebook


class TestOutputs:
    def test_clean_notebook_yields_nothing(self) -> None:
        nb = notebook(code_cell(0, "x = 1", execution_count=1))
        assert outputs.check(nb) == []

    def test_small_outputs_warn(self) -> None:
        nb = notebook(code_cell(0, "print(1)", execution_count=1, output_sizes=(100,)))
        findings = outputs.check(nb)
        assert [f.severity for f in findings] == [Severity.WARNING]
        assert "1 cell(s)" in findings[0].message

    def test_large_outputs_error_and_mention_history(self) -> None:
        nb = notebook(
            code_cell(0, "plot()", execution_count=1, output_sizes=(300 * 1024,))
        )
        findings = outputs.check(nb)
        assert [f.severity for f in findings] == [Severity.ERROR]
        assert "forever" in findings[0].message

    def test_sizes_accumulate_across_cells(self) -> None:
        nb = notebook(
            code_cell(0, "a()", execution_count=1, output_sizes=(200 * 1024,)),
            code_cell(1, "b()", execution_count=2, output_sizes=(100 * 1024,)),
        )
        assert [f.severity for f in outputs.check(nb)] == [Severity.ERROR]

    def test_evidence_names_the_biggest_cells_first(self) -> None:
        nb = notebook(
            code_cell(0, "small()", execution_count=1, output_sizes=(10,)),
            code_cell(1, "big()", execution_count=2, output_sizes=(5000,)),
        )
        evidence = outputs.check(nb)[0].evidence
        assert evidence[0].startswith("cell 1")

    def test_human_sizes(self) -> None:
        assert outputs._human(10) == "10 B"
        assert outputs._human(2048) == "2.0 kB"
        assert outputs._human(3 * 1024 * 1024) == "3.0 MB"
