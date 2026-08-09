"""
Notebook format conversions for qpynb: ``.qmd`` <-> ``.ipynb`` <-> ``.py``,
plus clearing/normalising executed ``.ipynb`` outputs.

``.qmd`` <-> ``.ipynb`` conversions go through ``quarto convert`` (the
canonical tool); anything involving ``.py`` goes through ``jupytext``. The
``.qmd`` -> ``.py`` path uses :func:`qmd2py`, which extracts ``{python}``
cells into a flat script (closely matching the original ``quarto_utils.py``).
"""

import subprocess
import sys
from pathlib import Path

import sciris as sc

from .config import discover_notebooks


def qmd2py(qmd_path, py_path=None, keep_text=True):
    """
    Convert a ``.qmd`` file to a ``.py`` file by extracting Python code cells.

    Each ``` ```{python} ... ``` ``` block becomes a cell, separated by
    ``#%% Cell N`` headers and two blank lines between cells. Raises an
    exception if blocks are ambiguous (e.g., nested or unclosed code fences).

    Lines starting with ``%`` or ``!`` (IPython magics / shell commands) are
    commented out since they are not valid Python.

    Args:
        qmd_path (str/Path): path to the ``.qmd`` file
        py_path (str/Path): path to write the ``.py`` file (default: same name
            with a ``.py`` extension)
        keep_text (bool): if True, include non-code text as comments prefixed
            with ``# ``

    Returns the :class:`~pathlib.Path` of the written ``.py`` file.
    """
    qmd_path = sc.path(qmd_path)
    if py_path is None:
        py_path = qmd_path.with_suffix(".py")
    else:
        py_path = sc.path(py_path)

    text = sc.loadtext(qmd_path)
    lines = text.splitlines()

    chunks = []  # List of (type, content) tuples; type is 'code' or 'text'
    in_block = False
    current_cell = []
    current_text = []
    block_start_line = None

    for i, line in enumerate(lines, start=1):
        stripped = line.strip()
        if stripped.startswith("```{python}"):
            if in_block:
                raise ValueError(
                    f"Nested or unclosed code block: new block at line {i}, "
                    f"previous block started at line {block_start_line}"
                )
            if keep_text and current_text:
                chunks.append(("text", current_text))
                current_text = []
            in_block = True
            block_start_line = i
            current_cell = []
        elif stripped == "```" and in_block:
            chunks.append(("code", current_cell))
            in_block = False
            current_cell = []
            block_start_line = None
        elif in_block:
            current_cell.append(line)
        elif keep_text:
            current_text.append(line)

    if in_block:
        raise ValueError(f"Unclosed code block starting at line {block_start_line}")

    if keep_text and current_text:
        chunks.append(("text", current_text))

    # Build output
    parts = []
    cell_num = 0
    for kind, content in chunks:
        if kind == "code":
            cell_num += 1
            processed = []
            for line in content:
                if line.lstrip().startswith(("%", "!")):
                    processed.append(
                        f"# {line}  # IPython not supported in Python files"
                    )
                else:
                    processed.append(line)
            parts.append(f"#%% Cell {cell_num}\n" + "\n".join(processed))
        else:  # text
            commented = "\n".join(
                f"# {line}" if line.strip() else "#" for line in content
            )
            parts.append(commented)

    output = "\n\n\n".join(parts) + "\n"
    sc.savetext(py_path, output)
    return py_path


def _run(cmd, cwd=None):
    """Run a subprocess, raising a clear error (with captured output) on failure."""
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)
    except FileNotFoundError as e:
        tool = cmd[0]
        hint = (
            "Install Quarto from https://quarto.org and ensure it is on your PATH."
            if tool == "quarto"
            else f"Install it (e.g. `pip install {tool}`)."
        )
        raise RuntimeError(
            f"Required tool {tool!r} was not found on your PATH. {hint}"
        ) from e
    if proc.returncode != 0:
        raise RuntimeError(
            f"Command failed ({' '.join(cmd)}):\n{proc.stdout}\n{proc.stderr}"
        )
    return proc


def _guard_overwrite(out_path, src_path, force):
    """Raise unless it is safe to write ``out_path`` (a different, absent, or forced dest)."""
    out_path = sc.path(out_path)
    if out_path.resolve() == sc.path(src_path).resolve():
        return  # converting to the same file (no-op cases) is fine
    if out_path.exists() and not force:
        raise FileExistsError(
            f"{out_path} already exists; refusing to overwrite. Pass --force to overwrite."
        )


def _quarto_convert(path, force=False):
    """
    Convert ``.qmd`` <-> ``.ipynb`` using ``quarto convert``, returning the
    path of the produced file.

    ``quarto convert`` toggles between the two formats and writes the output
    alongside the input with the opposite extension, so the destination is
    overwrite-guarded first.
    """
    path = sc.path(path)
    other = ".ipynb" if path.suffix == ".qmd" else ".qmd"
    out_path = path.with_suffix(other)
    _guard_overwrite(out_path, path, force)
    # Run in the file's own directory: `quarto convert` will otherwise append
    # quarto ignores to the .gitignore of whatever git repo the cwd sits in.
    _run(["quarto", "convert", path.name], cwd=str(path.parent))
    return out_path


def to_py(path, force=False):
    """
    Convert a notebook to a Python (``.py``) file.

    ``.qmd`` files use :func:`qmd2py`; ``.ipynb`` files use ``jupytext``
    (percent format). An existing destination is not overwritten unless
    ``force`` is set. Returns the output :class:`~pathlib.Path`.
    """
    path = sc.path(path)
    if path.suffix == ".py":
        return path
    out_path = path.with_suffix(".py")
    _guard_overwrite(out_path, path, force)
    if path.suffix == ".qmd":
        return qmd2py(path, out_path)
    if path.suffix == ".ipynb":
        _run(["jupytext", "--to", "py:percent", "--output", str(out_path), str(path)])
        return out_path
    raise ValueError(f"Don't know how to convert {path} to .py")


def to_qmd(path, force=False):
    """
    Convert a notebook to a Quarto (``.qmd``) file.

    ``.ipynb`` uses ``quarto convert``; ``.py`` uses ``jupytext``. An existing
    destination is not overwritten unless ``force`` is set. Returns the output
    :class:`~pathlib.Path`.
    """
    path = sc.path(path)
    if path.suffix == ".qmd":
        return path
    if path.suffix == ".ipynb":
        return _quarto_convert(path, force=force)
    if path.suffix == ".py":
        out_path = path.with_suffix(".qmd")
        _guard_overwrite(out_path, path, force)
        _run(["jupytext", "--to", "qmd", "--output", str(out_path), str(path)])
        return out_path
    raise ValueError(f"Don't know how to convert {path} to .qmd")


def to_ipynb(path, force=False):
    """
    Convert a notebook to a Jupyter (``.ipynb``) file.

    ``.qmd`` uses ``quarto convert``; ``.py`` uses ``jupytext``. An existing
    destination is not overwritten unless ``force`` is set. Returns the output
    :class:`~pathlib.Path`.
    """
    path = sc.path(path)
    if path.suffix == ".ipynb":
        return path
    if path.suffix == ".qmd":
        return _quarto_convert(path, force=force)
    if path.suffix == ".py":
        out_path = path.with_suffix(".ipynb")
        _guard_overwrite(out_path, path, force)
        _run(["jupytext", "--to", "ipynb", "--output", str(out_path), str(path)])
        return out_path
    raise ValueError(f"Don't know how to convert {path} to .ipynb")


def clear_outputs(*paths, dry_run=False):
    """
    Clear saved outputs from ``.ipynb`` notebooks and normalise them.

    Removes cell outputs and execution counts, then rewrites each notebook via
    ``nbformat`` (which normalises structure). Operates on the ``.ipynb`` files
    found in ``paths`` (or the whole project if none are given). Files that are
    already clean are left untouched. With ``dry_run`` set, nothing is written.

    Returns the list of notebooks that were (or would be) modified.
    """
    import nbformat

    notebooks = discover_notebooks(list(paths) or None)
    ipynbs = [nb for nb in notebooks if nb.suffix == ".ipynb"]
    if not ipynbs:
        print("No .ipynb notebooks found to clear.")
        return []

    cleared = []
    for nb_path in ipynbs:
        nb = nbformat.read(str(nb_path), as_version=4)
        changed = False
        for cell in nb.cells:
            if cell.get("cell_type") != "code":
                continue
            if cell.get("outputs") or cell.get("execution_count") is not None:
                changed = True
            cell["outputs"] = []
            cell["execution_count"] = None
        try:  # normalise structure where supported; never fatal
            n_norm, nb = nbformat.validator.normalize(nb)
            changed = changed or bool(n_norm)
        except Exception:
            pass
        if not changed:
            print(f"Already clean: {nb_path.name}")
            continue
        cleared.append(nb_path)
        verb = "Would clear" if dry_run else "Cleared"
        print(f"{verb}: {nb_path.name}")
        if not dry_run:
            nbformat.write(nb, str(nb_path))
    return cleared


# Allow `python -m quartodoc.qpyd.convert <file>` for ad-hoc qmd->py conversion
if __name__ == "__main__":
    for arg in sys.argv[1:]:
        print(to_py(arg))
