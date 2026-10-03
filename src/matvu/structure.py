"""Core structure container shared by every reader and backend."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

import numpy as np


@dataclass
class Structure:
    """A chemical structure in Cartesian coordinates.

    Parameters
    ----------
    lattice:
        ``(3, 3)`` array whose rows are the lattice vectors ``a``, ``b``, ``c``
        in Angstrom. Use zeros for non-periodic (molecular) structures.
    cart_coords:
        ``(N, 3)`` Cartesian positions in Angstrom.
    symbols:
        Element symbols, one per position.
    pbc:
        Periodicity flags per lattice vector.
    info:
        Free-form metadata (comment line, source format, ...).
    """

    lattice: np.ndarray
    cart_coords: np.ndarray
    symbols: list[str]
    pbc: tuple[bool, bool, bool] = (True, True, True)
    info: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        lattice = np.asarray(self.lattice, dtype=float)
        if lattice.shape != (3, 3):
            raise ValueError(f"lattice must have shape (3, 3), got {lattice.shape}")
        coords = np.asarray(self.cart_coords, dtype=float)
        if coords.ndim != 2 or coords.shape[1] != 3:
            raise ValueError(f"cart_coords must have shape (N, 3), got {coords.shape}")
        symbols = [str(s).strip() for s in self.symbols]
        if len(symbols) != coords.shape[0]:
            raise ValueError(
                f"got {len(symbols)} symbols for {coords.shape[0]} positions"
            )
        self.lattice = lattice
        self.cart_coords = coords
        self.symbols = symbols
        self.pbc = tuple(bool(p) for p in self.pbc)  # type: ignore[assignment]

    # ------------------------------------------------------------------ basics

    @property
    def n_atoms(self) -> int:
        """Number of atoms."""
        return int(self.cart_coords.shape[0])

    @property
    def volume(self) -> float:
        """Cell volume in cubic Angstrom (0 for non-periodic structures)."""
        return float(abs(np.linalg.det(self.lattice)))

    @property
    def frac_coords(self) -> np.ndarray:
        """Fractional coordinates; requires a non-singular lattice."""
        if self.volume < 1e-12:
            raise ValueError("fractional coordinates need a non-singular lattice")
        return self.cart_coords @ np.linalg.inv(self.lattice)

    @property
    def center(self) -> np.ndarray:
        """Mean Cartesian position (geometric centre)."""
        return self.cart_coords.mean(axis=0)

    @property
    def formula(self) -> str:
        """Compact formula string, e.g. ``Si8``, ``H2O``, ``Cl4Na4``."""
        counts = Counter(self.symbols)
        keys = sorted(counts)
        if "C" in counts:
            order = ["C"]
            if "H" in counts:
                order.append("H")
            order += [k for k in keys if k not in ("C", "H")]
        else:
            order = keys
        return "".join(s + (str(counts[s]) if counts[s] > 1 else "") for s in order)

    # ------------------------------------------------------------- operations

    def supercell(self, rep) -> "Structure":
        """Return an integer repeat of the cell, e.g. ``rep=(2, 1, 1)``."""
        if self.volume < 1e-12:
            raise ValueError("cannot build a supercell without a periodic lattice")
        nx, ny, nz = (int(r) for r in rep)
        if nx < 1 or ny < 1 or nz < 1:
            raise ValueError("supercell repetitions must be positive integers")
        shifts = [
            i * self.lattice[0] + j * self.lattice[1] + k * self.lattice[2]
            for i in range(nx)
            for j in range(ny)
            for k in range(nz)
        ]
        shifts = np.asarray(shifts)
        new_coords = (self.cart_coords[None, :, :] + shifts[:, None, :]).reshape(-1, 3)
        new_symbols = list(self.symbols) * (nx * ny * nz)
        new_lattice = np.array(
            [
                self.lattice[0] * nx,
                self.lattice[1] * ny,
                self.lattice[2] * nz,
            ]
        )
        info = dict(self.info)
        info["supercell"] = (nx, ny, nz)
        return Structure(new_lattice, new_coords, new_symbols, self.pbc, info)
