# Changelog

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
