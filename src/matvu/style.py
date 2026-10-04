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

    # colours
    palette: str = "matvu"
    palette_overrides: dict[str, str] | None = None  # per-element #RRGGBB overrides

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
    transparent: bool = True  # transparent PNG/PDF/SVG by default
    margin: float = 0.06
    canvas: tuple[float, float] | None = None  # fixed view-plane size in Angstrom
    width_in: float = 6.0
    dpi: int = 300
    perspective: float = 0.18  # 0 = orthographic, larger = stronger perspective
    depth_cue: float = 0.0  # 0..1 aerial-perspective fade towards the background


def style_preset(name: str = "3d") -> Style:
    """Named style presets.

    ``"3d"``
        Shaded ball-and-stick with mild perspective (the default).
    ``"toon"``
        Animation/cel style: flat colours with a two-tone cel shadow and
        silhouette outlines; the perspective camera is kept.
    ``"flat"``
        Pure flat fill with silhouette outlines (no shading at all); the
        perspective camera is kept.
    """
    key = str(name).lower()
    if key in ("3d", "default", "shaded"):
        return Style()
    if key in ("toon", "cartoon", "anime", "cel"):
        return Style(
            shading=False,
            ambient=0.72,  # shadow tone level of the cel shading
            diffuse=0.0,
            specular=0.0,
            depth_cue=0.30,
        )
    if key in ("flat", "2d"):
        return Style(
            shading=False,
            ambient=1.0,  # no shadow at all: pure flat fill
            diffuse=0.0,
            specular=0.0,
            depth_cue=0.30,
        )
    raise ValueError(
        f"unknown style preset {name!r}; available: ['3d', 'toon', 'flat']"
    )
