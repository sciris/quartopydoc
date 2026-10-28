"""
Docs variables, for Quarto's ``var`` shortcode (``{{< var version >}}``).

They can be declared in the ``qpyd.variables`` section of ``_quarto.yml``::

    qpyd:
      variables:
        version: {attr: __version__}         # read from the package's source
        versiondate: {attr: __versiondate__}
        license: MIT                         # any other value is used as is

or computed in an optional ``_variables.py`` file alongside ``_quarto.yml``::

    import quartodoc as qd

    version = qd.get_version()
    versiondate = qd.get_attr("__versiondate__")

``qpyd prerender`` writes them to ``_variables.yml`` (see
:func:`write_variables_yml`), so they work however the site is rendered. If a
name is in both, ``_variables.py`` wins.
"""

import runpy
import types
import warnings
from pathlib import Path

import yaml

from .config import VARIABLES_PY, docs_dir, load_quarto_config

VARIABLES_YML = "_variables.yml"


def _serializable(value):
    try:
        yaml.safe_dump(value)
        return True
    except yaml.YAMLError:
        return False


def load_variables(path=None):
    """
    Execute ``_variables.py`` and return the values it exports.

    Args:
        path: path to the variables file (default: ``_variables.py`` in the
            docs dir). If it does not exist, an empty dict is returned.

    Returns a ``{name: value}`` dict. If the file defines ``__all__``, exactly
    those names are exported. Otherwise every name is, except those beginning
    with ``_``, modules, and callables (functions and classes). A value that
    can't be written to YAML is skipped with a warning, as is a name in
    ``__all__`` that isn't defined.

    Note: this executes ``_variables.py``, just like a ``conftest.py``. Only
    run it on files you trust.
    """
    if path is None:
        path = docs_dir() / VARIABLES_PY
    path = Path(path)
    if not path.exists():
        return {}

    namespace = runpy.run_path(str(path))

    if "__all__" in namespace:
        names = list(namespace["__all__"])
    else:
        names = [
            key for key, value in namespace.items()
            if not key.startswith("_")
            and not isinstance(value, types.ModuleType)
            and not callable(value)
        ]

    variables = {}
    for key in names:
        if key not in namespace:
            warnings.warn(f"{path.name}: {key!r} is in __all__ but not defined, so skipping it")
        elif not _serializable(namespace[key]):
            value = namespace[key]
            warnings.warn(
                f"{path.name}: {key} is a {type(value).__name__}, which can't be "
                "written to YAML, so skipping it (convert it to a str, int, list, ...)"
            )
        else:
            variables[key] = namespace[key]
    return variables


def config_variables(start=None):
    """
    Return the variables declared in the ``qpyd.variables`` section of ``_quarto.yml``.

    A value of the form ``{attr: NAME}`` is read from the documented package's
    source with :func:`quartodoc.get_attr` (or :func:`quartodoc.get_version` for
    ``__version__``), without importing it; a dotted ``NAME`` says which package
    or module to read, e.g. ``{attr: sciris.__version__}``. Any other value is
    used as is.
    """
    from ..metadata import get_attr, get_version

    data, _ = load_quarto_config(start)
    declared = (data.get("qpyd") or {}).get("variables") or {}
    package = (data.get("quartodoc") or {}).get("package")

    variables = {}
    for key, value in declared.items():
        if isinstance(value, dict) and set(value) == {"attr"}:
            name = value["attr"]
            module, _, attr = name.rpartition(".")
            if attr == "__version__":
                value = get_version(module or package)
            else:
                value = get_attr(name, package=package)
        variables[key] = value
    return variables


def write_variables_yml(path=None, yml_path=None):
    """
    Write the variables from ``qpyd.variables`` in ``_quarto.yml`` and from
    ``_variables.py`` into ``_variables.yml``, so they can be used with Quarto's
    ``var`` shortcode (``{{< var version >}}``) however the site is rendered.

    Args:
        path: path to ``_variables.py`` (default: the one in the docs dir); its
            folder is also where ``_quarto.yml`` is looked for
        yml_path: path to ``_variables.yml`` (default: alongside ``path``)

    Does nothing if there are no variables. Other keys already in
    ``_variables.yml`` are kept, and the file is only rewritten if a value
    changed (so it doesn't look modified to git or Quarto).

    Returns the variables written, or ``None`` if the file was left as is.
    """
    folder = Path(path).parent if path else docs_dir()
    variables = {**config_variables(folder), **load_variables(path)}
    if not variables:
        return None
    if yml_path is None:
        yml_path = folder / VARIABLES_YML
    yml_path = Path(yml_path)
    existing = {}
    if yml_path.exists():
        existing = yaml.safe_load(yml_path.read_text()) or {}
    updated = {**existing, **variables}
    if updated == existing:
        return None
    yml_path.write_text(yaml.safe_dump(updated, sort_keys=False))
    return variables
