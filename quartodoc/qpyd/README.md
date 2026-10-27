# qpyd

A CLI for building [Quarto](https://quarto.org)-based Python API documentation
with quartodoc. It bundles the docs workflow (render / preview / publish /
scaffold) and parallel notebook management into two console scripts:

- **`qpyd`** — build, render, preview, publish, and scaffold a docs site
- **`qpynb`** — manage notebooks (`.qmd` / `.ipynb`); also available as `qpyd nb …`

It generalizes the docs workflow of [Starsim](https://github.com/starsimhub/starsim)
(its former `docs/quarto_utils.py`). Built on `sciris`, `jupytext`, `nbformat`,
and the external `quarto` binary.

## Commands

### `qpyd`

| Command | Description |
|---|---|
| `qpyd prerender [--force]` | Build the pre-render artifacts: API docs (`quartodoc build`), alias customization, interlinks (if there are external sources), a Sphinx `objects.inv`, and any `qpyd.prerender.commands`. Skipped if nothing it depends on changed since the last build. |
| `qpyd render [quarto args]` | Run `prerender`, then `quarto render` (with timing). Extra args pass through to Quarto. |
| `qpyd preview [quarto args]` | Run `prerender`, then `quarto preview` (live reload). |
| `qpyd gh-publish` | `quarto render --cache-refresh` then `quarto publish gh-pages`. **Publishes to a remote branch.** |
| `qpyd init [path] [--package NAME]` | Scaffold a docs folder with a starter `_quarto.yml`, `index.qmd`, and `_variables.py` (never overwrites existing files). |
| `qpyd clean [--dry-run]` | Delete generated scratch files and folders matching the `qpyd.clean` config patterns (opt-in; never deletes source files, or folders containing any). |
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
instead of running redundantly (and racing) once per notebook. The hooks also
no-op when Quarto renders only some pages (`quarto render page.qmd`), so those
renders stay fast.

## `_variables.py`

An optional file alongside `_quarto.yml`. Public, non-callable,
YAML-serializable names defined in it are passed to `quarto render` as
`-M key:value` metadata (YAML-encoded, so strings like `"1.10"` stay strings),
and `qpyd prerender` writes them to `_variables.yml`, so `{{< var version >}}`
works however the site is rendered:

```python
import quartodoc as qd
version = qd.get_version()                    # read without importing the package
versiondate = qd.get_attr("__versiondate__")  # any literal module-level constant
```

## Relevant `_quarto.yml` keys

```yaml
project:
  pre-render: qpyd prerender
  # post-render: qpyd clean   # optional, opt-in
quartodoc:
  package: your_package       # read by prerender for aliases / objects.inv
qpyd:
  prerender:                  # optional project-specific pre-render steps
    commands: [python make_index.py]  # run after the standard steps
    inputs: [make_index.py]   # extra files the build depends on
    outputs: [index.json]     # extra files it creates
  clean:                      # optional glob patterns for `qpyd clean`
    - '**/my-*.png'           # source files (.qmd/.ipynb/.py/.md) are never deleted
execute:
  freeze: auto
```
