"""
qpyd — a CLI for building Quarto-based Python API documentation with quartodoc.

Two console scripts are exposed (see ``[project.scripts]`` in pyproject.toml):

* ``qpyd``  -> :data:`cli`    — build / render / preview / publish / init
* ``qpynb`` -> :data:`nb_cli` — notebook management (also available as ``qpyd nb``)

Both are re-exported here so the entry points stay stable as internal modules
are added or moved.
"""

from .cli import cli
from .nb import nb_cli

__all__ = ["cli", "nb_cli"]
