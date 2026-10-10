"""CIF reader: cell parameters, atom sites and symmetry expansion.

Covers the common geometry-only use of CIF files::

* ``_cell_length_*`` / ``_cell_angle_*`` cell parameters,
* an ``_atom_site`` loop with fractional coordinates, and
* symmetry operations (``_symmetry_equiv_pos_as_xyz`` /
  ``_space_group_symop_operation_xyz``) that expand the asymmetric unit into
  the full cell; files without operations are read as P1.

Occupancies are honoured only as an on/off flag (zero-occupancy sites are
dropped); partly occupied sites are kept as full atoms.
"""

from __future__ import annotations

import re

import numpy as np

from .. import elements
from ..structure import Structure

_UNCERTAINTY = re.compile(r"\((?:\d+)\)\s*$")
_SYMBOL_START = re.compile(r"^[A-Za-z]{1,2}")
_TERM = re.compile(r"([+-]?)([^+-]+)")

_CELL_KEYS = {
    "_cell_length_a": "a",
    "_cell_length_b": "b",
    "_cell_length_c": "c",
    "_cell_angle_alpha": "alpha",
    "_cell_angle_beta": "beta",
    "_cell_angle_gamma": "gamma",
}

_SYMMETRY_KEYS = (
    "_symmetry_equiv_pos_as_xyz",
    "_space_group_symop_operation_xyz",
    "_space_group_symop.operation_xyz",
)

_SITE_COLUMNS = (
    "_atom_site_type_symbol",
    "_atom_site_label",
    "_atom_site_fract_x",
    "_atom_site_fract_y",
    "_atom_site_fract_z",
    "_atom_site_occupancy",
)


# --------------------------------------------------------------------- numbers


def _parse_number(text: str) -> float:
    """Parse a CIF numeric value, dropping the standard uncertainty."""
    token = _unquote(str(text)).strip()
    if token in ("", ".", "?"):
        raise ValueError(f"CIF value is missing: {text!r}")
    token = _UNCERTAINTY.sub("", token)
    try:
        return float(token)
    except ValueError as exc:
        raise ValueError(f"cannot parse CIF number {text!r}") from exc


def _unquote(text: str) -> str:
    token = str(text).strip()
    if len(token) >= 2 and token[0] == token[-1] and token[0] in "'\"":
        return token[1:-1]
    return token


def _parse_fraction(text: str) -> float:
    """``1/2``, ``0.25``, ``2`` and ``/2`` (meaning 1/2) as a float."""
    token = text.strip()
    if token in ("", "+"):
        return 1.0
    if token.startswith("/"):
        token = "1" + token
    if "/" in token:
        numerator, _, denominator = token.partition("/")
        return float(numerator or "1") / float(denominator)
    return float(token)


def lattice_from_parameters(
    a: float, b: float, c: float, alpha: float, beta: float, gamma: float
) -> np.ndarray:
    """Cell vectors from cell parameters (a along x, b in the xy-plane)."""
    alpha_r, beta_r, gamma_r = np.radians([alpha, beta, gamma])
    cos_a, cos_b, cos_g = np.cos([alpha_r, beta_r, gamma_r])
    sin_g = np.sin(gamma_r)
    if abs(sin_g) < 1e-12:
        raise ValueError("gamma = 0 or 180 deg gives a degenerate cell")
    vector_a = np.array([a, 0.0, 0.0])
    vector_b = np.array([b * cos_g, b * sin_g, 0.0])
    cx = c * cos_b
    cy = c * (cos_a - cos_b * cos_g) / sin_g
    cz_squared = c * c - cx * cx - cy * cy
    if cz_squared < -1e-8:
        raise ValueError("inconsistent cell parameters")
    vector_c = np.array([cx, cy, np.sqrt(max(cz_squared, 0.0))])
    return np.array([vector_a, vector_b, vector_c])


# ------------------------------------------------------------------ symmetry


def _parse_component(component: str) -> tuple[np.ndarray, float]:
    """``1/2+y`` -> coefficients ``[0, 1, 0]`` and translation ``0.5``."""
    text = component.replace(" ", "").replace("*", "").lower()
    if not text:
        raise ValueError("empty symmetry component")
    coefficients = np.zeros(3)
    constant = 0.0
    for sign_text, body in _TERM.findall(text):
        if not body:
            continue
        sign = -1.0 if sign_text == "-" else 1.0
        variable = None
        for axis, letter in enumerate("xyz"):
            if letter in body:
                variable = axis
                break
        if variable is None:
            constant += sign * _parse_fraction(body)
        else:
            coefficient_text = body.replace("xyz"[variable], "")
            coefficients[variable] += sign * _parse_fraction(coefficient_text)
    return coefficients, constant


def _parse_operator(text: str) -> tuple[np.ndarray, np.ndarray]:
    """``'1/2+x, y, -z'`` -> rotation matrix and translation vector."""
    raw = _unquote(text)
    if raw in ("", ".", "?"):
        raise ValueError(f"missing symmetry operation: {text!r}")
    parts = raw.split(",")
    if len(parts) != 3:
        raise ValueError(f"symmetry operation needs three components: {text!r}")
    matrix = np.zeros((3, 3))
    translation = np.zeros(3)
    for row, part in enumerate(parts):
        matrix[row], translation[row] = _parse_component(part)
    return matrix, translation


def _expand_sites(
    fractional: np.ndarray,
    symbols: list[str],
    operators: list[tuple[np.ndarray, np.ndarray]],
) -> tuple[np.ndarray, list[str]]:
    points: list[np.ndarray] = []
    point_symbols: list[str] = []
    seen: set[tuple[int, int, int]] = set()
    for matrix, translation in operators:
        transformed = (fractional @ matrix.T + translation) % 1.0
        for position, symbol in zip(transformed, symbols):
            key = tuple(int(round(value * 10000)) % 10000 for value in position)
            if key in seen:
                continue
            seen.add(key)
            points.append(position)
            point_symbols.append(symbol)
    return np.asarray(points, dtype=float), point_symbols


# -------------------------------------------------------------------- parsing


def _split_values(text: str) -> list[str]:
    """Whitespace split that keeps quoted values together."""
    values: list[str] = []
    index, size = 0, len(text)
    while index < size:
        character = text[index]
        if character.isspace():
            index += 1
            continue
        if character in "'\"":
            quote = character
            index += 1
            start = index
            while index < size and text[index] != quote:
                index += 1
            values.append(text[start:index])
            index += 1
        else:
            start = index
            while index < size and not text[index].isspace():
                index += 1
            values.append(text[start:index])
    return values


def _site_symbol(site: dict[str, str]) -> str:
    for key in ("_atom_site_type_symbol", "_atom_site_label"):
        raw = _unquote(site.get(key, ""))
        if raw and raw not in (".", "?"):
            match = _SYMBOL_START.match(raw)
            if match:
                candidate = elements.normalise_symbol(match.group(0))
                if elements.is_known(candidate):
                    return candidate
            return elements.normalise_symbol(raw)
    raise ValueError(
        "CIF atom site has neither _atom_site_type_symbol nor _atom_site_label"
    )


def _consume_row(
    row: dict[str, str],
    cell: dict[str, float],
    operators: list[str],
    sites: list[dict[str, str]],
) -> None:
    for key, value in row.items():
        field = _CELL_KEYS.get(key)
        if field is not None:
            cell[field] = _parse_number(value)
    for key in _SYMMETRY_KEYS:
        value = row.get(key)
        if value is not None and value.strip() not in (".", "?"):
            operators.append(value)
    if "_atom_site_fract_x" in row:
        sites.append({key: row.get(key, "") for key in _SITE_COLUMNS})


def read_cif(text: str) -> Structure:
    """Parse a CIF string into a :class:`Structure`."""
    lines = [line.split("#")[0].rstrip() for line in text.splitlines()]
    cell: dict[str, float] = {}
    operators: list[str] = []
    sites: list[dict[str, str]] = []
    block_name = ""
    seen_data = False

    index, size = 0, len(lines)
    while index < size:
        line = lines[index].strip()
        if not line:
            index += 1
            continue
        lowered = line.lower()
        if lowered.startswith("data_"):
            if seen_data:
                break  # only the first data block is used
            seen_data = True
            block_name = line[5:].strip()
            index += 1
            continue
        if lowered.startswith("loop_"):
            headers: list[str] = []
            cursor = index + 1
            while cursor < size and lines[cursor].strip().startswith("_"):
                headers.append(lines[cursor].strip().split()[0].lower())
                cursor += 1
            raw_values: list[str] = []
            while cursor < size:
                row_line = lines[cursor].strip()
                if not row_line:
                    cursor += 1
                    continue
                if row_line.startswith(("_", "loop_", "data_", "save_", "stop_")):
                    break
                raw_values.extend(_split_values(row_line))
                cursor += 1
            width = len(headers)
            if width:
                for start in range(0, len(raw_values) - width + 1, width):
                    _consume_row(
                        dict(zip(headers, raw_values[start : start + width])),
                        cell,
                        operators,
                        sites,
                    )
            index = cursor
            continue
        if line.startswith("_"):
            parts = line.split(maxsplit=1)
            key = parts[0].lower()
            value = parts[1].strip() if len(parts) > 1 else ""
            field = _CELL_KEYS.get(key)
            if field is not None and value:
                cell[field] = _parse_number(value)
            elif key in _SYMMETRY_KEYS and value:
                operators.append(value)
            index += 1
            continue
        index += 1

    if not sites:
        raise ValueError("CIF contains no _atom_site loop with fractional coordinates")
    missing = [name for name in ("a", "b", "c", "alpha", "beta", "gamma") if name not in cell]
    if missing:
        raise ValueError(f"CIF is missing cell parameters: {', '.join(missing)}")
    lattice = lattice_from_parameters(
        cell["a"], cell["b"], cell["c"], cell["alpha"], cell["beta"], cell["gamma"]
    )

    occupancies = [
        1.0 if site["_atom_site_occupancy"] in ("", ".", "?") else _parse_number(site["_atom_site_occupancy"])
        for site in sites
    ]
    fractional = []
    symbols = []
    for site, occupancy in zip(sites, occupancies):
        if occupancy <= 1e-6:
            continue  # zero occupancy: the site does not exist
        fractional.append(
            [
                _parse_number(site["_atom_site_fract_x"]),
                _parse_number(site["_atom_site_fract_y"]),
                _parse_number(site["_atom_site_fract_z"]),
            ]
        )
        symbols.append(_site_symbol(site))
    if not fractional:
        raise ValueError("every CIF atom site has zero occupancy")

    parsed_ops = [_parse_operator(operator) for operator in operators]
    if not parsed_ops:
        parsed_ops = [(np.eye(3), np.zeros(3))]
    fractional_full, symbols_full = _expand_sites(
        np.asarray(fractional, dtype=float), symbols, parsed_ops
    )

    return Structure(
        lattice=lattice,
        cart_coords=fractional_full @ lattice,
        symbols=symbols_full,
        pbc=(True, True, True),
        info={
            "format": "cif",
            "comment": block_name,
            "symmetry_operations": len(parsed_ops),
        },
    )
