from __future__ import annotations

import json
from pathlib import Path

from notebook_lint import report
from notebook_lint.types import Severity

from .conftest import raw_code_cell, raw_notebook, write_notebook


def messy(tmp_path: Path) -> Path:
    """Trips outputs, secrets, order and staleness at once."""
    return write_notebook(
        tmp_path / "messy.ipynb",
        raw_notebook(
            [
                raw_code_cell("print(undefined_thing)", execution_count=5),
                raw_code_cell(
                    'key = "AKIA' 'IOSFODNN7EXAMPLE"',
                    execution_count=2,
                    outputs=[{"output_type": "stream", "text": "leaked"}],
                ),
            ]
        ),
    )


def clean(tmp_path: Path) -> Path:
    return write_notebook(
        tmp_path / "clean.ipynb",
        raw_notebook([raw_code_cell("x = 1\nprint(x)")]),
    )


class TestRun:
    def test_clean_notebook_has_no_findings(self, tmp_path: Path) -> None:
        result = report.run([str(clean(tmp_path))])
        assert result.notebooks == 1
        assert result.findings == []
        assert result.worst_severity() is None

    def test_messy_notebook_trips_every_check(self, tmp_path: Path) -> None:
        result = report.run([str(messy(tmp_path))])
        checks = {f.check for f in result.findings}
        assert checks == {"outputs", "secrets", "order", "staleness"}
        assert result.worst_severity() is Severity.ERROR

    def test_check_filter_limits_what_runs(self, tmp_path: Path) -> None:
        result = report.run([str(messy(tmp_path))], checks=["secrets"])
        assert {f.check for f in result.findings} == {"secrets"}

    def test_findings_group_by_path_then_severity(self, tmp_path: Path) -> None:
        paths = [str(messy(tmp_path)), str(clean(tmp_path))]
        result = report.run(sorted(paths))
        assert [f.path for f in result.findings] == sorted(
            [f.path for f in result.findings]
        )


class TestRendering:
    def test_json_summary_counts_by_severity(self, tmp_path: Path) -> None:
        payload = json.loads(report.render_json(report.run([str(messy(tmp_path))])))
        assert payload["notebooks"] == 1
        assert payload["summary"]["error"] == 1  # the credential
        assert payload["summary"]["warning"] >= 2  # order + staleness at least
        assert all(f["path"] for f in payload["findings"])

    def test_text_groups_findings_under_the_notebook_path(self, tmp_path: Path) -> None:
        path = str(messy(tmp_path))
        text = report.render_text(report.run([path]))
        assert path in text
        assert "[secrets]" in text
        assert "ERROR" in text

    def test_text_for_a_clean_run_says_so(self, tmp_path: Path) -> None:
        text = report.render_text(report.run([str(clean(tmp_path))]))
        assert "no findings" in text
