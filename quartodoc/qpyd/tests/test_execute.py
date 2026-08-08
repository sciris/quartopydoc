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
