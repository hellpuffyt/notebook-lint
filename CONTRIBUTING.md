# Contributing

Thanks for looking into notebook-lint.

## Setup

```console
python -m venv .venv && . .venv/bin/activate   # Scripts\activate on Windows
pip install -e ".[dev]"
```

## Before opening a pull request

```console
pytest            # the whole suite; new behaviour needs new tests
ruff check .      # lint
mypy              # strict — the src/ tree carries full annotations
```

## Ground rules

- **No runtime dependencies.** `dependencies = []` is a feature, not an
  oversight.
- **No execution, ever.** Every check must be static. A check that needs a
  kernel belongs in a different tool.
- **Findings must be checkable and secrets must stay redacted.** Evidence
  names cells and sizes; credential evidence carries a prefix and a length,
  never the value.
- **Precision over recall in the secrets patterns.** A linter that cries
  wolf gets removed from CI within a week, which protects nobody. New
  patterns need a concrete credential shape and placeholder handling.
