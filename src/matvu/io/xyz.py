"""Reader for plain XYZ and extended XYZ (extxyz) files.

Plain XYZ files become non-periodic molecules. Extended XYZ files that carry
the ``Lattice="..."`` header property become periodic structures; ``pbc="T T
F"`` is honoured when present.
"""

from __future__ import annotations

import re

import numpy as np

from .. import elements
from ..structure import Structure

_LATTICE = re.compile(r'Lattice\s*=\s*"([^"]+)"', re.IGNORECASE)
_PBC = re.compile(r'\bpbc\s*=\s*"([^"]+)"', re.IGNORECASE)

_TRUE = {"t", "true", "1", "yes"}


def read_xyz(text: str) -> Structure:
    """Parse an XYZ/extxyz string into a :class:`Structure`."""
    lines = text.splitlines()
    if not lines:
        raise ValueError("empty XYZ file")
    try:
        n_atoms = int(lines[0].split()[0])
    except (IndexError, ValueError) as exc:
        raise ValueError(
            f"the first XYZ line must be an atom count, got {lines[0]!r}"
        ) from exc
    if n_atoms < 0:
        raise ValueError("XYZ atom count must be non-negative")
    if len(lines) < 2 + n_atoms:
        raise ValueError(
            f"XYZ declares {n_atoms} atoms but has only {max(len(lines) - 2, 0)} rows"
        )
    comment = lines[1].strip() if len(lines) > 1 else ""

    symbols: list[str] = []
    coords: list[list[float]] = []
    for row in range(n_atoms):
        tokens = lines[2 + row].split()
        if len(tokens) < 4:
            raise ValueError(f"XYZ row {row + 3} needs symbol + x y z: {lines[2 + row]!r}")
        try:
            coords.append([float(value) for value in tokens[1:4]])
        except ValueError as exc:
            raise ValueError(f"XYZ row {row + 3} has non-numeric coordinates") from exc
        symbols.append(elements.normalise_symbol(tokens[0]))

    lattice = np.zeros((3, 3))
    pbc = (False, False, False)
    lattice_match = _LATTICE.search(comment)
    if lattice_match:
        values = lattice_match.group(1).split()
        if len(values) != 9:
            raise ValueError("extxyz Lattice= must contain nine numbers")
        lattice = np.asarray([float(value) for value in values], dtype=float).reshape(3, 3)
        pbc_match = _PBC.search(comment)
        if pbc_match:
            flags = [token.lower() in _TRUE for token in pbc_match.group(1).split()]
            flags += [False] * (3 - len(flags))
            pbc = (flags[0], flags[1], flags[2])
        else:
            pbc = (True, True, True)

    return Structure(
        lattice=lattice,
        cart_coords=np.asarray(coords, dtype=float),
        symbols=symbols,
        pbc=pbc,
        info={"format": "xyz", "comment": comment},
    )
