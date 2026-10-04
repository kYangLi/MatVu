"""Renderable scene and camera projection."""

from __future__ import annotations

import itertools
from dataclasses import dataclass

import numpy as np

from . import elements, palettes
from .geometry import find_bonds, principal_axes
from .structure import Structure, formula_from_symbols
from .style import Style


@dataclass
class Scene:
    """Backend-independent description of what to draw.

    Positions are centred on the structure's geometric centre. Bonds are
    index pairs into ``positions``.
    """

    positions: np.ndarray
    symbols: list[str]
    radii: np.ndarray
    colours: np.ndarray
    bonds: np.ndarray
    lattice: np.ndarray | None = None
    pbc: tuple[bool, bool, bool] = (True, True, True)

    cell_origin: np.ndarray | None = None
    n_core: int | None = None

    @property
    def n_atoms(self) -> int:
        return int(self.positions.shape[0])

    @property
    def n_bonds(self) -> int:
        return int(self.bonds.shape[0])

    @property
    def formula(self) -> str:
        """Compact formula of the structure (boundary images excluded)."""
        symbols = self.symbols if self.n_core is None else self.symbols[: self.n_core]
        return formula_from_symbols(symbols)


SLAB_FLATNESS = 0.45
MOLECULAR_SPAN = 0.5
_SPAN_TOLERANCE = 1e-6


def _spans_like_molecule(fractional: np.ndarray) -> bool:
    """True when atoms occupy clearly less than the full cell in every axis."""
    if fractional.size == 0:
        return False
    return float(np.ptp(fractional, axis=0).max()) < MOLECULAR_SPAN - _SPAN_TOLERANCE


def molecular_box(scene: Scene) -> bool:
    """True when the cell is just a vacuum box around a finite molecule."""
    if scene.cell_origin is None or scene.lattice is None:
        return False
    if abs(np.linalg.det(scene.lattice)) < 1e-9:
        return False
    if scene.n_atoms == 0:
        return False
    fractional = (scene.positions - scene.cell_origin) @ np.linalg.inv(scene.lattice)
    return _spans_like_molecule(fractional)


def slab_normal(scene: Scene, *, flatness: float = SLAB_FLATNESS) -> np.ndarray | None:
    """Normal of a quasi-2D slab (layered material), or ``None``.

    Molecular vacuum boxes are excluded, so flat molecules are not slabs.
    """
    if scene.n_atoms < 3:
        return None
    if scene.cell_origin is None or scene.lattice is None:
        return None
    if abs(np.linalg.det(scene.lattice)) < 1e-9:
        return None
    if molecular_box(scene):
        return None
    weights = np.array([elements.atomic_mass(s) for s in scene.symbols])
    values, axes = principal_axes(scene.positions, weights)
    if values[0] <= 1e-12:
        return None
    thickness = float(np.sqrt(max(values[2], 0.0)))
    width = float(np.sqrt(values[0]))
    if width <= 1e-12 or thickness > flatness * width:
        return None
    return axes[:, 2].astype(float)


# Index pairs of the 12 edges of a cube (corner bit order: i*4 + j*2 + k).
CELL_EDGE_INDICES: list[tuple[int, int]] = [
    (corner, corner | bit)
    for corner in range(8)
    for bit in (4, 2, 1)
    if not corner & bit
]


def cell_corners(scene: Scene) -> np.ndarray | None:
    """Eight corners of the displayed cell in scene coordinates, or ``None``.

    Returns ``None`` for non-periodic, zero-volume, *molecular* and *slab*
    cells: molecules (atoms occupying less than half of every lattice
    direction) and 2D layered materials do not get a frame.
    """
    if scene.cell_origin is None or scene.lattice is None:
        return None
    if not any(scene.pbc):
        return None
    if abs(np.linalg.det(scene.lattice)) < 1e-9:
        return None
    if molecular_box(scene):
        return None
    if slab_normal(scene) is not None:
        return None  # 2D materials: no box edges
    if scene.n_atoms == 0:
        return None
    fractional = (scene.positions - scene.cell_origin) @ np.linalg.inv(scene.lattice)
    if float(np.ptp(fractional, axis=0).max()) < 0.5:
        return None
    origin = np.asarray(scene.cell_origin, dtype=float)
    lattice = np.asarray(scene.lattice, dtype=float)
    return np.array(
        [
            origin + i * lattice[0] + j * lattice[1] + k * lattice[2]
            for i in (0.0, 1.0)
            for j in (0.0, 1.0)
            for k in (0.0, 1.0)
        ]
    )


@dataclass
class Projection:
    """Orthographic projection of a scene onto the screen plane."""

    xy: np.ndarray
    depth: np.ndarray
    radii: np.ndarray
    basis: np.ndarray


def _boundary_images(structure: Structure, margin: float) -> Structure:
    """Mirror boundary atoms into a thin margin outside the cell.

    Atoms sitting on (or close to) the cell faces get their periodic copies on
    the opposite faces, so the cell looks symmetric and complete (the classic
    VESTA-style figure). Copies that end up isolated are dropped later by
    :func:`build_scene`. ``margin = 0`` disables the decoration.
    """
    if margin <= 0.0 or structure.n_atoms == 0:
        return structure
    if structure.volume < 1e-12 or not any(structure.pbc):
        return structure
    fractional = structure.frac_coords
    if _spans_like_molecule(fractional):
        return structure  # molecular vacuum box

    existing = structure.cart_coords
    kept_blocks = [existing]
    images: list[np.ndarray] = []
    symbols: list[str] = []
    for shift in itertools.product((-1.0, 0.0, 1.0), repeat=3):
        if shift == (0.0, 0.0, 0.0):
            continue
        shifted = fractional + np.asarray(shift)
        inside = np.all((shifted >= -margin) & (shifted <= 1.0 + margin), axis=1)
        for index in np.where(inside)[0]:
            cart = shifted[index] @ structure.lattice
            if any(
                float(np.linalg.norm(block - cart, axis=1).min()) < 1e-6
                for block in kept_blocks
            ):
                continue
            images.append(cart)
            symbols.append(structure.symbols[index])
            kept_blocks.append(cart.reshape(1, 3))
    if not images:
        return structure
    new_cart = np.vstack([existing, np.asarray(images)])
    new_symbols = list(structure.symbols) + symbols
    return Structure(
        structure.lattice, new_cart, new_symbols, structure.pbc, dict(structure.info)
    )


def build_scene(structure: Structure, style: Style | None = None) -> Scene:
    """Turn a :class:`Structure` into a :class:`Scene` using a style.

    Periodic boundary atoms are mirrored into a thin margin outside the cell
    (``Style.boundary_padding``) so the cell looks complete and boundary
    bonds are drawn. Metal-metal pairs are not bonded by default
    (``Style.metal_metal_bonds`` re-enables them). When a structure ends up
    with no bonds at all, atoms are drawn at ``Style.unbonded_atom_scale``
    (clear lattice spheres, useful for bulk metals).
    """
    style = style or Style()
    working = _boundary_images(structure, style.boundary_padding)
    positions = working.cart_coords - working.center
    symbols = list(working.symbols)
    bonds = find_bonds(working, tolerance=style.bond_tolerance)
    if not style.metal_metal_bonds:
        bonds = [
            (i, j)
            for i, j in bonds
            if not (elements.is_metal(symbols[i]) and elements.is_metal(symbols[j]))
        ]
    # Drop mirror images that ended up completely unbonded (their bonding
    # partners would live further outside the margin); keep them for
    # bond-free structures such as bulk metals.
    if working.n_atoms > structure.n_atoms and bonds:
        used = np.zeros(working.n_atoms, dtype=bool)
        for i, j in bonds:
            used[i] = used[j] = True
        keep = used | (np.arange(working.n_atoms) < structure.n_atoms)
        if not keep.all():
            working = Structure(
                working.lattice,
                working.cart_coords[keep],
                [s for s, k in zip(working.symbols, keep) if k],
                working.pbc,
                dict(working.info),
            )
            remap = np.cumsum(keep) - 1
            bonds = [(int(remap[i]), int(remap[j])) for i, j in bonds]
            positions = working.cart_coords - working.center
            symbols = list(working.symbols)
    if bonds or structure.n_atoms <= 1:
        scale = style.atom_scale
    else:
        scale = style.unbonded_atom_scale
    radii = (
        np.array([elements.covalent_radius(s) for s in symbols]) * scale
    )
    radii = np.maximum(radii, style.min_atom_radius)
    colours = np.array(
        [
            palettes.colour_rgb(style.palette, symbol, style.palette_overrides)
            for symbol in symbols
        ]
    )
    bond_array = np.asarray(bonds, dtype=int).reshape(-1, 2)
    return Scene(
        positions=positions,
        symbols=symbols,
        radii=radii,
        colours=colours,
        bonds=bond_array,
        lattice=structure.lattice,
        pbc=structure.pbc,
        cell_origin=-working.center,
        n_core=structure.n_atoms,
    )


def project(scene: Scene, view) -> Projection:
    """Orthographic projection; larger ``depth`` means closer to the camera."""
    basis = view.basis
    view_coords = scene.positions @ basis.T
    return Projection(
        xy=view_coords[:, :2],
        depth=view_coords[:, 2],
        radii=scene.radii.copy(),
        basis=basis,
    )
