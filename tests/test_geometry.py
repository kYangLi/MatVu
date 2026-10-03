from pathlib import Path

import numpy as np
import pytest

from matvu import load_structure
from matvu.geometry import (
    cell_params,
    distance_matrix,
    find_bonds,
    minimum_image,
    principal_axes,
)

DATA = Path(__file__).resolve().parents[1] / "examples" / "structures"


def test_minimum_image_wraps_to_nearest_image():
    lattice = np.eye(3) * 10.0
    wrapped = minimum_image(np.array([9.0, 0.0, 0.0]), lattice, (True, True, True))
    assert np.allclose(wrapped, [-1.0, 0.0, 0.0])


def test_minimum_image_respects_pbc_flags():
    lattice = np.eye(3) * 10.0
    wrapped = minimum_image(np.array([9.0, 0.0, 0.0]), lattice, (False, True, True))
    assert np.allclose(wrapped, [9.0, 0.0, 0.0])


def test_si_diamond_coordination_and_cell_bonds():
    si = load_structure(DATA / "Si.POSCAR")
    # Chemical neighbours: every atom has four bonds at a*sqrt(3)/4.
    bond_length = 5.43 * np.sqrt(3) / 4
    periodic_bonds = find_bonds(si, use_mic=True)
    assert len(periodic_bonds) == 16
    distances = distance_matrix(si)
    for i, j in periodic_bonds:
        assert distances[i, j] == pytest.approx(bond_length, abs=1e-6)
    # Drawable bonds only connect atoms that physically live in the cell.
    cell_bonds = find_bonds(si)
    assert 0 < len(cell_bonds) < len(periodic_bonds)


def test_nacl_bonds_within_cell():
    nacl = load_structure(DATA / "NaCl.POSCAR")
    assert len(find_bonds(nacl)) == 12


def test_water_has_two_oh_bonds():
    water = load_structure(DATA / "water.POSCAR")
    bonds = find_bonds(water)
    assert len(bonds) == 2
    distances = distance_matrix(water)
    for i, j in bonds:
        assert distances[i, j] == pytest.approx(0.9572, abs=1e-3)


def test_principal_axes_of_elongated_cloud():
    coords = np.column_stack([np.arange(5) * 2.0, np.zeros(5), np.zeros(5)])
    values, axes = principal_axes(coords)
    assert abs(axes[0, 0]) == pytest.approx(1.0, abs=1e-6)
    assert values[0] > values[1] >= 0.0


def test_cell_params_cubic():
    params = cell_params(np.eye(3) * 5.0)
    assert params["a"] == pytest.approx(5.0)
    assert params["alpha"] == pytest.approx(90.0)


def test_supercell_repeats_and_scales():
    si = load_structure(DATA / "Si.POSCAR")
    big = si.supercell((2, 1, 1))
    assert big.n_atoms == 16
    assert big.volume == pytest.approx(2 * si.volume)
    assert big.lattice[0, 0] == pytest.approx(2 * si.lattice[0, 0])
