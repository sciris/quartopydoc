"""
quartopydoc is a package for building delightful python API documentation.

It is a fork of quartodoc by Michael Chow, with formatting customizations and
extra utilities for working with notebooks.
"""

# flake8: noqa

import importlib
from typing import TYPE_CHECKING

from .metadata import get_attr, get_version

if TYPE_CHECKING:  # so static analysis (type checkers, griffe) sees the lazy names
    from .autosummary import get_function, get_object, Builder
    from .autosummary import BuilderPkgdown, BuilderSinglePage
    from .renderers import MdRenderer
    from .inventory import convert_inventory, create_inventory
    from .ast import preview
    from .builder.blueprint import blueprint
    from .builder.collect import collect
    from .layout import Auto

# The rest of the API is imported on first use: importing it all (griffe, the
# builder, the renderers) takes most of a second, which every `qpyd` command,
# and so every docs build, would otherwise pay even when it doesn't need them
_lazy = {
    "get_function": ".autosummary",
    "get_object": ".autosummary",
    "Builder": ".autosummary",
    "BuilderPkgdown": ".autosummary",
    "BuilderSinglePage": ".autosummary",
    "MdRenderer": ".renderers",
    "convert_inventory": ".inventory",
    "create_inventory": ".inventory",
    "preview": ".ast",
    "blueprint": ".builder.blueprint",
    "collect": ".builder.collect",
    "Auto": ".layout",
}


def __getattr__(name):
    if name in _lazy:
        value = getattr(importlib.import_module(_lazy[name], __name__), name)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__():
    return sorted([*globals(), *_lazy])


__all__ = (
    "Auto",
    "blueprint",
    "collect",
    "convert_inventory",
    "create_inventory",
    "get_attr",
    "get_function",
    "get_object",
    "get_version",
    "preview",
    "Builder",
    "BuilderPkgdown",
    "BuilderSinglePage",
    "MdRenderer",
)
