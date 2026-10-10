<!-- markdownlint-disable MD033 MD036 -->
<h1><p align="center">
  <img src="https://raw.githubusercontent.com/kYangLi/MatVu/main/docs/_image/logo.svg" alt="MatVu Logo" width="560">
</p></h1>

<div align="center">

### Automatic viewpoint optimization for materials structures

[![tests](https://github.com/kYangLi/MatVu/actions/workflows/test.yml/badge.svg)](https://github.com/kYangLi/MatVu/actions/workflows/test.yml)
[![release](https://github.com/kYangLi/MatVu/actions/workflows/release.yml/badge.svg)](https://github.com/kYangLi/MatVu/actions/workflows/release.yml)
[![PyPI Version](https://img.shields.io/pypi/v/matvu.svg)](https://pypi.org/project/matvu/)
[![Python versions](https://img.shields.io/pypi/pyversions/matvu.svg)](https://pypi.org/project/matvu/)
[![License](https://img.shields.io/pypi/l/matvu.svg)](https://pypi.org/project/matvu/)

[![GitHub Issues](https://img.shields.io/github/issues/kYangLi/MatVu.svg)](https://github.com/kYangLi/MatVu/issues)
[![GitHub Stars](https://img.shields.io/github/stars/kYangLi/MatVu.svg?style=social)](https://github.com/kYangLi/MatVu/stargazers)

*Point it at a structure — it finds the view.*
</div>

*MatVu* is an automatic viewpoint optimization and visualization toolkit for materials structures. Give it a structure file (a POSCAR to start with) and it works out a clear, publication-ready viewing direction on its own — no manual rotating, zooming and re-rendering until the figure looks right.

At the core of *MatVu* is **a viewpoint search that treats the camera angle as an optimization problem**. It scores hundreds of candidate directions by projected atom overlap, bond foreshortening and framing, keeps a comfortable above-horizon elevation band, and then picks the view that spreads the atoms out most evenly (*maximin projected dispersion*). Built-in conventions make series of figures consistent: every cubic crystal shares one fixed three-quarter view, layered 2D materials are shown at a ~30° tilt, and flat molecules keep their face-on view.

Rendering is handled by pluggable backends: a **`tracer`** backend that performs analytic ray casting in pure NumPy (exact sphere/stick occlusion, no OpenGL/VTK, works headless) and a fast **`matplotlib`** preview backend. Three look presets — `3d`, `toon` (animation/cel style) and `flat` — share the same geometry, and a **theme system** lets you design your own element colours and atom radii in a small TOML file.

*MatVu* handles periodic crystals, 2D materials and finite molecules through one uniform `Structure` model, draws symmetric unit-cell figures with mirrored boundary atoms, and writes transparent PNG/PDF/SVG by default.

---

- [Core Features](#core-features)
- [Quick Start](#quick-start)
  - [Installation](#installation)
  - [Basic Usage](#basic-usage)
  - [Rendering Styles](#rendering-styles)
  - [Gallery](#gallery)
  - [Uniform-Scale Series](#uniform-scale-series)
  - [Batch Rendering and Animations](#batch-rendering-and-animations)
- [Themes](#themes)
- [Citation](#citation)
- [Application Scenarios](#application-scenarios)
- [Contributing](#contributing)
- [License](#license)
- [Support \& Contact](#support--contact)

## Core Features

- **Automatic Viewpoint Optimization:** Scores hundreds of candidate directions (Fibonacci sampling plus high-symmetry directions) for occlusion, bond foreshortening and framing, then selects the most evenly spread view; cubic lattices share one fixed three-quarter convention.

- **Publication-Ready Output:** Transparent PNG/TIFF/WebP and PDF/SVG by default, strict atom radii (display sizes proportional to covalent radii), designed element palettes and symmetric unit-cell frames (`--cell auto|always|never`, decoupled from the viewpoint choice).

- **Multiple Rendering Backends:** An analytic ray-casting `tracer` (pure NumPy, exact occlusion, supersampling, orthographic or perspective) and a fast `matplotlib` preview backend — more backends can be registered.

- **Look Presets and Themes:** `3d`, `toon` (cel shading) and `flat` styles; three official palettes (`matvu`, `jmol`, `pastel`) plus user-editable TOML themes covering colours, radii and any style parameter.

- **Works for Crystals, 2D Materials and Molecules:** One `Structure` model for periodic cells (with mirrored boundary atoms), layered slabs (automatic tilted views) and finite molecules (face-on views), driven by a plugin reader registry — POSCAR/CONTCAR, CIF (with symmetry expansion) and XYZ/extxyz are built in.

- **Project-Scale Workflows:** `matvu batch` renders every structure of a project tree (DeepH-style `dft/**/POSCAR` out of the box, in place or mirrored to a figure directory) and `matvu animate` exports 360° orbit GIF/WebP animations from the automatic view.

## Quick Start

### Installation

Publish version:

```bash
pip install matvu
```

Development version:

```bash
git clone https://github.com/kYangLi/MatVu
cd MatVu
uv venv
uv pip install -e ".[dev]"
pytest
```

### Basic Usage

One line is enough — the view is chosen automatically:

```python
from matvu import render, render_array, render_batch, render_orbit

render("POSCAR", view="auto")            # -> POSCAR_view.png (transparent)
render("POSCAR", style="toon", view="a") # explicit style and view

image = render_array("POSCAR", view="auto")     # (H, W, 4) float RGBA in memory
render_batch("dft/", "figures/", jobs=0)        # every dft/**/POSCAR
render_orbit("POSCAR", "spin.gif", frames=72)   # 360 deg orbit animation
```

Command line:

```bash
matvu render POSCAR --style toon -o figure.png   # animation-style figure
matvu render POSCAR --force-cell -o fig.png      # force the unit-cell frame
matvu render POSCAR --canvas 12 12 -o fig.png   # uniform scale across figures
matvu candidates POSCAR -n 12 -o candidates.png # ranked viewpoint contact sheet
matvu batch dft/ -o figures/ -j 0               # every dft/**/POSCAR (mirrored)
matvu animate POSCAR --frames 72 -o spin.gif    # 360 deg orbit animation
matvu info POSCAR                               # composition, cell, volume
matvu theme list                                # built-in themes and palettes
```

### Rendering Styles

| Preset | Look | Camera |
| --- | --- | --- |
| `3d` (default) | shaded ball-and-stick, soft highlights | perspective |
| `toon` | animation/cel style: flat colours, two-tone shadow, outlines | perspective |
| `flat` | pure flat fill with outlines, no shading | perspective |

All presets share the same automatic viewpoint; `toon` and `flat` add an aerial-perspective depth fade.

### Gallery

Every figure is rendered with a completely automatic viewpoint — no manual rotation. Ready-made images live in [`examples/figures/`](examples/figures/); regenerate them with `python examples/showcase.py --style <preset>`.

[![MatVu showcase — toon](https://raw.githubusercontent.com/kYangLi/MatVu/main/examples/figures/showcase_toon.png)](examples/figures/)

Other ready-made figures: [`3d`](https://raw.githubusercontent.com/kYangLi/MatVu/main/examples/figures/showcase_3d.png) · [`flat`](https://raw.githubusercontent.com/kYangLi/MatVu/main/examples/figures/showcase_flat.png) · palette sheet [`palettes.png`](https://raw.githubusercontent.com/kYangLi/MatVu/main/examples/figures/palettes.png)

### Uniform-Scale Series

By default every figure is fitted to its own structure. For a series of comparable figures, pass the same canvas:

```bash
matvu render POSCAR --canvas 18 18 -o fig.png
```

The canvas is a *minimum* size: if a structure does not fit, the image expands instead of clipping, so atoms keep exactly the same size across the series.

### Batch Rendering and Animations

`matvu batch` walks a project tree and renders every structure it finds — a DeepH-style layout needs no arguments beyond the root directory:

```bash
matvu batch dft/                         # every dft/**/POSCAR -> POSCAR_view.png beside it
matvu batch dft/ -o figures/             # mirror the tree under figures/ instead
matvu batch dft/ --format pdf,png -j 0   # vector + raster, all cores
matvu batch dft/ --pattern "POSCAR,CONTCAR,*.vasp,*.cif" --skip-existing
```

It defaults to **`png`** — transparent, previewable right next to the calculation and consistent with `matvu render`; pass `--format pdf` (or `pdf,png`) for vector figures. `--skip-existing` makes re-runs incremental and `-j 0` uses every core.

`matvu animate` turns the automatic view into a looping 360° orbit:

```bash
matvu animate POSCAR --frames 72 -o spin.gif          # GIF (flat background)
matvu animate POSCAR --frames 72 -o spin.webp         # animated WebP (keeps transparency)
matvu animate POSCAR --frames 72 --frames-dir frames/ # transparent PNG frames
```

`--axis auto` (the default) picks the world axis most perpendicular to the view, so the camera is guaranteed to move; `--axis x|y|z` pins it to a fixed axis.

## Themes

Colours and sizes live in a **theme**: a small TOML file with a palette, atom radii and optional style overrides. Three carefully designed palettes ship with MatVu — `matvu` (default: modern, muted, family-coherent), `jmol` (classic CPK) and `pastel` (soft variant):

```bash
matvu render POSCAR --style toon --palette pastel -o fig.png
matvu theme export matvu -o my-theme.toml     # full default theme to edit
matvu render POSCAR --theme my-theme.toml -o fig.png
```

```toml
name = "lab-theme"
description = "our group colours"
palette = "matvu"          # base palette: matvu | jmol | pastel

[radii]
atom_scale = 0.40          # display radius = covalent radius * scale
min_radius = 0.0
unbonded_scale = 0.45      # bond-free structures (bulk metals)
bond_radius = 0.09
bond_tolerance = 1.20

[colors]                   # per-element overrides on top of the palette
O = "#FF5A4A"
Fe = "#B87333"
```

A `[style]` table can additionally set any `Style` field (`depth_cue`, `background`, `shading`, ...).

## Citation

*Any and all use of this software, in whole or in part, should clearly acknowledge and link to this repository.*

If you use *MatVu* in academic work, please cite the software using the metadata in [`CITATION.cff`](CITATION.cff) (GitHub's **Cite this repository** button uses the same file). A methods paper is in preparation.

## Application Scenarios

- **Paper and thesis figures**: one command per structure, consistent viewpoints across a series, vector and transparent output ready for LaTeX/slides
- **Teaching and presentations**: quick, readable ball-and-stick figures in `toon`/`flat` styles without a GUI
- **High-throughput screening**: batch-render large structure sets with fixed palettes, radii and camera conventions
- **Method development**: the viewpoint scoring, palettes and backends are modular and fully unit-tested (119 tests) — easy to extend and compare

## Contributing

Contributions are welcome. The workflow is short:

1. Fork the repository and create a feature branch.
2. Set up the development environment (`uv venv && uv pip install -e ".[dev]"`).
3. Add tests for new behaviour and run the full suite: `pytest`.
4. Open a pull request; the `tests` workflow runs on Python 3.10–3.13 for every push and PR.

See [`docs/design.md`](docs/design.md) for the architecture and the viewpoint scoring model, and [`docs/releasing.md`](docs/releasing.md) for the release process.

## License

GPL-3.0-or-later. See the [LICENSE](LICENSE) file for details.

## Support & Contact

- 🐛 **Issue Reporting**: [GitHub Issues](https://github.com/kYangLi/MatVu/issues)
- 📦 **Package**: [pypi.org/project/matvu](https://pypi.org/project/matvu/)
- 📖 **Design Notes**: [`docs/design.md`](docs/design.md) · [`docs/roadmap.md`](docs/roadmap.md)

---

*MatVu is research software: viewpoints are chosen automatically, but the judgement of a good figure stays with you — feedback and issues are always welcome.*
