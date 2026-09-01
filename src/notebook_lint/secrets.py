"""Credential material in cell sources and committed outputs.

Patterns are chosen for precision over recall: a linter that cries wolf on
every hex string gets removed from CI within a week, which protects nobody.
Each pattern names a concrete credential *shape*, and generic assignments
require both a telling variable name and a plausible secret value.
"""

from __future__ import annotations

import re

from .types import Finding, Notebook, Severity

#: (name, compiled pattern). Shapes with vendor-defined prefixes first.
PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("AWS access key id", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b")),
    ("Slack token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b")),
    ("OpenAI-style key", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b")),
    ("Google API key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b")),
    ("private key block", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    (
        "credential assignment",
        re.compile(
            r"""(?ix)
            \b(?:api[_-]?key|secret|token|passwd|password|auth)\b   # the name
            \s*[:=]\s*
            ["'](?P<value>[^"'\s]{12,})["']                          # the value
            """,
        ),
    ),
)

#: Values that look like placeholders are the author doing it right.
PLACEHOLDER = re.compile(
    r"(?i)^(\$\{?[A-Z_]+\}?|<[^>]+>|xxx+|\.\.\.|your[-_].*|changeme.*|dummy.*|example.*|\*+)$"
)


def scan_text(text: str) -> list[tuple[str, str]]:
    """(pattern name, redacted evidence) for each hit in ``text``."""
    hits: list[tuple[str, str]] = []
    for name, pattern in PATTERNS:
        for match in pattern.finditer(text):
            value = match.groupdict().get("value") or match.group(0)
            if PLACEHOLDER.match(value):
                continue
            hits.append((name, _redact(value)))
    return hits


def _redact(value: str) -> str:
    """Enough to locate the credential, never enough to reuse it."""
    if len(value) <= 8:
        return value[:2] + "…"
    return f"{value[:4]}…{value[-2:]} ({len(value)} chars)"


def check(notebook: Notebook) -> list[Finding]:
    findings = []
    for cell in notebook.cells:
        hits = scan_text(cell.source)
        if not hits:
            continue
        findings.append(
            Finding(
                check="secrets",
                severity=Severity.ERROR,
                message=(
                    f"cell {cell.index} contains what looks like "
                    f"{_summary(hits)}; a committed notebook is public the "
                    "moment the repo is, and git history keeps it after "
                    "deletion"
                ),
                path=notebook.path,
                cell=cell.index,
                evidence=tuple(f"{name}: {redacted}" for name, redacted in hits[:5]),
            )
        )
    return findings


def _summary(hits: list[tuple[str, str]]) -> str:
    names = sorted({name for name, _ in hits})
    if len(names) == 1:
        return f"a {names[0]}"
    return "credentials (" + ", ".join(names) + ")"
