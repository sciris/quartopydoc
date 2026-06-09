"""
``qpyd init``: scaffold a ``docs/`` folder with a starter ``_quarto.yml``.

Existing files are never overwritten, so running ``init`` in an established
project is safe and idempotent.
"""

from pathlib import Path

from .config import CONFIG_NAME, VARIABLES_PY

# Token-substituted rather than ``str.format``-ed to avoid escaping the many
# literal ``{{< ... >}}`` braces a Quarto config contains.
_QUARTO_YML = """\
project:
  type: website
  output-dir: _site
  pre-render: qpyd prerender
  # Optional cleanup of generated scratch files after rendering. Disabled by
  # default; enable by uncommenting and configuring the `qpyd.clean` patterns
  # below (only matching, non-source files are deleted).
  # post-render: qpyd clean

website:
  title: "__TITLE__"
  navbar:
    left:
      - href: index.qmd
        text: Home
      - href: api/index.qmd
        text: API reference
  sidebar:
    - id: api
      contents:
        - api/index.qmd

format:
  html:
    theme: cosmo
    toc: true

filters:
  - interlinks

interlinks:
  sources:
    python:
      url: https://docs.python.org/3/

quartodoc:
  package: __PACKAGE__
  title: API reference
  dir: api
  parser: google
  sections:
    - title: API reference
      desc: API documentation for __PACKAGE__.
      contents: []

# Optional: glob patterns for `qpyd clean` to delete after rendering. Source
# files (.qmd/.ipynb/.py/.md) are never deleted, even if matched.
# qpyd:
#   clean:
#     - '**/my-*.png'

execute:
  freeze: auto   # Only re-execute notebooks that have changed
  cache: true
  error: false   # Stop the build if a notebook errors
"""

_INDEX_QMD = """\
---
title: "__TITLE__"
---

Welcome to the __PACKAGE__ documentation.

See the [API reference](api/index.qmd) to get started.
"""

_VARIABLES_PY = '''\
"""
Optional variables made available to `quarto render` as `-M key:value` flags.

Public, YAML-serialisable, non-callable names defined here are passed through
by `qpyd render` / `qpyd preview`. For example:

    import __PACKAGE__
    version = __PACKAGE__.__version__
"""
'''


def _write_if_absent(path, content, created):
    if path.exists():
        print(f"  exists, leaving as-is: {path}")
        return
    path.write_text(content)
    created.append(path)
    print(f"  created: {path}")


def init(path="docs", package=None):
    """
    Create ``path`` (default ``docs/``) with a starter ``_quarto.yml``,
    ``index.qmd``, and ``_variables.py`` if they do not already exist.

    Args:
        path: directory to scaffold.
        package: package name to document. If omitted, the generated files use
            the literal ``your_package`` placeholder, which you should edit.

    Returns the list of files that were created.
    """
    docs = Path(path)
    docs.mkdir(parents=True, exist_ok=True)

    package = package or "your_package"
    title = package

    def fill(template):
        return template.replace("__PACKAGE__", package).replace("__TITLE__", title)

    created = []
    print(f"Initializing docs in {docs.resolve()} (package={package!r})")
    _write_if_absent(docs / CONFIG_NAME, fill(_QUARTO_YML), created)
    _write_if_absent(docs / "index.qmd", fill(_INDEX_QMD), created)
    _write_if_absent(docs / VARIABLES_PY, fill(_VARIABLES_PY), created)

    if not created:
        print("Nothing to do; all starter files already exist.")
    return created
