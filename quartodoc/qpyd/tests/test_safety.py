"""Regression tests for the safety / correctness fixes from the review."""

import nbformat
import pytest

from quartodoc.qpyd import clean, config, convert, execute, variables


# --- clean: opt-in, project-scoped, source-protecting (CRITICAL/HIGH) -------


def test_clean_refuses_without_quarto_yml(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "example-thing.qmd").write_text("x")
    (tmp_path / "my-scratch.txt").write_text("x")
    removed = clean.clean_outputs()
    assert removed == []
    assert (tmp_path / "example-thing.qmd").exists()  # nothing deleted


def test_clean_no_patterns_is_noop(tmp_path, monkeypatch):
    (tmp_path / "_quarto.yml").write_text("quartodoc:\n  package: x\n")
    monkeypatch.chdir(tmp_path)
    (tmp_path / "my-scratch.png").write_bytes(b"x")
    removed = clean.clean_outputs()
    assert removed == []
    assert (tmp_path / "my-scratch.png").exists()


def test_clean_never_deletes_source_files(tmp_path, monkeypatch):
    (tmp_path / "_quarto.yml").write_text(
        "quartodoc:\n  package: x\nqpyd:\n  clean:\n    - '**/example*.*'\n"
    )
    monkeypatch.chdir(tmp_path)
    (tmp_path / "example-usage.qmd").write_text("source!")
    (tmp_path / "example-output.png").write_bytes(b"x")
    removed = clean.clean_outputs()
    assert (tmp_path / "example-usage.qmd").exists()  # .qmd protected
    assert (tmp_path / "example-output.png") not in []  # png is deletable
    assert not (tmp_path / "example-output.png").exists()
    assert all(p.suffix != ".qmd" for p in removed)


def test_clean_dry_run_keeps_files(tmp_path, monkeypatch):
    (tmp_path / "_quarto.yml").write_text(
        "quartodoc:\n  package: x\nqpyd:\n  clean:\n    - '**/my-*.png'\n"
    )
    monkeypatch.chdir(tmp_path)
    junk = tmp_path / "my-fig.png"
    junk.write_bytes(b"x")
    removed = clean.clean_outputs(dry_run=True)
    assert junk in [p for p in removed]
    assert junk.exists()


def test_clean_skips_under_hook_guard(tmp_path, monkeypatch):
    (tmp_path / "_quarto.yml").write_text(
        "quartodoc:\n  package: x\nqpyd:\n  clean:\n    - '**/my-*.png'\n"
    )
    monkeypatch.chdir(tmp_path)
    junk = tmp_path / "my-fig.png"
    junk.write_bytes(b"x")
    monkeypatch.setenv("QPYD_SKIP_HOOKS", "1")
    assert clean.clean_outputs() == []
    assert junk.exists()


# --- refresh: project-scoped, finds nested caches (HIGH/LOW) ----------------


def test_refresh_refuses_without_quarto_yml(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "_freeze").mkdir()
    assert execute.refresh_cache() == []
    assert (tmp_path / "_freeze").exists()


def test_refresh_finds_nested_jupyter_cache(tmp_path, monkeypatch):
    (tmp_path / "_quarto.yml").write_text("quartodoc:\n  package: x\n")
    (tmp_path / "_freeze").mkdir()
    nested = tmp_path / "tutorials" / ".jupyter_cache"
    nested.mkdir(parents=True)
    monkeypatch.chdir(tmp_path)
    removed = execute.refresh_cache(dry_run=True)
    assert any(p.name == ".jupyter_cache" for p in removed)
    assert any(p.name == "_freeze" for p in removed)


# --- prerender hook guard (HIGH) --------------------------------------------


def test_prerender_skips_under_hook_guard(monkeypatch, capsys):
    from quartodoc.qpyd import prerender

    monkeypatch.setenv("QPYD_SKIP_HOOKS", "1")
    prerender.prerender()  # must not invoke quartodoc build etc.
    # If it tried to build, it would print the "Starting Quarto docs build"
    # heading; assert it did not run.
    assert "Starting Quarto docs build" not in capsys.readouterr().out


# --- variables -M serialization (MED) ---------------------------------------


def test_variables_to_args_yaml_scalars():
    args = variables.variables_to_args(
        {"v": "1.2.3", "flag": True, "missing": None, "n": 5, "items": [1, 2]}
    )
    flat = dict(zip(args[::2], args[1::2])) if False else args
    assert "v:1.2.3" in args
    assert "flag:true" in args  # not Python "True"
    assert "missing:null" in args  # not "None"
    assert "n:5" in args
    assert "items:[1, 2]" in args


# --- conversion overwrite guard (MED) ---------------------------------------


def test_to_py_refuses_overwrite(tmp_path):
    nb = nbformat.v4.new_notebook()
    nb.cells = [nbformat.v4.new_code_cell("x = 1")]
    ipynb = tmp_path / "n.ipynb"
    nbformat.write(nb, str(ipynb))
    (tmp_path / "n.py").write_text("# precious hand-written file\n")
    with pytest.raises(FileExistsError):
        convert.to_py(ipynb)
    assert "precious" in (tmp_path / "n.py").read_text()  # untouched


def test_to_py_force_overwrites(tmp_path):
    qmd = tmp_path / "n.qmd"
    qmd.write_text("```{python}\nx = 1\n```\n")
    (tmp_path / "n.py").write_text("old")
    out = convert.to_py(qmd, force=True)
    assert out.exists()
    assert "old" not in out.read_text()


# --- _excluded base relative to scan target (LOW) ---------------------------


def test_discover_handles_dotted_absolute_target(tmp_path):
    # A scan target whose absolute path passes through a hidden dir must still
    # have its notebooks discovered.
    hidden = tmp_path / ".cache" / "proj"
    hidden.mkdir(parents=True)
    (hidden / "nb.qmd").write_text("```{python}\nx = 1\n```\n")
    found = config.discover_notebooks([str(hidden)])
    assert [p.name for p in found] == ["nb.qmd"]


# --- summary classification by leading marker (LOW) -------------------------


def test_summary_not_fooled_by_checkmark_in_stderr():
    # A failure result that embeds a YAY (✓) in captured stderr must still be
    # classified as a failure.
    failing = f"{execute.BOO} Execution failed for x:\n  assert ok {execute.YAY}\n(time: 0.1 s)"
    passing = f"{execute.YAY} y executed successfully (time: 0.1 s)"
    table = execute._summarize(["x", "y"], [failing, passing])
    assert not execute._succeeded(failing)
    assert execute._succeeded(passing)
