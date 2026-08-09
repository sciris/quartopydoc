"""
Removal of auto-generated temporary files (an optional ``post-render`` step).

This is intentionally **opt-in and conservative**. Unlike the original
starsim-specific ``clean_outputs()`` (which knew that ``tutorials/`` and
``user_guide/`` held only scratch output), a general-purpose tool cannot assume
which files are disposable. So:

* Patterns are read from the ``qpyd.clean`` key of ``_quarto.yml`` and default
  to **nothing** — running ``qpyd clean`` in an unconfigured project is a no-op.
* It refuses to run outside a real Quarto project (no cwd fallback).
* It never deletes notebook/source files (``.qmd``, ``.ipynb``, ``.py``,
  ``.md``), even if a configured pattern matches them.
"""

import os

import sciris as sc

from .config import _excluded, load_quarto_config, project_root

# File extensions that are (almost) always hand-authored source and must never
# be deleted by a glob-based cleanup, regardless of configured patterns.
PROTECTED_SUFFIXES = {".qmd", ".ipynb", ".py", ".md"}


def _clean_patterns():
    """Read ``qpyd.clean`` glob patterns from ``_quarto.yml`` (default: none)."""
    data, _ = load_quarto_config()
    qpyd_cfg = data.get("qpyd") or {}
    patterns = qpyd_cfg.get("clean") or []
    if isinstance(patterns, str):
        patterns = [patterns]
    return list(patterns)


def clean_outputs(patterns=None, dry_run=False):
    """
    Delete auto-generated temporary files within the docs directory.

    Args:
        patterns: glob patterns (relative to the docs dir) to remove. If
            omitted, patterns are read from the ``qpyd.clean`` config key, which
            defaults to an empty list (so cleaning is a no-op until configured).
        dry_run: if True, only print what *would* be removed.

    Returns the list of matched files. Refuses to run outside a Quarto project,
    skips build/hidden directories, and never deletes protected source files
    (see :data:`PROTECTED_SUFFIXES`).
    """
    if os.environ.get("QPYD_SKIP_HOOKS"):
        # We are running inside a per-notebook `quarto render` (see
        # execute.render_notebook); skip the project post-render cleanup.
        return []

    root = project_root()
    if root is None:
        print("No _quarto.yml found; refusing to clean outside a Quarto project.")
        return []

    patterns = patterns if patterns is not None else _clean_patterns()
    if not patterns:
        print(
            "No clean patterns configured. Set 'qpyd.clean' in _quarto.yml, e.g.:\n"
            "  qpyd:\n    clean:\n      - '**/my-*.png'"
        )
        return []

    matched = set()
    for pattern in patterns:
        for path in root.glob(pattern):
            if not path.is_file():
                continue
            if _excluded(path, root):
                continue
            if path.suffix.lower() in PROTECTED_SUFFIXES:
                print(f"Skipping protected source file: {path}")
                continue
            matched.add(path.resolve())

    files = sorted(matched)
    if not files:
        print("No temporary files to clean.")
        return []

    for path in files:
        verb = "Would delete" if dry_run else "Deleting"
        print(f"{verb}: {path}")
        if not dry_run:
            sc.rmpath(path, die=False)
    return files
