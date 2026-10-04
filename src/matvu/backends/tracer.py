"""Software ray-casting backend: exact occlusion without OpenGL or VTK.

Every pixel ray is intersected analytically with the scene's spheres (atoms)
and half-cylinders (bonds) and composited through a z-buffer, so sticks are
properly occluded by balls and vice versa — no painter's-algorithm artefacts.

Two camera models share the same code path:

* orthographic (``Style.perspective = 0``) - canonical for exact crystal views;
* perspective (default, mild) - natural depth for slabs, molecules and
  publication-style figures.

Pure numpy, deterministic, works headless; anti-aliasing by supersampling.
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
    view: np.ndarray,
) -> np.ndarray:
    """Lambert + Blinn-Phong shading; ``view`` points to the camera.

    With ``style.shading`` disabled the surface is a flat colour with a
    darker silhouette outline (flat-design look).
    """
    if not style.shading:
        # Two-tone cel shading (animation style): a flat lit colour with a
        # hard shadow band, a silhouette outline and no highlights.
        lambert = np.clip(normals @ key_light, 0.0, 1.0)
        band = np.clip((lambert - 0.35) / 0.10, 0.0, 1.0)
        intensity = style.ambient + (1.0 - style.ambient) * band
        colour = base[None, None, :] * intensity[..., None]
        view_term = np.clip(np.einsum("...i,...i", normals, view), 0.0, 1.0)
        outline = np.clip((0.22 - view_term) / 0.22, 0.0, 1.0)
        outline_colour = base * 0.35
        cel = (
            colour * (1.0 - outline[..., None])
            + outline_colour[None, None, :] * outline[..., None]
        )
        return np.clip(cel, 0.0, 1.0)
    lambert = np.clip(normals @ key_light, 0.0, 1.0)
    fill = np.clip(normals @ fill_light, 0.0, 1.0) * 0.12
    half = key_light + view
    half = half / np.linalg.norm(half, axis=-1, keepdims=True)
    specular = (
        np.clip(np.einsum("...i,...i", normals, half), 0.0, 1.0)
        ** style.highlight_shininess
    )
    intensity = style.ambient + style.diffuse * lambert + fill
    # Darken towards the silhouette so spheres read against the background.
    edge = 0.75 + 0.25 * np.clip(np.einsum("...i,...i", normals, view), 0.0, 1.0)
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

    scene_radius = 1.0
    if scene.n_atoms:
        scene_radius = float(np.max(np.linalg.norm(positions, axis=1) + radii))
    scene_radius = max(scene_radius, 1e-3)

    perspective = max(float(getattr(style, "perspective", 0.0)), 0.0)
    if perspective > 1e-6:
        camera_distance = scene_radius / perspective
        focal = camera_distance
        camera_position = camera_distance * direction
    else:
        camera_distance = None
        focal = 0.0
        camera_position = None

    # Depth range of the scene along the view, for the aerial-perspective cue.
    if camera_distance is None:
        t_near = 4.0 * scene_radius
        t_far = 6.0 * scene_radius
    else:
        t_near = max(camera_distance - scene_radius, 1e-6)
        t_far = camera_distance + scene_radius
    background = _rgb(style.background)

    def image_points(points: np.ndarray) -> np.ndarray:
        """Map world points ``(..., 3)`` to image-plane coordinates."""
        x = points @ right
        y = points @ up
        if camera_distance is None:
            return np.stack([x, y], axis=-1)
        depth = camera_distance - (points @ direction)
        scale = focal / np.maximum(depth, 1e-6)
        return np.stack([x * scale, y * scale], axis=-1)

    def image_radius(centre: np.ndarray, radius: float) -> float:
        if camera_distance is None:
            return radius
        depth = camera_distance - float(centre @ direction)
        return radius * focal / max(depth, 1e-6)

    # Framing: image-plane bounding box of atoms (plus radii) and cell corners.
    if scene.n_atoms:
        atom_images = image_points(positions)
        atom_image_radii = np.array(
            [
                image_radius(positions[i], float(radii[i]))
                for i in range(scene.n_atoms)
            ],
            dtype=np.float64,
        )
        framing_radii = atom_image_radii * 1.08  # safety for perspective spread
        lower = (atom_images - framing_radii[:, None]).min(axis=0) - style.bond_radius
        upper = (atom_images + framing_radii[:, None]).max(axis=0) + style.bond_radius
    else:
        atom_images = np.zeros((0, 2), dtype=np.float32)
        atom_image_radii = np.zeros(0, dtype=np.float64)
        lower = np.zeros(2, dtype=np.float64)
        upper = np.ones(2, dtype=np.float64)

    corners = cell_corners(scene) if style.draw_cell else None
    if corners is not None:
        corner_image = image_points(corners.astype(np.float32))
        lower = np.minimum(lower, corner_image.min(axis=0))
        upper = np.maximum(upper, corner_image.max(axis=0))

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
    depth = np.full((height, width), np.inf, dtype=np.float32)
    colour = np.zeros((height, width, 3), dtype=np.float32)

    def pixel_window(centre_x: float, centre_y: float, radius: float):
        col0 = int(np.floor((centre_x - radius - x0) / (x1 - x0) * width))
        col1 = int(np.ceil((centre_x + radius - x0) / (x1 - x0) * width))
        row0 = int(np.floor((y1 - centre_y - radius) / (y1 - y0) * height))
        row1 = int(np.ceil((y1 - centre_y + radius) / (y1 - y0) * height))
        return max(row0, 0), min(row1, height), max(col0, 0), min(col1, width)

    def make_rays(row0, row1, col0, col1):
        sx = x_coords[col0:col1][None, :]
        sy = y_coords[row0:row1][:, None]
        plane = sx[..., None] * right + sy[..., None] * up
        if camera_distance is None:
            origins = plane + (5.0 * scene_radius) * direction
            dirs = np.empty_like(origins)
            dirs[...] = -direction
            return origins, dirs
        vector = plane - camera_position
        dirs = vector / np.linalg.norm(vector, axis=-1, keepdims=True)
        origins = np.broadcast_to(camera_position, vector.shape)
        return origins, dirs

    def write(row0, row1, col0, col1, t, valid, base, normals, view_dirs, flat=False):
        block = depth[row0:row1, col0:col1]
        update = valid & (t < block)
        if not update.any():
            return
        if flat:
            shaded = np.broadcast_to(base, (row1 - row0, col1 - col0, 3))
        else:
            shaded = _shade(normals, base, style, key_light, fill_light, view_dirs)
        if style.depth_cue > 0.0:
            fade = (
                np.clip((t - t_near) / max(t_far - t_near, 1e-9), 0.0, 1.0)
                * style.depth_cue
            )
            shaded = shaded * (1.0 - fade[..., None]) + background * fade[..., None]
        depth[row0:row1, col0:col1] = np.where(update, t, block)
        block_colour = colour[row0:row1, col0:col1]
        colour[row0:row1, col0:col1] = np.where(
            update[..., None], shaded, block_colour
        )

    for index in range(scene.n_atoms):
        centre = positions[index]
        radius = float(radii[index])
        image_c = atom_images[index]
        image_r = float(atom_image_radii[index])
        row0, row1, col0, col1 = pixel_window(
            float(image_c[0]), float(image_c[1]), image_r * 1.25 + 1e-6
        )
        if row0 >= row1 or col0 >= col1:
            continue
        origins, dirs = make_rays(row0, row1, col0, col1)
        offset = origins - centre
        b_term = np.einsum("...i,...i", offset, dirs)
        c_term = np.einsum("...i,...i", offset, offset) - radius * radius
        disc = b_term * b_term - c_term
        valid = disc >= 0.0
        t = -b_term - np.sqrt(np.maximum(disc, 0.0))
        valid = valid & (t > 0.0)
        t_safe = np.where(valid, t, 0.0)
        normals = (origins + t_safe[..., None] * dirs - centre) / radius
        write(row0, row1, col0, col1, t, valid, colours[index], normals, -dirs)

    def put_cylinder(start, end, radius, base, flat=False):
        axis = end - start
        length = float(np.linalg.norm(axis))
        if length < 1e-6:
            return
        image_a = image_points(start[None, :])[0]
        image_b = image_points(end[None, :])[0]
        radius_a = image_radius(start, radius)
        radius_b = image_radius(end, radius)
        centre_x = 0.5 * float(image_a[0] + image_b[0])
        centre_y = 0.5 * float(image_a[1] + image_b[1])
        half_extent = (
            0.5 * float(np.hypot(image_b[0] - image_a[0], image_b[1] - image_a[1]))
            + max(radius_a, radius_b)
        ) * 1.25 + 1e-6
        row0, row1, col0, col1 = pixel_window(centre_x, centre_y, half_extent)
        if row0 >= row1 or col0 >= col1:
            return
        origins, dirs = make_rays(row0, row1, col0, col1)
        unit = axis / length
        offset = origins - start
        direction_parallel = dirs @ unit
        axial_offset = offset @ unit
        v = dirs - direction_parallel[..., None] * unit
        perpendicular = offset - axial_offset[..., None] * unit
        vv = np.einsum("...i,...i", v, v)
        b_term = np.einsum("...i,...i", perpendicular, v)
        c_term = np.einsum("...i,...i", perpendicular, perpendicular) - radius**2
        disc = b_term * b_term - vv * c_term
        sqrt_disc = np.sqrt(np.maximum(disc, 0.0))
        safe_vv = np.where(vv > 1e-12, vv, 1.0)
        t_one = (-b_term - sqrt_disc) / safe_vv
        t_two = (-b_term + sqrt_disc) / safe_vv
        axial_one = axial_offset + t_one * direction_parallel
        axial_two = axial_offset + t_two * direction_parallel
        both_ok = (disc >= 0.0) & (vv > 1e-12)
        ok_one = both_ok & (t_one > 0.0) & (axial_one >= 0.0) & (axial_one <= length)
        ok_two = both_ok & (t_two > 0.0) & (axial_two >= 0.0) & (axial_two <= length)
        t = np.where(ok_one, t_one, np.where(ok_two, t_two, np.inf))
        valid = np.isfinite(t)
        t_safe = np.where(valid, t, 0.0)
        normals = (perpendicular + t_safe[..., None] * v) / radius
        write(row0, row1, col0, col1, t, valid, base, normals, -dirs, flat=flat)

    bond_colours = colours if style.shading else colours * 0.8
    for i, j in scene.bonds:
        a = positions[i]
        b = positions[j]
        middle = 0.5 * (a + b)
        put_cylinder(a, middle, style.bond_radius, bond_colours[i])
        put_cylinder(middle, b, style.bond_radius, bond_colours[j])

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
    coverage = (depth < np.inf).astype(np.float32)
    if factor > 1:
        colour = colour.reshape(final_height, factor, final_width, factor, 3).mean(
            axis=(1, 3)
        )
        coverage = coverage.reshape(final_height, factor, final_width, factor).mean(
            axis=(1, 3)
        )

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
