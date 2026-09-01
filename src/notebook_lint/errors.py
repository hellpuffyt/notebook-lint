"""Errors that reach the user as exit code 1."""

from __future__ import annotations


class NotebookLintError(Exception):
    """Base class for everything reported as a usage/input failure."""


class NotebookFormatError(NotebookLintError):
    """The file is not a readable Jupyter notebook."""
