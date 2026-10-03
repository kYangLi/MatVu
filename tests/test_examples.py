from pathlib import Path

import pytest

from matvu import render
from matvu.style import Style

DATA = Path(__file__).resolve().parents[1] / "examples" / "structures"
EXAMPLES = sorted(DATA.glob("*.POSCAR"))


@pytest.mark.parametrize("path", EXAMPLES, ids=lambda path: path.stem)
def test_example_renders_with_auto_view(tmp_path, path):
    style = Style(width_in=1.0, dpi=60, supersample=1)
    output = render(path, output=tmp_path / f"{path.stem}.png", view="auto", style=style)
    assert Path(output).exists()
    assert Path(output).stat().st_size > 500
