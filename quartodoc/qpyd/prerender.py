"""
Pre-render build steps (the ``pre-render`` hook).

Generalised from the ``pre`` branch of the original ``quarto_utils.py``:

* :func:`build_api_docs` — ``quartodoc build``
* :func:`customize_aliases` — add short aliases to ``objects.json``
* :func:`build_interlinks` — ``quartodoc interlinks``
* :func:`build_objects_inv` — write a Sphinx-compatible ``objects.inv``

The package name is read from the ``quartodoc.package`` key in ``_quarto.yml``
rather than hard-coded. The original starsim-specific ``update_version`` step
is intentionally dropped; version injection is now handled generically by
``_variables.py`` (see :mod:`.variables`).
"""

import importlib
import sys
from pathlib import Path

import sciris as sc

from .config import get_package_name
from .render import run


@sc.timer("Build API docs")
def build_api_docs():
    """Generate the API reference pages via ``quartodoc build``."""
    sc.heading("Building API documentation...")
    return run([sys.executable, "-m", "quartodoc", "build"])


@sc.timer("Customize aliases")
def customize_aliases(mod_name=None, json_path="objects.json"):
    """
    Add short aliases to the objects inventory.

    For each ``pkg.submodule.Object`` that is also importable directly as
    ``pkg.Object``, register the shorter ``pkg.Object`` name so cross-references
    can use it. The package name defaults to ``quartodoc.package`` from
    ``_quarto.yml``.
    """
    mod_name = mod_name or get_package_name()
    if not mod_name:
        print("  No quartodoc.package configured; skipping alias customization.")
        return
    if not Path(json_path).exists():
        print(f"  {json_path} not found; skipping alias customization.")
        return

    sc.heading("Customizing aliases ...")
    try:
        mod = importlib.import_module(mod_name)
    except ImportError as e:
        print(f"  Could not import {mod_name!r} ({e}); skipping alias customization.")
        return
    mod_items = dir(mod)

    data = sc.loadjson(json_path)
    items = data["items"]
    names = [item["name"] for item in items]
    print(f'  Loaded {len(data["items"])} items')

    dups = []
    for item in items:
        parts = item["name"].split(".")
        if len(parts) < 3 or parts[0] != mod_name:
            continue
        objname = parts[2]  # e.g. 'Analyzer' from starsim.analyzers.Analyzer
        if objname in mod_items:
            remainder = ".".join(parts[2:])
            alias = f"{mod_name}.{remainder}"
            if alias not in names:
                dup = sc.dcp(item)
                dup["name"] = alias
                dups.append(dup)

    items.extend(dups)
    sc.savejson(json_path, data)
    print(f'  Saved {len(data["items"])} items')


@sc.timer("Build interlinks")
def build_interlinks():
    """Generate interlink inventories via ``quartodoc interlinks``."""
    sc.heading("Building docs links...")
    return run([sys.executable, "-m", "quartodoc", "interlinks"])


@sc.timer("Build objects.inv")
def build_objects_inv(json_path="objects.json", inv_path="objects.inv"):
    """
    Convert the quartodoc JSON inventory into a Sphinx-compatible
    ``objects.inv`` so other projects can resolve references via intersphinx.
    """
    import sphobjinv as soi

    if not Path(json_path).exists():
        print(f"  {json_path} not found; skipping objects.inv.")
        return

    sc.heading("Building Sphinx objects.inv ...")
    data = sc.loadjson(json_path)
    inv = soi.Inventory()
    inv.project = data.get("project", get_package_name(default="project"))
    inv.version = str(data.get("version", "0.0.0"))
    for item in data["items"]:
        inv.objects.append(
            soi.DataObjStr(
                name=item["name"],
                domain=item["domain"],
                role=item["role"],
                priority=str(item.get("priority", "1")),
                uri=item["uri"],
                dispname=item.get("dispname", "-") or "-",
            )
        )
    with open(inv_path, "wb") as f:
        f.write(soi.compress(inv.data_file()))
    print(f"  Wrote {len(inv.objects)} entries to {inv_path}")


@sc.timer("Pre-render")
def prerender():
    """Run all pre-render build steps in order.

    No-ops when ``QPYD_SKIP_HOOKS`` is set, which ``qpynb run`` does for its
    per-notebook ``quarto render`` calls — otherwise this heavy, shared-state
    build (rewriting ``objects.json``) would run once per notebook in parallel
    and race with itself.
    """
    import os

    if os.environ.get("QPYD_SKIP_HOOKS"):
        return
    sc.heading("Starting Quarto docs build", divider="★")
    build_api_docs()
    customize_aliases()
    build_interlinks()
    build_objects_inv()
