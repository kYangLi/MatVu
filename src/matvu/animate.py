"""Orbit animations: one full turn around a structure from the automatic view.

The animation starts at the automatically chosen viewpoint and rotates the
camera around a Cartesian axis, keeping the camera roll fixed::

    render_orbit("POSCAR", "spin.gif", frames=72, fps=18)
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from .backends.tracer import save_image, trace_image
from .io import load_structure
from .render import resolve_view
from .scene import build_scene
from .style import Style
from .viewpoint import View

_AXES = {
    "x": (1.0, 0.0, 0.0),
    "y": (0.0, 1.0, 0.0),
    "z": (0.0, 0.0, 1.0),
}


def rotation_matrix(axis, angle: float) -> np.ndarray:
    """Rodrigues rotation matrix around a (not necessarily unit) axis."""
    vector = np.asarray(axis, dtype=float).reshape(-1)
    if vector.size != 3 or float(np.linalg.norm(vector)) < 1e-12:
        raise ValueError("rotation axis must be a non-zero 3-vector")
    x, y, z = (vector / float(np.linalg.norm(vector))).tolist()
    cos, sin = float(np.cos(angle)), float(np.sin(angle))
    one = 1.0 - cos
    return np.array(
        [
            [cos + x * x * one, x * y * one - z * sin, x * z * one + y * sin],
            [y * x * one + z * sin, cos + y * y * one, y * z * one - x * sin],
            [z * x * one - y * sin, z * y * one + x * sin, cos + z * z * one],
        ]
    )


def orbit_views(
    base: View,
    *,
    degrees: float = 360.0,
    frames: int = 60,
    axis: str = "auto",
) -> list[View]:
    """Rotate ``base`` around a Cartesian axis into ``frames`` viewpoints.

    The first frame is the base view itself and the last frame stops one step
    short of a full turn, so the animation loops seamlessly. ``axis="auto"``
    (default) picks the world axis that is most perpendicular to the base
    view, so the camera is guaranteed to move (an orbit around the viewing
    direction itself would be static).
    """
    key = str(axis).lower()
    if key == "auto":
        key = "xyz"[int(np.argmin(np.abs(np.asarray(base.direction, dtype=float))))]
    if key not in _AXES:
        raise ValueError(f"unknown orbit axis {axis!r}; expected x, y, z or auto")
    if frames < 2:
        raise ValueError("frames must be at least 2")
    unit = _AXES[key]
    views: list[View] = []
    for index in range(frames):
        matrix = rotation_matrix(unit, np.radians(degrees) * index / frames)
        views.append(
            View(
                direction=matrix @ np.asarray(base.direction, dtype=float),
                up_hint=matrix @ np.asarray(base.up_hint, dtype=float),
            )
        )
    return views


def render_orbit(
    source,
    output=None,
    *,
    view="auto",
    style: Style | None = None,
    orbit: float = 360.0,
    frames: int = 60,
    fps: float = 12.0,
    axis: str = "auto",
    supercell=None,
    seed: int = 0,
    frames_dir=None,
    background: str | None = None,
) -> list[Path]:
    """Render an orbit animation and/or its individual frames.

    ``output`` may be a ``.gif`` (frames flattened over ``background``, white
    by default) or a ``.webp`` (keeps transparency). ``frames_dir`` writes
    transparent ``frame_XXXX.png`` files. Returns every written path.
    """
    structure = load_structure(source)
    if supercell is not None:
        structure = structure.supercell(supercell)
    style = style or Style()
    scene = build_scene(structure, style)
    base_view = resolve_view(scene, view, seed=seed)
    views = orbit_views(base_view, degrees=orbit, frames=frames, axis=axis)
    images = [trace_image(scene, item, style) for item in views]

    written: list[Path] = []
    if frames_dir is not None:
        directory = Path(frames_dir).expanduser()
        directory.mkdir(parents=True, exist_ok=True)
        for index, image in enumerate(images):
            frame_path = directory / f"frame_{index:04d}.png"
            save_image(image, frame_path, style)
            written.append(frame_path)

    if output is not None:
        target = Path(output).expanduser()
        suffix = target.suffix.lower()
        if suffix not in (".gif", ".webp"):
            raise ValueError("animation output must be .gif or .webp")
        target.parent.mkdir(parents=True, exist_ok=True)
        _save_animation(images, target, style, fps=fps, background=background)
        written.append(target)
    return written


def _save_animation(
    images: list[np.ndarray],
    target: Path,
    style: Style,
    *,
    fps: float,
    background: str | None,
) -> None:
    from matplotlib.colors import to_rgb
    from PIL import Image

    flat = background
    if flat is None:
        flat = style.background if not style.transparent else "white"
    background_rgb = np.asarray(to_rgb(flat), dtype=np.float32)

    converted = []
    for image in images:
        pixels = np.clip(image, 0.0, 1.0)
        if target.suffix.lower() == ".webp":
            converted.append(Image.fromarray((pixels * 255.0 + 0.5).astype(np.uint8)))
        else:
            alpha = pixels[..., 3:4]
            rgb = np.clip(
                pixels[..., :3] * alpha + background_rgb * (1.0 - alpha), 0.0, 1.0
            )
            converted.append(Image.fromarray((rgb * 255.0 + 0.5).astype(np.uint8)))
    duration = max(1, int(round(1000.0 / max(fps, 1e-6))))
    converted[0].save(
        target,
        save_all=True,
        append_images=converted[1:],
        duration=duration,
        loop=0,
    )
