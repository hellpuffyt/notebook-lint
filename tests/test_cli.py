from __future__ import annotations

import json
from pathlib import Path

import pytest

from notebook_lint import __version__, cli

from .conftest import raw_code_cell, raw_notebook, write_notebook


def clean_nb(tmp_path: Path) -> Path:
    return write_notebook(
        tmp_path / "clean.ipynb", raw_notebook([raw_code_cell("x = 1")])
    )


def leaky_nb(tmp_path: Path) -> Path:
    return write_notebook(
        tmp_path / "leaky.ipynb",
        raw_notebook([raw_code_cell('k = "AKIAIOSFODNN7EXAMPLE"')]),
    )


class TestExitCodes:
    def test_clean_run_exits_zero(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        assert cli.main([str(clean_nb(tmp_path))]) == cli.EXIT_OK

    def test_error_finding_exits_three(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        assert cli.main([str(leaky_nb(tmp_path))]) == cli.EXIT_FINDINGS

    def test_fail_on_never_reports_but_exits_zero(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        code = cli.main([str(leaky_nb(tmp_path)), "--fail-on", "never"])
        assert code == cli.EXIT_OK
        assert "secrets" in capsys.readouterr().out

    def test_fail_on_warning_trips_on_warnings(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        path = write_notebook(
            tmp_path / "w.ipynb",
            raw_notebook(
                [
                    raw_code_cell(
                        "x = 1",
                        execution_count=1,
                        outputs=[{"output_type": "stream", "text": "y"}],
                    )
                ]
            ),
        )
        assert cli.main([str(path)]) == cli.EXIT_OK
        assert cli.main([str(path), "--fail-on", "warning"]) == cli.EXIT_FINDINGS

    def test_missing_path_exits_one_on_stderr(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        code = cli.main([str(tmp_path / "absent.ipynb")])
        captured = capsys.readouterr()
        assert code == cli.EXIT_USAGE
        assert captured.err.startswith("error:")

    def test_empty_directory_exits_one(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        assert cli.main([str(tmp_path)]) == cli.EXIT_USAGE
        assert "no notebooks found" in capsys.readouterr().err


class TestOutput:
    def test_json_format(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        cli.main([str(leaky_nb(tmp_path)), "--format", "json", "--fail-on", "never"])
        payload = json.loads(capsys.readouterr().out)
        assert payload["notebooks"] == 1

    def test_directory_lints_every_notebook_in_it(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        clean_nb(tmp_path)
        leaky_nb(tmp_path)
        cli.main([str(tmp_path), "--format", "json", "--fail-on", "never"])
        assert json.loads(capsys.readouterr().out)["notebooks"] == 2

    def test_check_filter_governs_exit(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        assert cli.main([str(leaky_nb(tmp_path)), "--check", "outputs"]) == cli.EXIT_OK

    def test_version_flag(self, capsys: pytest.CaptureFixture[str]) -> None:
        with pytest.raises(SystemExit) as excinfo:
            cli.main(["--version"])
        assert excinfo.value.code == 0
        assert __version__ in capsys.readouterr().out


class TestModuleEntryPoint:
    def test_python_dash_m_invocation(self, tmp_path: Path) -> None:
        import subprocess
        import sys

        done = subprocess.run(
            [sys.executable, "-m", "notebook_lint", str(clean_nb(tmp_path))],
            capture_output=True,
            text=True,
            check=False,
        )
        assert done.returncode == 0
        assert "1 notebook(s) linted" in done.stdout
