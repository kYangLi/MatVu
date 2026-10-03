"""Renderable scene and camera projection."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from . import elements
from .geometry import find_bonds
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

    @property
    def n_atoms(self) -> int:
        return int(self.positions.shape[0])

    @property
    def n_bonds(self) -> int:
        return int(self.bonds.shape[0])

    @property
    def formula(self) -> str:
        """Compact formula of the scene contents."""
        return formula_from_symbols(self.symbols)


# Index pairs of the 12 edges of a cube (corner bit order: i*4 + j*2 + k).
CELL_EDGE_INDICES: list[tuple[int, int]] = [
    (corner, corner | bit)
    for corner in range(8)
    for bit in (4, 2, 1)
    if not corner & bit
]


def cell_corners(scene: Scene) -> np.ndarray | None:
    """Eight corners of the displayed cell in scene coordinates, or ``None``.

    Returns ``None`` for non-periodic, zero-volume *and molecular* cells:
    when the atoms occupy less than half of every lattice direction the cell
    is treated as a vacuum box around a molecule and no frame is drawn.
    """
    if scene.cell_origin is None or scene.lattice is None:
        return None
    if not any(scene.pbc):
        return None
    if abs(np.linalg.det(scene.lattice)) < 1e-9:
        return None
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


def build_scene(structure: Structure, style: Style | None = None) -> Scene:
    """Turn a :class:`Structure` into a :class:`Scene` using a style.

    Metal-metal pairs are not bonded by default (``Style.metal_metal_bonds``
    re-enables them). When a structure ends up with no bonds at all, atoms
    are drawn at ``Style.unbonded_atom_scale`` (close-packing look, useful
    for bulk metals).
    """
    style = style or Style()
    positions = structure.cart_coords - structure.center
    symbols = list(structure.symbols)
    bonds = find_bonds(structure, tolerance=style.bond_tolerance)
    if not style.metal_metal_bonds:
        bonds = [
            (i, j)
            for i, j in bonds
            if not (elements.is_metal(symbols[i]) and elements.is_metal(symbols[j]))
        ]
    if bonds or structure.n_atoms <= 1:
        scale = style.atom_scale
    else:
        scale = style.unbonded_atom_scale
    radii = (
        np.array([elements.covalent_radius(s) for s in symbols]) * scale
    )
    radii = np.maximum(radii, style.min_atom_radius)
    colours = np.array([elements.colour_rgb(s) for s in symbols])
    bond_array = np.asarray(bonds, dtype=int).reshape(-1, 2)
    return Scene(
        positions=positions,
        symbols=symbols,
        radii=radii,
        colours=colours,
        bonds=bond_array,
        lattice=structure.lattice,
        pbc=structure.pbc,
        cell_origin=-structure.center,
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
