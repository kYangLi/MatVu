from pathlib import Path

import numpy as np
import pytest

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


def test_slab_cells_have_no_frame():
    graphene = load_structure(DATA / "graphene.POSCAR").supercell((3, 3, 1))
    assert cell_corners(build_scene(graphene)) is None


def test_atom_radii_strictly_follow_covalent_radii():
    scene = build_scene(load_structure(DATA / "water.POSCAR"))
    # O (0.66 A) and H (0.31 A) keep their exact ratio at the same scale.
    assert scene.radii[0] == pytest.approx(0.40 * 0.66, rel=1e-9)
    assert scene.radii[1] == pytest.approx(0.40 * 0.31, rel=1e-9)


def test_hydrogen_colour_is_visible():
    from matvu import palettes

    for name in palettes.palette_names():
        assert max(palettes.colour_rgb(name, "H")) < 0.9  # not invisible white


def test_boundary_mirror_copies_decorate_the_cell():
    scene = build_scene(load_structure(DATA / "NaCl.POSCAR"))
    assert scene.n_atoms == 27  # classic rocksalt cell figure
    assert scene.formula == "Cl4Na4"  # the reported formula stays the cell content
    silicon = build_scene(load_structure(DATA / "Si.POSCAR"))
    assert silicon.n_atoms == 14
    assert silicon.formula == "Si8"


def test_metal_metal_bonds_are_skipped_by_default():
    scene = build_scene(load_structure(DATA / "Cu.POSCAR"))
    assert scene.n_bonds == 0
    # distinct lattice spheres, clearly separated (not close-packed)
    assert scene.radii[0] == pytest.approx(0.45 * 1.32, rel=1e-6)
    assert scene.formula == "Cu4"  # boundary images do not change the formula


def test_boundary_images_mirror_boundary_atoms():
    scene = build_scene(load_structure(DATA / "Cu.POSCAR"))
    fractional = (scene.positions - scene.cell_origin) @ np.linalg.inv(scene.lattice)
    assert scene.n_atoms > 4
    assert fractional.max() >= 1.0 - 1e-9
    assert np.any(np.all(np.isclose(fractional, [1.0, 0.0, 0.0]), axis=1))


def test_boundary_padding_can_be_disabled():
    scene = build_scene(
        load_structure(DATA / "Cu.POSCAR"), Style(boundary_padding=0.0)
    )
    assert scene.n_atoms == 4


def test_metal_metal_bonds_can_be_enabled():
    scene = build_scene(
        load_structure(DATA / "Cu.POSCAR"),
        Style(metal_metal_bonds=True, boundary_padding=0.0),
    )
    assert scene.n_bonds == 6  # nearest-neighbour pairs inside the cell


def test_mos2_keeps_only_mo_s_bonds():
    scene = build_scene(
        load_structure(DATA / "MoS2.POSCAR"), Style(boundary_padding=0.0)
    )
    symbols = scene.symbols
    assert scene.n_bonds == 2
    for i, j in scene.bonds:
        assert {symbols[i], symbols[j]} == {"Mo", "S"}


def test_unbonded_scale_is_not_used_when_bonds_exist():
    scene = build_scene(
        load_structure(DATA / "Si.POSCAR"), Style(boundary_padding=0.0)
    )
    assert scene.n_bonds == 7  # bonds drawable inside the cell
    assert scene.radii[0] < 0.6  # normal ball-and-stick radius
