"""Secrets printed into committed outputs (found in the audit: only cell
sources were scanned although the module promises "cell sources and committed
outputs"), and the guarantee that no full credential reaches the report."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from notebook_lint import cli, io, secrets

from .conftest import raw_code_cell, raw_notebook, write_notebook

AWS = "AK" + "IA" + "Z7Q3FAKEFIXTURE0"
GITHUB = "gh" + "p_" + "F4keF1xtureT0kenF0rTests0nly0123456789"
ASSIGNED = "Zq8vT2mW9kL4pX7rN5"


@pytest.mark.parametrize(
    "output",
    [
        {"output_type": "stream", "name": "stdout", "text": [f"key={AWS}\n"]},
        {"output_type": "execute_result", "execution_count": 1, "metadata": {},
         "data": {"text/plain": [f"'{GITHUB}'"]}},
        {"output_type": "error", "ename": "KeyError", "evalue": f"'{AWS}'",
         "traceback": [f"KeyError: {AWS}"]},
    ],
    ids=["stream", "execute_result", "error"],
)
def test_credentials_in_outputs_are_reported(
    tmp_path: Path, output: dict[str, object]
) -> None:
    path = write_notebook(
        tmp_path / "nb.ipynb",
        raw_notebook([raw_code_cell("print(load())", execution_count=1, outputs=[output])]),
    )
    findings = secrets.check(io.load(path))
    assert len(findings) == 1
    assert "(in output)" in findings[0].evidence[0]


def test_output_text_is_capped(tmp_path: Path) -> None:
    big = {"output_type": "stream", "name": "stdout", "text": "x" * 3_000_000}
    doc = raw_notebook([raw_code_cell("1", outputs=[big])])
    path = write_notebook(tmp_path / "nb.ipynb", doc)
    assert len(io.load(path).cells[0].output_text) == io.OUTPUT_TEXT_LIMIT


@pytest.mark.parametrize("fmt", ["text", "json"])
def test_no_full_credential_reaches_the_report(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], fmt: str
) -> None:
    out = {"output_type": "stream", "name": "stdout", "text": [GITHUB]}
    doc = raw_notebook([
        raw_code_cell(
            f'k = "{AWS}"\npassword = "{ASSIGNED}"', execution_count=1, outputs=[out]
        ),
    ])
    write_notebook(tmp_path / "nb.ipynb", doc)
    assert cli.main([str(tmp_path), "--format", fmt]) == cli.EXIT_FINDINGS
    printed = capsys.readouterr().out
    if fmt == "json":
        json.loads(printed)
    for value in (AWS, GITHUB, ASSIGNED):
        assert value not in printed
        assert value[4:-2] not in printed  # the redacted middle never appears
