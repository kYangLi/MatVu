"""Generate the MatVu logo assets into ``docs/_image/``.

The mark is a unit-cell cube with a small ball-and-stick fragment and a
viewing cone entering from the chosen vantage point. Colours follow the
official ``matvu`` palette; spheres reuse the matplotlib backend's sphere
shading, so the logo matches the renders.

Usage::

    .venv/bin/python examples/make_logo.py
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
matplotlib.rcParams["svg.fonttype"] = "path"
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Circle, Polygon

from matvu.backends.mpl import _sphere_sprite
from matvu.style import Style

OUT = Path(__file__).resolve().parents[1] / "docs" / "_image"
OUT.mkdir(parents=True, exist_ok=True)

CHARCOAL = "#3F4650"
RED = "#E04A3A"
SAND = "#D6B08C"
TEAL = "#4E8FA3"
GOLD = "#D9B93C"
GRAY = "#7A828C"
BOND = "#A6ADB6"

_STYLE = Style()


def _rgb(colour: str) -> np.ndarray:
    return np.array(
        [int(colour.lstrip("#")[i : i + 2], 16) / 255.0 for i in (0, 2, 4)]
    )


def _ball(ax, x, y, radius, colour, zorder):
    sprite = _sphere_sprite(_rgb(colour), _STYLE)
    ax.imshow(
        sprite,
        extent=(x - radius, x + radius, y - radius, y + radius),
        origin="upper",
        interpolation="bilinear",
        zorder=zorder,
    )


def draw_mark(ax, box, zorder=10):
    """Draw the MatVu mark scaled to fit ``box = (x, y, width, height)``."""
    x0, y0, width, height = box
    u = np.array([np.cos(np.radians(30)), -np.sin(np.radians(30))])
    v = np.array([-np.cos(np.radians(30)), -np.sin(np.radians(30))])
    w = np.array([0.0, 1.0])
    vantage3 = (0.5, 0.5, 1.55)

    def raw(fx, fy, fz):
        return fx * u + fy * v + fz * w

    cube_pts = [
        raw(fx, fy, fz) for fx in (0.0, 1.0) for fy in (0.0, 1.0) for fz in (0.0, 1.0)
    ]
    points = np.array(cube_pts + [raw(*vantage3)])
    low, high = points.min(axis=0), points.max(axis=0)
    span = np.maximum(high - low, 1e-9)
    scale = 0.98 * min(width / span[0], height / span[1])
    offset = (
        np.array([x0 + width / 2, y0 + height / 2]) - (low + high) / 2 * scale
    )

    def project(fx, fy, fz):
        return raw(fx, fy, fz) * scale + offset

    corners = {
        (fx, fy, fz): project(fx, fy, fz)
        for fx in (0.0, 1.0)
        for fy in (0.0, 1.0)
        for fz in (0.0, 1.0)
    }
    for (fx, fy, fz), p in corners.items():
        for axis in range(3):
            q = [fx, fy, fz]
            if q[axis] == 0.0:
                q[axis] = 1.0
                ax.plot(
                    [p[0], corners[tuple(q)][0]],
                    [p[1], corners[tuple(q)][1]],
                    color=CHARCOAL,
                    alpha=0.45,
                    lw=1.1,
                    solid_capstyle="round",
                    zorder=zorder,
                )

    vantage = project(*vantage3)
    left_top = corners[(0.0, 1.0, 1.0)]
    right_top = corners[(1.0, 0.0, 1.0)]
    ax.add_patch(
        Polygon(
            [vantage, left_top, right_top],
            closed=True,
            facecolor=GOLD,
            alpha=0.15,
            edgecolor="none",
            zorder=zorder - 2,
        )
    )
    for corner in (left_top, right_top):
        ax.plot(
            [vantage[0], corner[0]],
            [vantage[1], corner[1]],
            color=GOLD,
            alpha=0.6,
            lw=1.0,
            zorder=zorder - 1,
        )

    radius = 0.125 * scale
    atoms = [
        (0.84, 0.50, 0.50, SAND),
        (0.50, 0.84, 0.50, TEAL),
        (0.50, 0.50, 0.84, RED),
        (0.50, 0.50, 0.50, CHARCOAL),
    ]
    hub = project(0.5, 0.5, 0.5)
    for fx, fy, fz, _ in atoms[:-1]:
        q = project(fx, fy, fz)
        ax.plot(
            [hub[0], q[0]],
            [hub[1], q[1]],
            color=BOND,
            lw=radius * 72 * 0.55,
            solid_capstyle="round",
            zorder=zorder + 1,
        )
    for fx, fy, fz, colour in atoms:
        q = project(fx, fy, fz)
        _ball(ax, q[0], q[1], radius, colour, zorder + 2)

    ax.add_patch(
        Circle(
            vantage,
            radius=0.075 * scale,
            facecolor=GOLD,
            edgecolor="white",
            linewidth=1.4,
            zorder=zorder + 3,
        )
    )


def _text_width_units(text: str, fontsize: float, weight: str = "bold") -> float:
    """Width of ``text`` in canvas units (1 unit = 1 inch = 72 pt)."""
    from matplotlib.font_manager import FontProperties
    from matplotlib.textpath import TextPath

    path = TextPath((0, 0), text, size=fontsize, prop=FontProperties(weight=weight))
    return float(path.get_extents().width) / 72.0


def draw_wordmark(ax, x, y, fontsize, accent=RED, align="left"):
    width_mat = _text_width_units("Mat", fontsize)
    width_vu = _text_width_units("Vu", fontsize)
    start = x - (width_mat + width_vu) / 2 if align == "center" else x
    ax.text(
        start,
        y,
        "Mat",
        fontsize=fontsize,
        fontweight="bold",
        color=CHARCOAL,
        ha="left",
        va="center",
        zorder=20,
    )
    ax.text(
        start + width_mat,
        y,
        "Vu",
        fontsize=fontsize,
        fontweight="bold",
        color=accent,
        ha="left",
        va="center",
        zorder=20,
    )


def _new_axes(width, height):
    figure = plt.figure(figsize=(width, height), dpi=100)
    ax = figure.add_axes((0.0, 0.0, 1.0, 1.0))
    ax.set_xlim(0, width)
    ax.set_ylim(0, height)
    ax.set_aspect("equal")
    ax.set_axis_off()
    return figure, ax


def _save(figure, path_stem):
    for suffix in ("svg", "png"):
        figure.savefig(f"{path_stem}.{suffix}", transparent=True, pad_inches=0)
    plt.close(figure)
    print(f"wrote {path_stem}.svg / .png")


def make_logo(path_stem: str, tagline: bool, pure: bool = False):
    if pure:
        figure, ax = _new_axes(2.2, 2.2)
        draw_mark(ax, (0.15, 0.15, 1.9, 1.9))
    else:
        figure, ax = _new_axes(9.6, 1.8)
        draw_mark(ax, (0.12, 0.10, 1.62, 1.60))
        draw_wordmark(ax, 2.05, 1.08, 78)
        if tagline:
            ax.text(
                2.12,
                0.42,
                "automatic viewpoint optimization for materials structures",
                fontsize=15.5,
                color=GRAY,
                ha="left",
                va="center",
            )
    _save(figure, path_stem)


def make_social_preview():
    figure, ax = _new_axes(12.8, 6.4)
    figure.patch.set_facecolor("#F7F8FA")
    draw_mark(ax, (5.3, 3.15, 2.2, 2.1))
    draw_wordmark(ax, 6.4, 2.45, 118, align="center")
    ax.text(
        6.4,
        1.52,
        "automatic viewpoint optimization for materials structures",
        fontsize=16.5,
        color=GRAY,
        ha="center",
        va="center",
    )
    ax.text(
        6.4,
        0.98,
        "github.com/kYangLi/MatVu   ·   pip install matvu",
        fontsize=14,
        color=TEAL,
        ha="center",
        va="center",
    )
    figure.savefig(OUT / "social-preview.png", dpi=100, facecolor="#F7F8FA")
    plt.close(figure)
    print(f"wrote {OUT / 'social-preview.png'}")


if __name__ == "__main__":
    make_logo(str(OUT / "logo-large"), tagline=True)
    make_logo(str(OUT / "logo-small"), tagline=False)
    make_logo(str(OUT / "logo-pure"), tagline=False, pure=True)
    make_social_preview()
