# Changelog

## 0.1.1 (2026-10-10)

- **Fixed a severe `slab_normal()` misclassification**: layered detection now
  uses the lattice and the fractional vacuum (one direction with a
  several-Angstrom vacuum gap while the atoms stay within half the cell)
  instead of point-cloud PCA shape. Slightly flattened 3D crystals (e.g.
  CaI6SrTl2, Br6In2PbTl2, Ag2CaI6Rb2) and elongated cells (e.g. Hg2Mg2Te4)
  are no longer mistaken for slabs; structures filling the cell in every
  direction short-circuit the test immediately.
- **Unit-cell frame decoupled from the viewpoint**: new
  `Style.cell = "auto" | "always" | "never"` and CLI `--cell` /
  `--force-cell` / `--no-cell` — force frames for batch figures without
  changing the automatic view.
- `molecular_box()` now additionally requires real vacuum on *every* axis, so
  primitive cells of 2D materials (a single graphene cell) are no longer
  classified as molecular vacuum boxes.
- New `render_array()` returns the RGBA image in memory (no file round-trip)
  and `View.to_json()` / `View.from_json()` make viewpoints reproducible.
- Removed a duplicated span check in `cell_corners()`.

## 0.1.0 (2026-10-10)

First public release.

- `Structure` model with a POSCAR reader and a plugin registry for more formats
- Automatic viewpoint optimisation:
  - maximin projected-dispersion search for crystals, constrained to a
    comfortable above-horizon elevation band
  - one shared three-quarter view for all cubic lattices
  - ~30 degree tilt for layered 2D materials; face-on views for molecules
- Two rendering backends:
  - `tracer` (default): pure-numpy analytic ray casting with exact occlusion
    and supersampling, orthographic or perspective camera
  - `matplotlib`: fast preview backend (PNG / PDF / SVG)
- Look presets: `3d` (shaded), `toon` (cel/animation), `flat` (pure fill)
- Designed element palettes (`matvu`, `jmol`, `pastel`) and user-editable
  TOML themes covering colours, radii and style overrides
- Symmetric periodic boundary decoration, unit cell frames for 3D crystals,
  transparent output by default, fixed-canvas option for uniform-scale series
- CLI: `matvu render`, `matvu info`, `matvu candidates`, `matvu theme`
