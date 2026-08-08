"""
Notebook execution for qpynb.

Two execution modes, both run **in parallel**:

* ``check`` (:func:`execute_notebooks`) — extract each notebook to a temporary
  ``.py`` script and run it, purely to verify it executes without error. It
  touches no caches and leaves nothing behind. This mirrors the original
  ``execute_notebooks()`` from ``quarto_utils.py``.
* ``run`` (:func:`run_notebooks`) — ``quarto render`` each notebook, which
  executes it *and* updates the Quarto freeze cache (``_freeze/``) so a
  subsequent full-site render can reuse the results.

:func:`refresh_cache` deletes those cached copies so notebooks re-execute.
"""

import os
import subprocess
import sys
import tempfile
from pathlib import Path

import sciris as sc

from .config import (
    BOO,
    FREEZE_DIR,
    JUPYTER_CACHE_DIR,
    TIMEOUT,
    YAY,
    discover_notebooks,
    docs_dir,
    project_root,
    require_tool,
)
from .convert import qmd2py

# Non-interactive matplotlib backend, so notebooks that plot don't try to open
# a GUI window during headless execution.
_AGG_ENV = {**os.environ, "MPLBACKEND": "agg"}

_QUARTO_HINT = "Install Quarto from https://quarto.org and ensure it is on your PATH."
_JUPYTEXT_HINT = "Install it with `pip install jupytext`."


def _make_runnable_py(path, out_dir):
    """Produce a runnable ``.py`` for a ``.qmd`` or ``.ipynb`` in ``out_dir``."""
    path = sc.path(path)
    py_path = Path(out_dir) / (path.stem + ".py")
    if path.suffix == ".qmd":
        qmd2py(path, py_path)
    elif path.suffix == ".ipynb":
        subprocess.run(
            ["jupytext", "--to", "py:percent", "--output", str(py_path), str(path)],
            check=True,
            capture_output=True,
        )
    else:
        raise ValueError(f"Cannot execute {path}: not a .qmd or .ipynb notebook")
    return py_path


def execute_notebook(path):
    """
    Execute a single notebook by extracting it to a temp ``.py`` and running it.

    Returns a one-line result string (containing :data:`YAY` or :data:`BOO`
    and a ``(time: N s)`` suffix) describing success or failure.
    """
    path = sc.path(path).resolve()
    with sc.timer(label=sc.ansi.green(f"    Execution time for {path.name}")) as T:
        try:
            with tempfile.TemporaryDirectory() as tmp:
                py_path = _make_runnable_py(path, tmp)
                print(f"Executing {path.name}...")
                subprocess.run(
                    [sys.executable, "-m", "IPython", str(py_path)], # Use IPython so get_ipython() and display() are available
                    check=True,
                    capture_output=True,
                    cwd=str(path.parent),
                    env=_AGG_ENV,
                    timeout=TIMEOUT,
                )
            string = f"{YAY} {path.stem} executed successfully "
        except subprocess.CalledProcessError as e:
            err = (e.stderr or b"").decode(errors="ignore")
            string = f"{BOO} Execution failed for {path.stem}:\n{err[-1500:]}\n"
        except Exception as e:
            string = f"{BOO} Error processing {path.stem}: {e}\n"
    string += f"(time: {T.total:0.1f} s)"
    print(string)
    return string


def render_notebook(path, cwd=None):
    """
    Render a single notebook with ``quarto render``, updating the freeze cache.

    Returns a one-line result string, in the same format as
    :func:`execute_notebook`.
    """
    path = sc.path(path).resolve()
    cwd = str(cwd or docs_dir())
    # Suppress the project's own pre-/post-render hooks (e.g. `qpyd prerender`,
    # `qpyd clean`) for these per-notebook renders: running them once per
    # notebook in parallel would race on shared files (objects.json) and be
    # hugely redundant. The hooks honour QPYD_SKIP_HOOKS and no-op.
    env = {**_AGG_ENV, "QPYD_SKIP_HOOKS": "1"}
    with sc.timer(label=sc.ansi.green(f"    Render time for {path.name}")) as T:
        try:
            print(f"Rendering {path.name}...")
            subprocess.run(
                ["quarto", "render", str(path)],
                check=True,
                capture_output=True,
                cwd=cwd,
                env=env,
                timeout=TIMEOUT,
            )
            string = f"{YAY} {path.stem} rendered successfully "
        except subprocess.CalledProcessError as e:
            err = (e.stderr or b"").decode(errors="ignore")
            string = f"{BOO} Render failed for {path.stem}:\n{err[-1500:]}\n"
        except Exception as e:
            string = f"{BOO} Error rendering {path.stem}: {e}\n"
    string += f"(time: {T.total:0.1f} s)"
    print(string)
    return string


def _parallel(func, notebooks, serial=False):
    """
    Run ``func(i, path)`` over ``notebooks`` in parallel.

    A small staggered delay between launches avoids thundering-herd startup
    contention (the original code found the ``interval`` arg unreliable, so the
    delay is applied inside the worker).
    """

    def worker(i, path, pause=1.0):
        if not serial:  # staggering only matters for parallel startup
            sc.timedsleep(i * pause)
        return func(path)

    notebook_list = list(enumerate(notebooks))
    return sc.parallelize(
        worker,
        notebook_list,
        maxcpu=0.9,
        interval=1.0,
        lbkwargs=dict(verbose=False),
        serial=serial,
    )


def _succeeded(res):
    """
    Classify a result string by its *leading* marker.

    Result strings always start with YAY or BOO, but failure strings also embed
    captured stderr, which can itself contain a YAY checkmark (✓). So we must
    anchor on the start of the string, not test substring membership.
    """
    return res.lstrip().startswith(YAY)


def _summarize(notebooks, results):
    """Print per-notebook results and a sorted pass/fail summary."""
    table = sc.objdict()
    for nb, res in zip(notebooks, results):
        table[str(nb)] = res

    sc.heading("Results")
    print(sc.strjoin(results, sep=f'\n\n\n{"—" * 90}\n'))

    sc.heading("Summary")
    n_yay = sum(_succeeded(res) for res in results)
    n_boo = len(results) - n_yay
    summary = f"{n_yay} succeeded, {n_boo} failed\n"

    table.sort("values")
    for nb, res in table.items():
        if "time: " in res:
            timestr = res.rsplit("time: ", 1)[-1].split(")")[0].strip()
        else:
            timestr = "?"
        suffix = f"{sc.path(nb).name:30s} ({timestr})"
        if _succeeded(res):
            summary += f'\n{sc.ansi.green("Succeeded")}: {suffix}'
        else:
            summary += f'\n{sc.ansi.red("   Failed")}: {suffix}'
    print(summary)
    return table


@sc.timer("Check notebooks")
def execute_notebooks(*paths, serial=False):
    """
    Execute notebooks in parallel to verify they run (no caches updated).

    Args:
        paths: notebook files or folders (default: the whole project).
        serial: run one at a time (useful for debugging).

    Returns an :class:`sciris.objdict` mapping notebook path -> result string.
    """
    notebooks = discover_notebooks(list(paths) or None)
    if not notebooks:
        print("No notebooks found.")
        return sc.objdict()
    if any(nb.suffix == ".ipynb" for nb in notebooks):
        require_tool("jupytext", _JUPYTEXT_HINT)
    sc.heading(f"Checking {len(notebooks)} notebooks (no cache update)...")
    results = _parallel(execute_notebook, notebooks, serial=serial)
    return _summarize(notebooks, results)


@sc.timer("Run notebooks")
def run_notebooks(*paths, serial=False):
    """
    Render notebooks in parallel, updating the Quarto freeze cache.

    Args:
        paths: notebook files or folders (default: the whole project).
        serial: render one at a time (useful for debugging or to avoid
            concurrent ``quarto render`` contention).

    Returns an :class:`sciris.objdict` mapping notebook path -> result string.
    """
    notebooks = discover_notebooks(list(paths) or None)
    if not notebooks:
        print("No notebooks found.")
        return sc.objdict()
    require_tool("quarto", _QUARTO_HINT)
    sc.heading(f"Running {len(notebooks)} notebooks (updating {FREEZE_DIR}/)...")
    results = _parallel(render_notebook, notebooks, serial=serial)
    return _summarize(notebooks, results)


def refresh_cache(dry_run=False):
    """
    Delete cached copies of notebooks so they re-execute on the next render.

    Removes the Quarto freeze cache (``_freeze/``) and every jupyter-cache
    (``.jupyter_cache/``) under the docs directory — with ``cache: true``,
    Quarto creates the jupyter cache next to each input document, so these can
    be nested in subfolders rather than only at the project root. Quarto's
    internal ``.quarto/`` working dir is left alone (it regenerates itself).

    Returns the list of removed paths. With ``dry_run`` set, nothing is deleted.
    Refuses to run outside a Quarto project.
    """
    root = project_root()
    if root is None:
        print("No _quarto.yml found; refusing to refresh outside a Quarto project.")
        return []

    targets = [root / FREEZE_DIR]
    targets += sorted(root.rglob(JUPYTER_CACHE_DIR))  # nested per-folder caches
    existing = sorted({t for t in targets if t.exists()})
    if not existing:
        print(f"No cached copies found ({FREEZE_DIR}/, {JUPYTER_CACHE_DIR}/).")
        return []
    for target in existing:
        verb = "Would delete" if dry_run else "Deleting"
        print(f"{verb}: {target}")
        if not dry_run:
            sc.rmpath(target, die=False)
    return existing
