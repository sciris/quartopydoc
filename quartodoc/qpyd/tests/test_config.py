from quartodoc.qpyd import config


def test_discover_skips_prose_and_finds_python(docs):
    names = sorted(p.name for p in config.discover_notebooks(root=docs))
    assert "nb_ok.qmd" in names
    assert "nb_fail.qmd" in names
    assert "prose.qmd" not in names  # no {python} cell -> not a notebook


def test_discover_explicit_file_includes_prose(docs):
    nbs = config.discover_notebooks([str(docs / "prose.qmd")])
    assert [p.name for p in nbs] == ["prose.qmd"]


def test_discover_excludes_build_dirs(docs):
    freeze = docs / "_freeze"
    freeze.mkdir()
    (freeze / "cached.qmd").write_text("```{python}\nx = 1\n```\n")
    nbs = config.discover_notebooks(root=docs)
    assert all("_freeze" not in str(p) for p in nbs)


def test_discover_finds_ipynb(docs):
    (docs / "extra.ipynb").write_text("{}")
    names = [p.name for p in config.discover_notebooks(root=docs)]
    assert "extra.ipynb" in names


def test_find_config_and_package(docs, monkeypatch):
    monkeypatch.chdir(docs)
    assert config.find_quarto_config().name == "_quarto.yml"
    assert config.get_package_name() == "quartodoc"
    assert config.docs_dir().resolve() == docs.resolve()


def test_get_package_name_missing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert config.get_package_name(default="fallback") == "fallback"
