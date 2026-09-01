"""Builders: notebooks are constructed in code so each test states its exact
input, and written to disk only where the loader/CLI is what's under test."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from notebook_lint.types import Cell, Notebook


def code_cell(
    index: int,
    source: str,
    *,
    execution_count: int | None = None,
    output_sizes: tuple[int, ...] = (),
    output_types: tuple[str, ...] = (),
) -> Cell:
    return Cell(
        index=index,
        cell_type="code",
        source=source,
        execution_count=execution_count,
        output_sizes=output_sizes,
        output_types=output_types or tuple("stream" for _ in output_sizes),
    )


def notebook(
    *cells: Cell, language: str | None = "python", path: str = "nb.ipynb"
) -> Notebook:
    return Notebook(
        path=path,
        cells=cells,
        language=language,
        kernel_name="python3",
        nbformat=4,
    )


def raw_notebook(cells: list[dict[str, Any]], **overrides: Any) -> dict[str, Any]:
    """A minimal on-disk nbformat-4 document."""
    doc: dict[str, Any] = {
        "cells": cells,
        "metadata": {
            "kernelspec": {"name": "python3", "display_name": "Python 3"},
            "language_info": {"name": "python"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    doc.update(overrides)
    return doc


def raw_code_cell(
    source: str | list[str],
    *,
    execution_count: int | None = None,
    outputs: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "cell_type": "code",
        "source": source,
        "metadata": {},
        "execution_count": execution_count,
        "outputs": outputs or [],
    }


def write_notebook(path: Path, doc: dict[str, Any]) -> Path:
    path.write_text(json.dumps(doc), encoding="utf-8")
    return path
