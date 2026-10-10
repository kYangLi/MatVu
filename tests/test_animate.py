from pathlib import Path

import numpy as np
import pytest

from matvu import orbit_views, render_orbit
from matvu.cli import main
from matvu.style import Style
from matvu.viewpoint import View

DATA = Path(__file__).resolve().parents[1] / "examples" / "structures"
TINY = dict(width_in=1.2, dpi=60, supersample=1)


def test_orbit_views_rotate_around_z():
    views = orbit_views(View([1.0, 0.0, 0.0]), degrees=360.0, frames=4, axis="z")
    assert len(views) == 4
    azimuths = [view.angles_deg()[0] for view in views]
    assert azimuths[0] == pytest.approx(0.0)
    assert azimuths[1] == pytest.approx(90.0)
    assert azimuths[2] == pytest.approx(180.0)
    assert azimuths[3] == pytest.approx(-90.0)
    for view in views:
        assert float(np.linalg.norm(view.direction)) == pytest.approx(1.0)


def test_orbit_views_start_at_the_base_view():
    base = View([0.4, -0.2, 0.8])
    first = orbit_views(base, frames=6)[0]
    assert np.allclose(first.direction, base.direction)
    assert np.allclose(first.up_hint, base.up_hint)


def test_orbit_views_auto_axis_moves_a_face_on_view():
    # a face-on molecule looks along z: orbiting around z would be static
    views = orbit_views(View([0.0, 0.0, 1.0]), frames=4)
    assert not np.allclose(views[1].direction, views[0].direction)


def test_orbit_views_reject_bad_input():
    with pytest.raises(ValueError):
        orbit_views(View([1.0, 0.0, 0.0]), axis="w")
    with pytest.raises(ValueError):
        orbit_views(View([1.0, 0.0, 0.0]), frames=1)


def test_render_orbit_gif_and_frames(tmp_path):
    frames_dir = tmp_path / "frames"
    gif_path = tmp_path / "water_spin.gif"
    written = render_orbit(
        DATA / "water.POSCAR",
        gif_path,
        style=Style(**TINY),
        frames=4,
        frames_dir=frames_dir,
    )
    assert gif_path in written
    assert gif_path.exists()
    frames = sorted(frames_dir.glob("frame_*.png"))
    assert len(frames) == 4

    from PIL import Image

    with Image.open(gif_path) as image:
        assert image.n_frames == 4


def test_render_orbit_rejects_unknown_suffix(tmp_path):
    with pytest.raises(ValueError, match=".gif or .webp"):
        render_orbit(
            DATA / "water.POSCAR", tmp_path / "spin.mp4", style=Style(**TINY), frames=2
        )


def test_animate_cli(tmp_path):
    code = main(
        [
            "animate",
            str(DATA / "water.POSCAR"),
            "-o",
            str(tmp_path / "spin.gif"),
            "--frames",
            "4",
            "--width",
            "1.2",
            "--dpi",
            "60",
            "--supersample",
            "1",
        ]
    )
    assert code == 0
    assert (tmp_path / "spin.gif").exists()
