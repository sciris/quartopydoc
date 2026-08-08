"""
The top-level ``qpyd`` command group.

``qpyd`` orchestrates the docs build (prerender / render / preview / publish /
init / clean) and embeds the notebook commands under ``qpyd nb`` (an alias for
the standalone ``qpynb`` command).
"""

import click

from .nb import nb_cli
from .prerender import prerender
from .render import gh_publish, preview, render
from .scaffold import init

_PASSTHROUGH = dict(ignore_unknown_options=True, allow_extra_args=True)


@click.group(name="qpyd", invoke_without_command=True)
@click.version_option(package_name="quartopydoc")
@click.pass_context
def cli(ctx):
    """
    qpyd — build, render, and publish Quarto-based Python API docs.

    Run without a subcommand to show this help.
    """
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@cli.command("prerender")
def prerender_cmd():
    """Run pre-render build steps (API docs, aliases, interlinks, objects.inv)."""
    prerender()


@cli.command("render", context_settings=_PASSTHROUGH)
@click.option("--no-prerender", is_flag=True, help="Skip the pre-render build steps.")
@click.argument("quarto_args", nargs=-1, type=click.UNPROCESSED)
def render_cmd(no_prerender, quarto_args):
    """
    Run the pre-render steps, then 'quarto render', timing the build.

    Any extra arguments are passed through to 'quarto render'.
    """
    render(extra_args=quarto_args, do_prerender=not no_prerender)


@cli.command("preview", context_settings=_PASSTHROUGH)
@click.option("--no-prerender", is_flag=True, help="Skip the pre-render build steps.")
@click.argument("quarto_args", nargs=-1, type=click.UNPROCESSED)
def preview_cmd(no_prerender, quarto_args):
    """
    Run the pre-render steps, then 'quarto preview' (live-reloading server).

    Any extra arguments are passed through to 'quarto preview'.
    """
    preview(extra_args=quarto_args, do_prerender=not no_prerender)


@cli.command("gh-publish")
@click.option("--no-prerender", is_flag=True, help="Skip the pre-render build steps.")
def gh_publish_cmd(no_prerender):
    """Render and publish the site to GitHub Pages (the gh-pages branch)."""
    gh_publish(do_prerender=not no_prerender)


@cli.command("init")
@click.argument("path", default="docs")
@click.option("--package", default=None, help="Package name to document.")
def init_cmd(path, package):
    """Scaffold a docs/ folder with a starter _quarto.yml (existing files kept)."""
    init(path=path, package=package)


@cli.command("clean")
@click.option("--dry-run", is_flag=True, help="Show what would be deleted, without deleting.")
def clean_cmd(dry_run):
    """Remove auto-generated temporary files (my-*, example*) from the docs dir."""
    from .clean import clean_outputs

    clean_outputs(dry_run=dry_run)


# `qpyd nb ...` is an alias for the standalone `qpynb ...` command.
cli.add_command(nb_cli, name="nb")
