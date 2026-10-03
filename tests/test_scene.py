from pathlib import Path

from matvu import load_structure
from matvu.scene import CELL_EDGE_INDICES, build_scene, cell_corners
from matvu.style import Style

DATA = Path(__file__).resolve().parents[1] / "examples" / "structures"


def test_scene_carries_the_cell_frame():
    scene = build_scene(load_structure(DATA / "Si.POSCAR"))
    corners = cell_corners(scene)
    assert corners is not None
    assert corners.shape == (8, 3)
    assert len(CELL_EDGE_INDICES) == 12


def test_molecular_cell_has_no_frame():
    scene = build_scene(load_structure(DATA / "water.POSCAR"))
    assert cell_corners(scene) is None


def test_metal_metal_bonds_are_skipped_by_default():
    scene = build_scene(load_structure(DATA / "Cu.POSCAR"))
    assert scene.n_bonds == 0
    # With no bonds the atoms switch to the close-packing radius.
    assert scene.radii[0] > 1.0


def test_metal_metal_bonds_can_be_enabled():
    scene = build_scene(
        load_structure(DATA / "Cu.POSCAR"), Style(metal_metal_bonds=True)
    )
    assert scene.n_bonds == 6  # nearest-neighbour pairs inside the cell


def test_mos2_keeps_only_mo_s_bonds():
    scene = build_scene(load_structure(DATA / "MoS2.POSCAR"))
    symbols = scene.symbols
    assert scene.n_bonds == 2
    for i, j in scene.bonds:
        assert {symbols[i], symbols[j]} == {"Mo", "S"}


def test_unbonded_scale_is_not_used_when_bonds_exist():
    scene = build_scene(load_structure(DATA / "Si.POSCAR"))
    assert scene.n_bonds == 7  # bonds drawable inside the cell
    assert scene.radii[0] < 0.6  # normal ball-and-stick radius
