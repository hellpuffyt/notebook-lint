# Security policy

## Reporting a vulnerability

Please report security issues privately through GitHub's advisory form:
<https://github.com/hellpuffyt/notebook-lint/security/advisories/new>

Please do not open a public issue for a vulnerability, and never attach a
notebook containing a real credential — use a synthetic value of the same
shape.

In scope, for example: a full credential appearing in text or JSON output
(evidence must stay redacted), the tool executing notebook code or opening
network connections, or a crafted notebook that hangs it or exhausts memory.

A credential shape that is not detected is a detection gap; a normal issue
with a synthetic example is fine for those.

## Supported versions

Only the latest release on the default branch receives fixes.
