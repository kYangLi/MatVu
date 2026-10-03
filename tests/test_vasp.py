from pathlib import Path

import numpy as np
import pytest

from matvu import Structure, load_structure

DATA = Path(__file__).resolve().parents[1] / "examples" / "structures"


def test_read_si_poscar():
    structure = load_structure(DATA / "Si.POSCAR")
    assert isinstance(structure, Structure)
    assert structure.n_atoms == 8
    assert set(structure.symbols) == {"Si"}
    assert structure.volume == pytest.approx(5.43**3, rel=1e-6)
    assert structure.frac_coords.shape == (8, 3)


def test_vasp4_without_species_line():
    text = (
        "Si 8\n5.43\n1 0 0\n0 1 0\n0 0 1\n8\ndirect\n"
        + "\n".join(["0 0 0"] * 8)
    )
    structure = load_structure(text)
    assert structure.n_atoms == 8
    assert set(structure.symbols) == {"Si"}


def test_scale_applies_to_lattice_and_cartesian():
    text = "test\n2.0\n1 0 0\n0 1 0\n0 0 1\nH\n1\ncartesian\n1 0 0\n"
    structure = load_structure(text)
    assert structure.lattice[0, 0] == pytest.approx(2.0)
    assert structure.cart_coords[0, 0] == pytest.approx(2.0)


def test_negative_scale_is_interpreted_as_volume():
    text = "test\n-8.0\n1 0 0\n0 1 0\n0 0 1\nH\n1\ndirect\n0 0 0\n"
    structure = load_structure(text)
    assert structure.volume == pytest.approx(8.0, rel=1e-6)


def test_selective_dynamics_is_skipped():
    text = (
        "test\n1.0\n1 0 0\n0 1 0\n0 0 1\nH\n1\n"
        "Selective dynamics\ndirect\n0 0 0 T T T\n"
    )
    structure = load_structure(text)
    assert structure.n_atoms == 1


def test_cartesian_keyword():
    text = "test\n1.0\n1 0 0\n0 1 0\n0 0 1\nH\n1\nCartesian\n0.5 0.5 0.5\n"
    structure = load_structure(text)
    assert np.allclose(structure.cart_coords[0], [0.5, 0.5, 0.5])


def test_missing_position_lines_raise():
    text = "test\n1.0\n1 0 0\n0 1 0\n0 0 1\nH\n2\ndirect\n0 0 0\n"
    with pytest.raises(ValueError):
        load_structure(text)


def test_graphene_and_water_fixtures():
    graphene = load_structure(DATA / "graphene.POSCAR")
    assert graphene.n_atoms == 2
    assert set(graphene.symbols) == {"C"}
    water = load_structure(DATA / "water.POSCAR")
    assert water.n_atoms == 3
    assert water.symbols[0] == "O"


def test_formula_hill_order():
    water = load_structure(DATA / "water.POSCAR")
    assert water.formula == "H2O"
    nacl = load_structure(DATA / "NaCl.POSCAR")
    assert nacl.formula == "Cl4Na4"
