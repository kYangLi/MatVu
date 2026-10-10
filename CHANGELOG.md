# Changelog

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
