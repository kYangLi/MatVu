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
  render as close-packed spheres (`--metal-bonds` re-enables the sticks)
- Unit cell frame drawn automatically for periodic crystals (molecular vacuum
  boxes are detected and skipped; `--no-cell` hides the frame)
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

## Command line

```bash
matvu render POSCAR --view auto -o figure.png
matvu render POSCAR --view a --width 4 --dpi 600 -o figure.pdf
matvu render POSCAR --backend matplotlib -o preview.png   # fast preview
matvu candidates POSCAR -n 12 -o candidates.png
matvu info POSCAR
```

## License

GPL-3.0-or-later. See [LICENSE](LICENSE).
