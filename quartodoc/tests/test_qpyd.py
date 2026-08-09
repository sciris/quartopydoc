"""Smoke tests for the qpyd / qpynb console entry points.

Detailed unit tests live in quartodoc/qpyd/tests/.
"""

from click.testing import CliRunner

from quartodoc.qpyd import cli, nb_cli


def test_qpyd_cli_help():
    result = CliRunner().invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "qpyd" in result.output


def test_qpynb_cli_help():
    result = CliRunner().invoke(nb_cli, ["--help"])
    assert result.exit_code == 0
    assert "check" in result.output
