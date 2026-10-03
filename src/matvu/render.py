"""High-level API: ``render``, ``auto_view`` and view resolution."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from .backends import get_backend
from .io import load_structure
from .scene import Scene, build_scene
from .style import Style
from .viewpoint import View, pick_view


def render(
    source,
    output=None,
    *,
    view="auto",
    backend: str = "tracer",
    style: Style | None = None,
    supercell=None,
    seed: int = 0,
    **backend_kwargs,
):
    """Load a structure and render it.

    Parameters
    ----------
    source:
        Path, raw text or :class:`~matvu.structure.Structure`.
    view:
        ``"auto"`` (default), ``"a"``/``"b"``/``"c"``, ``"[h,k,l]"``, an
        explicit ``(x, y, z)`` direction or a :class:`~matvu.viewpoint.View`.
    backend:
        Registered backend name. ``"tracer"`` (default) casts rays analytically
        for exact sphere/stick occlusion; ``"matplotlib"`` is a fast preview.
    supercell:
        Optional ``(nx, ny, nz)`` repetition applied before rendering.
    """
    structure = load_structure(source)
    if supercell is not None:
        structure = structure.supercell(supercell)
    style = style or Style()
    scene = build_scene(structure, style)
    resolved = resolve_view(scene, view, seed=seed)
    backend_instance = get_backend(backend)
    if output is None:
        output = _default_output(source)
    return backend_instance.render(
        scene, resolved, style, output=output, **backend_kwargs
    )


def auto_view(
    source,
    *,
    style: Style | None = None,
    supercell=None,
    seed: int = 0,
    **kwargs,
) -> View:
    """Load a structure and return its automatically chosen viewpoint."""
    structure = load_structure(source)
    if supercell is not None:
        structure = structure.supercell(supercell)
    scene = build_scene(structure, style or Style())
    return pick_view(scene, seed=seed, **kwargs)


def resolve_view(scene: Scene, view, *, seed: int = 0) -> View:
    """Turn the many accepted ``view`` forms into a :class:`View`."""
    if view is None:
        return pick_view(scene, seed=seed)
    if isinstance(view, View):
        return view
    if isinstance(view, str):
        text = view.strip().lower()
        if text in ("", "auto"):
            return pick_view(scene, seed=seed)
        if text in ("a", "b", "c"):
            axis = ord(text) - ord("a")
            if scene.lattice is None or np.linalg.norm(scene.lattice[axis]) < 1e-9:
                raise ValueError(f"view {view!r} needs a periodic lattice")
            return View(scene.lattice[axis])
        if text.startswith("[") and text.endswith("]"):
            values = [float(v) for v in text[1:-1].replace(",", " ").split()]
            if len(values) != 3:
                raise ValueError(f"expected three indices in {view!r}")
            if scene.lattice is None or abs(np.linalg.det(scene.lattice)) < 1e-12:
                raise ValueError(f"view {view!r} needs a periodic lattice")
            return View(np.asarray(values) @ scene.lattice)
        parts = text.replace(",", " ").split()
        if len(parts) == 3:
            try:
                return View([float(v) for v in parts])
            except ValueError:
                pass
        raise ValueError(f"cannot interpret view {view!r}")
    direction = np.asarray(view, dtype=float).reshape(-1)
    if direction.size != 3:
        raise ValueError(f"expected a 3-vector view direction, got {view!r}")
    return View(direction)


def _default_output(source) -> Path:
    if isinstance(source, (str, Path)):
        text = str(source)
        if "\n" not in text:
            stem = Path(text).stem
            if stem:
                return Path(f"{stem}_view.png")
    return Path("preview.png")
