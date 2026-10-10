from pathlib import Path

import numpy as np
import pytest

from matvu import load_structure
from matvu.io.xyz import read_xyz

WATER_XYZ = """\
3
water molecule
O 0.00000 0.00000 0.11730
H 0.00000 0.75720 -0.46920
H 0.00000 -0.75720 -0.46920
"""

EXTXYZ = """\
2
Lattice="4.0 0.0 0.0 0.0 4.0 0.0 0.0 0.0 8.0" pbc="T T F" Properties=species:S:1:pos:R:3
Si 0.0 0.0 0.0
Si 2.0 2.0 2.0
"""


def test_read_plain_xyz_is_a_molecule():
    structure = read_xyz(WATER_XYZ)
    assert structure.formula == "H2O"
    assert structure.n_atoms == 3
    assert structure.volume == 0.0
    assert structure.pbc == (False, False, False)
    assert structure.info["comment"] == "water molecule"


def test_read_extxyz_lattice_and_pbc():
    structure = read_xyz(EXTXYZ)
    assert structure.n_atoms == 2
    assert structure.volume == pytest.approx(4.0 * 4.0 * 8.0)
    assert structure.pbc == (True, True, False)
    assert structure.lattice[2] == pytest.approx([0.0, 0.0, 8.0])
    assert np.allclose(structure.frac_coords[1], [0.5, 0.5, 0.25])


def test_xyz_atom_count_mismatch_raises():
    with pytest.raises(ValueError, match="declares 5 atoms"):
        read_xyz("5\ncomment\nH 0 0 0\n")


def test_xyz_row_must_have_symbol_and_coordinates():
    with pytest.raises(ValueError, match="symbol"):
        read_xyz("1\ncomment\nH 0 0\n")


def test_xyz_symbols_are_normalised():
    structure = read_xyz("1\ncomment\no 0.0 0.0 0.0\n")
    assert structure.symbols == ["O"]


def test_load_structure_sniffs_xyz(tmp_path):
    path = tmp_path / "water.xyz"
    path.write_text(WATER_XYZ)
    assert load_structure(path).formula == "H2O"
