# qpyd

A CLI for building [Quarto](https://quarto.org)-based Python API documentation
with quartodoc. It bundles the docs workflow (render / preview / publish /
scaffold) and parallel notebook management into two console scripts:

- **`qpyd`** — build, render, preview, publish, and scaffold a docs site
- **`qpynb`** — manage notebooks (`.qmd` / `.ipynb`); also available as `qpyd nb …`

It generalizes the starsim `docs/quarto_utils.py` workflow (kept verbatim as
[`quarto_utils.py`](quarto_utils.py) for reference). Built on `sciris`,
`jupytext`, `nbformat`, and the external `quarto` binary.

## Commands

### `qpyd`

| Command | Description |
|---|---|
| `qpyd prerender` | Build the pre-render artifacts: API docs (`quartodoc build`), alias customization, interlinks, and a Sphinx `objects.inv`. |
| `qpyd render [quarto args]` | Run `prerender`, then `quarto render` (with timing). Extra args pass through to Quarto. |
| `qpyd preview [quarto args]` | Run `prerender`, then `quarto preview` (live reload). |
| `qpyd gh-publish` | `quarto render --cache-refresh` then `quarto publish gh-pages`. **Publishes to a remote branch.** |
| `qpyd init [path] [--package NAME]` | Scaffold a docs folder with a starter `_quarto.yml`, `index.qmd`, and `_variables.py` (never overwrites existing files). |
| `qpyd clean [--dry-run]` | Delete generated scratch files matching the `qpyd.clean` config patterns (opt-in; never deletes source files). |
| `qpyd nb …` | Alias for `qpynb …`. |

`render` / `preview` / `gh-publish` accept `--no-prerender` to skip the build steps.

### `qpynb`

| Command | Description |
|---|---|
| `qpynb run [paths] [--serial]` | Execute notebooks **in parallel** via `quarto render`, updating the `_freeze/` cache. |
| `qpynb check [paths] [--serial]` | Execute notebooks **in parallel** to verify they run; touches no caches and leaves no artifacts. |
| `qpynb refresh [--dry-run]` | Delete cached copies (`_freeze/` and all nested `.jupyter_cache/`) so notebooks re-execute. |
| `qpynb to-py / to-qmd / to-ipynb PATH [--force]` | Convert between notebook formats. Won't overwrite an existing destination without `--force`. |
| `qpynb clear [paths] [--dry-run]` | Strip saved outputs from `.ipynb` notebooks and normalize them. |

`paths` may be individual notebooks or folders; omit them to act on the whole
project. A notebook is a `.ipynb`, or a `.qmd` containing a `{python}` cell.

## `run` vs `check` and the cache

"Cached copies" are Quarto's freeze cache (`_freeze/`), the project-level,
commit-friendly mechanism that lets `quarto render` skip re-execution
(`freeze: auto`). `qpynb run` pre-bakes that cache in parallel so a later full
site render is fast; `qpynb check` is a pure validation pass that never writes
it. During `run`, each per-notebook render runs with `QPYD_SKIP_HOOKS=1`, so a
project `pre-render: qpyd prerender` / `post-render: qpyd clean` hook no-ops
instead of running redundantly (and racing) once per notebook.

## `_variables.py`

An optional file alongside `_quarto.yml`. Public, non-callable,
YAML-serializable names defined in it are passed to `quarto render` as
`-M key:value` metadata (YAML-encoded, so strings like `"1.10"` stay strings):

```python
import starsim as ss
version = ss.__version__
versiondate = ss.__versiondate__
```

## Relevant `_quarto.yml` keys

```yaml
project:
  pre-render: qpyd prerender
  # post-render: qpyd clean   # optional, opt-in
quartodoc:
  package: your_package       # read by prerender for aliases / objects.inv
qpyd:
  clean:                      # optional glob patterns for `qpyd clean`
    - '**/my-*.png'           # source files (.qmd/.ipynb/.py/.md) are never deleted
execute:
  freeze: auto
```
