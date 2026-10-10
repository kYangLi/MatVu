from pathlib import Path

from matvu import render, render_array
from matvu.cli import main
from matvu.style import Style

DATA = Path(__file__).resolve().parents[1] / "examples" / "structures"


def test_render_water_png(tmp_path):
    output = Path(render(DATA / "water.POSCAR", output=tmp_path / "water.png", view="auto"))
    assert output.exists()
    assert output.stat().st_size > 5000


def test_render_si_pdf(tmp_path):
    output = Path(render(DATA / "Si.POSCAR", output=tmp_path / "si.pdf", view="a"))
    assert output.read_bytes()[:4] == b"%PDF"


def test_render_supercell(tmp_path):
    output = Path(
        render(
            DATA / "graphene.POSCAR",
            output=tmp_path / "graphene.png",
            view="auto",
            supercell=(2, 2, 1),
        )
    )
    assert output.exists()


def test_cli_render(tmp_path, capsys):
    code = main(
        [
            "render",
            str(DATA / "Si.POSCAR"),
            "-o",
            str(tmp_path / "cli.png"),
            "--view",
            "auto",
            "--print-view",
        ]
    )
    assert code == 0
    captured = capsys.readouterr().out
    assert "direction" in captured
    assert (tmp_path / "cli.png").exists()


def test_style_presets():
    from matvu.style import style_preset

    toon = style_preset("toon")
    assert toon.shading is False
    assert toon.perspective > 0.0  # keeps the perspective camera
    assert toon.depth_cue > 0.0
    assert 0.0 < toon.ambient < 1.0  # cel shadow tone

    flat = style_preset("flat")
    assert flat.shading is False
    assert flat.perspective > 0.0  # perspective as well
    assert flat.ambient == 1.0  # no shadow band at all

    shaded = style_preset("3d")
    assert shaded.shading is True
    assert shaded.perspective > 0.0
    assert shaded.depth_cue == 0.0


def test_cli_render_flat_style(tmp_path):
    code = main(
        [
            "render",
            str(DATA / "water.POSCAR"),
            "-o",
            str(tmp_path / "flat.png"),
            "--style",
            "flat",
        ]
    )
    assert code == 0
    assert (tmp_path / "flat.png").exists()


def test_render_array_returns_rgba():
    image = render_array(
        DATA / "water.POSCAR",
        view="auto",
        style=Style(width_in=1.5, dpi=80, supersample=1),
    )
    assert image.shape[2] == 4
    assert image[0, 0, 3] == 0.0  # transparent background


def test_cli_canvas_option(tmp_path):
    code = main(
        [
            "render",
            str(DATA / "water.POSCAR"),
            "--canvas",
            "6",
            "4",
            "-o",
            str(tmp_path / "canvas.png"),
        ]
    )
    assert code == 0
    assert (tmp_path / "canvas.png").exists()


def test_cli_info(capsys):
    assert main(["info", str(DATA / "NaCl.POSCAR")]) == 0
    captured = capsys.readouterr().out
    assert "Cl4Na4" in captured
