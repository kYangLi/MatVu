"""Minimal but robust VASP ``POSCAR`` / ``CONTCAR`` reader."""

from __future__ import annotations

import re

import numpy as np

from ..structure import Structure

_SYMBOL_PATTERN = re.compile(r"[A-Z][a-z]?")


def _is_float(token: str) -> bool:
    try:
        float(token)
        return True
    except ValueError:
        return False


def read_poscar(text: str) -> Structure:
    """Parse a POSCAR/CONTCAR string into a :class:`Structure`.

    Supports VASP 4 (no species line, symbols taken from the comment) and
    VASP 5+ layouts, ``Direct``/``Cartesian`` coordinates, negative scale
    factors (target volume) and ``Selective dynamics``.
    """
    lines = [line.rstrip() for line in text.splitlines() if line.strip()]
    if len(lines) < 8:
        raise ValueError("not a valid POSCAR: too few lines")

    comment = lines[0].strip()
    scale = float(lines[1].split()[0])
    lattice = np.array(
        [[float(v) for v in lines[i].split()[:3]] for i in range(2, 5)],
        dtype=float,
    )
    if scale < 0.0:
        volume = abs(np.linalg.det(lattice))
        if volume < 1e-12:
            raise ValueError("negative POSCAR scale needs a non-singular lattice")
        scale = (abs(scale) / volume) ** (1.0 / 3.0)
    lattice = lattice * scale

    index = 5
    tokens = lines[index].split()
    if tokens and all(_is_float(t) for t in tokens):
        # VASP 4: counts only; species come from the comment line.
        counts = [int(float(t)) for t in tokens]
        species = _SYMBOL_PATTERN.findall(comment)
        if len(species) != len(counts):
            species = [f"X{i + 1}" for i in range(len(counts))]
        index += 1
    else:
        species = tokens
        index += 1
        counts = [int(float(t)) for t in lines[index].split()]
        index += 1

    if len(species) != len(counts):
        raise ValueError("POSCAR species/count mismatch")
    if any(c < 0 for c in counts):
        raise ValueError("POSCAR atom counts must be non-negative")
    n_atoms = sum(counts)

    if lines[index].strip().lower().startswith("s"):
        index += 1  # Selective dynamics
    mode = lines[index].strip().lower()
    if mode.startswith("d"):
        direct = True
    elif mode.startswith(("c", "k")):
        direct = False
    else:
        raise ValueError(f"expected Direct/Cartesian in POSCAR, got {lines[index]!r}")
    index += 1

    if len(lines) - index < n_atoms:
        raise ValueError(
            f"POSCAR declares {n_atoms} atoms but has only {len(lines) - index} "
            "position lines"
        )
    coords = np.array(
        [
            [float(v) for v in lines[index + i].split()[:3]]
            for i in range(n_atoms)
        ],
        dtype=float,
    )
    cart = coords @ lattice if direct else coords * scale

    symbols = [s for s, count in zip(species, counts) for _ in range(count)]
    return Structure(
        lattice=lattice,
        cart_coords=cart,
        symbols=symbols,
        pbc=(True, True, True),
        info={"comment": comment, "format": "vasp"},
    )
