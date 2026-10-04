"""Element colour palettes.

The palettes are deliberate designs, not arbitrary assignments:

* hues follow the classic CPK conventions where they help recognition
  (H light, C charcoal, N blue, O red, F/Cl green, S gold, P amber, ...);
* saturation and lightness are tuned to one coherent modern look that reads
  well on white *and* on dark backgrounds;
* elements of the same family share a colour family on purpose (the first-row
  transition metals use a steel/teal scale, the noble gases are pale, ...).

``jmol`` keeps the classic Jmol/CPK table for compatibility, and ``pastel``
is a documented lightening of the default palette.
"""

from __future__ import annotations

from . import elements

# Official default palette ("matvu").
_MATVU: dict[str, str] = {
    # main group ---------------------------------------------------------
    "H": "#C7CBD1", "He": "#C2D4E0",
    "Li": "#9A7FD6", "Be": "#9CC26E", "B": "#D9A0A0", "C": "#3F4650",
    "N": "#4A6FD4", "O": "#E04A3A", "F": "#8CC46E", "Ne": "#A9CDD8",
    "Na": "#8B6FC9", "Mg": "#7FB87F", "Al": "#94A3B5", "Si": "#D6B08C",
    "P": "#E08A38", "S": "#D9B93C", "Cl": "#57A85C", "Ar": "#8FC0C9",
    "K": "#6F5ABF", "Ca": "#7FAF85",
    # first-row transition metals: a single steel/teal scale ------------
    "Sc": "#A8B0BC", "Ti": "#97A4B8", "V": "#8B95B3", "Cr": "#7D88A8",
    "Mn": "#937FB5", "Fe": "#C9723F", "Co": "#B87BA6", "Ni": "#6FAE7E",
    "Cu": "#BC7A4E", "Zn": "#7F8FB5",
    "Ga": "#B08FA0", "Ge": "#7F9A9A", "As": "#A983C4", "Se": "#D69A42",
    "Br": "#A85252", "Kr": "#62A8C2",
    "Rb": "#6A4FB3", "Sr": "#74A878",
    # heavier transition / post-transition metals ------------------------
    "Y": "#74B8BC", "Zr": "#72A8B4", "Nb": "#5F9BAC", "Mo": "#4E8FA3",
    "Tc": "#3F8397", "Ru": "#35798C", "Rh": "#2F7186", "Pd": "#2A6B7F",
    "Ag": "#B3B8BE", "Cd": "#D2B77F", "In": "#A98C8C", "Sn": "#6F8A8F",
    "Sb": "#977BB0", "Te": "#C08A40", "I": "#8A5AA6", "Xe": "#5C9CB4",
    "Cs": "#5646A0", "Ba": "#7FAF6F", "La": "#6FACC8", "Ce": "#D0C488",
    "Hf": "#6FA4BE", "Ta": "#6A9BBA", "W": "#5C93B5", "Re": "#528AAE",
    "Os": "#4A80A8", "Ir": "#43779F", "Pt": "#A3ACB6", "Au": "#D2A63C",
    "Hg": "#A3A3B8", "Tl": "#9A8383", "Pb": "#6F737A", "Bi": "#966FA8",
    "Th": "#5AA6C2", "U": "#4F97B5",
}

_JMOL: dict[str, str] = elements.all_colours()


def _lighten(hex_colour: str, amount: float) -> str:
    text = hex_colour.lstrip("#")
    channels = [int(text[i : i + 2], 16) / 255.0 for i in (0, 2, 4)]
    mixed = [channel + (1.0 - channel) * amount for channel in channels]
    return "#" + "".join(f"{round(channel * 255):02X}" for channel in mixed)


# Soft pastel variant of the default palette (a documented transformation).
_PASTEL: dict[str, str] = {
    symbol: _lighten(colour, 0.35) for symbol, colour in _MATVU.items()
}
_PASTEL["H"] = "#CFD3D9"  # keep hydrogen readable, not white
_PASTEL["C"] = "#6E7680"  # charcoal has to stay dark enough

PALETTES: dict[str, dict[str, str]] = {
    "matvu": _MATVU,
    "jmol": _JMOL,
    "pastel": _PASTEL,
}


def palette_names() -> list[str]:
    """Names of the built-in palettes."""
    return sorted(PALETTES)


def _normalised_overrides(overrides) -> dict[str, str]:
    if not overrides:
        return {}
    return {elements.normalise_symbol(key): value for key, value in overrides.items()}


def palette_colour(palette: str = "matvu", symbol: str = "H", overrides=None) -> str:
    """``#RRGGBB`` colour of one element in a palette (with user overrides)."""
    base = PALETTES.get(str(palette).lower())
    if base is None:
        raise ValueError(
            f"unknown palette {palette!r}; available: {palette_names()}"
        )
    normalised = elements.normalise_symbol(symbol)
    merged = _normalised_overrides(overrides)
    if normalised in merged:
        return merged[normalised]
    if normalised in base:
        return base[normalised]
    return elements.colour_hex(symbol)


def colour_rgb(
    palette: str = "matvu", symbol: str = "H", overrides=None
) -> tuple[float, float, float]:
    """Colour of one element as three floats in [0, 1]."""
    text = palette_colour(palette, symbol, overrides).lstrip("#")
    return tuple(int(text[i : i + 2], 16) / 255.0 for i in (0, 2, 4))  # type: ignore[return-value]
