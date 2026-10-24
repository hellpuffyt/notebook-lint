# Changelog

## Unreleased

Fixed:

- Credentials printed into committed outputs (stream text, `text/plain`
  results, tracebacks) were never scanned; only cell sources were.
- Staleness false positives: lambda parameters reported as undefined names;
  non-Python cell magics (`%%bash`, `%%writefile`, …) reported as syntax
  errors; every name used after `from x import *` reported as undefined.
- Token-shaped test fixtures are now assembled at runtime.

Added: `SECURITY.md`, `.editorconfig`, `docs/PRODUCTION_READINESS.md`,
an Installation section (the package is not on PyPI).

## 0.1.0 — 2026-09-01

Initial release.

- Four static checks over nbformat-4 notebooks: committed outputs (severity
  scales with size), redacted credential detection tuned for precision,
  execution-order verification against `execution_count`, and staleness —
  syntax-dead cells and top-level reads of names no earlier cell defines,
  with IPython magics understood and non-Python notebooks skipped honestly.
- `notebook-lint` CLI over files and directories (recursive,
  `.ipynb_checkpoints` skipped): text and JSON output, per-check filtering,
  CI exit codes (`0` clean, `1` input error, `3` findings at or above
  `--fail-on`).
- Zero runtime dependencies; Python 3.10–3.13.
