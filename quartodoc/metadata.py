"""
Read a package's version (and other module-level constants) without importing it.

These are meant for a docs site's ``_variables.py`` (see :mod:`quartodoc.qpyd.variables`),
which runs on every render, so importing a large package there would make every
build slower::

    import quartodoc as qd

    version = qd.get_version()  # the package in quartodoc.package of _quarto.yml
    versiondate = qd.get_attr("__versiondate__")
"""

import ast
import json
import re
import importlib.metadata
import importlib.util
from pathlib import Path

__all__ = ["get_attr", "get_version"]

# Where a package usually keeps its version and similar constants, in the order
# they are searched (the package's own __init__.py comes last)
VERSION_MODULES = ["version", "_version", "__version__", "__about__"]

_missing = object()


def _default_package():
    from .qpyd.config import get_package_name

    package = get_package_name()
    if not package:
        raise ValueError(
            "No package given, and there is no quartodoc.package in _quarto.yml"
        )
    return package


def _source_file(module):
    """
    The source file of a module (e.g. ``starsim.version``), found without
    importing it or its parent packages, or ``None`` if there isn't one.
    """
    top, *rest = module.split(".")
    try:
        spec = importlib.util.find_spec(top)
    except (ImportError, ValueError):
        return None
    if spec is None:
        return None
    if not rest:
        return Path(spec.origin) if spec.origin and spec.has_location else None
    for location in spec.submodule_search_locations or []:
        base = Path(location).joinpath(*rest)
        for path in [base.with_suffix(".py"), base / "__init__.py"]:
            if path.is_file():
                return path
    return None


def _read_constant(path, name):
    """
    The value last assigned to ``name`` at the top level of ``path``, which must
    be a literal. Returns ``_missing`` if ``name`` isn't assigned there.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    value = _missing
    for node in tree.body:
        if isinstance(node, ast.Assign):
            targets = node.targets
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            targets = [node.target]
        else:
            continue
        if any(isinstance(t, ast.Name) and t.id == name for t in targets):
            try:
                value = ast.literal_eval(node.value)
            except ValueError:
                raise ValueError(
                    f"{name} in {path} isn't a literal value (e.g. it is computed), "
                    f"so it can't be read without importing the package; import it instead"
                ) from None
    return value


def get_attr(name, package=None, default=_missing):
    """
    Read a module-level constant of a package from its source, without importing it.

    Args:
        name: the constant, e.g. ``"__versiondate__"``. A dotted name says which
            module to read it from, e.g. ``"starsim.version.__versiondate__"``.
        package: the package to look in (default: ``quartodoc.package`` from
            ``_quarto.yml``). Its ``version.py``, ``_version.py``,
            ``__version__.py``, ``__about__.py`` and ``__init__.py`` are searched,
            in that order.
        default: returned if the constant isn't found (otherwise ``AttributeError``
            is raised)

    The value must be a literal (a string, number, tuple, list, dict, ...); one
    that is computed (e.g. an f-string) raises ``ValueError``.

    **Example**::

        versiondate = qd.get_attr("__versiondate__")
    """
    if "." in name:
        module, name = name.rsplit(".", 1)
        modules = [module]
    else:
        package = package or _default_package()
        modules = [f"{package}.{m}" for m in VERSION_MODULES] + [package]

    for module in modules:
        path = _source_file(module)
        if path is not None:
            value = _read_constant(path, name)
            if value is not _missing:
                return value

    if default is not _missing:
        return default
    raise AttributeError(f"Could not find {name} in {', '.join(modules)}")


def get_version(package=None):
    """
    The version of a package, found without importing it.

    The ``__version__`` in the package's source wins, since that is current even
    for an editable install whose recorded version is out of date; if there is
    none (or it is computed), the installed distribution's version is used (e.g.
    for versions from git tags).

    Args:
        package: the package (default: ``quartodoc.package`` from ``_quarto.yml``)

    **Example**::

        version = qd.get_version()
    """
    package = package or _default_package()
    try:
        version = get_attr("__version__", package=package, default=None)
    except ValueError:  # computed, e.g. from importlib.metadata
        version = None
    if version is not None:
        return str(version)

    dist = _distribution(package.split(".")[0])
    if dist is None:
        raise LookupError(f"Could not find the version of {package}")
    return dist.version


def _normalize(name):
    """A distribution name in its normalized form (PEP 503)."""
    return re.sub(r"[-_.]+", "-", name).lower()


def _distribution(top):
    """
    The installed distribution that provides the importable package ``top``.

    Usually there is one, but several can claim the same package (e.g. a stale
    install, or a leftover ``.egg-info`` folder from a project that was later
    renamed), so prefer the one that the package is actually imported from: an
    editable install pointing at its folder, then one that lists its files.
    """
    names = {
        _normalize(name)
        for name in importlib.metadata.packages_distributions().get(top, [top])
    }
    # (not importlib.metadata.distribution(name), which only returns the first
    # one found on sys.path)
    dists = [
        dist
        for dist in importlib.metadata.distributions()
        if _normalize(dist.metadata["Name"] or "") in names
    ]
    if len(dists) <= 1:
        return dists[0] if dists else None

    source = _source_file(top)
    if source is None:
        return dists[0]
    source = source.resolve()
    for dist in dists:
        url = json.loads(dist.read_text("direct_url.json") or "{}").get("url", "")
        if url.startswith("file://") and source.is_relative_to(
            Path(url[len("file://") :]).resolve()
        ):
            return dist
    for dist in dists:
        for file in dist.files or []:
            if Path(dist.locate_file(file)).resolve() == source:
                return dist
    return dists[0]
