"""Viewpoint generation, scoring and automatic selection.

This module is the core of MatVu: it decides *where to look from*.
Everything here is rendering-backend independent.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from . import elements
from .geometry import principal_axes, view_basis
from .scene import Scene, molecular_box, project, slab_normal

# Penalty weights (must sum to 1).
W_OCCLUSION = 0.60
W_BOND = 0.25
W_ASPECT = 0.15


@dataclass
class View:
    """A camera direction pointing from the scene towards the camera."""

    direction: np.ndarray
    up_hint: np.ndarray = field(default_factory=lambda: np.array([0.0, 0.0, 1.0]))

    def __post_init__(self) -> None:
        d = np.asarray(self.direction, dtype=float).reshape(-1)
        if d.size != 3:
            raise ValueError("view direction must be a 3-vector")
        norm = float(np.linalg.norm(d))
        if norm < 1e-12:
            raise ValueError("view direction must be non-zero")
        self.direction = d / norm
        u = np.asarray(self.up_hint, dtype=float).reshape(-1)
        if u.size != 3 or float(np.linalg.norm(u)) < 1e-12:
            u = np.array([0.0, 0.0, 1.0])
        self.up_hint = u / float(np.linalg.norm(u))

    @property
    def basis(self) -> np.ndarray:
        """Camera basis ``[right, up, direction]`` as rows."""
        return view_basis(self.direction, self.up_hint)

    def angles_deg(self) -> tuple[float, float]:
        """``(azimuth, elevation)`` of the direction, in degrees."""
        azimuth = float(np.degrees(np.arctan2(self.direction[1], self.direction[0])))
        elevation = float(np.degrees(np.arcsin(np.clip(self.direction[2], -1, 1))))
        return azimuth, elevation

    def __repr__(self) -> str:
        azimuth, elevation = self.angles_deg()
        return f"View(azimuth={azimuth:.1f} deg, elevation={elevation:.1f} deg)"


def fibonacci_sphere(n: int) -> np.ndarray:
    """``(n, 3)`` quasi-uniform unit vectors on the sphere."""
    indices = np.arange(n, dtype=float) + 0.5
    phi = np.arccos(1.0 - 2.0 * indices / n)
    theta = np.pi * (1.0 + 5.0**0.5) * indices
    return np.column_stack(
        [
            np.cos(theta) * np.sin(phi),
            np.sin(theta) * np.sin(phi),
            np.cos(phi),
        ]
    )


def special_directions(scene: Scene) -> list[np.ndarray]:
    """High-symmetry directions: principal axes and lattice vectors."""
    directions: list[np.ndarray] = []
    if scene.n_atoms:
        weights = np.array([elements.atomic_mass(s) for s in scene.symbols])
        _, axes = principal_axes(scene.positions, weights)
        for k in range(3):
            directions.append(axes[:, k])
            directions.append(-axes[:, k])
    if scene.lattice is not None and abs(np.linalg.det(scene.lattice)) > 1e-9:
        for vector in scene.lattice:
            norm = float(np.linalg.norm(vector))
            if norm > 1e-12:
                directions.append(vector / norm)
                directions.append(-vector / norm)
    return directions


def candidate_views(scene: Scene, *, n_surface: int = 240) -> list[View]:
    """Deduplicated candidate views: Fibonacci sphere + special directions."""
    unique: list[np.ndarray] = []
    for direction in list(fibonacci_sphere(n_surface)) + special_directions(scene):
        direction = direction / np.linalg.norm(direction)
        if all(float(np.dot(direction, other)) < 0.9986 for other in unique):
            unique.append(direction)
    return [View(d) for d in unique]


SLAB_TILT_DEG = 32.0


def projected_dispersion(scene: Scene, view: View) -> float:
    """Maximin spread of the projected atoms (larger = more evenly spread).

    Only the core atoms of the cell are considered (boundary mirror images
    are decoration). The projected coordinates are normalised by their RMS
    radius, then the smallest pairwise distance is returned: a view with
    overlapping or clustered atoms scores low, a well-spread view scores high.
    """
    positions = (
        scene.positions if scene.n_core is None else scene.positions[: scene.n_core]
    )
    xy = (positions @ view.basis.T)[:, :2]
    xy = xy - xy.mean(axis=0)
    rms = float(np.sqrt((xy**2).sum(axis=1).mean()))
    if rms < 1e-12:
        return 0.0
    xy = xy / rms
    difference = xy[:, None, :] - xy[None, :, :]
    distances = np.sqrt((difference**2).sum(axis=-1))
    np.fill_diagonal(distances, np.inf)
    return float(distances.min())


def _circle_intersection_area(distance, radius_a, radius_b) -> np.ndarray:
    """Area of the intersection of two circles (vectorised, exact)."""
    distance = np.asarray(distance, dtype=float)
    radius_a = np.asarray(radius_a, dtype=float)
    radius_b = np.asarray(radius_b, dtype=float)
    distance, radius_a, radius_b = np.broadcast_arrays(
        distance, radius_a, radius_b
    )
    result = np.zeros(distance.shape, dtype=float)
    contained = distance <= np.abs(radius_a - radius_b)
    result[contained] = (
        np.pi * np.minimum(radius_a, radius_b)[contained] ** 2
    )
    partial = (distance < radius_a + radius_b) & ~contained
    if np.any(partial):
        d = distance[partial]
        big = radius_a[partial]
        small = radius_b[partial]
        part_one = small**2 * np.arccos(
            np.clip((d**2 + small**2 - big**2) / (2.0 * d * small), -1.0, 1.0)
        )
        part_two = big**2 * np.arccos(
            np.clip((d**2 + big**2 - small**2) / (2.0 * d * big), -1.0, 1.0)
        )
        part_three = 0.5 * np.sqrt(
            np.maximum(
                0.0,
                (-d + small + big)
                * (d + small - big)
                * (d - small + big)
                * (d + small + big),
            )
        )
        result[partial] = part_one + part_two - part_three
    return result


def score(scene: Scene, view: View) -> dict[str, float]:
    """Score one viewpoint. Higher ``score`` (in [0, 1]) is better.

    Metrics
    -------
    occlusion:
        Mean fraction of each atom's projected disk that is covered by atoms
        closer to the camera. Continuous measure: a pair that barely fails to
        overlap is penalised slightly, a fully hidden atom counts as one.
    bond_penalty:
        Mean penalty for bonds that are strongly foreshortened (nearly
        pointing at the camera).
    aspect_penalty:
        Penalty when the projected bounding box is much wider than tall
        (or vice versa).
    """
    projection = project(scene, view)
    xy, depth, radii = projection.xy, projection.depth, projection.radii
    n_atoms = scene.n_atoms

    # Occlusion: mean covered fraction of each atom's projected disk.
    coverage = np.zeros(n_atoms, dtype=float)
    for i in range(n_atoms):
        nearer = depth > depth[i]
        if not np.any(nearer):
            continue
        distance = np.hypot(
            xy[nearer, 0] - xy[i, 0], xy[nearer, 1] - xy[i, 1]
        )
        lens_area = _circle_intersection_area(distance, radii[i], radii[nearer])
        disk_area = np.pi * radii[i] ** 2
        coverage[i] = min(float(lens_area.sum()) / disk_area, 1.0)
    occlusion = float(coverage.mean())

    # Bond foreshortening.
    if scene.n_bonds:
        a, b = scene.bonds[:, 0], scene.bonds[:, 1]
        projected = np.linalg.norm(xy[a] - xy[b], axis=1)
        true_length = np.linalg.norm(
            scene.positions[a] - scene.positions[b], axis=1
        )
        ratio = projected / np.maximum(true_length, 1e-12)
        bond_penalty = float(np.mean(np.clip(1.0 - ratio / 0.35, 0.0, 1.0)))
    else:
        bond_penalty = 0.0

    # Framing.
    lower = (xy - radii[:, None]).min(axis=0)
    upper = (xy + radii[:, None]).max(axis=0)
    spans = np.maximum(upper - lower, 1e-9)
    aspect_ratio = float(max(spans) / min(spans))
    aspect_penalty = float(np.clip((aspect_ratio - 2.2) / 2.0, 0.0, 1.0))

    total = 1.0 - (
        W_OCCLUSION * occlusion + W_BOND * bond_penalty + W_ASPECT * aspect_penalty
    )
    return {
        "score": total,
        "occlusion": occlusion,
        "bond_penalty": bond_penalty,
        "aspect_penalty": aspect_penalty,
    }


def _perturbations(
    direction: np.ndarray, sigma: float, n: int, rng: np.random.Generator
) -> list[np.ndarray]:
    basis = view_basis(direction)
    tangent_1, tangent_2 = basis[0], basis[1]
    out = []
    for _ in range(n):
        candidate = direction + sigma * (
            rng.normal() * tangent_1 + rng.normal() * tangent_2
        )
        out.append(candidate / np.linalg.norm(candidate))
    return out


def pick_view(
    scene: Scene,
    *,
    n_surface: int = 240,
    refine_rounds: int = 2,
    samples_per_round: int = 64,
    seed: int = 0,
) -> View:
    """Search for the best viewpoint.

    Global Fibonacci candidates (plus high-symmetry directions, used as a
    tie-break) followed by cone-shaped local refinement.
    """
    rng = np.random.default_rng(seed)
    candidates = candidate_views(scene, n_surface=n_surface)
    scores = [score(scene, view)["score"] for view in candidates]

    # Prefer bird's-eye views: use only above-horizon candidates when any
    # exist (looking down at the structure reads more naturally than looking
    # up at it).
    upright = [
        index
        for index, candidate in enumerate(candidates)
        if candidate.angles_deg()[1] >= 5.0
    ]
    pool = upright if upright else list(range(len(candidates)))

    best_index = max(pool, key=lambda index: scores[index])
    best_score = scores[best_index]

    # Aesthetic selection among the near-best candidates.
    # - layered (quasi-2D) materials: moderate tilt from the layer normal;
    # - finite molecules: face-on view, tie-broken towards high symmetry;
    # - 3D crystals and clusters: maximin projected dispersion, so the atoms
    #   spread out as evenly as possible in the picture.
    normal = slab_normal(scene)
    lattice_directions: list[np.ndarray] = []
    if scene.lattice is not None:
        for vector in scene.lattice:
            norm = float(np.linalg.norm(vector))
            if norm > 1e-12:
                lattice_directions.append(vector / norm)
    is_molecule = molecular_box(scene)

    def aesthetically_ok(direction: np.ndarray) -> bool:
        """Keep refined views inside the same aesthetic region as the pick."""
        elevation = float(
            np.degrees(np.arcsin(np.clip(direction[2], -1.0, 1.0)))
        )
        if normal is not None:
            if elevation < 0.0:
                return False
            slant = float(
                np.degrees(
                    np.arccos(np.clip(abs(float(direction @ normal)), 0.0, 1.0))
                )
            )
            return 12.0 <= slant <= 58.0
        if is_molecule:
            return elevation >= 0.0
        if elevation < 5.0 or elevation > 65.0:
            return False
        if lattice_directions:
            return max(abs(float(direction @ u)) for u in lattice_directions) <= 0.95
        return True

    if normal is not None:
        top = [i for i in pool if scores[i] >= best_score - 0.02]
        angles = [
            float(
                np.degrees(
                    np.arccos(np.clip(abs(candidates[i].direction @ normal), 0.0, 1.0))
                )
            )
            for i in top
        ]
        tilted = [k for k, angle in enumerate(angles) if 18.0 <= angle <= 52.0]
        if tilted:
            best_index = top[min(tilted, key=lambda k: abs(angles[k] - SLAB_TILT_DEG))]
            best_score = scores[best_index]
    elif is_molecule:
        specials = special_directions(scene)
        if specials:
            top = [i for i in pool if scores[i] >= best_score - 0.01]
            alignment = [
                max(abs(float(candidates[i].direction @ s)) for s in specials)
                for i in top
            ]
            best_index = top[int(np.argmax(alignment))]
            best_score = scores[best_index]
    else:
        # Comfortable elevation band for 3D crystals: neither looking up nor
        # a steep bird's-eye view.
        band = [
            i for i in pool if 10.0 <= candidates[i].angles_deg()[1] <= 60.0
        ]
        available = band if band else pool
        top = [i for i in available if scores[i] >= best_score - 0.02]
        # Avoid "weird top-down" views: drop candidates nearly parallel to a
        # lattice vector when there are off-axis alternatives.
        if lattice_directions:
            off_axis = [
                i
                for i in top
                if max(
                    abs(float(candidates[i].direction @ u)) for u in lattice_directions
                )
                <= 0.92
            ]
            if off_axis:
                top = off_axis
        dispersion = [projected_dispersion(scene, candidates[i]) for i in top]
        best_index = top[int(np.argmax(dispersion))]
        best_score = scores[best_index]

    best = candidates[best_index]

    for round_index in range(refine_rounds):
        sigma = np.radians(20.0 / (3.0**round_index))
        for direction in _perturbations(
            best.direction, sigma, samples_per_round, rng
        ):
            candidate = View(direction)
            if not aesthetically_ok(candidate.direction):
                continue
            value = score(scene, candidate)["score"]
            if value > best_score + 1e-9:
                best, best_score = candidate, value
    return best
