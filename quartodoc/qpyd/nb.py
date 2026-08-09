"""The ``qpynb`` command group: notebook management for Quarto docs."""

import click

from .convert import clear_outputs, to_ipynb, to_py, to_qmd
from .execute import execute_notebooks, refresh_cache, run_notebooks

_SERIAL_HELP = "Process one notebook at a time instead of in parallel (for debugging)."


@click.group(name="qpynb", invoke_without_command=True)
@click.version_option(package_name="quartopydoc")
@click.pass_context
def nb_cli(ctx):
    """
    Manage Quarto notebooks (.qmd / .ipynb): run, check, convert, and clean.

    Run without a subcommand to show this help.
    """
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@nb_cli.command("run")
@click.argument("paths", nargs=-1, type=click.Path())
@click.option("--serial", is_flag=True, help=_SERIAL_HELP)
def run_cmd(paths, serial):
    """
    Execute notebooks in parallel and update cached copies (Quarto _freeze/).

    With no PATHS, every notebook in the project is run. PATHS may be
    individual notebooks or folders of notebooks.
    """
    run_notebooks(*paths, serial=serial)


@nb_cli.command("check")
@click.argument("paths", nargs=-1, type=click.Path())
@click.option("--serial", is_flag=True, help=_SERIAL_HELP)
def check_cmd(paths, serial):
    """
    Execute notebooks in parallel to verify they run; do NOT update caches.

    Like 'run', but a pure validation pass that leaves no artifacts and does
    not touch the freeze cache.
    """
    execute_notebooks(*paths, serial=serial)


@nb_cli.command("refresh")
@click.option(
    "--dry-run", is_flag=True, help="Show what would be deleted, without deleting."
)
def refresh_cmd(dry_run):
    """Delete cached copies of notebooks (_freeze/ and .jupyter_cache/)."""
    refresh_cache(dry_run=dry_run)


_FORCE_HELP = "Overwrite the destination file if it already exists."


@nb_cli.command("to-py")
@click.argument("path", type=click.Path(exists=True))
@click.option("--force", is_flag=True, help=_FORCE_HELP)
def to_py_cmd(path, force):
    """Convert a notebook (.qmd or .ipynb) to a Python (.py) file."""
    click.echo(f"Wrote {to_py(path, force=force)}")


@nb_cli.command("to-qmd")
@click.argument("path", type=click.Path(exists=True))
@click.option("--force", is_flag=True, help=_FORCE_HELP)
def to_qmd_cmd(path, force):
    """Convert a notebook (.ipynb or .py) to a Quarto (.qmd) file."""
    click.echo(f"Wrote {to_qmd(path, force=force)}")


@nb_cli.command("to-ipynb")
@click.argument("path", type=click.Path(exists=True))
@click.option("--force", is_flag=True, help=_FORCE_HELP)
def to_ipynb_cmd(path, force):
    """Convert a notebook (.qmd or .py) to a Jupyter (.ipynb) file."""
    click.echo(f"Wrote {to_ipynb(path, force=force)}")


@nb_cli.command("clear")
@click.argument("paths", nargs=-1, type=click.Path())
@click.option(
    "--dry-run", is_flag=True, help="Show what would be cleared, without writing."
)
def clear_cmd(paths, dry_run):
    """Clear saved outputs from .ipynb notebooks and normalize them."""
    clear_outputs(*paths, dry_run=dry_run)
