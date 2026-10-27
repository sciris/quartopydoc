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
  ``.md``), even if a configured pattern matches them; a pattern that matches a
  folder removes it only if it holds no such files.
"""

import shutil

import sciris as sc

from .config import _excluded, as_list, hook_skip_reason, project_root, qpyd_config

# File extensions that are (almost) always hand-authored source and must never
# be deleted by a glob-based cleanup, regardless of configured patterns.
PROTECTED_SUFFIXES = {".qmd", ".ipynb", ".py", ".md"}


def _clean_patterns():
    """Read ``qpyd.clean`` glob patterns from ``_quarto.yml`` (default: none)."""
    return as_list(qpyd_config().get("clean"))


def clean_outputs(patterns=None, dry_run=False):
    """
    Delete auto-generated temporary files (and folders) within the docs directory.

    Args:
        patterns: glob patterns (relative to the docs dir) to remove. If
            omitted, patterns are read from the ``qpyd.clean`` config key, which
            defaults to an empty list (so cleaning is a no-op until configured).
        dry_run: if True, only print what *would* be removed.

    Returns the list of matched paths. Refuses to run outside a Quarto project,
    skips build/hidden directories, and never deletes protected source files
    (see :data:`PROTECTED_SUFFIXES`), nor folders that contain any.

    As a ``post-render`` hook, it does nothing for renders of selected pages,
    or inside the per-notebook renders of ``qpynb run`` (see
    :func:`.config.hook_skip_reason`).
    """
    if hook_skip_reason():
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
            if _excluded(path, root):
                continue
            if path.is_dir():
                protected = [
                    p for p in path.rglob("*") if p.suffix.lower() in PROTECTED_SUFFIXES
                ]
                if protected:
                    print(f"Skipping folder with source files: {path}")
                    continue
            elif not path.is_file():
                continue
            elif path.suffix.lower() in PROTECTED_SUFFIXES:
                print(f"Skipping protected source file: {path}")
                continue
            matched.add(path.resolve())

    # a folder's own contents needn't be listed (or removed) separately
    files = sorted(p for p in matched if not any(d in matched for d in p.parents))
    if not files:
        print("No temporary files to clean.")
        return []

    for path in files:
        verb = "Would delete" if dry_run else "Deleting"
        print(f"{verb}: {path}")
        if not dry_run:
            if path.is_dir():
                shutil.rmtree(path, ignore_errors=True)
            else:
                sc.rmpath(path, die=False)
    return files
