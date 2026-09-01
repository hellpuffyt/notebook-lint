from __future__ import annotations

from notebook_lint import secrets
from notebook_lint.types import Severity

from .conftest import code_cell, notebook


class TestScanText:
    def test_aws_access_key_id(self) -> None:
        hits = secrets.scan_text('key = "AKIAIOSFODNN7EXAMPLE"')
        assert [name for name, _ in hits][0] == "AWS access key id"

    def test_github_token(self) -> None:
        token = "ghp_" + "a" * 36
        assert secrets.scan_text(f"t = '{token}'")

    def test_private_key_block(self) -> None:
        hits = secrets.scan_text("-----BEGIN RSA PRIVATE KEY-----")
        assert hits and hits[0][0] == "private key block"

    def test_generic_assignment_requires_name_and_value(self) -> None:
        assert secrets.scan_text('api_key = "supersecretvalue123"')
        # A telling name with a placeholder value is the author doing it right.
        assert secrets.scan_text('api_key = "<YOUR-KEY-HERE>"') == []
        assert secrets.scan_text('api_key = "${API_KEY}"') == []
        # A secret-looking value under an innocent name stays quiet: precision
        # over recall, by design.
        assert secrets.scan_text('flavour = "supersecretvalue123"') == []

    def test_short_values_are_not_flagged(self) -> None:
        assert secrets.scan_text('password = "hunter2"') == []

    def test_redaction_never_echoes_the_credential(self) -> None:
        value = "AKIAIOSFODNN7EXAMPLE"
        _, redacted = secrets.scan_text(f'k = "{value}"')[0]
        assert value not in redacted
        assert redacted.startswith(value[:4])


class TestCheck:
    def test_clean_cells_yield_nothing(self) -> None:
        nb = notebook(code_cell(0, "x = compute()"))
        assert secrets.check(nb) == []

    def test_finding_is_an_error_anchored_to_the_cell(self) -> None:
        nb = notebook(
            code_cell(0, "x = 1"),
            code_cell(1, 'aws = "AKIAIOSFODNN7EXAMPLE"'),
        )
        findings = secrets.check(nb)
        assert [f.severity for f in findings] == [Severity.ERROR]
        assert findings[0].cell == 1
        assert "history keeps it" in findings[0].message

    def test_markdown_cells_are_scanned_too(self) -> None:
        from notebook_lint.types import Cell

        markdown = Cell(
            index=0,
            cell_type="markdown",
            source="token: ghp_" + "b" * 36,
            execution_count=None,
        )
        assert secrets.check(notebook(markdown))

    def test_multiple_hits_in_one_cell_are_one_finding(self) -> None:
        nb = notebook(
            code_cell(
                0,
                'a = "AKIAIOSFODNN7EXAMPLE"\nb = "AKIAIOSFODNN7EXAMPLF"',
            )
        )
        findings = secrets.check(nb)
        assert len(findings) == 1
        assert len(findings[0].evidence) == 2
