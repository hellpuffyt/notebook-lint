# Production readiness — notebook-lint

Audit date: 2026-10-22. Tested code commit: `3997226` (branch
`audit/production-readiness`); later commits change documentation and
repository metadata only.

## Scope

Static, dependency-free linter for nbformat-4 notebooks with four checks:
committed outputs, credentials (redacted evidence), execution order, and
staleness (cells that cannot parse or read names no earlier cell defines).
It never executes notebook code. Architecture: `io.py` (load + reduce) →
`outputs.py` / `secrets.py` / `order.py` / `staleness.py` → `report.py` →
`cli.py`.

## Platforms and prerequisites

Python ≥ 3.10, no runtime dependencies. Verified on macOS 27 (Apple
Silicon), Python 3.12 (full + clean clone), 3.10 and 3.13 (suite). Not on
PyPI. Linux/Windows CI legs not run for this audit.

## Clean-clone verification

```bash
git clone -b audit/production-readiness <repo> notebook-lint && cd notebook-lint
python3.12 -m venv .venv && .venv/bin/python -m pip install -e .   # exit 0
.venv/bin/notebook-lint examples/messy.ipynb          # 3 warnings, exit 0 (default --fail-on error)
.venv/bin/notebook-lint . --format json               # valid JSON
.venv/bin/notebook-lint . --fail-on warning           # exit 3
.venv/bin/python -m pip install -e ".[dev]"
pytest                                                # 81 passed
ruff check . ; mypy                                   # clean; no issues in 11 files
```

## Commands and outcomes

| Step | Command | Exit | Result |
|---|---|---:|---|
| Baseline (main `b853ed6`) | `pytest -q` | 0 | 71 passed, 0 failed, 0 skipped |
| Baseline lint/types | `ruff check .`, `mypy` | 0, 0 | clean |
| Final (3.10, 3.12, 3.13) | `pytest` | 0 | 81 passed, 0 failed, 0 skipped |
| CI coverage gate | `pytest -q --cov --cov-fail-under=95` | 0 | 95.8% |
| New tests on original code | `PYTHONPATH=<main>/src pytest <new tests>` | 1 | 7 failed, 3 passed |
| Dependency audit | `uvx pip-audit … --strict -s osv` | 0 | no known vulnerabilities |
| Secret scan | detect-secrets (tree), credential-pattern `git grep` (all history) | – | tree: test fixtures only; history: AWS documentation key `AKIA…EXAMPLE` and a PEM header string in tests of `7d3443f`/`b853ed6` (not credentials) |

CI: default branch `main`: **success** (`b853ed6`). Audit branch: pending
until pushed.

## Bugs found and fixed

| # | Severity | Defect | Regression test |
|---|---|---|---|
| 1 | High (missed secrets) | Credentials printed into outputs (stream, `text/plain`, tracebacks) never scanned, though `secrets.py` documented "cell sources and committed outputs" | `tests/test_audit_output_secrets.py` |
| 2 | Medium (false positive) | Lambda parameters reported as undefined names | `test_lambda_parameters_are_not_undefined_reads` |
| 3 | Medium (false error) | `%%bash`, `%%writefile` … cells reported as invalid Python (severity error) | `test_non_python_cell_magic_is_not_a_syntax_error` |
| 4 | Low (false positive) | Every name after `from x import *` reported as depending on a deleted cell. **Expected value of `test_star_import_does_not_crash` changed; justification in the test.** | same test |
| 5 | Low (docs) | README had no installation instructions; redaction format undocumented | README |

## Security review

No execution of notebook code, no network, no writes. Report evidence is
redacted (first 4 + last 2 chars + length); a test asserts no full fixture
credential nor its redacted middle appears in text or JSON output. Output
text retained per cell is capped at 1 MB. History hits are documentation
placeholders — **no rotation needed**.

## Known limitations

Static only; binary/image outputs not scanned for secrets; staleness is
name-based and ignores reads inside functions/lambdas; non-Python kernels
skipped.

## Acceptance checklist

| Item | Expected | Command / test | Result | Actual | Reference |
|---|---|---|---|---|---|
| A1 | Install from source | README | pass | exit 0 | clean clone |
| A2 | Suite/lint/types/coverage | CI commands | pass | 81 passed, 95.8% | CI |
| A3 | Secrets in sources and outputs found, redacted | tests | pass | yes | `test_secrets.py`, `test_audit_output_secrets.py` |
| A4 | Exit codes 0/1/3 per `--fail-on` | tests + clean clone | pass | yes | `test_cli.py` |
| A5 | Order and outputs checks | tests | pass | yes | `test_order.py`, `test_outputs.py` |
| A6 | Staleness without known false positives above | tests | pass | yes | `test_staleness.py` |
| A7 | Checkpoints skipped; bad input exit 1 | tests | pass | yes | `test_io.py`, `test_cli.py` |

## Classification proposal

**Partially Verified** — documented behaviour tested on macOS with Python
3.10–3.13 and clean clone passes. Not verified: Linux/Windows CI on the
audit branch (pending push).
