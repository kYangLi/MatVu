import numpy as np

from matvu import Structure, View
from matvu.scene import build_scene
from matvu.viewpoint import (
    fibonacci_sphere,
    pick_view,
    projected_dispersion,
    score,
    slab_normal,
)


def _chain() -> Structure:
    positions = np.column_stack([np.arange(5) * 1.42, np.zeros(5), np.zeros(5)])
    return Structure(np.zeros((3, 3)), positions, ["C"] * 5, pbc=(False, False, False))


def _ring() -> Structure:
    angles = np.linspace(0.0, 2.0 * np.pi, 6, endpoint=False)
    radius = 1.42
    positions = np.column_stack(
        [radius * np.cos(angles), radius * np.sin(angles), np.zeros(6)]
    )
    return Structure(np.zeros((3, 3)), positions, ["C"] * 6, pbc=(False, False, False))


def test_fibonacci_sphere_is_unit_and_deterministic():
    first = fibonacci_sphere(50)
    second = fibonacci_sphere(50)
    assert first.shape == (50, 3)
    assert np.allclose(np.linalg.norm(first, axis=1), 1.0)
    assert np.allclose(first, second)


def test_chain_view_is_perpendicular_to_the_chain():
    scene = build_scene(_chain())
    view = pick_view(scene, seed=0)
    assert abs(float(view.direction[0])) < 0.4


def test_ring_prefers_face_on_view():
    scene = build_scene(_ring())
    face_on = score(scene, View([0.0, 0.0, 1.0]))["score"]
    edge_on = score(scene, View([1.0, 0.0, 0.0]))["score"]
    assert face_on > edge_on
    view = pick_view(scene, seed=0)
    assert abs(float(view.direction[2])) > 0.8


def test_score_is_bounded_and_finite():
    scene = build_scene(_chain())
    result = score(scene, View([0.0, 1.0, 0.0]))
    assert 0.0 <= result["score"] <= 1.0
    for key in ("occlusion", "bond_penalty", "aspect_penalty"):
        assert np.isfinite(result[key])


def test_view_angles():
    azimuth, elevation = View([1.0, 0.0, 0.0]).angles_deg()
    assert azimuth == 0.0
    assert elevation == 0.0
    _, elevation = View([0.0, 0.0, 1.0]).angles_deg()
    assert elevation == 90.0


def test_slab_normal_only_for_layered_periodic_structures():
    from pathlib import Path

    from matvu import load_structure

    data = Path(__file__).resolve().parents[1] / "examples" / "structures"
    graphene = load_structure(data / "graphene.POSCAR").supercell((3, 3, 1))
    normal = slab_normal(build_scene(graphene))
    assert normal is not None
    assert abs(float(normal[2])) > 0.99
    assert slab_normal(build_scene(load_structure(data / "Si.POSCAR"))) is None
    assert slab_normal(build_scene(load_structure(data / "water.POSCAR"))) is None


def test_graphene_auto_view_is_tilted():
    from pathlib import Path

    from matvu import load_structure

    data = Path(__file__).resolve().parents[1] / "examples" / "structures"
    scene = build_scene(load_structure(data / "graphene.POSCAR").supercell((3, 3, 1)))
    view = pick_view(scene, seed=0)
    angle = float(np.degrees(np.arccos(abs(float(view.direction[2])))))
    assert 10.0 < angle < 65.0


def test_view_json_round_trip(tmp_path):
    view = View([0.3, -0.5, 0.8])
    path = tmp_path / "view.json"
    view.to_json(path)
    loaded = View.from_json(path)
    assert np.allclose(loaded.direction, view.direction)
    assert np.allclose(loaded.up_hint, view.up_hint)
    assert np.allclose(View.from_json(view.to_json()).direction, view.direction)
    assert np.allclose(View.from_dict(view.to_dict()).direction, view.direction)


def test_cubic_crystals_share_one_view():
    from pathlib import Path

    from matvu import load_structure

    data = Path(__file__).resolve().parents[1] / "examples" / "structures"
    views = []
    for name in ("Si.POSCAR", "NaCl.POSCAR", "ZnS.POSCAR", "Cu.POSCAR"):
        scene = build_scene(load_structure(data / name))
        views.append(pick_view(scene, seed=0).direction)
    for direction in views[1:]:
        assert np.allclose(direction, views[0], atol=1e-9)


def test_crystal_views_stay_in_comfortable_band():
    from pathlib import Path

    from matvu import load_structure

    data = Path(__file__).resolve().parents[1] / "examples" / "structures"
    scene = build_scene(load_structure(data / "Cu.POSCAR"))
    view = pick_view(scene, seed=0)
    elevation = view.angles_deg()[1]
    assert 5.0 <= elevation <= 65.0


def test_auto_views_look_from_above():
    from pathlib import Path

    from matvu import load_structure

    data = Path(__file__).resolve().parents[1] / "examples" / "structures"
    for name in ("Si.POSCAR", "NaCl.POSCAR", "Cu.POSCAR", "graphene.POSCAR"):
        scene = build_scene(load_structure(data / name))
        view = pick_view(scene, seed=0)
        assert view.angles_deg()[1] >= 0.0, name


def test_dispersion_drives_non_cubic_crystal_views():
    from pathlib import Path

    from matvu import load_structure

    data = Path(__file__).resolve().parents[1] / "examples" / "structures"
    base = load_structure(data / "Cu.POSCAR")

    # fcc columns coincide when looking along the cubic c axis
    cubic_scene = build_scene(base.supercell((2, 2, 2)))
    assert projected_dispersion(cubic_scene, View([0.0, 0.0, 1.0])) < 1e-9

    # a tetragonal distortion breaks the cubic convention; there the maximin
    # dispersion drives the viewpoint choice
    tetragonal = Structure(
        np.diag([3.615, 3.615, 5.4]), base.cart_coords, base.symbols
    )
    scene = build_scene(tetragonal)
    view = pick_view(scene, seed=0)
    assert projected_dispersion(scene, view) > 0.2
