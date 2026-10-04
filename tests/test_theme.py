from pathlib import Path

import pytest

from matvu import Style, export_theme, load_structure, load_theme, palette_names
from matvu import palettes
from matvu.cli import main
from matvu.scene import build_scene

DATA = Path(__file__).resolve().parents[1] / "examples" / "structures"


def test_palettes_are_complete_and_well_formed():
    assert set(palette_names()) == {"matvu", "jmol", "pastel"}
    for name in palette_names():
        for symbol in ("H", "C", "N", "O", "Si", "Fe", "Cu", "Au", "U"):
            colour = palettes.palette_colour(name, symbol)
            assert len(colour) == 7
            assert colour.startswith("#")


def test_hydrogen_is_not_white_in_any_palette():
    for name in palette_names():
        assert max(palettes.colour_rgb(name, "H")) < 0.9


def test_colour_overrides_win():
    assert palettes.palette_colour("matvu", "O", {"O": "#123456"}) == "#123456"
    assert palettes.palette_colour("matvu", "o", {"O": "#123456"}) == "#123456"


def test_unknown_palette_raises():
    with pytest.raises(ValueError):
        palettes.palette_colour("nope", "H")


def test_load_builtin_theme():
    theme = load_theme("pastel")
    assert theme.style.palette == "pastel"
    assert theme.colour("O") == palettes.palette_colour("pastel", "O")


def test_load_custom_theme(tmp_path):
    path = tmp_path / "custom.toml"
    path.write_text(
        """
name = "custom"
palette = "matvu"

[radii]
atom_scale = 0.55
bond_radius = 0.12

[colors]
O = "#123456"

[style]
depth_cue = 0.5
""",
        encoding="utf-8",
    )
    theme = load_theme(path, base=Style())
    assert theme.name == "custom"
    assert theme.style.atom_scale == pytest.approx(0.55)
    assert theme.style.bond_radius == pytest.approx(0.12)
    assert theme.style.depth_cue == pytest.approx(0.5)
    assert theme.colour("O") == "#123456"

    scene = build_scene(load_structure(DATA / "water.POSCAR"), theme.style)
    assert scene.radii[0] == pytest.approx(0.55 * 0.66, rel=1e-9)
    assert scene.colours[0] == pytest.approx((0x12 / 255, 0x34 / 255, 0x56 / 255))


def test_export_theme_round_trip(tmp_path):
    output = export_theme("matvu", tmp_path / "matvu.toml")
    assert output.exists()
    theme = load_theme(output)
    assert theme.colour("Fe") == palettes.palette_colour("matvu", "Fe")
    assert theme.style.atom_scale == pytest.approx(0.40)


def test_cli_theme_list(capsys):
    assert main(["theme", "list"]) == 0
    out = capsys.readouterr().out
    assert "matvu" in out
    assert "pastel" in out


def test_cli_render_with_theme(tmp_path):
    code = main(
        [
            "render",
            str(DATA / "water.POSCAR"),
            "--style",
            "toon",
            "--theme",
            "pastel",
            "-o",
            str(tmp_path / "pastel.png"),
        ]
    )
    assert code == 0
    assert (tmp_path / "pastel.png").exists()
