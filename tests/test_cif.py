import numpy as np
import pytest

from matvu import load_structure
from matvu.geometry import cell_params
from matvu.io.cif import lattice_from_parameters, read_cif

NACL_CIF = """\
data_NaCl
_cell_length_a 5.6402(3)
_cell_length_b 5.6402
_cell_length_c 5.6402
_cell_angle_alpha 90
_cell_angle_beta 90
_cell_angle_gamma 90
loop_
_atom_site_label
_atom_site_type_symbol
_atom_site_fract_x
_atom_site_fract_y
_atom_site_fract_z
Na1 Na 0 0 0
Cl1 Cl 0.5 0.5 0.5
"""

SYMMETRY_CIF = """\
data_expansion
_cell_length_a 4.0
_cell_length_b 4.0
_cell_length_c 6.0
_cell_angle_alpha 90
_cell_angle_beta 90
_cell_angle_gamma 90
loop_
_symmetry_equiv_pos_site_id
_symmetry_equiv_pos_as_xyz
1 'x, y, z'
2 '1/2+x, 1/2-y, z'
loop_
_atom_site_label
_atom_site_fract_x
_atom_site_fract_y
_atom_site_fract_z
C1 0.25 0.25 0.5
"""


def test_read_simple_cif():
    structure = read_cif(NACL_CIF)
    assert structure.formula == "ClNa"
    assert structure.n_atoms == 2
    assert structure.volume == pytest.approx(5.6402**3, rel=1e-6)
    assert structure.info["format"] == "cif"


def test_cif_symmetry_expansion_and_deduplication():
    structure = read_cif(SYMMETRY_CIF)
    assert structure.n_atoms == 2
    fractional = np.sort(structure.frac_coords % 1.0, axis=0)
    assert fractional[0] == pytest.approx([0.25, 0.25, 0.5])
    assert fractional[1] == pytest.approx([0.75, 0.25, 0.5])
    assert structure.info["symmetry_operations"] == 2


def test_cif_operations_that_map_onto_themselves_are_deduplicated():
    text = """\
data_dedup
_cell_length_a 3
_cell_length_b 3
_cell_length_c 3
_cell_angle_alpha 90
_cell_angle_beta 90
_cell_angle_gamma 90
loop_
_symmetry_equiv_pos_as_xyz
'x, y, z'
'-x, -y, -z'
loop_
_atom_site_label
_atom_site_fract_x
_atom_site_fract_y
_atom_site_fract_z
Na1 0 0 0
Cl1 0.5 0.5 0.5
"""
    assert read_cif(text).n_atoms == 2


def test_cif_zero_occupancy_sites_are_dropped():
    text = """\
data_occupancy
_cell_length_a 3
_cell_length_b 3
_cell_length_c 3
_cell_angle_alpha 90
_cell_angle_beta 90
_cell_angle_gamma 90
loop_
_atom_site_label
_atom_site_fract_x
_atom_site_fract_y
_atom_site_fract_z
_atom_site_occupancy
H1 0 0 0 1
H2 0.5 0.5 0.5 0
"""
    structure = read_cif(text)
    assert structure.n_atoms == 1


def test_lattice_from_parameters_convention():
    lattice = lattice_from_parameters(3.0, 3.0, 5.0, 90.0, 90.0, 120.0)
    assert lattice[0] == pytest.approx([3.0, 0.0, 0.0])
    assert lattice[1] == pytest.approx([-1.5, 3.0 * np.sqrt(3.0) / 2.0, 0.0])
    assert lattice[2] == pytest.approx([0.0, 0.0, 5.0])
    params = cell_params(lattice)
    assert params["a"] == pytest.approx(3.0)
    assert params["c"] == pytest.approx(5.0)
    assert params["gamma"] == pytest.approx(120.0)


@pytest.mark.parametrize(
    "header",
    [
        "_symmetry_equiv_pos_as_xyz",
        "_space_group_symop_operation_xyz",
        "_space_group_symop.operation_xyz",
    ],
)
def test_cif_symmetry_header_aliases(header):
    text = f"""\
data_alias
_cell_length_a 4
_cell_length_b 4
_cell_length_c 4
_cell_angle_alpha 90
_cell_angle_beta 90
_cell_angle_gamma 90
loop_
{header}
'x, y, z'
'1/2+x, 1/2+y, 1/2+z'
loop_
_atom_site_type_symbol
_atom_site_fract_x
_atom_site_fract_y
_atom_site_fract_z
Si 0 0 0
"""
    assert read_cif(text).n_atoms == 2


def test_cif_without_cell_raises():
    with pytest.raises(ValueError, match="cell parameters"):
        read_cif(
            "data_x\nloop_\n_atom_site_label\n_atom_site_fract_x\n"
            "_atom_site_fract_y\n_atom_site_fract_z\nH1 0 0 0\n"
        )


def test_load_structure_sniffs_cif(tmp_path):
    path = tmp_path / "sample.cif"
    path.write_text(NACL_CIF)
    structure = load_structure(path)
    assert structure.formula == "ClNa"
    assert structure.n_atoms == 2
