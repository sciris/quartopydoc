"""Tests for reading package versions and constants without importing them."""

import sys

import pytest

import quartodoc as qd


@pytest.fixture
def pkg(tmp_path, monkeypatch):
    """A package whose import would fail, so reading it must not import it."""
    root = tmp_path / "qd_meta_pkg"
    root.mkdir()
    (root / "__init__.py").write_text(
        "raise RuntimeError('imported!')\n__author__ = 'Someone'\n"
    )
    (root / "version.py").write_text(
        "__version__ = '1.2.3'\n"
        "__versiondate__ = '2026-01-02'\n"
        "__license__ = f'v{__version__}'\n"
        "__extra__ = {'a': [1, 2]}\n"
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    yield "qd_meta_pkg"
    assert "qd_meta_pkg" not in sys.modules


def test_get_version_and_attr(pkg):
    assert qd.get_version(pkg) == "1.2.3"
    assert qd.get_attr("__versiondate__", pkg) == "2026-01-02"
    assert qd.get_attr("__extra__", pkg) == {"a": [1, 2]}
    assert qd.get_attr("__author__", pkg) == "Someone"  # falls back to __init__.py


def test_get_attr_dotted(pkg):
    assert qd.get_attr("qd_meta_pkg.version.__versiondate__") == "2026-01-02"


def test_get_attr_missing_and_computed(pkg):
    with pytest.raises(AttributeError):
        qd.get_attr("__nope__", pkg)
    assert qd.get_attr("__nope__", pkg, default=None) is None
    with pytest.raises(ValueError, match="isn't a literal"):
        qd.get_attr("__license__", pkg)


def test_get_version_falls_back_to_metadata(tmp_path, monkeypatch):
    # A package with no literal __version__ (e.g. it comes from git tags), and
    # two distributions claiming it: a stale .egg-info first on sys.path, and the
    # editable install it's really imported from
    src = tmp_path / "src"
    (src / "qd_scm_pkg").mkdir(parents=True)
    (src / "qd_scm_pkg" / "__init__.py").write_text(
        "from importlib.metadata import version\n__version__ = version('qd-scm-pkg')\n"
    )
    stale = tmp_path / "stale" / "qd_scm_pkg.egg-info"
    stale.mkdir(parents=True)
    (stale / "PKG-INFO").write_text("Metadata-Version: 2.1\nName: qd-scm-pkg\nVersion: 0.1\n")
    (stale / "top_level.txt").write_text("qd_scm_pkg\n")
    installed = tmp_path / "site" / "qd_scm_pkg-2.0.dist-info"
    installed.mkdir(parents=True)
    (installed / "METADATA").write_text("Metadata-Version: 2.1\nName: qd-scm-pkg\nVersion: 2.0\n")
    (installed / "top_level.txt").write_text("qd_scm_pkg\n")
    (installed / "direct_url.json").write_text(
        f'{{"url": "{src.as_uri()}", "dir_info": {{"editable": true}}}}'
    )
    for path in [tmp_path / "site", src, tmp_path / "stale"]:  # stale ends up first
        monkeypatch.syspath_prepend(str(path))
    assert qd.get_version("qd_scm_pkg") == "2.0"


def test_default_package_from_quarto_yml(pkg, tmp_path, monkeypatch):
    (tmp_path / "_quarto.yml").write_text(f"quartodoc:\n  package: {pkg}\n")
    monkeypatch.chdir(tmp_path)
    assert qd.get_version() == "1.2.3"
    assert qd.get_attr("__versiondate__") == "2026-01-02"
