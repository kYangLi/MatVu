"""Element data: masses, radii and CPK/Jmol colours.

Sources
-------
- Covalent radii: Cordero et al., Dalton Trans. 2008.
- Van der Waals radii: Bondi (1964) with common extensions.
- Colours: Jmol CPK table.
- Masses: IUPAC standard atomic weights (abridged).
"""

from __future__ import annotations

from functools import lru_cache

# symbol -> (atomic_mass, covalent_radius, vdw_radius, colour)
_ELEMENTS: dict[str, tuple[float, float, float, str]] = {
    "H": (1.008, 0.31, 1.20, "#FFFFFF"),
    "He": (4.003, 0.28, 1.40, "#D9FFFF"),
    "Li": (6.94, 1.28, 1.82, "#CC80FF"),
    "Be": (9.012, 0.96, 1.53, "#C2FF00"),
    "B": (10.81, 0.84, 1.92, "#FFB5B5"),
    "C": (12.011, 0.76, 1.70, "#909090"),
    "N": (14.007, 0.71, 1.55, "#3050F8"),
    "O": (15.999, 0.66, 1.52, "#FF0D0D"),
    "F": (18.998, 0.57, 1.47, "#90E050"),
    "Ne": (20.180, 0.58, 1.54, "#B3E3F5"),
    "Na": (22.990, 1.66, 2.27, "#AB5CF2"),
    "Mg": (24.305, 1.41, 1.73, "#8AFF00"),
    "Al": (26.982, 1.21, 1.84, "#BFA6A6"),
    "Si": (28.085, 1.11, 2.10, "#F0C8A0"),
    "P": (30.974, 1.07, 1.80, "#FF8000"),
    "S": (32.06, 1.05, 1.80, "#FFFF30"),
    "Cl": (35.45, 1.02, 1.75, "#1FF01F"),
    "Ar": (39.948, 1.06, 1.88, "#80D1E3"),
    "K": (39.098, 2.03, 2.75, "#8F40D4"),
    "Ca": (40.078, 1.76, 2.31, "#3DFF00"),
    "Sc": (44.956, 1.70, 2.15, "#E6E6E6"),
    "Ti": (47.867, 1.60, 2.11, "#BFC2C7"),
    "V": (50.942, 1.53, 2.07, "#A6A6AB"),
    "Cr": (51.996, 1.39, 2.06, "#8A99C7"),
    "Mn": (54.938, 1.39, 2.05, "#9C7AC7"),
    "Fe": (55.845, 1.32, 2.04, "#E06633"),
    "Co": (58.933, 1.26, 2.00, "#F090A0"),
    "Ni": (58.693, 1.24, 1.97, "#50D050"),
    "Cu": (63.546, 1.32, 1.96, "#C88033"),
    "Zn": (65.38, 1.22, 2.01, "#7D80B0"),
    "Ga": (69.723, 1.22, 1.87, "#C28F8F"),
    "Ge": (72.630, 1.20, 2.11, "#668F8F"),
    "As": (74.922, 1.19, 1.85, "#BD80E3"),
    "Se": (78.971, 1.20, 1.90, "#FFA100"),
    "Br": (79.904, 1.20, 1.85, "#A62929"),
    "Kr": (83.798, 1.16, 2.02, "#5CB8D1"),
    "Rb": (85.468, 2.20, 3.03, "#702EB0"),
    "Sr": (87.62, 1.95, 2.49, "#00FF00"),
    "Y": (88.906, 1.90, 2.32, "#94FFFF"),
    "Zr": (91.224, 1.75, 2.23, "#94E0E0"),
    "Nb": (92.906, 1.64, 2.18, "#73C2C9"),
    "Mo": (95.95, 1.54, 2.17, "#54B5B5"),
    "Tc": (98.0, 1.47, 2.16, "#3B9E9E"),
    "Ru": (101.07, 1.46, 2.13, "#248F8F"),
    "Rh": (102.906, 1.42, 2.10, "#0A7D8C"),
    "Pd": (106.42, 1.39, 2.10, "#006985"),
    "Ag": (107.868, 1.45, 2.11, "#C0C0C0"),
    "Cd": (112.414, 1.44, 2.18, "#FFD98F"),
    "In": (114.818, 1.42, 1.93, "#A67573"),
    "Sn": (118.710, 1.39, 2.17, "#668080"),
    "Sb": (121.760, 1.39, 2.06, "#9E63B5"),
    "Te": (127.60, 1.38, 2.06, "#D47A00"),
    "I": (126.904, 1.39, 1.98, "#940094"),
    "Xe": (131.293, 1.40, 2.16, "#429EB0"),
    "Cs": (132.905, 2.44, 3.43, "#57178F"),
    "Ba": (137.327, 2.15, 2.68, "#00C900"),
    "La": (138.905, 2.07, 2.43, "#70D4FF"),
    "Ce": (140.116, 2.04, 2.42, "#FFFFC7"),
    "Hf": (178.49, 1.75, 2.23, "#4DC2FF"),
    "Ta": (180.948, 1.70, 2.22, "#4DA6FF"),
    "W": (183.84, 1.62, 2.18, "#2194D6"),
    "Re": (186.207, 1.51, 2.16, "#267DAB"),
    "Os": (190.23, 1.44, 2.16, "#266696"),
    "Ir": (192.217, 1.41, 2.13, "#175487"),
    "Pt": (195.084, 1.36, 2.13, "#D0D0E0"),
    "Au": (196.967, 1.36, 2.14, "#FFD123"),
    "Hg": (200.592, 1.32, 2.23, "#B8B8D0"),
    "Tl": (204.38, 1.45, 1.96, "#A6544D"),
    "Pb": (207.2, 1.46, 2.02, "#575961"),
    "Bi": (208.980, 1.48, 2.07, "#9E4FB5"),
    "Th": (232.038, 2.00, 2.37, "#00BAFF"),
    "U": (238.029, 1.96, 2.41, "#008FFF"),
}

# Fallback for symbols that are not in the table (e.g. dummy atoms).
_UNKNOWN = ("X", 1.40, 1.70, "#FF1493")


def normalise_symbol(symbol: str) -> str:
    """Return the conventional capitalisation of an element symbol."""
    text = str(symbol).strip()
    if not text:
        return "X"
    return text[0].upper() + text[1:].lower()


def is_known(symbol: str) -> bool:
    """Whether the symbol has a dedicated entry in the element table."""
    return normalise_symbol(symbol) in _ELEMENTS


def _data(symbol: str) -> tuple[float, float, float, str]:
    return _ELEMENTS.get(normalise_symbol(symbol), _UNKNOWN)


def atomic_mass(symbol: str) -> float:
    """Atomic mass in u."""
    return _data(symbol)[0]


def covalent_radius(symbol: str) -> float:
    """Covalent radius in Angstrom."""
    return _data(symbol)[1]


def vdw_radius(symbol: str) -> float:
    """Van der Waals radius in Angstrom."""
    return _data(symbol)[2]


def colour_hex(symbol: str) -> str:
    """Jmol CPK colour as ``#RRGGBB``."""
    return _data(symbol)[3]


@lru_cache(maxsize=None)
def colour_rgb(symbol: str) -> tuple[float, float, float]:
    """Jmol CPK colour as three floats in [0, 1]."""
    text = colour_hex(symbol).lstrip("#")
    return tuple(int(text[i : i + 2], 16) / 255.0 for i in (0, 2, 4))  # type: ignore[return-value]
