"""Console entry point. Exit codes are the CI contract:

* 0 — linted, nothing at or above ``--fail-on``
* 1 — usage or input error
* 3 — findings at or above ``--fail-on``
"""

from __future__ import annotations

import argparse
import sys

from . import __version__, io, report
from .errors import NotebookLintError
from .types import Severity

EXIT_OK = 0
EXIT_USAGE = 1
EXIT_FINDINGS = 3


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="notebook-lint",
        description=(
            "Lint Jupyter notebooks for committed outputs, secrets, "
            "out-of-order execution, and cells that no longer run."
        ),
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument(
        "paths",
        nargs="+",
        help="notebooks or directories (searched recursively for *.ipynb)",
    )
    parser.add_argument(
        "--format", choices=("text", "json"), default="text",
        help="output format (default: text)",
    )
    parser.add_argument(
        "--fail-on", choices=("error", "warning", "never"), default="error",
        help="exit 3 when a finding at or above this severity exists (default: error)",
    )
    parser.add_argument(
        "--check", action="append", choices=sorted(report.CHECKS),
        help="restrict to one or more checks (repeatable)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        notebooks = io.discover(list(args.paths))
        if not notebooks:
            print("error: no notebooks found under the given paths", file=sys.stderr)
            return EXIT_USAGE
        result = report.run([str(p) for p in notebooks], args.check)
    except NotebookLintError as err:
        print(f"error: {err}", file=sys.stderr)
        return EXIT_USAGE

    print(report.render_json(result) if args.format == "json" else report.render_text(result))

    if args.fail_on == "never":
        return EXIT_OK
    threshold = Severity.ERROR if args.fail_on == "error" else Severity.WARNING
    worst = result.worst_severity()
    if worst is not None and worst.rank >= threshold.rank:
        return EXIT_FINDINGS
    return EXIT_OK
