from __future__ import annotations

from notebook_lint import staleness
from notebook_lint.types import Severity

from .conftest import code_cell, notebook


class TestStripMagics:
    def test_line_magics_blank_but_preserve_line_numbers(self) -> None:
        stripped = staleness.strip_magics("%matplotlib inline\nx = 1")
        assert stripped == "\nx = 1"

    def test_shell_escapes_blank(self) -> None:
        assert staleness.strip_magics("!pip install pandas") == ""

    def test_help_suffix_blanks(self) -> None:
        assert staleness.strip_magics("len?") == ""

    def test_ordinary_code_is_untouched(self) -> None:
        assert staleness.strip_magics("x = a % b") == "x = a % b"


class TestSyntaxErrors:
    def test_unparseable_cell_is_an_error_with_the_line(self) -> None:
        nb = notebook(code_cell(0, "def broken(:\n    pass"))
        findings = staleness.check(nb)
        assert [f.severity for f in findings] == [Severity.ERROR]
        assert "line 1" in findings[0].message

    def test_magics_do_not_count_as_syntax_errors(self) -> None:
        nb = notebook(code_cell(0, "%time\nx = 1"))
        assert staleness.check(nb) == []


class TestUndefinedNames:
    def test_name_defined_in_an_earlier_cell_is_fine(self) -> None:
        nb = notebook(
            code_cell(0, "df = load()"),
            code_cell(1, "df.head()"),
        )
        # `load` itself is undefined in cell 0 — that is the point of the
        # check, so define it there.
        nb = notebook(
            code_cell(0, "def load():\n    return 1\ndf = load()"),
            code_cell(1, "print(df)"),
        )
        assert staleness.check(nb) == []

    def test_name_from_a_deleted_cell_warns(self) -> None:
        nb = notebook(code_cell(0, "print(df)"))
        findings = staleness.check(nb)
        assert [f.severity for f in findings] == [Severity.WARNING]
        assert "'df'" in findings[0].message
        assert findings[0].evidence == ("df",)

    def test_name_defined_below_its_use_warns(self) -> None:
        nb = notebook(
            code_cell(0, "print(result)"),
            code_cell(1, "result = 3"),
        )
        assert len(staleness.check(nb)) == 1

    def test_imports_define_names(self) -> None:
        nb = notebook(
            code_cell(0, "import pandas as pd\nfrom os import path"),
            code_cell(1, "pd.DataFrame(); path.join('a', 'b')"),
        )
        assert staleness.check(nb) == []

    def test_loop_with_and_walrus_targets_define_names(self) -> None:
        nb = notebook(
            code_cell(
                0,
                "for i in range(3):\n    pass\n"
                "with open('f') as fh:\n    pass\n"
                "if (n := 4):\n    pass",
            ),
            code_cell(1, "print(i, fh, n)"),
        )
        assert staleness.check(nb) == []

    def test_reads_inside_function_bodies_are_not_flagged(self) -> None:
        nb = notebook(code_cell(0, "def use():\n    return helper()"))
        assert staleness.check(nb) == []

    def test_builtins_and_jupyter_globals_are_known(self) -> None:
        nb = notebook(code_cell(0, "print(len([]), get_ipython(), Out)"))
        assert staleness.check(nb) == []

    def test_non_python_notebooks_report_nothing_rather_than_guessing(self) -> None:
        nb = notebook(code_cell(0, "val x = readr::read_csv(f)"), language="r")
        assert staleness.check(nb) == []

    def test_star_import_does_not_crash(self) -> None:
        nb = notebook(
            code_cell(0, "from math import *"),
            code_cell(1, "print(pi)"),
        )
        # Expected value changed during the audit (was: 1 finding for `pi`).
        # Justification: after a star import the defined names are statically
        # unknowable, so the finding's message ("depends on a cell that was
        # deleted, moved below it, or run out of order") would be false for a
        # perfectly valid notebook; the README promises static judgements made
        # "honestly", and the module docstring calls the analysis conservative.
        # Undefined-name findings are therefore suppressed after `import *`.
        findings = staleness.check(nb)
        assert findings == []

    def test_except_handler_name_defines(self) -> None:
        nb = notebook(
            code_cell(0, "try:\n    pass\nexcept ValueError as err:\n    pass"),
            code_cell(1, "print(err)"),
        )
        assert staleness.check(nb) == []


class TestAuditRegressions:
    """False positives found in the production-readiness audit."""

    def test_lambda_parameters_are_not_undefined_reads(self) -> None:
        nb = notebook(code_cell(0, "v = [1]\nf = lambda a: a + 1\nsorted(v, key=lambda i: i)"))
        assert staleness.check(nb) == []

    def test_lambda_default_is_still_a_read(self) -> None:
        findings = staleness.check(notebook(code_cell(0, "f = lambda a=missing: a")))
        assert [f.evidence for f in findings] == [("missing",)]

    def test_non_python_cell_magic_is_not_a_syntax_error(self) -> None:
        nb = notebook(
            code_cell(0, "%%bash\nfor f in *.csv; do echo $f; done"),
            code_cell(1, "%%writefile a.txt\nhello: this isn't python"),
        )
        assert staleness.check(nb) == []

    def test_python_body_cell_magic_is_still_checked(self) -> None:
        findings = staleness.check(notebook(code_cell(0, "%%time\nprint(undefined_name)")))
        assert [f.evidence for f in findings] == [("undefined_name",)]
