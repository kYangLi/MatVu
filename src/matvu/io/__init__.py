"""Reader registry and format dispatch.

New formats plug in without touching the core::

    from matvu import Structure, register_reader

    def read_cif(text: str) -> Structure:
        ...

    register_reader("cif", read_cif)
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from ..structure import Structure

_READERS: dict[str, Callable[[str], Structure]] = {}


def register_reader(
    name: str,
    reader: Callable[[str], Structure],
    *,
    overwrite: bool = False,
) -> None:
    """Register a text-to-:class:`Structure` reader under ``name``."""
    key = str(name).lower().lstrip(".")
    if not overwrite and key in _READERS:
        raise ValueError(f"a reader for {key!r} is already registered")
    _READERS[key] = reader


def available_formats() -> list[str]:
    """Names of all registered readers."""
    return sorted(_READERS)


def load_structure(source, *, format: str | None = None) -> Structure:
    """Load a structure from a path, raw text, file object or existing object.

    ``format`` forces a registered reader; otherwise the format is guessed
    from the file name (``POSCAR``, ``CONTCAR``, ``*.vasp``, ...).
    """
    if isinstance(source, Structure):
        return source
    if hasattr(source, "read"):
        text = source.read()
        name = str(getattr(source, "name", "") or "")
        return _parse_text(text, name, format)
    if isinstance(source, (str, Path)):
        text_or_path = str(source)
        if "\n" not in text_or_path:
            path = Path(text_or_path).expanduser()
            if path.is_file():
                content = path.read_text(encoding="utf-8", errors="replace")
                return _parse_text(content, path.name, format)
        return _parse_text(text_or_path, "", format)  # raw text
    raise TypeError(f"cannot load a structure from {type(source).__name__}")


def _parse_text(text: str, filename: str, format: str | None) -> Structure:
    if format is not None:
        key = str(format).lower().lstrip(".")
        reader = _READERS.get(key)
        if reader is None:
            raise ValueError(
                f"unknown format {format!r}; available: {available_formats()}"
            )
        return reader(text)
    key = _sniff_format(filename)
    if key is None and len(_READERS) == 1:
        key = next(iter(_READERS))
    if key is None:
        raise ValueError(
            f"cannot infer the format of {filename!r}; "
            f"pass format=... (available: {available_formats()})"
        )
    return _READERS[key](text)


def _sniff_format(filename: str) -> str | None:
    name = Path(filename).name.lower()
    suffix = Path(filename).suffix.lower()
    if name in ("poscar", "contcar") or suffix in (".poscar", ".vasp"):
        return "vasp"
    return None


# Built-in readers register themselves on import.
from . import vasp as _vasp  # noqa: E402

register_reader("vasp", _vasp.read_poscar)
