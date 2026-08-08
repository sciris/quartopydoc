from click.testing import CliRunner

from quartodoc.qpyd import cli, nb_cli


def test_qpyd_help():
    result = CliRunner().invoke(cli, ["--help"])
    assert result.exit_code == 0
    for cmd in ["render", "preview", "prerender", "gh-publish", "init", "clean", "nb"]:
        assert cmd in result.output


def test_qpynb_no_subcommand_shows_help():
    result = CliRunner().invoke(nb_cli, [])
    assert result.exit_code == 0
    for cmd in ["run", "check", "refresh", "to-py", "to-qmd", "to-ipynb", "clear"]:
        assert cmd in result.output


def test_nb_alias():
    result = CliRunner().invoke(cli, ["nb", "--help"])
    assert result.exit_code == 0
    assert "check" in result.output


def test_init_scaffolds(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(cli, ["init", "mydocs", "--package", "foo"])
    assert result.exit_code == 0, result.output
    cfg = tmp_path / "mydocs" / "_quarto.yml"
    assert cfg.exists()
    assert (tmp_path / "mydocs" / "index.qmd").exists()
    assert "package: foo" in cfg.read_text()


def test_init_idempotent(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    CliRunner().invoke(cli, ["init", "d", "--package", "foo"])
    cfg = tmp_path / "d" / "_quarto.yml"
    cfg.write_text("custom")  # tamper
    CliRunner().invoke(cli, ["init", "d", "--package", "foo"])
    assert cfg.read_text() == "custom"  # existing file not overwritten


def test_to_py_cli(tmp_path):
    qmd = tmp_path / "n.qmd"
    qmd.write_text("```{python}\nx = 1\n```\n")
    result = CliRunner().invoke(nb_cli, ["to-py", str(qmd)])
    assert result.exit_code == 0, result.output
    assert (tmp_path / "n.py").exists()


def test_clean_dry_run(tmp_path, monkeypatch):
    # clean is opt-in via the qpyd.clean config key, and only deletes
    # non-source files that match.
    (tmp_path / "_quarto.yml").write_text(
        "quartodoc:\n  package: x\nqpyd:\n  clean:\n    - '**/my-*.png'\n"
    )
    junk = tmp_path / "my-scratch.png"
    junk.write_bytes(b"x")
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(cli, ["clean", "--dry-run"])
    assert result.exit_code == 0, result.output
    assert junk.exists()  # dry-run must not delete
    assert "my-scratch.png" in result.output
