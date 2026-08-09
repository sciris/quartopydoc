# Overview


[![CI](https://github.com/sciris/quartopydoc/actions/workflows/ci.yml/badge.svg)](https://github.com/sciris/quartopydoc/actions/workflows/ci.yml)

**quartopydoc** lets you quickly generate Python package API reference documentation using Markdown and [Quarto](https://quarto.org). It is designed as an alternative to [Sphinx](https://www.sphinx-doc.org/en/master/).

quartopydoc is a fork of [quartodoc](https://github.com/machow/quartodoc), created by Michael Chow at Posit. Only the name of the distribution differs: you still import `quartodoc`, still run `quartodoc build`, and still configure a `quartodoc:` section in your `_quarto.yml`. For what the fork adds on top, see [differences from quartodoc](#differences-from-quartodoc).

Check out the below screencast for a walkthrough of creating a documentation site, or read on for instructions.

<p align="center">

<a href="https://www.loom.com/share/fb4eb736848e470b8409ba46b514e2ed">
<img src="https://cdn.loom.com/sessions/thumbnails/fb4eb736848e470b8409ba46b514e2ed-00001.gif" width="75%">
</a>
</p>

<br>

## Installation

``` bash
python -m pip install quartopydoc
```

or from GitHub

``` bash
python -m pip install git+https://github.com/sciris/quartopydoc.git
```

Note that the package is installed as `quartopydoc`, but imported as `quartodoc`.

> [!IMPORTANT]
>
> ### Install Quarto
>
> If you haven’t already, you’ll need to [install Quarto](https://quarto.org/docs/get-started/) before you can use quartodoc.

## Basic use

Getting started with quartodoc takes two steps: configuring quartodoc, then generating documentation pages for your library.

You can configure quartodoc alongside the rest of your Quarto site in the [`_quarto.yml`](https://quarto.org/docs/projects/quarto-projects.html) file you are already using for Quarto. To [configure quartodoc](https://sciris.github.io/quartopydoc/get-started/basic-docs.html#site-configuration), you need to add a `quartodoc` section to the top level your `_quarto.yml` file. Below is a minimal example of a configuration that documents the `quartodoc` package:

<!-- Starter Template -->

``` yaml
project:
  type: website

# tell quarto to read the generated sidebar
metadata-files:
  - reference/_sidebar.yml

# tell quarto to read the generated styles
format:
  html:
    css:
      - reference/_styles-quartodoc.css

quartodoc:
  # the name used to import the package you want to create reference docs for
  package: quartodoc

  # write sidebar and style data
  sidebar: reference/_sidebar.yml
  css: reference/_styles-quartodoc.css

  sections:
    - title: Some functions
      desc: Functions to inspect docstrings.
      contents:
        # the functions being documented in the package.
        # you can refer to anything: class methods, modules, etc..
        - get_object
        - preview
```

Now that you have configured quartodoc, you can generate the reference API docs with the following command:

``` bash
quartodoc build
```

This will create a `reference/` directory with an `index.qmd` and documentation pages for listed functions, like `get_object` and `preview`.

Finally, preview your website with quarto:

``` bash
quarto preview
```

## Rebuilding site

You can preview your `quartodoc` site using the following commands:

First, watch for changes to the library you are documenting so that your docs will automatically re-generate:

``` bash
quartodoc build --watch
```

Second, preview your site:

``` bash
quarto preview
```

## Looking up objects

Generating API reference docs for Python objects involves two pieces of configuration:

1.  the package name.
2.  a list of objects for content.

quartodoc can look up a wide variety of objects, including functions, modules, classes, attributes, and methods:

``` yaml
quartodoc:
  package: quartodoc
  sections:
    - title: Some section
      desc: ""
      contents:
        - get_object        # function: quartodoc.get_object
        - ast.preview       # submodule func: quartodoc.ast.preview
        - MdRenderer        # class: quartodoc.MdRenderer
        - MdRenderer.render # method: quartodoc.MDRenderer.render
        - renderers         # module: quartodoc.renderers
```

The functions listed in `contents` are assumed to be imported from the package.

Instead of listing them out, you can set `contents: auto` to document every public submodule of the package:

``` yaml
quartodoc:
  package: quartodoc
  sections:
    - title: All modules
      desc: ""
      contents: auto
```

## Differences from quartodoc

Everything documented for quartodoc still applies. On top of it, quartopydoc adds:

**The `qpyd` and `qpynb` commands.** Where `quartodoc build` generates your API reference pages, `qpyd` wraps the whole docs lifecycle — pre-render builds, rendering, previewing, publishing, and scaffolding a new docs folder — and `qpynb` runs, checks, converts, and cleans notebooks in parallel. See [the qpyd CLI](https://sciris.github.io/quartopydoc/get-started/qpyd-cli.html).

**`contents: auto`.** Document every public submodule of a package without listing them out, as shown [above](#looking-up-objects). Private modules and test modules are skipped.

**griffe 2.x.** quartopydoc requires griffe 2.0 or later, and tracks its current API.

Note: installing both `quartopydoc` and `quartodoc` into the same environment will conflict, since both provide the `quartodoc` package and the `quartodoc` command.

## Learning more

Go [to the next page](https://sciris.github.io/quartopydoc/get-started/basic-docs.html) to learn how to configure quartodoc sites, or check out these handy pages:

- [The qpyd CLI](https://sciris.github.io/quartopydoc/get-started/qpyd-cli.html): building, previewing, and publishing a site, and managing notebooks.
- [Examples page](https://sciris.github.io/quartopydoc/examples/index.html): sites using quartodoc.
- [Tutorials page](https://sciris.github.io/quartopydoc/tutorials/index.html): screencasts of building a quartodoc site.
- [Docstring issues and examples](https://sciris.github.io/quartopydoc/get-started/docstring-examples.html): common issues when formatting docstrings.
- [Programming, the big picture](https://sciris.github.io/quartopydoc/get-started/dev-big-picture.html): the nitty gritty of how quartodoc works, and how to extend it.
