"""Renderable scene and camera projection."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from . import elements
from .geometry import find_bonds
from .structure import Structure
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

    @property
    def n_atoms(self) -> int:
        return int(self.positions.shape[0])

    @property
    def n_bonds(self) -> int:
        return int(self.bonds.shape[0])


@dataclass
class Projection:
    """Orthographic projection of a scene onto the screen plane."""

    xy: np.ndarray
    depth: np.ndarray
    radii: np.ndarray
    basis: np.ndarray


def build_scene(structure: Structure, style: Style | None = None) -> Scene:
    """Turn a :class:`Structure` into a :class:`Scene` using a style."""
    style = style or Style()
    positions = structure.cart_coords - structure.center
    radii = (
        np.array([elements.covalent_radius(s) for s in structure.symbols])
        * style.atom_scale
    )
    radii = np.maximum(radii, style.min_atom_radius)
    colours = np.array([elements.colour_rgb(s) for s in structure.symbols])
    bonds = find_bonds(structure, tolerance=style.bond_tolerance)
    bond_array = np.asarray(bonds, dtype=int).reshape(-1, 2)
    return Scene(
        positions=positions,
        symbols=list(structure.symbols),
        radii=radii,
        colours=colours,
        bonds=bond_array,
        lattice=structure.lattice,
        pbc=structure.pbc,
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
