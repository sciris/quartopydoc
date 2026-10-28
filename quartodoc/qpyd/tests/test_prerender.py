"""Tests for the pre-render build: skipping when up to date, hooks, extra steps."""

import json

import pytest

from quartodoc.qpyd import prerender

CONFIG = """\
quartodoc:
  package: qpyd_test_missing_pkg
  dir: api
qpyd:
  prerender:
    commands: [python make_index.py]
    inputs: [make_index.py]
    outputs: [index.json]
"""


@pytest.fixture
def site(tmp_path, monkeypatch):
    """A docs dir whose `run` calls are recorded (and fake the build outputs)."""
    (tmp_path / "_quarto.yml").write_text(CONFIG)
    (tmp_path / "make_index.py").write_text("# makes index.json\n")
    monkeypatch.chdir(tmp_path)
    for var in ["QPYD_SKIP_HOOKS", "QPYD_FORCE_PRERENDER", "QUARTO_PROJECT_RENDER_ALL"]:
        monkeypatch.delenv(var, raising=False)
    monkeypatch.delenv("QUARTO_PROJECT_OUTPUT_DIR", raising=False)

    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        if isinstance(cmd, list) and cmd[-1] == "build":
            (tmp_path / "api").mkdir(exist_ok=True)
            (tmp_path / "objects.json").write_text(json.dumps({"items": []}))
        elif cmd == "python make_index.py":
            (tmp_path / "index.json").write_text("{}")

    monkeypatch.setattr(prerender, "run", fake_run)
    return tmp_path, calls


def _built(calls):
    return any(isinstance(c, list) and c[-1] == "build" for c in calls)


def test_prerender_builds_then_skips(site):
    root, calls = site
    prerender.prerender()
    assert _built(calls)
    assert "python make_index.py" in calls
    assert (root / "objects.inv").exists()
    calls.clear()
    prerender.prerender()
    assert calls == []  # nothing changed, so nothing rebuilt


def test_prerender_force(site, monkeypatch):
    _, calls = site
    prerender.prerender()
    calls.clear()
    prerender.prerender(force=True)
    assert _built(calls)
    calls.clear()
    monkeypatch.setenv("QPYD_FORCE_PRERENDER", "1")
    prerender.prerender()
    assert _built(calls)


def test_prerender_reruns_when_inputs_change(site):
    root, calls = site
    prerender.prerender()
    calls.clear()
    (root / "make_index.py").write_text("# changed\n")
    prerender.prerender()
    assert _built(calls)


def test_prerender_reruns_when_outputs_missing(site):
    root, calls = site
    prerender.prerender()
    calls.clear()
    (root / "index.json").unlink()
    prerender.prerender()
    assert _built(calls)


def test_prerender_skipped_for_partial_quarto_render(site, monkeypatch):
    _, calls = site
    monkeypatch.setenv("QUARTO_PROJECT_OUTPUT_DIR", "_site")
    prerender.prerender()
    assert calls == []
    monkeypatch.setenv("QUARTO_PROJECT_RENDER_ALL", "1")  # a full render runs it
    prerender.prerender()
    assert _built(calls)


def test_interlinks_only_with_external_sources(tmp_path):
    cfg = tmp_path / "_quarto.yml"
    cfg.write_text("interlinks:\n  sources: {}\n")
    assert not prerender.has_external_interlinks(tmp_path)
    cfg.write_text("interlinks:\n  sources:\n    self:\n      url: /\n")
    assert not prerender.has_external_interlinks(tmp_path)
    cfg.write_text("interlinks:\n  sources:\n    numpy:\n      url: https://numpy.org/doc/stable/\n")
    assert prerender.has_external_interlinks(tmp_path)


def test_prerender_writes_variables_yml(site):
    root, _ = site
    (root / "_variables.py").write_text("version = '1.2'\n")
    prerender.prerender()
    assert "version: '1.2'" in (root / "_variables.yml").read_text()
