"""
Support for an optional ``_variables.py`` file living alongside ``_quarto.yml``.

The file defines plain Python values (often derived from the documented
package), for example::

    import starsim as ss

    version = ss.__version__
    versiondate = ss.__versiondate__

These are collected into a dict (skipping private names, callables, and
anything that is not YAML-serialisable) and turned into ``quarto render``
metadata flags (``-M key:value``) so they can be referenced in documents.
"""

import runpy
from pathlib import Path

import yaml

from .config import VARIABLES_PY, docs_dir


def load_variables(path=None):
    """
    Execute ``_variables.py`` and return the public, serialisable values.

    Args:
        path: path to the variables file (default: ``_variables.py`` in the
            docs dir). If it does not exist, an empty dict is returned.

    Returns a ``{name: value}`` dict. Names beginning with ``_``, callables,
    and values that cannot be safely dumped to YAML are skipped.

    Note: this executes ``_variables.py``, just like a ``conftest.py``. Only
    run it on files you trust.
    """
    if path is None:
        path = docs_dir() / VARIABLES_PY
    path = Path(path)
    if not path.exists():
        return {}

    namespace = runpy.run_path(str(path))

    variables = {}
    for key, value in namespace.items():
        if key.startswith("_"):
            continue
        if callable(value):
            continue
        try:
            yaml.safe_dump({key: value})
        except Exception:
            continue
        variables[key] = value
    return variables


def _yaml_scalar(value):
    """
    Render a Python value as a single-line YAML scalar.

    This keeps the ``-M`` payload valid YAML so Quarto parses it as the intended
    type: ``True`` -> ``true``, ``None`` -> ``null``, ``"2026"`` -> ``'2026'``
    (a quoted string, not the int 2026), ``[1, 2]`` -> ``[1, 2]``. Using plain
    ``str()`` would emit Python casing (``True``/``None``) that YAML mis-parses.
    """
    return yaml.safe_dump(value, default_flow_style=True).splitlines()[0]


def variables_to_args(variables):
    """
    Convert a ``{name: value}`` dict into a flat ``quarto render`` arg list.

    For example ``{"version": "1.2"}`` becomes ``["-M", "version:1.2"]``. Each
    pair is a separate ``argv`` element, so no shell quoting is required even
    for values containing spaces. Values are encoded as YAML scalars (see
    :func:`_yaml_scalar`) so non-string types round-trip correctly.
    """
    args = []
    for key, value in variables.items():
        args += ["-M", f"{key}:{_yaml_scalar(value)}"]
    return args


def variable_args(path=None):
    """Convenience wrapper: load ``_variables.py`` and return its ``-M`` args."""
    return variables_to_args(load_variables(path))
