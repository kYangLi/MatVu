"""Rendering style independent of any particular backend."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Style:
    """Sizes, colours and output settings for ball-and-stick rendering.

    Lengths are in Angstrom; size-related fields are interpreted in scene
    units so every backend shows the same proportions.
    """

    # atoms and bonds
    atom_scale: float = 0.40
    min_atom_radius: float = 0.18
    bond_radius: float = 0.09
    bond_tolerance: float = 1.20
    draw_bonds: bool = True

    # shading
    shading: bool = True
    sphere_res: int = 256
    light: tuple[float, float, float] = (-0.45, 0.55, 0.70)
    ambient: float = 0.42
    diffuse: float = 0.58
    specular: float = 0.45
    highlight_shininess: float = 24.0
    supersample: int = 2  # anti-aliasing factor for the tracer backend

    # canvas
    background: str = "white"
    transparent: bool = False
    margin: float = 0.06
    width_in: float = 6.0
    dpi: int = 300
