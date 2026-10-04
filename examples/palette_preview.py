"""Render a swatch sheet for every built-in palette.

Usage::

    .venv/bin/python examples/palette_preview.py
    # -> examples/out/palettes.png
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle

from matvu import elements, palettes

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "examples" / "out" / "palettes.png"

_COLUMNS = 18
_RADIUS = 0.42


def _luminance(colour: str) -> float:
    text = colour.lstrip("#")
    red, green, blue = (int(text[i : i + 2], 16) / 255.0 for i in (0, 2, 4))
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def main() -> None:
    symbols = elements.symbols()
    rows = (len(symbols) + _COLUMNS - 1) // _COLUMNS
    row_height = 1.0
    figure_height = len(palettes.PALETTES) * (rows * row_height + 0.9) + 0.4
    figure = plt.figure(figsize=(_COLUMNS * row_height, figure_height), dpi=160)
    axes = figure.add_axes((0.0, 0.0, 1.0, 1.0))
    axes.set_xlim(0, _COLUMNS)
    axes.set_ylim(-figure_height + 0.5, 0.5)
    axes.set_axis_off()
    axes.set_aspect("equal")

    y = 0.0
    for name in palettes.palette_names():
        axes.text(0.1, y - 0.35, f"{name}", fontsize=13, family="monospace")
        y -= 0.75
        for index, symbol in enumerate(symbols):
            row, column = divmod(index, _COLUMNS)
            x = column + 0.5
            centre_y = y - row - 0.5
            colour = palettes.palette_colour(name, symbol)
            axes.add_patch(
                Circle((x, centre_y), _RADIUS, facecolor=colour, edgecolor="none")
            )
            axes.text(
                x,
                centre_y,
                symbol,
                ha="center",
                va="center",
                fontsize=8,
                color="#FFFFFF" if _luminance(colour) < 0.55 else "#222222",
            )
        y -= rows * row_height + 0.15

    figure.savefig(OUTPUT, dpi=160, facecolor="#F5F6F8")
    plt.close(figure)
    print(f"wrote {OUTPUT}")


if __name__ == "__main__":
    main()
