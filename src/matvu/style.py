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
    min_atom_radius: float = 0.0  # 0 = radii strictly proportional to atomic radii
    unbonded_atom_scale: float = 0.45  # used when the structure ends up with no bonds
    bond_radius: float = 0.09
    bond_tolerance: float = 1.20
    metal_metal_bonds: bool = False
    draw_bonds: bool = True
    boundary_padding: float = 0.10  # fractional margin of mirrored boundary atoms

    # cell frame
    draw_cell: bool = True
    cell_linewidth: float = 1.0  # in points, at the final image size
    cell_colour: str = "#4d4d4d"

    # shading
    shading: bool = True
    sphere_res: int = 256
    light: tuple[float, float, float] = (-0.45, 0.55, 0.70)
    ambient: float = 0.30
    diffuse: float = 0.62
    specular: float = 0.30
    highlight_shininess: float = 32.0
    supersample: int = 2  # anti-aliasing factor for the tracer backend

    # canvas
    background: str = "white"
    transparent: bool = False
    margin: float = 0.06
    width_in: float = 6.0
    dpi: int = 300
    perspective: float = 0.18  # 0 = orthographic, larger = stronger perspective
    depth_cue: float = 0.0  # 0..1 aerial-perspective fade towards the background


def style_preset(name: str = "3d") -> Style:
    """Named style presets.

    ``"3d"``
        Shaded ball-and-stick with mild perspective (the default).
    ``"flat"``
        Flat-design look with a 2.5D feel: solid colours, silhouette
        outlines, a gentle directional shading (no highlights) and an
        orbital depth cue that fades distant atoms towards the background.
    """
    key = str(name).lower()
    if key in ("3d", "default", "shaded"):
        return Style()
    if key in ("flat", "2d"):
        return Style(
            shading=False,
            ambient=0.70,
            diffuse=0.38,
            specular=0.0,
            perspective=0.0,
            depth_cue=0.35,
        )
    raise ValueError(f"unknown style preset {name!r}; available: ['3d', 'flat']")
