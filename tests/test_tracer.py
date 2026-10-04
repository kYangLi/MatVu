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


def test_tracer_opaque_background_can_be_requested():
    view = View([0.0, 1.0, 0.0])
    style = _flat_style()
    style.transparent = False
    image = trace_image(_scene(False), view, style, supersample=1)
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


def test_default_style_is_transparent():
    from matvu.style import Style

    default_style = Style()
    view = View([0.0, 1.0, 0.0])
    image = trace_image(_scene(False), view, default_style, supersample=1)
    assert image[2, 2, 3] == 0.0


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


def test_depth_cue_fades_distant_atoms():
    view = View([1.0, 0.0, 0.0])  # depths vary along this view
    plain_style = _flat_style()
    plain_style.shading = False
    plain_style.depth_cue = 0.0
    faded_style = _flat_style()
    faded_style.shading = False
    faded_style.depth_cue = 0.5
    plain = trace_image(_scene(True), view, plain_style, supersample=1)
    faded = trace_image(_scene(True), view, faded_style, supersample=1)
    assert not np.allclose(plain, faded)
    # distant surfaces are mixed towards the white background
    assert faded[:, :, :3].mean() > plain[:, :, :3].mean()


def test_flat_shading_uses_exact_colour():
    view = View([0.0, 1.0, 0.0])
    style = _flat_style()
    style.shading = False
    style.perspective = 0.0
    image = trace_image(_scene(True), view, style, supersample=1)
    height, width = image.shape[:2]
    centre = image[height // 2, width // 2]
    assert np.allclose(centre[:3], [0.1, 0.8, 0.1], atol=1e-3)


def _dark_runs(row) -> list[int]:
    runs: list[int] = []
    current = 0
    for value in row:
        if value:
            current += 1
        elif current:
            runs.append(current)
            current = 0
    if current:
        runs.append(current)
    return runs


def _single_atom_scene(extra: float | None = None) -> Scene:
    positions = [[0.0, 0.0, 0.0]]
    if extra is not None:
        positions.append([extra, 0.0, 0.0])
    number = len(positions)
    return Scene(
        positions=np.array(positions),
        symbols=["C"] * number,
        radii=np.full(number, 0.4),
        colours=np.tile([0.2, 0.2, 0.2], (number, 1)),
        bonds=np.zeros((0, 2), dtype=int),
        lattice=np.zeros((3, 3)),
        pbc=(False, False, False),
    )


def test_fixed_canvas_keeps_atom_sizes_and_canvas_constant():
    style = Style(
        canvas=(8.0, 8.0),
        width_in=2.0,
        dpi=100,
        supersample=1,
        shading=False,
        transparent=False,
    )
    view = View([0.0, 1.0, 0.0])
    single = trace_image(_single_atom_scene(), view, style, supersample=1)
    pair = trace_image(_single_atom_scene(3.0), view, style, supersample=1)
    assert single.shape[:2] == pair.shape[:2] == (200, 200)
    single_runs = _dark_runs(single[single.shape[0] // 2, :, 0] < 0.5)
    pair_runs = _dark_runs(pair[pair.shape[0] // 2, :, 0] < 0.5)
    assert len(single_runs) == 1
    assert len(pair_runs) == 2
    # identical atom diameter in pixels in both figures
    assert abs(single_runs[0] - pair_runs[0]) <= 2
    assert abs(pair_runs[0] - pair_runs[1]) <= 2


def test_fixed_canvas_aspect():
    style = Style(canvas=(8.0, 4.0), width_in=2.0, dpi=100, supersample=1)
    view = View([0.0, 1.0, 0.0])
    image = trace_image(_single_atom_scene(), view, style, supersample=1)
    assert image.shape[:2] == (100, 200)


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
