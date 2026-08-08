import shutil
from pathlib import Path

import pytest

DATA = Path(__file__).parent / "data"


@pytest.fixture
def docs(tmp_path):
    """A temp docs dir with a minimal _quarto.yml and the sample notebooks."""
    (tmp_path / "_quarto.yml").write_text("quartodoc:\n  package: quartodoc\n")
    for f in DATA.glob("*.qmd"):
        shutil.copy(f, tmp_path / f.name)
    return tmp_path
