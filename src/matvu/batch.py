"""Batch rendering: every structure of a project tree, in place.

A DeepH-style layout works out of the box::

    matvu batch dft/                   # renders every dft/**/POSCAR
    matvu batch dft/ -o figures/       # mirror the tree under figures/
    matvu batch dft/ --format pdf,png  # vector + raster per structure

The figure of each structure is written next to its input file
(``POSCAR_view.png``) unless ``output_dir`` is given, in which case the
relative directory layout is mirrored below ``output_dir``.
"""

from __future__ import annotations

import glob
import os
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable, Sequence

from .backends import get_backend
from .backends.tracer import save_image, trace_image
from .io import load_structure
from .render import resolve_view
from .scene import build_scene
from .style import Style

DEFAULT_PATTERNS = ("POSCAR",)
_RASTER = {
    ".png": "png",
    ".tif": "tif",
    ".tiff": "tiff",
    ".webp": "webp",
    ".jpg": "jpg",
    ".jpeg": "jpeg",
    ".bmp": "bmp",
}


@dataclass
class BatchResult:
    """Outcome of rendering one input file."""

    source: Path
    outputs: list[Path] = field(default_factory=list)
    formula: str = ""
    azimuth: float = 0.0
    elevation: float = 0.0
    error: str | None = None
    skipped: bool = False

    @property
    def ok(self) -> bool:
        return self.error is None


def find_structures(
    sources: Iterable[str | Path],
    patterns: Sequence[str] = DEFAULT_PATTERNS,
) -> list[Path]:
    """Expand files, directories and glob patterns into structure files.

    Directories are searched recursively for files matching ``patterns``
    (default: files literally named ``POSCAR``). ``CONTCAR`` or ``*.vasp``
    can be added through ``patterns``; shell-style patterns like
    ``dft/**/POSCAR`` are accepted directly as sources.
    """
    pattern_list = [str(pattern) for pattern in patterns] or list(DEFAULT_PATTERNS)
    found: set[Path] = set()
    for source in sources:
        text = str(source)
        path = Path(text).expanduser()
        if path.is_file():
            found.add(path)
            continue
        if path.is_dir():
            for pattern in pattern_list:
                found.update(
                    candidate for candidate in path.rglob(pattern) if candidate.is_file()
                )
            continue
        if any(character in text for character in "*?["):
            for hit in glob.glob(text, recursive=True):
                candidate = Path(hit)
                if candidate.is_file():
                    found.add(candidate)
            continue
        raise FileNotFoundError(f"no such file or directory: {text}")
    return sorted(found)


def _relative_base(source: Path, sources: Sequence[str | Path]) -> Path | None:
    """Deepest source directory containing ``source`` (for tree mirroring)."""
    best: Path | None = None
    for candidate in sources:
        path = Path(str(candidate)).expanduser()
        if not path.is_dir():
            continue
        try:
            source.relative_to(path)
        except ValueError:
            continue
        if best is None or len(path.parts) > len(best.parts):
            best = path
    return best


def _output_paths(
    source: Path,
    output_dir: Path | None,
    base: Path | None,
    suffixes: Sequence[str],
) -> list[Path]:
    if output_dir is None:
        parent = source.parent
    else:
        parent = output_dir
        if base is not None:
            try:
                parent = output_dir / source.relative_to(base).parent
            except ValueError:
                parent = output_dir
    return [parent / f"{source.stem}_view.{suffix}" for suffix in suffixes]


def _normalise_formats(formats: Iterable[str]) -> list[str]:
    cleaned = []
    for item in formats:
        for part in str(item).split(","):
            suffix = part.strip().lower().lstrip(".")
            if suffix and suffix not in cleaned:
                cleaned.append(suffix)
    if not cleaned:
        raise ValueError("at least one output format is required")
    return cleaned


def _render_one(task) -> BatchResult:
    source, outputs, style, view_spec, seed, supercell, backend = task
    try:
        structure = load_structure(source)
        if supercell is not None:
            structure = structure.supercell(supercell)
        scene = build_scene(structure, style)
        view = resolve_view(scene, view_spec, seed=seed)
        written: list[Path] = []
        for output in outputs:
            output.parent.mkdir(parents=True, exist_ok=True)
        if backend == "tracer":
            image = trace_image(scene, view, style)
            for output in outputs:
                written.append(Path(save_image(image, output, style)))
        else:
            renderer = get_backend(backend)
            for output in outputs:
                written.append(Path(renderer.render(scene, view, style, output=output)))
        azimuth, elevation = view.angles_deg()
        return BatchResult(
            source=source,
            outputs=written,
            formula=structure.formula,
            azimuth=float(azimuth),
            elevation=float(elevation),
        )
    except Exception as exc:  # noqa: BLE001 - collected into the batch summary
        return BatchResult(source=source, error=f"{type(exc).__name__}: {exc}")


def render_batch(
    sources: Iterable[str | Path],
    output_dir: str | Path | None = None,
    *,
    patterns: Sequence[str] = DEFAULT_PATTERNS,
    formats: Sequence[str] = ("png",),
    style: Style | None = None,
    view="auto",
    seed: int = 0,
    supercell: Sequence[int] | None = None,
    backend: str = "tracer",
    jobs: int = 1,
    skip_existing: bool = False,
    progress: Callable[[BatchResult, int, int], None] | None = None,
) -> list[BatchResult]:
    """Render every structure found in ``sources``.

    ``jobs=1`` renders sequentially; ``jobs > 1`` uses that many worker
    processes; ``jobs=0`` uses all CPU cores.
    """
    source_list = list(sources)
    files = find_structures(source_list, patterns)
    suffixes = _normalise_formats(formats)
    style = style or Style()
    out_dir = Path(output_dir).expanduser() if output_dir is not None else None

    tasks = []
    results: list[BatchResult] = []
    total = len(files)
    for source in files:
        if out_dir is None:
            outputs = _output_paths(source, None, None, suffixes)
        else:
            base = _relative_base(source, source_list)
            outputs = _output_paths(source, out_dir, base, suffixes)
        if skip_existing and outputs and all(output.exists() for output in outputs):
            results.append(BatchResult(source=source, outputs=list(outputs), skipped=True))
            if progress is not None:
                progress(results[-1], len(results), total)
            continue
        tasks.append(
            (source, outputs, style, view, seed, supercell, backend)
        )

    workers = int(jobs)
    if workers == 0:
        workers = os.cpu_count() or 1
    if workers < 1:
        raise ValueError("jobs must be >= 1, or 0 to use all cores")
    if workers <= 1 or len(tasks) <= 1:
        for index, task in enumerate(tasks):
            result = _render_one(task)
            results.append(result)
            if progress is not None:
                progress(result, len(results), total)
    else:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            futures = [pool.submit(_render_one, task) for task in tasks]
            for future in as_completed(futures):
                result = future.result()
                results.append(result)
                if progress is not None:
                    progress(result, len(results), total)

    order = {source: index for index, source in enumerate(files)}
    results.sort(key=lambda item: order.get(item.source, len(order)))
    return results
