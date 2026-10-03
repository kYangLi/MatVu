"""Geometry helpers: minimum image, distances, bonds, principal axes."""

from __future__ import annotations

import numpy as np

from . import elements
from .structure import Structure


def minimum_image(
    delta: np.ndarray,
    lattice: np.ndarray,
    pbc: tuple[bool, bool, bool] = (True, True, True),
) -> np.ndarray:
    """Wrap displacement vector(s) into the nearest periodic image.

    Works for a single ``(3,)`` vector or a stacked ``(..., 3)`` array.
    """
    delta = np.asarray(delta, dtype=float)
    if abs(np.linalg.det(lattice)) < 1e-12:
        return delta
    if not any(pbc):
        return delta
    frac = delta @ np.linalg.inv(lattice)
    shifts = np.zeros_like(frac)
    for axis, periodic in enumerate(pbc):
        if periodic:
            shifts[..., axis] = np.round(frac[..., axis])
    return delta - shifts @ lattice


def distance_matrix(structure: Structure, *, mic: bool = True) -> np.ndarray:
    """Full ``(N, N)`` distance matrix in Angstrom."""
    positions = structure.cart_coords
    delta = positions[:, None, :] - positions[None, :, :]
    if mic:
        delta = minimum_image(delta, structure.lattice, structure.pbc)
    return np.linalg.norm(delta, axis=-1)


def find_bonds(
    structure: Structure,
    *,
    tolerance: float = 1.2,
    min_distance: float = 0.1,
    use_mic: bool = False,
) -> list[tuple[int, int]]:
    """Distance-based bond list ``[(i, j), ...]`` with ``i < j``.

    Two atoms are bonded when their distance is below
    ``tolerance * (r_cov(i) + r_cov(j))``.

    By default only bonds whose *direct* distance passes the test are
    returned, so every bond can be drawn inside the displayed cell. Set
    ``use_mic=True`` for the chemical neighbour list of an infinite crystal.
    """
    delta = structure.cart_coords[:, None, :] - structure.cart_coords[None, :, :]
    if use_mic:
        delta = minimum_image(delta, structure.lattice, structure.pbc)
    distances = np.linalg.norm(delta, axis=-1)
    radii = np.array([elements.covalent_radius(s) for s in structure.symbols])
    cutoffs = tolerance * (radii[:, None] + radii[None, :])
    np.fill_diagonal(distances, np.inf)
    bonded = (distances <= cutoffs) & (distances > min_distance)
    rows, cols = np.where(np.triu(bonded, k=1))
    return list(zip(rows.tolist(), cols.tolist()))


def principal_axes(
    coords: np.ndarray, weights: np.ndarray | None = None
) -> tuple[np.ndarray, np.ndarray]:
    """Principal axes of the point cloud (columns of the returned matrix).

    Returns ``(eigenvalues, eigenvectors)`` sorted by decreasing eigenvalue.
    """
    points = np.asarray(coords, dtype=float)
    centered = points - points.mean(axis=0)
    if weights is None:
        weights = np.ones(len(points))
    weights = np.asarray(weights, dtype=float)
    weights = weights / max(weights.sum(), 1e-12)
    covariance = (centered * weights[:, None]).T @ centered
    values, vectors = np.linalg.eigh(covariance)
    order = np.argsort(values)[::-1]
    return values[order], vectors[:, order]


def view_basis(
    direction: np.ndarray, up_hint: np.ndarray = (0.0, 0.0, 1.0)
) -> np.ndarray:
    """Orthonormal camera basis ``[right, up, direction]`` as rows.

    ``direction`` points from the scene towards the camera.
    """
    d = np.asarray(direction, dtype=float)
    d = d / np.linalg.norm(d)
    u = np.asarray(up_hint, dtype=float)
    if np.linalg.norm(np.cross(u, d)) < 1e-8:
        u = np.array([0.0, 0.0, 1.0]) if abs(d[2]) < 0.9 else np.array([0.0, 1.0, 0.0])
    right = np.cross(u, d)
    right = right / np.linalg.norm(right)
    up = np.cross(d, right)
    return np.vstack([right, up, d])


def cell_params(lattice: np.ndarray) -> dict[str, float]:
    """Cell lengths and angles ``a, b, c, alpha, beta, gamma``."""
    lattice = np.asarray(lattice, dtype=float)
    a, b, c = (float(np.linalg.norm(v)) for v in lattice)

    def angle(u: np.ndarray, v: np.ndarray, nu: float, nv: float) -> float:
        if nu < 1e-12 or nv < 1e-12:
            return 90.0
        cosine = float(np.dot(u, v) / (nu * nv))
        return float(np.degrees(np.arccos(np.clip(cosine, -1.0, 1.0))))

    return {
        "a": a,
        "b": b,
        "c": c,
        "alpha": angle(lattice[1], lattice[2], b, c),
        "beta": angle(lattice[0], lattice[2], a, c),
        "gamma": angle(lattice[0], lattice[1], a, b),
    }
