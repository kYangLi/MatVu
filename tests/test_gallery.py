from pathlib import Path

import numpy as np

from matvu import load_structure
from matvu.cli import main
from matvu.gallery import rank_candidates, render_candidates
from matvu.scene import build_scene

DATA = Path(__file__).resolve().parents[1] / "examples" / "structures"


def test_rank_candidates_is_sorted_and_limited():
    scene = build_scene(load_structure(DATA / "Si.POSCAR"))
    ranking = rank_candidates(scene, n=5, n_surface=48)
    assert len(ranking.candidates) == 5
    assert ranking.n_evaluated >= 5
    scores = [candidate.score for candidate in ranking.candidates]
    assert scores == sorted(scores, reverse=True)
    assert all(0.0 <= score <= 1.0 for score in scores)
    for candidate in ranking.candidates:
        assert candidate.view.direction.shape == (3,)
        assert 0.0 <= candidate.occlusion <= 1.0
        assert 0.0 <= candidate.bond_penalty <= 1.0
        assert 0.0 <= candidate.aspect_penalty <= 1.0
    assert ranking.auto is not None
    assert abs(float(np.linalg.norm(ranking.auto.view.direction)) - 1.0) < 1e-9
    assert 0.0 <= ranking.auto.score <= 1.0


def test_rank_candidates_uses_scene_formula():
    scene = build_scene(load_structure(DATA / "water.POSCAR"))
    assert scene.formula == "H2O"


def test_render_candidates_sheet(tmp_path):
    output = Path(
        render_candidates(
            DATA / "water.POSCAR",
            output=tmp_path / "sheet.png",
            n=4,
            n_surface=48,
        )
    )
    assert output.exists()
    assert output.stat().st_size > 5000


def test_render_candidates_clamps_to_available(tmp_path):
    output = Path(
        render_candidates(
            DATA / "water.POSCAR",
            output=tmp_path / "sheet.png",
            n=500,
            n_surface=16,
        )
    )
    assert output.exists()


def test_cli_candidates(tmp_path, capsys):
    code = main(
        [
            "candidates",
            str(DATA / "Si.POSCAR"),
            "-o",
            str(tmp_path / "sheet.png"),
            "-n",
            "4",
            "--n-surface",
            "48",
        ]
    )
    assert code == 0
    captured = capsys.readouterr().out
    assert "auto view" in captured
    assert (tmp_path / "sheet.png").exists()
