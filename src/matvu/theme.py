"""Themes: palette + radii + style overrides in a user-editable TOML file.

Example theme file::

    name = "lab-theme"
    description = "our group colours"
    palette = "matvu"          # base palette: matvu | jmol | pastel

    [radii]
    atom_scale = 0.40          # display radius = covalent radius * scale
    min_radius = 0.0
    unbonded_scale = 0.45      # used for bond-free structures (metals)
    bond_radius = 0.09
    bond_tolerance = 1.20

    [colors]                   # per-element overrides on top of the palette
    O = "#FF5A4A"
    Fe = "#B87333"

Any :class:`~matvu.style.Style` field can additionally be set in a ``[style]``
table (for example ``background = "white"`` or ``depth_cue = 0.4``).
"""

from __future__ import annotations

from dataclasses import dataclass, fields
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10
    import tomli as tomllib

from . import palettes
from .style import Style

_RADIUS_KEYS = {
    "atom_scale": "atom_scale",
    "min_radius": "min_atom_radius",
    "unbonded_scale": "unbonded_atom_scale",
    "bond_radius": "bond_radius",
    "bond_tolerance": "bond_tolerance",
}
_STYLE_SKIP = {"palette", "palette_overrides"}
_STYLE_KEYS = {field.name for field in fields(Style)} - _STYLE_SKIP


@dataclass
class Theme:
    """A loaded theme: name, style (with palette) and description."""

    name: str
    style: Style
    description: str = ""

    def colour(self, symbol: str) -> str:
        """Resolved ``#RRGGBB`` colour (palette plus theme overrides)."""
        return palettes.palette_colour(
            self.style.palette, symbol, self.style.palette_overrides
        )


def available_themes() -> list[str]:
    """Names of the built-in themes (one per palette)."""
    return palettes.palette_names()


def load_theme(source, *, base: Style | None = None) -> Theme:
    """Load a built-in theme name or a ``.toml`` theme file.

    ``base`` is the starting :class:`Style` (e.g. a look preset such as
    ``style_preset("toon")``); the theme's tables are applied on top of it.
    """
    style = base or Style()
    if isinstance(source, Path) or (isinstance(source, str) and Path(source).is_file()):
        path = Path(source)
        data = tomllib.loads(path.read_text(encoding="utf-8"))
        name = str(data.get("name") or path.stem)
    else:
        key = str(source).lower()
        if key not in palettes.palette_names():
            raise ValueError(
                f"unknown theme {source!r}: expected one of "
                f"{palettes.palette_names()} or a path to a .toml theme file"
            )
        data = {"name": key, "palette": key}
        name = key

    for key, value in data.get("radii", {}).items():
        target = _RADIUS_KEYS.get(key)
        if target is None:
            raise ValueError(
                f"unknown [radii] key {key!r}; expected {sorted(_RADIUS_KEYS)}"
            )
        setattr(style, target, float(value))
    for key, value in data.get("style", {}).items():
        if key not in _STYLE_KEYS:
            raise ValueError(f"unknown [style] key {key!r}")
        setattr(style, key, value)
    style.palette = str(data.get("palette", style.palette))
    overrides = data.get("colors", {})
    style.palette_overrides = dict(overrides) if overrides else None
    return Theme(name=name, style=style, description=str(data.get("description", "")))


def export_theme(name: str, path=None) -> Path:
    """Write a full built-in theme as a TOML file users can copy and edit."""
    key = str(name).lower()
    if key not in palettes.palette_names():
        raise ValueError(
            f"unknown theme {name!r}; available: {palettes.palette_names()}"
        )
    destination = Path(path) if path else Path(f"{key}.toml")
    lines = [
        f'name = "{key}"',
        f'description = "MatVu built-in theme: {key} palette, default radii"',
        f'palette = "{key}"',
        "",
        "[radii]",
        "atom_scale = 0.40",
        "min_radius = 0.0",
        "unbonded_scale = 0.45",
        "bond_radius = 0.09",
        "bond_tolerance = 1.20",
        "",
        "[colors]",
    ]
    for symbol, colour in palettes.PALETTES[key].items():
        lines.append(f'{symbol} = "{colour}"')
    destination.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return destination
