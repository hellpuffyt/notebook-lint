"""Load .ipynb files into the reduced model the checks work on.

The full output payloads are measured and dropped: the checks need to know a
cell carries 4 MB of base64 PNG, not what the pixels are, and notebooks with
huge outputs are exactly the ones this tool is pointed at.
"""

from __future__ import annotations

import json
from pathlib import Path

from .errors import NotebookFormatError
from .types import Cell, Notebook


def discover(paths: list[str | Path]) -> list[Path]:
    """Expand files and directories into a sorted list of notebook paths.

    Directories are walked recursively; checkpoint copies are skipped —
    linting `.ipynb_checkpoints` would double-report every finding against
    a file nobody edits.
    """
    found: set[Path] = set()
    for raw in paths:
        path = Path(raw)
        if path.is_dir():
            for candidate in path.rglob("*.ipynb"):
                if ".ipynb_checkpoints" not in candidate.parts:
                    found.add(candidate)
        elif path.suffix == ".ipynb":
            found.add(path)
        else:
            raise NotebookFormatError(f"{path}: not a notebook (.ipynb) or directory")
    return sorted(found)


def load(path: str | Path) -> Notebook:
    path = Path(path)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except OSError as err:
        raise NotebookFormatError(f"cannot read {path}: {err.strerror or err}") from err
    except json.JSONDecodeError as err:
        raise NotebookFormatError(f"{path}: not valid JSON: {err.msg}") from err
    if not isinstance(raw, dict) or "cells" not in raw:
        raise NotebookFormatError(f"{path}: no cells; not a Jupyter notebook")

    nbformat = raw.get("nbformat")
    if not isinstance(nbformat, int) or nbformat < 4:
        raise NotebookFormatError(
            f"{path}: nbformat {nbformat!r} unsupported (needs 4+)"
        )

    metadata = raw.get("metadata") if isinstance(raw.get("metadata"), dict) else {}
    assert isinstance(metadata, dict)
    kernelspec = metadata.get("kernelspec")
    kernel_name = (
        kernelspec.get("name") if isinstance(kernelspec, dict) else None
    )
    language_info = metadata.get("language_info")
    language = (
        language_info.get("name") if isinstance(language_info, dict) else None
    )

    cells_raw = raw["cells"]
    if not isinstance(cells_raw, list):
        raise NotebookFormatError(f"{path}: cells is not a list")

    cells = []
    for index, cell_raw in enumerate(cells_raw):
        if not isinstance(cell_raw, dict):
            raise NotebookFormatError(f"{path}: cell {index} is not an object")
        cells.append(_cell(cell_raw, index))

    return Notebook(
        path=str(path),
        cells=tuple(cells),
        language=language if isinstance(language, str) else None,
        kernel_name=kernel_name if isinstance(kernel_name, str) else None,
        nbformat=nbformat,
    )


def _cell(raw: dict[str, object], index: int) -> Cell:
    source_raw = raw.get("source", "")
    if isinstance(source_raw, list):
        source = "".join(str(part) for part in source_raw)
    else:
        source = str(source_raw)

    execution_count = raw.get("execution_count")
    outputs_raw = raw.get("outputs")
    sizes: list[int] = []
    kinds: list[str] = []
    if isinstance(outputs_raw, list):
        for output in outputs_raw:
            sizes.append(len(json.dumps(output)))
            kind = output.get("output_type") if isinstance(output, dict) else None
            kinds.append(kind if isinstance(kind, str) else "unknown")

    return Cell(
        index=index,
        cell_type=str(raw.get("cell_type", "code")),
        source=source,
        execution_count=execution_count if isinstance(execution_count, int) else None,
        output_sizes=tuple(sizes),
        output_types=tuple(kinds),
    )
