"""
Wrappers around ``quarto render`` / ``quarto preview`` / ``quarto publish``.

Each of these optionally runs the pre-render build steps first (see
:mod:`.prerender`) and appends any ``_variables.py`` values as ``-M`` metadata
flags (see :mod:`.variables`).
"""

import subprocess
import time

import sciris as sc

from .variables import variable_args


def run(cmd, **kwargs):
    """
    Verbose ``subprocess.run`` that echoes the command first and raises on
    failure.

    ``cmd`` may be a string (run via the shell) or a list of arguments. A
    missing executable is reported with an actionable message rather than a
    bare ``FileNotFoundError`` traceback.
    """
    shell = isinstance(cmd, str)
    shown = cmd if shell else sc.strjoin(cmd, sep=" ")
    sc.printgreen(f"\n> {shown}\n")
    try:
        return subprocess.run(cmd, check=True, shell=shell, **kwargs)
    except FileNotFoundError as e:
        tool = cmd.split()[0] if shell else cmd[0]
        hint = (
            "Install Quarto from https://quarto.org and ensure it is on your PATH."
            if tool == "quarto"
            else f"Ensure {tool!r} is installed and on your PATH."
        )
        raise RuntimeError(f"Required tool {tool!r} was not found. {hint}") from e


def _maybe_prerender(do_prerender):
    if do_prerender:
        from .prerender import prerender

        prerender()


def render(extra_args=(), do_prerender=True):
    """
    Run the pre-render steps, then ``quarto render``, reporting elapsed time.

    Args:
        extra_args: extra arguments passed through to ``quarto render``.
        do_prerender: run :func:`.prerender.prerender` first (default True).
    """
    t0 = time.time()
    _maybe_prerender(do_prerender)
    run(["quarto", "render", *extra_args, *variable_args()])
    elapsed = time.time() - t0
    print(f"\nDone: docs built in {elapsed:0.1f} s")


def preview(extra_args=(), do_prerender=True):
    """
    Run the pre-render steps, then ``quarto preview`` (live-reloading server).

    Args:
        extra_args: extra arguments passed through to ``quarto preview``.
        do_prerender: run :func:`.prerender.prerender` first (default True).
    """
    _maybe_prerender(do_prerender)
    run(["quarto", "preview", *extra_args, *variable_args()])


def gh_publish(do_prerender=True):
    """
    Render and publish the site to GitHub Pages (the ``gh-pages`` branch).

    Mirrors the original ``publish`` script: a full ``quarto render
    --cache-refresh`` followed by ``quarto publish gh-pages --no-render``. This
    pushes to a remote branch, so it is intentionally never run automatically.
    """
    _maybe_prerender(do_prerender)
    run(["quarto", "render", "--cache-refresh", *variable_args()])
    run(["quarto", "publish", "gh-pages", "--no-render", "--no-prompt", "--no-browser"])
