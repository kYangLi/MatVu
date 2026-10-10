# MatVu examples

Everything in this folder is meant to be run directly to produce figures —
no configuration needed.

## Layout

| Path | Contents |
| --- | --- |
| `structures/` | Small input structures (POSCAR): crystals (Si, NaCl, ZnS, Cu), 2D materials (graphene, MoS2) and molecules (benzene, water) |
| `showcase.py` | Renders all of them with fully automatic viewpoints: one PNG per structure plus a labelled contact sheet |
| `palette_preview.py` | Swatch sheet of every built-in palette |
| `figures/` | **Ready-made outputs** of the scripts above (committed — no need to run anything) |
| `out/` | Scratch output directory (git-ignored) |

## Running

```bash
# from the repository root, with the venv active
.venv/bin/python examples/showcase.py --style toon    # -> examples/out/showcase_toon.png
.venv/bin/python examples/showcase.py                 # default preset `3d`
.venv/bin/python examples/showcase.py --style flat
.venv/bin/python examples/palette_preview.py          # -> examples/out/palettes.png
```

Extras: `--dpi`, `--width`, `--cols`, `--canvas W H` (uniform scale across
structures) and `--out DIR` to write somewhere else:

```bash
.venv/bin/python examples/showcase.py --style toon --canvas 18 18 --out /tmp/matvu
```

The committed copies in `figures/` are the contact sheets from these commands
(`--dpi 150`). Rendering the same structure twice gives the same viewpoint and
image — the automatic view search is deterministic.

## Your own project

The same engine works on the command line for whole project trees and
animations:

```bash
matvu batch dft/ -o figures/ --style toon --force-cell   # every dft/**/POSCAR
matvu animate structures/Si.POSCAR --frames 72 -o spin.gif
```

`matvu batch` writes `POSCAR_view.png` next to each structure by default (or
mirrors the tree under `-o DIR`); see the README for formats, selection
patterns and parallelism.

Repository tooling (logo and social-preview assets) lives in [`scripts/`](../scripts/),
not here.
