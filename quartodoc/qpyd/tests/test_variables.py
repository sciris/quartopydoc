import pytest
import yaml

from quartodoc.qpyd import variables


def test_load_variables_filters(tmp_path):
    vf = tmp_path / "_variables.py"
    vf.write_text(
        "import os\n"  # a module: not YAML-serialisable -> skipped
        "version = '1.2.3'\n"
        "count = 5\n"
        "_private = 'hidden'\n"  # underscore -> skipped
        "def helper():\n    return 1\n"  # callable -> skipped
    )
    assert variables.load_variables(vf) == {"version": "1.2.3", "count": 5}


def test_load_variables_all(tmp_path):
    vf = tmp_path / "_variables.py"
    vf.write_text(
        "__all__ = ['version', '_meta']\n"
        "version = '1.2.3'\n"
        "other = 'not exported'\n"
        "_meta = {'a': 1}\n"  # in __all__, so exported despite the underscore
    )
    assert variables.load_variables(vf) == {"version": "1.2.3", "_meta": {"a": 1}}


def test_load_variables_warns_on_skipped(tmp_path):
    vf = tmp_path / "_variables.py"
    vf.write_text("import fractions\nratio = fractions.Fraction(1, 3)\nok = 1\n")
    with pytest.warns(UserWarning, match="ratio is a Fraction"):
        assert variables.load_variables(vf) == {"ok": 1}
    vf.write_text("__all__ = ['missing']\n")
    with pytest.warns(UserWarning, match="'missing' is in __all__"):
        assert variables.load_variables(vf) == {}


def test_config_variables(tmp_path, monkeypatch):
    pkg = tmp_path / "qd_vars_pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("raise RuntimeError('imported!')\n")
    (pkg / "version.py").write_text("__version__ = '2.0'\n__versiondate__ = '2026-03-04'\n")
    monkeypatch.syspath_prepend(str(tmp_path))
    (tmp_path / "_quarto.yml").write_text(
        "quartodoc:\n  package: qd_vars_pkg\n"
        "qpyd:\n  variables:\n"
        "    version: {attr: __version__}\n"
        "    versiondate: {attr: qd_vars_pkg.version.__versiondate__}\n"
        "    license: MIT\n"
        "    shadowed: from yml\n"
    )
    (tmp_path / "_variables.py").write_text("shadowed = 'from py'\n")
    assert variables.write_variables_yml(tmp_path / "_variables.py") == {
        "version": "2.0",
        "versiondate": "2026-03-04",
        "license": "MIT",
        "shadowed": "from py",
    }


def test_load_missing_returns_empty(tmp_path):
    assert variables.load_variables(tmp_path / "nope.py") == {}


def test_write_variables_yml(tmp_path):
    (tmp_path / "_variables.py").write_text("version = '1.10'\n")
    yml = tmp_path / "_variables.yml"
    yml.write_text("other: kept\n")
    assert variables.write_variables_yml(tmp_path / "_variables.py") == {"version": "1.10"}
    assert yaml.safe_load(yml.read_text()) == {"other": "kept", "version": "1.10"}
    mtime = yml.stat().st_mtime_ns
    assert variables.write_variables_yml(tmp_path / "_variables.py") is None  # unchanged
    assert yml.stat().st_mtime_ns == mtime


def test_write_variables_yml_without_py(tmp_path):
    assert variables.write_variables_yml(tmp_path / "_variables.py") is None
    assert not (tmp_path / "_variables.yml").exists()
