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
- POSCAR reader with a small plugin interface for future formats (CIF, XYZ, ...)
- Ball-and-stick renderer on a lightweight matplotlib backend (PNG / PDF / SVG)
- Core architecture prepared for multiple backends (interactive web view planned)
- Periodic crystals, 2D materials and finite molecules through one `Structure` model

## Status

Early local development — **not released, not on PyPI, the API may change.**

Roadmap: interactive web backend, candidate-view gallery, perspective camera,
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

## Command line

```bash
matvu render POSCAR --view auto -o figure.png
matvu render POSCAR --view a --width 4 --dpi 600 -o figure.pdf
matvu info POSCAR
```

## License

GPL-3.0-or-later. See [LICENSE](LICENSE).
