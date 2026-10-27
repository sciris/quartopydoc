from quartodoc.qpyd import execute


def _write(directory, name, code):
    path = directory / name
    path.write_text(f"```{{python}}\n{code}\n```\n")
    return path


def test_execute_notebook_pass(tmp_path):
    nb = _write(tmp_path, "ok.qmd", "x = 1 + 1\nassert x == 2\nprint('ok')")
    assert execute.YAY in execute.execute_notebook(nb)


def test_execute_notebook_fail(tmp_path):
    nb = _write(tmp_path, "bad.qmd", "raise ValueError('boom')")
    assert execute.BOO in execute.execute_notebook(nb)


def test_execute_notebooks_serial(tmp_path, monkeypatch):
    (tmp_path / "_quarto.yml").write_text("quartodoc:\n  package: x\n")
    _write(tmp_path, "a.qmd", "print('a')")
    _write(tmp_path, "b.qmd", "raise RuntimeError('x')")
    monkeypatch.chdir(tmp_path)

    results = execute.execute_notebooks(serial=True)

    assert len(results) == 2
    combined = "".join(results.values())
    assert execute.YAY in combined and execute.BOO in combined


def test_refresh_dry_run_keeps_cache(tmp_path, monkeypatch):
    (tmp_path / "_quarto.yml").write_text("quartodoc:\n  package: x\n")
    (tmp_path / "_freeze").mkdir()
    monkeypatch.chdir(tmp_path)

    removed = execute.refresh_cache(dry_run=True)

    assert any("_freeze" in str(p) for p in removed)
    assert (tmp_path / "_freeze").exists()  # dry-run must not delete


def test_refresh_empty(tmp_path, monkeypatch):
    (tmp_path / "_quarto.yml").write_text("quartodoc:\n  package: x\n")
    monkeypatch.chdir(tmp_path)
    assert execute.refresh_cache() == []


def test_runnable_py_does_not_shadow_imports(tmp_path):
    # A notebook called numpy.qmd must not become numpy.py, which would shadow
    # NumPy itself (the script's folder is first on sys.path when it runs)
    qmd = tmp_path / "numpy.qmd"
    qmd.write_text("```{python}\nimport json\n```\n")
    out = tmp_path / "out"
    out.mkdir()
    py = execute._make_runnable_py(qmd, out)
    assert py.name != "numpy.py"
    assert py.parent == out


def test_failure_output_includes_stdout():
    assert "Traceback" in execute._output_tail(b"Traceback: boom", b"")
