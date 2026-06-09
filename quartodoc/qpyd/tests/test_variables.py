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


def test_variables_to_args():
    # Values are YAML-encoded so Quarto (which parses -M values as YAML)
    # preserves them as strings rather than coercing "1.2"->float 1.2.
    args = variables.variables_to_args({"version": "1.2", "date": "2026"})
    assert args == ["-M", "version:'1.2'", "-M", "date:'2026'"]


def test_variables_to_args_plain_string_unquoted():
    # A string that isn't number/bool/null-like needs no quoting.
    assert variables.variables_to_args({"name": "starsim"}) == ["-M", "name:starsim"]


def test_load_missing_returns_empty(tmp_path):
    assert variables.load_variables(tmp_path / "nope.py") == {}


def test_variable_args_roundtrip(tmp_path):
    (tmp_path / "_variables.py").write_text("name = 'starsim'\n")
    assert variables.variable_args(tmp_path / "_variables.py") == ["-M", "name:starsim"]
