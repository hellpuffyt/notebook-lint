from __future__ import annotations

import json
from pathlib import Path

import pytest

from notebook_lint import io
from notebook_lint.errors import NotebookFormatError

from .conftest import raw_code_cell, raw_notebook, write_notebook


class TestLoad:
    def test_minimal_notebook_loads(self, tmp_path: Path) -> None:
        path = write_notebook(
            tmp_path / "a.ipynb", raw_notebook([raw_code_cell("x = 1")])
        )
        nb = io.load(path)
        assert len(nb.cells) == 1
        assert nb.cells[0].source == "x = 1"
        assert nb.language == "python"
        assert nb.kernel_name == "python3"

    def test_list_sources_are_joined_verbatim(self, tmp_path: Path) -> None:
        path = write_notebook(
            tmp_path / "a.ipynb", raw_notebook([raw_code_cell(["x = 1\n", "y = 2"])])
        )
        assert io.load(path).cells[0].source == "x = 1\ny = 2"

    def test_output_sizes_are_measured_not_kept(self, tmp_path: Path) -> None:
        output = {"output_type": "stream", "text": "hello world"}
        path = write_notebook(
            tmp_path / "a.ipynb",
            raw_notebook([raw_code_cell("print('hi')", execution_count=1, outputs=[output])]),
        )
        cell = io.load(path).cells[0]
        assert cell.output_sizes == (len(json.dumps(output)),)
        assert cell.output_types == ("stream",)

    def test_markdown_cells_are_kept_but_not_code(self, tmp_path: Path) -> None:
        doc = raw_notebook(
            [{"cell_type": "markdown", "source": "# title", "metadata": {}}]
        )
        nb = io.load(write_notebook(tmp_path / "a.ipynb", doc))
        assert nb.cells[0].cell_type == "markdown"
        assert nb.code_cells == ()

    def test_not_json_is_a_named_error(self, tmp_path: Path) -> None:
        path = tmp_path / "a.ipynb"
        path.write_text("{oops", encoding="utf-8")
        with pytest.raises(NotebookFormatError, match="not valid JSON"):
            io.load(path)

    def test_json_without_cells_is_refused(self, tmp_path: Path) -> None:
        path = tmp_path / "a.ipynb"
        path.write_text('{"nbformat": 4}', encoding="utf-8")
        with pytest.raises(NotebookFormatError, match="no cells"):
            io.load(path)

    def test_nbformat_3_is_refused_not_misread(self, tmp_path: Path) -> None:
        doc = raw_notebook([raw_code_cell("x = 1")], nbformat=3)
        with pytest.raises(NotebookFormatError, match="nbformat 3"):
            io.load(write_notebook(tmp_path / "a.ipynb", doc))

    def test_missing_file_reports_the_path(self, tmp_path: Path) -> None:
        with pytest.raises(NotebookFormatError, match="cannot read"):
            io.load(tmp_path / "absent.ipynb")

    def test_missing_kernelspec_is_tolerated(self, tmp_path: Path) -> None:
        doc = raw_notebook([raw_code_cell("x = 1")], metadata={})
        nb = io.load(write_notebook(tmp_path / "a.ipynb", doc))
        assert nb.kernel_name is None
        assert nb.language is None


class TestDiscover:
    def test_single_file(self, tmp_path: Path) -> None:
        path = write_notebook(tmp_path / "a.ipynb", raw_notebook([raw_code_cell("1")]))
        assert io.discover([path]) == [path]

    def test_directory_is_recursive_and_sorted(self, tmp_path: Path) -> None:
        write_notebook(tmp_path / "b.ipynb", raw_notebook([]))
        (tmp_path / "sub").mkdir()
        write_notebook(tmp_path / "sub" / "a.ipynb", raw_notebook([]))
        found = io.discover([tmp_path])
        assert [p.name for p in found] == ["b.ipynb", "a.ipynb"]

    def test_checkpoint_copies_are_skipped(self, tmp_path: Path) -> None:
        (tmp_path / ".ipynb_checkpoints").mkdir()
        write_notebook(
            tmp_path / ".ipynb_checkpoints" / "a-checkpoint.ipynb", raw_notebook([])
        )
        write_notebook(tmp_path / "a.ipynb", raw_notebook([]))
        assert [p.name for p in io.discover([tmp_path])] == ["a.ipynb"]

    def test_non_notebook_file_is_refused(self, tmp_path: Path) -> None:
        path = tmp_path / "script.py"
        path.write_text("x = 1", encoding="utf-8")
        with pytest.raises(NotebookFormatError, match="not a notebook"):
            io.discover([path])

    def test_duplicates_collapse(self, tmp_path: Path) -> None:
        path = write_notebook(tmp_path / "a.ipynb", raw_notebook([]))
        assert io.discover([path, tmp_path]) == [path]
