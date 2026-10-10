"""Matplotlib backend: static, publication-oriented ball-and-stick rendering.

The scene is projected orthographically onto a 2D plane and drawn with a
painter's algorithm: spheres are shaded sprites placed with ``imshow`` and
bonds are split half-coloured sticks. The result is deterministic, works in
headless environments and can be written to PNG, PDF or SVG.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from ..scene import CELL_EDGE_INDICES, Scene, cell_corners, project
from ..style import Style
from ..viewpoint import View
from .base import Backend

_SPRITE_CACHE: dict[tuple, np.ndarray] = {}


def _sphere_sprite(colour: np.ndarray, style: Style) -> np.ndarray:
    """RGBA sprite of a shaded sphere, cached per (colour, style)."""
    key = (
        tuple(np.round(colour, 4)),
        style.sphere_res,
        tuple(np.round(style.light, 3)),
        style.ambient,
        style.diffuse,
        style.specular,
        style.highlight_shininess,
        style.shading,
    )
    cached = _SPRITE_CACHE.get(key)
    if cached is not None:
        return cached

    resolution = int(style.sphere_res)
    lin = np.linspace(-1.0, 1.0, resolution)
    xx, yy = np.meshgrid(lin, lin[::-1])  # row 0 is the top of the sprite
    r2 = xx * xx + yy * yy
    inside = r2 <= 1.0
    zz = np.sqrt(np.clip(1.0 - r2, 0.0, 1.0))

    if style.shading:
        light = np.asarray(style.light, dtype=float)
        light = light / np.linalg.norm(light)
        lambert = np.clip(
            xx * light[0] + yy * light[1] + zz * light[2], 0.0, None
        )
        shade = style.ambient + style.diffuse * lambert
        half = light + np.array([0.0, 0.0, 1.0])
        half = half / np.linalg.norm(half)
        specular = (
            np.clip(xx * half[0] + yy * half[1] + zz * half[2], 0.0, None)
            ** style.highlight_shininess
        )
        edge = np.clip(zz, 0.0, 1.0) ** 0.3
        rgb = np.clip(
            colour[None, None, :] * shade[..., None] * edge[..., None]
            + style.specular * specular[..., None],
            0.0,
            1.0,
        )
    else:
        rgb = np.broadcast_to(np.asarray(colour, dtype=float), (resolution, resolution, 3)).copy()

    alpha = np.clip((1.0 - np.sqrt(r2)) * (resolution / 3.0), 0.0, 1.0) * inside
    sprite = np.dstack([rgb, alpha])
    _SPRITE_CACHE[key] = sprite
    return sprite


class MatplotlibBackend(Backend):
    """Static ball-and-stick renderer on top of matplotlib."""

    name = "matplotlib"
    interactive = False

    def render(
        self,
        scene: Scene,
        view: View,
        style: Style,
        output=None,
        show: bool = False,
        **kwargs,
    ):
        import matplotlib.pyplot as plt

        projection = project(scene, view)
        xy, depth, radii = projection.xy, projection.depth, projection.radii

        lower = (xy - radii[:, None]).min(axis=0)
        upper = (xy + radii[:, None]).max(axis=0)

        corners = cell_corners(scene, style.cell)
        edge_data: list[tuple[np.ndarray, np.ndarray, float]] = []
        if corners is not None:
            planar_corners = corners @ projection.basis.T
            lower = np.minimum(lower, planar_corners[:, :2].min(axis=0))
            upper = np.maximum(upper, planar_corners[:, :2].max(axis=0))
            for a, b in CELL_EDGE_INDICES:
                edge_data.append(
                    (
                        planar_corners[a, :2],
                        planar_corners[b, :2],
                        float(planar_corners[a, 2] + planar_corners[b, 2]) * 0.5,
                    )
                )

        pad = np.maximum(upper - lower, 1e-9) * style.margin + 1e-9
        lower = lower - pad
        upper = upper + pad
        nominal_width: float | None = None
        if style.canvas is not None:
            canvas_width, canvas_height = (float(value) for value in style.canvas)
            centre_x = 0.5 * (float(lower[0]) + float(upper[0]))
            centre_y = 0.5 * (float(lower[1]) + float(upper[1]))
            used_width = max(canvas_width, float(upper[0] - lower[0]))
            used_height = max(canvas_height, float(upper[1] - lower[1]))
            x0, x1 = centre_x - used_width / 2.0, centre_x + used_width / 2.0
            y0, y1 = centre_y - used_height / 2.0, centre_y + used_height / 2.0
            nominal_width = canvas_width
        else:
            x0, x1 = float(lower[0]), float(upper[0])
            y0, y1 = float(lower[1]), float(upper[1])
        x_span = max(x1 - x0, 1e-9)
        y_span = max(y1 - y0, 1e-9)

        width_in = float(style.width_in)
        if nominal_width is not None:
            # Same scale as the nominal canvas: the figure grows instead.
            scale_in_per_unit = width_in / nominal_width
            width_in = x_span * scale_in_per_unit
            height_in = y_span * scale_in_per_unit
        else:
            height_in = width_in * y_span / x_span
        figure = plt.figure(figsize=(width_in, height_in), dpi=style.dpi)
        figure.patch.set_facecolor(style.background)
        axes = figure.add_axes((0.0, 0.0, 1.0, 1.0))
        axes.set_facecolor(style.background)
        axes.set_axis_off()
        axes.set_xlim(x0, x1)
        axes.set_ylim(y0, y1)

        # Painter's algorithm: far primitives first; on equal depth draw bonds
        # before atoms so spheres always sit on top of their bond caps.
        items: list[tuple[float, int, int, int]] = [
            (float(depth[i]), 1, 0, i) for i in range(len(xy))
        ]
        if style.draw_bonds:
            for bond_index, (a, b) in enumerate(scene.bonds):
                items.append(
                    (float(depth[a] + depth[b]) * 0.5, 0, 1, bond_index)
                )
        for edge_index, (_, _, edge_depth) in enumerate(edge_data):
            items.append((edge_depth, 0, 2, edge_index))
        items.sort(key=lambda item: (item[0], item[1]))

        points_per_angstrom = width_in * 72.0 / x_span
        for rank, (_, _, kind, index) in enumerate(items):
            if kind == 0:
                radius = float(radii[index])
                x, y = float(xy[index, 0]), float(xy[index, 1])
                sprite = _sphere_sprite(scene.colours[index], style)
                axes.imshow(
                    sprite,
                    extent=(x - radius, x + radius, y - radius, y + radius),
                    origin="upper",
                    interpolation="bilinear",
                    zorder=rank,
                )
            elif kind == 1:
                _draw_bond(
                    axes,
                    scene,
                    xy,
                    index,
                    points_per_angstrom,
                    rank,
                    style,
                )
            else:
                start_2d, end_2d, _ = edge_data[index]
                axes.plot(
                    [start_2d[0], end_2d[0]],
                    [start_2d[1], end_2d[1]],
                    color=style.cell_colour,
                    lw=max(0.4, style.cell_linewidth),
                    solid_capstyle="round",
                    zorder=rank,
                )

        if output is not None:
            output = Path(output)
            figure.savefig(
                output,
                dpi=style.dpi,
                facecolor=style.background,
                transparent=style.transparent,
            )
            plt.close(figure)
            return output
        if show:
            plt.show()
            return None
        return figure


def _draw_bond(axes, scene, xy, index, points_per_angstrom, zorder, style) -> None:
    a, b = scene.bonds[index]
    start = xy[a].astype(float)
    end = xy[b].astype(float)
    direction_2d = end - start
    length = float(np.linalg.norm(direction_2d))
    if length < 1e-9:
        return
    unit = direction_2d / length
    # Clip the stick at the projected sphere surfaces. For an orthographic
    # projection this is exact, and it stops sticks lying flat on the balls.
    start = start + unit * float(scene.radii[a])
    end = end - unit * float(scene.radii[b])
    if float(np.linalg.norm(end - start)) <= 1e-6:
        return
    middle = 0.5 * (start + end)
    line_width = max(0.4, 2.0 * style.bond_radius * points_per_angstrom)
    outline = np.clip(
        0.5 * (scene.colours[a] + scene.colours[b]) * 0.40, 0.0, 1.0
    )
    # Slightly darker than the atom colour so light atoms (H) stay visible
    # on a light background.
    colour_a = np.clip(scene.colours[a] * 0.80, 0.0, 1.0)
    colour_b = np.clip(scene.colours[b] * 0.80, 0.0, 1.0)
    axes.plot(
        [start[0], end[0]],
        [start[1], end[1]],
        color=outline,
        lw=line_width * 1.18,
        solid_capstyle="round",
        zorder=zorder,
    )
    axes.plot(
        [start[0], middle[0]],
        [start[1], middle[1]],
        color=colour_a,
        lw=line_width,
        solid_capstyle="round",
        zorder=zorder + 0.2,
    )
    axes.plot(
        [middle[0], end[0]],
        [middle[1], end[1]],
        color=colour_b,
        lw=line_width,
        solid_capstyle="round",
        zorder=zorder + 0.2,
    )
