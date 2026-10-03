from pathlib import Path

import numpy as np

from matvu import Structure, View, render
from matvu.backends.tracer import trace_image
from matvu.scene import Scene, build_scene
from matvu.style import Style

DATA = Path(__file__).resolve().parents[1] / "examples" / "structures"


def _scene(with_middle_atom: bool) -> Scene:
    positions = [[-2.0, 0.0, 0.0], [2.0, 0.0, 0.0]]
    symbols = ["C", "C"]
    colours = [[0.9, 0.1, 0.1], [0.1, 0.1, 0.9]]
    radii = [0.2, 0.2]
    bonds = [[0, 1]]
    if with_middle_atom:
        positions.append([0.0, 0.0, 0.0])
        symbols.append("C")
        colours.append([0.1, 0.8, 0.1])
        radii.append(0.8)
        bonds = [[0, 2], [2, 1]]
    return Scene(
        positions=np.array(positions, dtype=float),
        symbols=symbols,
        radii=np.array(radii, dtype=float),
        colours=np.array(colours, dtype=float),
        bonds=np.array(bonds, dtype=int),
        lattice=np.zeros((3, 3)),
        pbc=(False, False, False),
    )


def _flat_style() -> Style:
    # Flat colours make the expected pixel values exact: colour == base.
    return Style(
        width_in=2.0,
        dpi=40,
        supersample=1,
        ambient=1.0,
        diffuse=0.0,
        specular=0.0,
        margin=0.05,
        bond_radius=0.08,
    )


def test_tracer_atom_occludes_bond():
    view = View([0.0, 1.0, 0.0])
    image = trace_image(_scene(True), view, _flat_style(), supersample=1)
    height, width = image.shape[:2]
    centre = image[height // 2, width // 2]
    # The green middle ball is in front of the stick.
    assert centre[1] > 0.5
    assert centre[0] < 0.5
    assert centre[2] < 0.5


def test_tracer_bond_visible_between_atoms():
    view = View([0.0, 1.0, 0.0])
    image = trace_image(_scene(False), view, _flat_style(), supersample=1)
    height, width = image.shape[:2]
    centre = image[height // 2, width // 2]
    # Without the middle atom the stick is exposed at the image centre
    # (one of the two half-colours; here the red half of the seam pixel).
    assert centre[:3].max() > 0.5
    assert centre[1] < 0.5  # not the green middle ball
    assert min(centre[0], centre[2]) < 0.2  # clearly one bond colour, not white


def test_tracer_background_is_opaque_white():
    view = View([0.0, 1.0, 0.0])
    image = trace_image(_scene(False), view, _flat_style(), supersample=1)
    corner = image[2, 2]
    assert np.allclose(corner[:3], 1.0, atol=1e-3)
    assert corner[3] == 1.0


def test_tracer_transparent_background():
    view = View([0.0, 1.0, 0.0])
    style = _flat_style()
    style.transparent = True
    image = trace_image(_scene(False), view, style, supersample=1)
    corner = image[2, 2]
    assert corner[3] == 0.0
    assert image.shape[2] == 4


def test_cell_frame_is_drawn():
    lattice = np.eye(3) * 4.0
    positions = np.array([[0.0, 0.0, 0.0], [2.5, 2.5, 2.5]])
    structure = Structure(lattice, positions, ["H", "H"], pbc=(True, True, True))
    style_on = Style(width_in=1.5, dpi=50, supersample=1, atom_scale=0.25)
    style_off = Style(
        width_in=1.5, dpi=50, supersample=1, atom_scale=0.25, draw_cell=False
    )
    view = View([0.0, 1.0, 0.0])
    with_frame = trace_image(build_scene(structure, style_on), view, style_on)
    without_frame = trace_image(build_scene(structure, style_off), view, style_off)
    assert with_frame.shape == without_frame.shape
    assert not np.allclose(with_frame, without_frame)


def test_perspective_changes_the_image():
    lattice = np.zeros((3, 3))
    positions = np.array([[-1.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 0.0, 1.5]])
    structure = Structure(lattice, positions, ["H", "H", "H"], pbc=(False, False, False))
    style_ortho = Style(width_in=1.5, dpi=50, supersample=1, perspective=0.0)
    style_persp = Style(width_in=1.5, dpi=50, supersample=1, perspective=0.35)
    view = View([0.0, 1.0, 0.0])
    ortho = trace_image(build_scene(structure, style_ortho), view, style_ortho)
    persp = trace_image(build_scene(structure, style_persp), view, style_persp)
    assert ortho.shape == persp.shape
    assert not np.allclose(ortho, persp)


def test_render_with_tracer_backend(tmp_path):
    style = Style(width_in=1.5, dpi=80, supersample=1)
    output = Path(
        render(
            DATA / "water.POSCAR",
            output=tmp_path / "water_tracer.png",
            view="auto",
            backend="tracer",
            style=style,
        )
    )
    assert output.exists()
    assert output.stat().st_size > 1000
