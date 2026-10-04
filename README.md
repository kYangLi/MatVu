# MatVu

**Automatic viewpoint optimization and visualization for materials structures.**

Point MatVu at a structure — a POSCAR to start with — and it works out a
clear, publication-ready view for you. No manual rotating.

```python
from matvu import render

render("POSCAR", view="auto")   # -> POSCAR_view.png
```

## Why

Tools like VESTA and ASE are powerful, but choosing a good camera angle is
still manual work: you rotate, zoom and re-render until the figure looks right.
MatVu treats the viewpoint itself as an optimization problem. It analyses
the geometry — projected atom overlap, bond foreshortening, framing — and picks
a direction that shows the structure clearly, then renders a ball-and-stick
figure suitable for papers.

## Features

Early development, but already useful:

- `view="auto"`: viewpoint search over hundreds of candidate directions
  (Fibonacci sampling + principal axes + lattice directions, then local refinement)
- `matvu candidates`: contact sheet of the top-ranked viewpoints, annotated with
  angles and scores — the tool used to calibrate the scoring model
- Sensible defaults for metals: metal-metal bonds are skipped and bulk metals
  render as a clear lattice of distinct spheres (`--metal-bonds` re-enables
  the sticks)
- Fixed-canvas option for a uniform-scale series: `--canvas W H` (Angstrom,
  also `Style.canvas`) keeps the canvas and atom size identical across
  figures; the canvas is a *minimum* size, so oversized structures expand the
  image instead of clipping (scale preserved). By default there is no canvas:
  every figure is fitted to its own structure, so small molecules are shown
  large enough to read
- Automatic viewpoint selection uses a maximin projected-dispersion criterion
  for crystals (atoms spread out evenly; views stay in a comfortable
  above-horizon elevation band, neither looking up nor steep top-down), a
  ~30 degree tilt for layered materials and face-on views for molecules
- Three look presets, all sharing the same automatic viewpoint and the
  perspective camera: `3d` (shaded, default), `toon` (animation/cel style:
  flat colours, two-tone shadow, outlines) and `flat` (pure flat fill with
  outlines, no shading). `toon`/`flat` add an aerial-perspective depth fade.
  Example: `matvu render --style toon`
- Transparent background by default (PNG/TIFF/WebP with alpha, PDF/SVG
  transparent too); `--opaque` restores a white background. Hydrogen uses a
  light grey instead of pure white so it stays visible
- Atom sizes are strictly proportional to covalent radii at a uniform scale
  (no forced minimum radius)
- Three designed element palettes (`matvu`, `jmol`, `pastel`) with a
  user-editable TOML theme format covering colours, radii and style
  overrides — see [Themes](#themes)
- Unit cell frame drawn for 3D crystals only; molecular vacuum boxes and 2D
  slab cells are detected automatically and skipped (`--no-cell` hides it)
- Mild perspective by default (`--perspective 0` for orthographic);
  layered 2D materials are automatically shown at a ~30 degree tilt while
  flat molecules keep their face-on view
- Boundary atoms are mirrored into a thin margin outside the cell, so the
  cell looks symmetric and complete (the classic cell figure); isolated
  copies are dropped automatically, `--boundary-padding 0` disables it
- POSCAR reader with a small plugin interface for future formats (CIF, XYZ, ...)
- Ball-and-stick rendering with two backends:
  - `tracer` (default): an analytic ray-casting renderer in pure numpy with a
    z-buffer — exact sphere/stick occlusion, 2x supersampling, no OpenGL/VTK
  - `matplotlib`: fast preview backend (PNG / PDF / SVG)
- Core architecture prepared for multiple backends (interactive web view planned)
- Periodic crystals, 2D materials and finite molecules through one `Structure` model

## Status

Early local development — **not released, not on PyPI, the API may change.**

Roadmap: interactive web backend, perspective camera,
polyhedra and space-filling styles, CIF/XYZ readers, symmetry-aware viewpoints.
See `docs/design.md` for the architecture and the viewpoint scoring model, and
`docs/roadmap.md` for the development plan and handover notes.

## Install (development)

```bash
git clone https://github.com/<account>/MatVu   # once the repository is public
cd MatVu
uv venv
uv pip install -e ".[dev]"
pytest
```

## Examples

```bash
.venv/bin/python examples/showcase.py
```

Renders every structure in `examples/structures/` with an automatically chosen
viewpoint and the tracer backend, writing individual figures plus a contact
sheet to `examples/out/`.

## Themes

Colours and sizes live in a **theme**: a small TOML file with a palette,
atom radii and optional style overrides. Three carefully designed palettes
ship with MatVu — `matvu` (default: modern, muted, family-coherent),
`jmol` (classic CPK) and `pastel` (soft variant):

```bash
matvu render POSCAR --style toon --palette pastel -o fig.png
matvu theme list
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

A `[style]` table can additionally set any `Style` field
(`depth_cue`, `background`, `shading`, ...).

## Command line

```bash
matvu render POSCAR --view auto -o figure.png
matvu render POSCAR --view a --width 4 --dpi 600 -o figure.pdf
matvu render POSCAR --style toon -o toon.png               # animation style
matvu render POSCAR --style flat -o flat.png               # pure flat fill
matvu render POSCAR --canvas 12 12 -o fig.png              # uniform scale across figures
matvu render POSCAR --backend matplotlib -o preview.png   # fast preview
matvu candidates POSCAR -n 12 -o candidates.png
matvu info POSCAR
```

## License

GPL-3.0-or-later. See [LICENSE](LICENSE).
