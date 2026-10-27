"""
Pre-render build steps (the ``pre-render`` hook).

Generalised from the ``pre`` branch of the original ``quarto_utils.py``:

* :func:`build_api_docs` — ``quartodoc build``
* :func:`customize_aliases` — add short aliases to ``objects.json``
* :func:`build_interlinks` — ``quartodoc interlinks`` (only if there are
  external interlink sources)
* :func:`build_objects_inv` — write a Sphinx-compatible ``objects.inv``
* any project-specific commands from ``qpyd.prerender.commands``

The package name is read from the ``quartodoc.package`` key in ``_quarto.yml``
rather than hard-coded. Version injection is handled generically by
``_variables.py`` (see :mod:`.variables`), which is written to
``_variables.yml`` first.

Since these steps only depend on the package source, quartodoc and the docs
config, they are skipped when none of those changed since the last build (see
:func:`prerender_up_to_date`).
"""

import hashlib
import importlib
import importlib.metadata
import importlib.util
import json
import os
import sys
from pathlib import Path

import sciris as sc

from .config import (
    CONFIG_NAME,
    VARIABLES_PY,
    as_list,
    docs_dir,
    get_package_name,
    hook_skip_reason,
    load_quarto_config,
    qpyd_config,
)
from .render import run
from .variables import write_variables_yml

# Where the hash of the inputs to the last successful build is kept
STATE_FILE = ".quarto/qpyd-prerender.json"

# Default output folder of `quartodoc build` (the quartodoc.dir key)
DEFAULT_API_DIR = "reference"


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


def has_external_interlinks(start=None):
    """
    Whether ``_quarto.yml`` lists any interlink sources besides the project's
    own docs (otherwise ``quartodoc interlinks`` has nothing to fetch).
    """
    data, _ = load_quarto_config(start)
    sources = (data.get("interlinks") or {}).get("sources") or {}
    return any((src or {}).get("url") != "/" for src in sources.values())


@sc.timer("Build interlinks")
def build_interlinks():
    """Generate interlink inventories via ``quartodoc interlinks``."""
    sc.heading("Building docs links...")
    return run([sys.executable, "-m", "quartodoc", "interlinks"])


def _package_version(package):
    """Installed version of ``package``, or ``None`` if it can't be found."""
    if not package:
        return None
    try:
        return importlib.metadata.version(package)
    except importlib.metadata.PackageNotFoundError:
        return None


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
    package = get_package_name()
    data = sc.loadjson(json_path)
    inv = soi.Inventory()
    inv.project = data.get("project", package or "project")
    inv.version = str(data.get("version") or _package_version(package) or "0.0.0")
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


def prerender_config(start=None):
    """
    The ``qpyd.prerender`` settings, as lists:

    * ``commands``: extra shell commands to run (in the docs dir) after the
      standard steps, e.g. ``python make_api.py``
    * ``inputs``: extra files (or globs, relative to the docs dir) the build
      depends on, e.g. the scripts those commands run
    * ``outputs``: extra files the build creates, so it reruns if they go missing
    """
    cfg = qpyd_config(start).get("prerender") or {}
    return {key: as_list(cfg.get(key)) for key in ["commands", "inputs", "outputs"]}


def _module_files(name):
    """The source files of an importable module or package (without importing it)."""
    try:
        spec = importlib.util.find_spec(name)
    except (ImportError, ValueError):
        spec = None
    if spec is None:
        return []
    if spec.submodule_search_locations:
        files = []
        for location in spec.submodule_search_locations:
            for suffix in ("*.py", "*.pyi"):
                files += Path(location).rglob(suffix)
        return sorted(files)
    return [Path(spec.origin)] if spec.origin and os.path.exists(spec.origin) else []


def prerender_inputs(start=None):
    """
    Every file the pre-render build depends on: ``_quarto.yml``, the documented
    package's source, quartodoc's own source, and ``qpyd.prerender.inputs``.
    """
    root = docs_dir(start)
    files = [root / CONFIG_NAME]
    for pattern in prerender_config(start)["inputs"]:
        files += sorted(root.glob(pattern))
    package = get_package_name(start)
    if package:
        files += _module_files(package)
    files += _module_files("quartodoc")
    return [f for f in files if f.is_file()]


def prerender_outputs(start=None):
    """The files and folders the pre-render build creates."""
    data, _ = load_quarto_config(start)
    api_dir = (data.get("quartodoc") or {}).get("dir", DEFAULT_API_DIR)
    outputs = ["objects.json", "objects.inv", api_dir]
    outputs += prerender_config(start)["outputs"]
    return [docs_dir(start) / f for f in outputs]


def prerender_hash(start=None):
    """Hash of the contents (and paths) of :func:`prerender_inputs`."""
    md5 = hashlib.md5()
    for path in prerender_inputs(start):
        md5.update(str(path).encode())
        md5.update(path.read_bytes())
    return md5.hexdigest()


def prerender_up_to_date(start=None):
    """
    Whether the outputs of the last build exist and its inputs haven't changed.
    """
    state_file = docs_dir(start) / STATE_FILE
    if not state_file.exists():
        return False
    if not all(path.exists() for path in prerender_outputs(start)):
        return False
    try:
        state = json.loads(state_file.read_text())
    except (OSError, ValueError):
        return False
    return state.get("hash") == prerender_hash(start)


def _save_state(build_hash, start=None):
    state_file = docs_dir(start) / STATE_FILE
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text(json.dumps({"hash": build_hash}))


@sc.timer("Pre-render")
def prerender(force=False):
    """Run all pre-render build steps in order.

    Skipped when run as a Quarto hook for a render of selected pages, and when
    ``QPYD_SKIP_HOOKS`` is set, which ``qpynb run`` does for its per-notebook
    ``quarto render`` calls (see :func:`.config.hook_skip_reason`).

    The API build itself is skipped if its inputs haven't changed since the last
    build, unless ``force`` is set (or ``QPYD_FORCE_PRERENDER=1``).
    """
    reason = hook_skip_reason()
    if reason:
        print(f"qpyd prerender: {reason}, so skipping the pre-render steps")
        return

    if write_variables_yml():
        print(f"Updated _variables.yml from {VARIABLES_PY}")

    force = force or bool(os.environ.get("QPYD_FORCE_PRERENDER"))
    build_hash = prerender_hash()
    if not force and prerender_up_to_date():
        print(
            "qpyd prerender: the package, quartodoc and the docs config are unchanged, "
            "so not rebuilding the API docs (use --force to rebuild)"
        )
        return

    sc.heading("Starting Quarto docs build", divider="★")
    build_api_docs()
    customize_aliases()
    if has_external_interlinks():
        build_interlinks()
    build_objects_inv()
    for command in prerender_config()["commands"]:
        run(command, cwd=str(docs_dir()))
    _save_state(build_hash)
