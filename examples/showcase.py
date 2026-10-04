"""MatVu showcase: fully automatic viewpoint + tracer rendering.

For every example structure the view is chosen automatically (``view="auto"``)
and rendered with the analytic ray-casting backend. Individual images and one
contact sheet end up in ``examples/out/``.

Usage::

    .venv/bin/python examples/showcase.py [--dpi 200] [--width 4.5]
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from matvu import auto_view, load_structure, render
from matvu.scene import build_scene
from matvu.style import Style, style_preset

ROOT = Path(__file__).resolve().parents[1]
STRUCTURES = ROOT / "examples" / "structures"
OUTPUT = ROOT / "examples" / "out"
TILES = OUTPUT / "showcase"

# Metal-metal bonds are skipped by default (see Style.metal_metal_bonds), so
# Cu renders as close-packed spheres and MoS2 keeps only Mo-S sticks.
CASES: list[dict] = [
    {"name": "si", "file": "Si.POSCAR", "supercell": (2, 2, 2), "title": "Si — diamond"},
    {"name": "nacl", "file": "NaCl.POSCAR", "supercell": (2, 2, 2), "title": "NaCl — rocksalt"},
    {"name": "zns", "file": "ZnS.POSCAR", "supercell": (2, 2, 2), "title": "ZnS — zincblende"},
    {"name": "cu", "file": "Cu.POSCAR", "supercell": None, "title": "Cu — fcc metal"},
    {
        "name": "mos2",
        "file": "MoS2.POSCAR",
        "supercell": (3, 3, 1),
        "title": "MoS2 — monolayer",
    },
    {"name": "graphene", "file": "graphene.POSCAR", "supercell": (3, 3, 1), "title": "graphene — 2D"},
    {"name": "benzene", "file": "benzene.POSCAR", "supercell": None, "title": "C6H6 — molecule"},
    {"name": "water", "file": "water.POSCAR", "supercell": None, "title": "H2O — molecule"},
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dpi", type=int, default=200)
    parser.add_argument("--width", type=float, default=4.5)
    parser.add_argument("--cols", type=int, default=4)
    parser.add_argument("--style", default="3d", choices=["3d", "toon", "flat"])
    parser.add_argument(
        "--canvas",
        nargs=2,
        type=float,
        default=[18.0, 18.0],
        metavar=("W", "H"),
        help="fixed view-plane size in Angstrom (0 0 disables)",
    )
    args = parser.parse_args()

    tiles = TILES / args.style
    tiles.mkdir(parents=True, exist_ok=True)
    base_style = style_preset(args.style)
    base_style.width_in = args.width
    base_style.dpi = args.dpi
    base_style.supersample = 2
    if args.canvas[0] > 0 and args.canvas[1] > 0:
        base_style.canvas = (args.canvas[0], args.canvas[1])

    rendered = []
    for case in CASES:
        structure = load_structure(STRUCTURES / case["file"])
        if case["supercell"] is not None:
            structure = structure.supercell(case["supercell"])
        view = auto_view(structure, style=base_style)
        output = tiles / f"{case['name']}.png"
        render(structure, output=output, view=view, style=base_style)
        scene = build_scene(structure, base_style)
        azimuth, elevation = view.angles_deg()
        rendered.append(
            (case["title"], scene.formula, output, azimuth, elevation)
        )
        print(
            f"[showcase] {case['title']:<22} {scene.formula:<8} "
            f"az {azimuth:6.1f} deg  el {elevation:5.1f} deg  -> {output.name}"
        )

    sheet_name = "showcase.png" if args.style == "3d" else f"showcase_{args.style}.png"
    compose(rendered, args.cols, base_style, OUTPUT / sheet_name)
    return 0


def compose(rendered, cols: int, style: Style, output) -> None:
    images = [plt.imread(item[2]) for item in rendered]
    count = len(rendered)
    rows = (count + cols - 1) // cols
    tile = style.width_in
    row_height = tile + 0.45
    figure_height = rows * row_height + 0.5
    figure = plt.figure(figsize=(cols * tile, figure_height), dpi=style.dpi)
    figure.patch.set_facecolor("#ffffff")

    header_frac = 0.5 / figure_height
    usable = 1.0 - header_frac
    caption_frac = 0.45 / row_height

    for index, (title, formula, path, azimuth, elevation) in enumerate(rendered):
        row, col = divmod(index, cols)
        x0 = col / cols
        cell_width = 1.0 / cols
        cell_height = usable / rows
        y0 = (1.0 - (row + 1) / rows) * usable
        caption_height = cell_height * caption_frac
        axes = figure.add_axes(
            (
                x0 + 0.006,
                y0 + caption_height + 0.006,
                cell_width - 0.012,
                cell_height - caption_height - 0.012,
            )
        )
        axes.imshow(images[index], interpolation="bilinear")
        axes.set_axis_off()
        figure.text(
            x0 + cell_width / 2,
            y0 + caption_height / 2,
            f"{title}   [{formula}]   auto: az {azimuth:.0f}°  el {elevation:.0f}°",
            ha="center",
            va="center",
            fontsize=9.5,
            color="#333333",
        )

    figure.text(
        0.5,
        1.0 - header_frac / 2,
        "MatVu — automatic viewpoint search + analytic tracer rendering "
        "(no manual rotation)",
        ha="center",
        va="center",
        fontsize=13,
    )
    figure.savefig(output, dpi=style.dpi, facecolor="#ffffff")
    plt.close(figure)
    print(f"[showcase] contact sheet -> {output}")


if __name__ == "__main__":
    raise SystemExit(main())
