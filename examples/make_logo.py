"""Generate the MatVu logo assets into ``docs/_image/``.

Flat 2D cartoon mark: a small ball-and-stick fragment drawn with solid
colours and bold outlines (matching the ``toon`` render style), framed by
four viewfinder corners. Colours follow the official ``matvu`` palette.

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
from matplotlib.patches import Circle

OUT = Path(__file__).resolve().parents[1] / "docs" / "_image"
OUT.mkdir(parents=True, exist_ok=True)

CHARCOAL = "#3F4650"
RED = "#E04A3A"
SAND = "#D6B08C"
TEAL = "#4E8FA3"
GOLD = "#D9B93C"
GRAY = "#7A828C"

# molecule: (x, y, colour, radius) in local units, hub first for bonds
ATOMS = [
    (-0.34, -0.20, TEAL, 0.130),
    (0.34, -0.20, SAND, 0.130),
    (0.00, 0.40, RED, 0.130),
    (0.00, 0.00, CHARCOAL, 0.155),
]
BRACKET = 0.70
BRACKET_ARM = 0.20


def _hex_to_rgb(colour: str) -> np.ndarray:
    return np.array(
        [int(colour.lstrip("#")[i : i + 2], 16) / 255.0 for i in (0, 2, 4)]
    )


def _rgb_to_hex(rgb: np.ndarray) -> str:
    return "#" + "".join(f"{round(max(0.0, min(1.0, c)) * 255):02X}" for c in rgb)


def _darken(colour: str, factor: float) -> str:
    return _rgb_to_hex(_hex_to_rgb(colour) * factor)


def _bond(ax, start, end, colour_a, colour_b, width_pt, zorder):
    middle = ((start[0] + end[0]) / 2, (start[1] + end[1]) / 2)
    outline = _darken(
        _rgb_to_hex((_hex_to_rgb(colour_a) + _hex_to_rgb(colour_b)) / 2), 0.42
    )
    ax.plot(
        [start[0], end[0]],
        [start[1], end[1]],
        color=outline,
        lw=width_pt * 1.26,
        solid_capstyle="round",
        zorder=zorder,
    )
    for point_a, point_b, colour in (
        (start, middle, colour_a),
        (middle, end, colour_b),
    ):
        ax.plot(
            [point_a[0], point_b[0]],
            [point_a[1], point_b[1]],
            color=_darken(colour, 0.82),
            lw=width_pt,
            solid_capstyle="round",
            zorder=zorder + 0.1,
        )


def draw_mark(ax, box, zorder=10):
    """Draw the flat cartoon mark scaled to fit ``box = (x, y, w, h)``."""
    x0, y0, width, height = box
    extent = 2 * (BRACKET + 0.14)
    scale = min(width, height) / extent
    centre = np.array([x0 + width / 2, y0 + height / 2])

    # centre the molecule's bounding box on the viewfinder centre
    xs = [x - r for x, _, _, r in ATOMS] + [x + r for x, _, _, r in ATOMS]
    ys = [y - r for _, y, _, r in ATOMS] + [y + r for _, y, _, r in ATOMS]
    shift = np.array([(min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2])

    def place(x, y):
        p = centre + (np.array([x, y]) - shift) * scale
        return float(p[0]), float(p[1])

    # viewfinder corners (cartoon focus frame)
    bracket_lw = max(1.6, 0.042 * scale * 72)
    for sx in (-1, 1):
        for sy in (-1, 1):
            corner = place(sx * BRACKET, sy * BRACKET)
            ax.plot(
                [corner[0], place(sx * BRACKET - sx * BRACKET_ARM, sy * BRACKET)[0]],
                [corner[1], corner[1]],
                color=GOLD,
                lw=bracket_lw,
                solid_capstyle="round",
                zorder=zorder,
            )
            ax.plot(
                [corner[0], corner[0]],
                [corner[1], place(sx * BRACKET, sy * BRACKET - sy * BRACKET_ARM)[1]],
                color=GOLD,
                lw=bracket_lw,
                solid_capstyle="round",
                zorder=zorder,
            )

    hub = ATOMS[-1][:2]
    bond_width = ATOMS[-1][3] * scale * 72 * 0.52
    for x, y, colour, _ in ATOMS[:-1]:
        _bond(
            ax,
            place(*hub),
            place(x, y),
            ATOMS[-1][2],
            colour,
            bond_width,
            zorder + 1,
        )

    for x, y, colour, radius in ATOMS:
        ax.add_patch(
            Circle(
                place(x, y),
                radius * scale,
                facecolor=colour,
                edgecolor=_darken(colour, 0.45),
                linewidth=max(1.4, radius * scale * 72 * 0.22),
                zorder=zorder + 2,
            )
        )

    # small camera lens in the lower-right of the viewfinder, just focused
    lens = place(0.49, -0.49)
    lens_r = 0.125 * scale
    lens_edge = max(1.5, lens_r * 72 * 0.16)
    ax.add_patch(
        Circle(
            lens,
            lens_r,
            facecolor="#D9E4EA",
            edgecolor=CHARCOAL,
            linewidth=lens_edge,
            zorder=zorder + 4,
        )
    )
    ax.add_patch(
        Circle(
            lens,
            lens_r * 0.52,
            facecolor=TEAL,
            edgecolor=_darken(TEAL, 0.55),
            linewidth=lens_edge * 0.7,
            zorder=zorder + 5,
        )
    )
    glint = (lens[0] - lens_r * 0.34, lens[1] + lens_r * 0.34)
    ax.add_patch(
        Circle(
            glint,
            lens_r * 0.2,
            facecolor="white",
            edgecolor="none",
            zorder=zorder + 6,
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
        draw_mark(ax, (0.12, 0.12, 1.96, 1.96))
    else:
        figure, ax = _new_axes(9.6, 1.8)
        draw_mark(ax, (0.10, 0.10, 1.62, 1.60))
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
    draw_mark(ax, (5.35, 3.20, 2.1, 2.0))
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
