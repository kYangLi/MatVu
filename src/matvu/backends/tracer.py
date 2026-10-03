"""Software ray-casting backend: exact occlusion without OpenGL or VTK.

Every pixel ray is intersected analytically with the scene's spheres (atoms)
and half-cylinders (bonds) and composited through a z-buffer, so sticks are
properly occluded by balls and vice versa — no painter's-algorithm artefacts.
Pure numpy, deterministic, works headless; anti-aliasing by supersampling.

This is MatVu's high-quality static renderer, comparable in spirit to the
POV-Ray workflow used by ASE/VESTA, but with no external binary.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from ..scene import CELL_EDGE_INDICES, Scene, cell_corners
from ..style import Style
from ..viewpoint import View
from .base import Backend


class TracerBackend(Backend):
    """Analytic ray caster for ball-and-stick scenes."""

    name = "tracer"
    interactive = False

    def render(
        self,
        scene: Scene,
        view: View,
        style: Style,
        output=None,
        width_px=None,
        height_px=None,
        supersample: int | None = None,
        **kwargs,
    ):
        image = trace_image(
            scene,
            view,
            style,
            width_px=width_px,
            height_px=height_px,
            supersample=supersample,
        )
        if output is None:
            return image
        return _save_image(image, Path(output), style)


def _rgb(colour) -> np.ndarray:
    from matplotlib.colors import to_rgb

    return np.asarray(to_rgb(colour), dtype=np.float32)


def _shade(
    normals: np.ndarray,
    base: np.ndarray,
    style: Style,
    key_light: np.ndarray,
    fill_light: np.ndarray,
    view_direction: np.ndarray,
) -> np.ndarray:
    """Lambert + Blinn-Phong shading for a block of surface normals."""
    lambert = np.clip(normals @ key_light, 0.0, 1.0)
    fill = np.clip(normals @ fill_light, 0.0, 1.0) * 0.12
    half = key_light + view_direction
    half = half / np.linalg.norm(half)
    specular = np.clip(normals @ half, 0.0, 1.0) ** style.highlight_shininess
    intensity = style.ambient + style.diffuse * lambert + fill
    # Darken towards the silhouette so spheres read against the background.
    edge = 0.75 + 0.25 * np.clip(normals @ view_direction, 0.0, 1.0)
    shaded = (
        intensity[..., None] * base * edge[..., None]
        + style.specular * specular[..., None]
    )
    return np.clip(shaded, 0.0, 1.0)


def trace_image(
    scene: Scene,
    view: View,
    style: Style,
    *,
    width_px: int | None = None,
    height_px: int | None = None,
    supersample: int | None = None,
) -> np.ndarray:
    """Ray-cast the scene and return a float RGBA image in [0, 1]."""
    basis = view.basis.astype(np.float32)
    right, up, direction = basis[0], basis[1], basis[2]

    positions = scene.positions.astype(np.float32)
    radii = scene.radii.astype(np.float32)
    colours = scene.colours.astype(np.float32)

    # Camera lights: style.light is given in screen space (right, up, towards
    # the camera), exactly like the matplotlib sprite shading.
    key_screen = np.asarray(style.light, dtype=np.float32)
    key_screen = key_screen / np.linalg.norm(key_screen)
    key_light = key_screen[0] * right + key_screen[1] * up + key_screen[2] * direction
    fill_screen = np.asarray((0.65, -0.55, 0.25), dtype=np.float32)
    fill_screen = fill_screen / np.linalg.norm(fill_screen)
    fill_light = fill_screen[0] * right + fill_screen[1] * up + fill_screen[2] * direction

    # View-plane bounds from the projected atoms.
    planar = positions @ basis.T
    planar_xy = planar[:, :2]
    lower = (planar_xy - radii[:, None]).min(axis=0) - style.bond_radius
    upper = (planar_xy + radii[:, None]).max(axis=0) + style.bond_radius

    # The cell frame is part of the picture when it is drawn.
    corners = cell_corners(scene) if style.draw_cell else None
    if corners is not None:
        corner_xy = (corners.astype(np.float32) @ basis.T)[:, :2]
        lower = np.minimum(lower, corner_xy.min(axis=0))
        upper = np.maximum(upper, corner_xy.max(axis=0))

    pad = np.maximum(upper - lower, 1e-6) * style.margin
    lower = lower - pad
    upper = upper + pad
    x0, y0 = float(lower[0]), float(lower[1])
    x1, y1 = float(upper[0]), float(upper[1])

    final_width = int(width_px) if width_px else max(4, int(round(style.width_in * style.dpi)))
    aspect = (y1 - y0) / max(x1 - x0, 1e-9)
    final_height = int(height_px) if height_px else max(4, int(round(final_width * aspect)))

    factor = int(supersample if supersample is not None else style.supersample)
    factor = max(1, factor)
    width = final_width * factor
    height = final_height * factor

    x_coords = x0 + (np.arange(width, dtype=np.float32) + 0.5) * np.float32(
        (x1 - x0) / width
    )
    y_coords = y1 - (np.arange(height, dtype=np.float32) + 0.5) * np.float32(
        (y1 - y0) / height
    )
    depth = np.full((height, width), -np.inf, dtype=np.float32)
    colour = np.zeros((height, width, 3), dtype=np.float32)

    def pixel_window(centre_x: float, centre_y: float, radius: float):
        col0 = int(np.floor((centre_x - radius - x0) / (x1 - x0) * width))
        col1 = int(np.ceil((centre_x + radius - x0) / (x1 - x0) * width))
        row0 = int(np.floor((y1 - centre_y - radius) / (y1 - y0) * height))
        row1 = int(np.ceil((y1 - centre_y + radius) / (y1 - y0) * height))
        return max(row0, 0), min(row1, height), max(col0, 0), min(col1, width)

    def write(row0, row1, col0, col1, hit, valid, base, normals, flat=False):
        block = depth[row0:row1, col0:col1]
        update = valid & (hit > block)
        if not update.any():
            return
        if flat:
            shaded = np.broadcast_to(base, (row1 - row0, col1 - col0, 3))
        else:
            shaded = _shade(normals, base, style, key_light, fill_light, direction)
        depth[row0:row1, col0:col1] = np.where(update, hit, block)
        block_colour = colour[row0:row1, col0:col1]
        colour[row0:row1, col0:col1] = np.where(
            update[..., None], shaded, block_colour
        )

    for index in range(scene.n_atoms):
        centre = positions[index]
        radius = float(radii[index])
        plane = basis @ centre
        row0, row1, col0, col1 = pixel_window(
            float(plane[0]), float(plane[1]), radius
        )
        if row0 >= row1 or col0 >= col1:
            continue
        sx = x_coords[col0:col1][None, :]
        sy = y_coords[row0:row1][:, None]
        points = sx[..., None] * right + sy[..., None] * up
        offset = centre - points
        md = offset @ direction
        mm = np.einsum("...i,...i", offset, offset)
        disc = md * md - (mm - radius * radius)
        valid = disc >= 0.0
        hit = md + np.sqrt(np.maximum(disc, 0.0))
        hit = np.where(valid, hit, 0.0)
        normals = (points + hit[..., None] * direction - centre) / radius
        write(row0, row1, col0, col1, hit, valid, colours[index], normals)

    def put_cylinder(start, end, radius, base, flat=False):
        axis = end - start
        length = float(np.linalg.norm(axis))
        if length < 1e-6:
            return
        unit = axis / length
        plane_a = basis @ start
        plane_b = basis @ end
        centre_x = 0.5 * float(plane_a[0] + plane_b[0])
        centre_y = 0.5 * float(plane_a[1] + plane_b[1])
        half_extent = 0.5 * float(
            np.hypot(plane_b[0] - plane_a[0], plane_b[1] - plane_a[1])
        ) + radius
        row0, row1, col0, col1 = pixel_window(centre_x, centre_y, half_extent)
        if row0 >= row1 or col0 >= col1:
            return
        sx = x_coords[col0:col1][None, :]
        sy = y_coords[row0:row1][:, None]
        points = sx[..., None] * right + sy[..., None] * up
        offset = points - start
        axial = offset @ unit
        perpendicular = offset - axial[..., None] * unit
        direction_parallel = float(direction @ unit)
        v = direction - direction_parallel * unit
        vv = float(v @ v)
        if vv < 1e-10:
            return  # bond axis (anti)parallel to the view; atoms cover it
        b_term = perpendicular @ v
        c_term = np.einsum("...i,...i", perpendicular, perpendicular) - radius**2
        disc = b_term * b_term - vv * c_term
        sqrt_disc = np.sqrt(np.maximum(disc, 0.0))
        s_one = (-b_term + sqrt_disc) / vv
        s_two = (-b_term - sqrt_disc) / vv
        t_one = axial + s_one * direction_parallel
        t_two = axial + s_two * direction_parallel
        ok_one = (disc >= 0.0) & (t_one >= 0.0) & (t_one <= length)
        ok_two = (disc >= 0.0) & (t_two >= 0.0) & (t_two <= length)
        hit = np.maximum(
            np.where(ok_one, s_one, -np.inf), np.where(ok_two, s_two, -np.inf)
        )
        valid = np.isfinite(hit)
        hit_safe = np.where(valid, hit, 0.0)
        normals = (perpendicular + hit_safe[..., None] * v) / radius
        write(row0, row1, col0, col1, hit, valid, base, normals, flat=flat)

    for i, j in scene.bonds:
        a = positions[i]
        b = positions[j]
        middle = 0.5 * (a + b)
        put_cylinder(a, middle, style.bond_radius, colours[i])
        put_cylinder(middle, b, style.bond_radius, colours[j])

    # Unit cell frame, drawn as thin unshaded sticks.
    if corners is not None:
        units_per_point = (x1 - x0) / (style.width_in * 72.0)
        frame_radius = max(style.cell_linewidth * 0.5 * units_per_point, 1e-4)
        frame_colour = _rgb(style.cell_colour)
        for a, b in CELL_EDGE_INDICES:
            put_cylinder(
                corners[a].astype(np.float32),
                corners[b].astype(np.float32),
                frame_radius,
                frame_colour,
                flat=True,
            )

    # Supersampled anti-aliasing.
    coverage = (depth > -np.inf).astype(np.float32)
    if factor > 1:
        colour = colour.reshape(final_height, factor, final_width, factor, 3).mean(
            axis=(1, 3)
        )
        coverage = coverage.reshape(final_height, factor, final_width, factor).mean(
            axis=(1, 3)
        )

    background = _rgb(style.background)
    if style.transparent:
        straight = np.divide(
            colour,
            coverage[..., None],
            out=np.zeros_like(colour),
            where=coverage[..., None] > 1e-6,
        )
        return np.concatenate([np.clip(straight, 0.0, 1.0), coverage[..., None]], axis=-1)
    composited = colour + background * (1.0 - coverage[..., None])
    alpha = np.ones((final_height, final_width, 1), dtype=np.float32)
    return np.concatenate([np.clip(composited, 0.0, 1.0), alpha], axis=-1)


def _save_image(image: np.ndarray, output: Path, style: Style):
    """Write a raster image directly, or embed it in a vector container."""
    import matplotlib.pyplot as plt

    image = np.clip(image, 0.0, 1.0)
    if output.suffix.lower() in (".png", ".jpg", ".jpeg", ".tif", ".tiff", ".webp", ".bmp"):
        plt.imsave(output, image)
        return output
    height, width = image.shape[:2]
    figure = plt.figure(figsize=(width / style.dpi, height / style.dpi), dpi=style.dpi)
    axes = figure.add_axes((0.0, 0.0, 1.0, 1.0))
    axes.set_axis_off()
    axes.imshow(image, interpolation="nearest")
    figure.savefig(output, dpi=style.dpi)
    plt.close(figure)
    return output
