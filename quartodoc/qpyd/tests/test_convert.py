import shutil

import nbformat
import pytest

from quartodoc.qpyd import convert


def test_qmd2py_extracts_cells(tmp_path):
    qmd = tmp_path / "n.qmd"
    qmd.write_text(
        "---\ntitle: t\n---\n\nIntro text\n\n"
        "```{python}\nx = 1\n%timeit x\n!ls\n```\n\nmore\n"
    )
    text = convert.qmd2py(qmd).read_text()
    assert "#%% Cell 1" in text
    assert "x = 1" in text
    assert "# %timeit x" in text  # magic commented out
    assert "# !ls" in text  # shell command commented out
    assert "# Intro text" in text  # prose preserved as comment


def test_qmd2py_unclosed_raises(tmp_path):
    qmd = tmp_path / "bad.qmd"
    qmd.write_text("```{python}\nx = 1\n")
    with pytest.raises(ValueError):
        convert.qmd2py(qmd)


def test_to_py_on_qmd(tmp_path):
    qmd = tmp_path / "n.qmd"
    qmd.write_text("```{python}\nx = 1\n```\n")
    out = convert.to_py(qmd)
    assert out.suffix == ".py" and out.exists()


def test_clear_outputs(tmp_path):
    nb = nbformat.v4.new_notebook()
    cell = nbformat.v4.new_code_cell("print(1)")
    cell.execution_count = 3
    cell.outputs = [nbformat.v4.new_output("stream", name="stdout", text="1\n")]
    nb.cells = [cell]
    path = tmp_path / "nb.ipynb"
    nbformat.write(nb, str(path))

    convert.clear_outputs(str(path))

    cleared = nbformat.read(str(path), as_version=4)
    assert cleared.cells[0].outputs == []
    assert cleared.cells[0].execution_count is None


@pytest.mark.skipif(not shutil.which("quarto"), reason="quarto not installed")
def test_qmd_to_ipynb(tmp_path):
    qmd = tmp_path / "n.qmd"
    qmd.write_text("---\ntitle: t\n---\n\n```{python}\nx = 1\n```\n")
    out = convert.to_ipynb(qmd)
    assert out.suffix == ".ipynb" and out.exists()


@pytest.mark.skipif(not shutil.which("jupytext"), reason="jupytext not installed")
def test_ipynb_to_py(tmp_path):
    nb = nbformat.v4.new_notebook()
    nb.cells = [nbformat.v4.new_code_cell("x = 1")]
    path = tmp_path / "nb.ipynb"
    nbformat.write(nb, str(path))
    out = convert.to_py(path)
    assert out.suffix == ".py" and out.exists()
    assert "x = 1" in out.read_text()
