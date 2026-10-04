from pathlib import Path

from matvu import render
from matvu.cli import main

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

    flat = style_preset("flat")
    assert flat.shading is False
    assert flat.perspective == 0.0
    assert flat.depth_cue > 0.0
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


def test_cli_info(capsys):
    assert main(["info", str(DATA / "NaCl.POSCAR")]) == 0
    captured = capsys.readouterr().out
    assert "Cl4Na4" in captured
