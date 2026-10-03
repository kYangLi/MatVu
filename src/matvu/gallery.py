"""Candidate viewpoint contact sheet.

Evaluates all auto-view candidates, ranks them by score and composes the top
``n`` into a single annotated grid image. This is the main tool for inspecting
and calibrating the viewpoint scoring model.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from io import BytesIO
from math import ceil
from pathlib import Path

import numpy as np

from .backends import get_backend
from .io import load_structure
from .scene import Scene, build_scene
from .style import Style
from .viewpoint import candidate_views, pick_view, score, special_directions


@dataclass(frozen=True)
class CandidateScore:
    """One evaluated viewpoint with its score breakdown."""

    view: object  # matvu.viewpoint.View
    score: float
    occlusion: float
    bond_penalty: float
    aspect_penalty: float


@dataclass
class Ranking:
    """Ranked candidates plus how many directions were evaluated."""

    candidates: list[CandidateScore]
    n_evaluated: int
    auto: CandidateScore | None = None


def _candidate(scene: Scene, view) -> CandidateScore:
    metrics = score(scene, view)
    return CandidateScore(
        view=view,
        score=metrics["score"],
        occlusion=metrics["occlusion"],
        bond_penalty=metrics["bond_penalty"],
        aspect_penalty=metrics["aspect_penalty"],
    )


def rank_candidates(
    scene: Scene, *, n: int = 12, n_surface: int = 240, seed: int = 0
) -> Ranking:
    """Score every candidate view and return the best ``n``, best first.

    ``Ranking.auto`` is the view that ``render(..., view="auto")`` would
    choose (with tie-break and local refinement), so the contact sheet can
    highlight the actual automatic choice.
    """
    views = candidate_views(scene, n_surface=n_surface)
    scored = [_candidate(scene, view) for view in views]
    scored.sort(key=lambda candidate: candidate.score, reverse=True)
    specials = special_directions(scene)

    def alignment(candidate: CandidateScore) -> float:
        if not specials:
            return 0.0
        return max(
            abs(float(candidate.view.direction @ direction))
            for direction in specials
        )

    scored.sort(key=lambda candidate: (-candidate.score, -alignment(candidate)))
    auto = _candidate(scene, pick_view(scene, n_surface=n_surface, seed=seed))
    return Ranking(candidates=scored[:n], n_evaluated=len(scored), auto=auto)


def _render_tile(scene: Scene, view, style: Style) -> np.ndarray:
    """Render one viewpoint to an RGBA tile image."""
    import matplotlib.pyplot as plt

    backend = get_backend("matplotlib")
    figure = backend.render(scene, view, style)
    buffer = BytesIO()
    figure.savefig(
        buffer,
        format="png",
        dpi=style.dpi,
        facecolor=style.background,
        transparent=style.transparent,
    )
    plt.close(figure)
    buffer.seek(0)
    return plt.imread(buffer, format="png")


def render_candidate_sheet(
    scene: Scene,
    ranking: Ranking,
    output,
    *,
    cols: int | None = None,
    tile_width: float = 2.0,
    tile_dpi: int = 150,
    dpi: int = 200,
    style: Style | None = None,
) -> Path:
    """Compose ranked viewpoints into an annotated grid image."""
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle

    style = style or Style()
    ranked = ranking.candidates
    if not ranked:
        raise ValueError("nothing to draw: the ranking is empty")

    # Show the ranked views; make sure the actual automatic choice is always
    # present, appending it as an extra cell when it fell outside the top n.
    display = list(ranked)
    auto_index = None
    if ranking.auto is not None:
        dots = [
            float(item.view.direction @ ranking.auto.view.direction)
            for item in display
        ]
        best_dot = max(dots) if dots else -1.0
        if best_dot > 0.99999:
            auto_index = dots.index(best_dot)
        else:
            display.append(ranking.auto)
            auto_index = len(display) - 1

    n = len(display)
    n_cols = max(1, cols or min(4, n))
    n_rows = ceil(n / n_cols)

    tile_style = replace(style, width_in=tile_width, dpi=tile_dpi)
    images = [_render_tile(scene, item.view, tile_style) for item in display]

    figure_width = n_cols * tile_width
    figure_height = n_rows * tile_width
    figure = plt.figure(figsize=(figure_width, figure_height), dpi=dpi)
    figure.patch.set_facecolor(style.background)

    header_frac = min(0.12, 0.40 / figure_height)
    usable_height = 1.0 - header_frac
    pad = 0.006
    label_frac = 0.16

    for index, (candidate, image) in enumerate(zip(display, images)):
        row, col = divmod(index, n_cols)
        x0 = col / n_cols
        cell_width = 1.0 / n_cols
        cell_height = usable_height / n_rows
        y0 = (1.0 - (row + 1) / n_rows) * usable_height
        label_height = cell_height * label_frac
        axes = figure.add_axes(
            (
                x0 + pad,
                y0 + label_height + pad,
                cell_width - 2 * pad,
                cell_height - label_height - 2 * pad,
            )
        )
        axes.imshow(image, interpolation="bilinear")
        axes.set_axis_off()

        azimuth, elevation = candidate.view.angles_deg()
        is_auto = index == auto_index
        label = (
            f"{'★ ' if is_auto else ''}#{index + 1} · {azimuth:.0f}°/{elevation:.0f}°"
            f" · s={candidate.score:.3f}"
        )
        figure.text(
            x0 + cell_width / 2,
            y0 + label_height / 2,
            label,
            ha="center",
            va="center",
            fontsize=8.5,
            color="#d62728" if is_auto else "#333333",
        )
        if is_auto:
            figure.add_artist(
                Rectangle(
                    (x0 + pad / 2, y0 + pad / 2),
                    cell_width - pad,
                    cell_height - pad,
                    transform=figure.transFigure,
                    fill=False,
                    edgecolor="#d62728",
                    linewidth=1.8,
                )
            )

    header = (
        f"MatVu candidate views — {scene.formula} · top {len(ranked)} of "
        f"{ranking.n_evaluated} · ★ = auto choice"
    )
    figure.text(
        0.5, 1.0 - header_frac / 2, header, ha="center", va="center", fontsize=11
    )

    output = Path(output)
    figure.savefig(output, dpi=dpi, facecolor=style.background)
    plt.close(figure)
    return output


def render_candidates(
    source,
    output=None,
    *,
    n: int = 12,
    n_surface: int = 240,
    seed: int = 0,
    style: Style | None = None,
    supercell=None,
    cols: int | None = None,
    tile_width: float = 2.0,
    dpi: int = 200,
) -> Path:
    """Load a structure and write a candidate-view contact sheet."""
    structure = load_structure(source)
    if supercell is not None:
        structure = structure.supercell(supercell)
    style = style or Style()
    scene = build_scene(structure, style)
    ranking = rank_candidates(scene, n=n, n_surface=n_surface, seed=seed)
    if output is None:
        output = _default_sheet_name(source)
    return render_candidate_sheet(
        scene,
        ranking,
        output,
        cols=cols,
        tile_width=tile_width,
        dpi=dpi,
        style=style,
    )


def _default_sheet_name(source) -> Path:
    if isinstance(source, (str, Path)):
        text = str(source)
        if "\n" not in text:
            stem = Path(text).stem
            if stem:
                return Path(f"{stem}_candidates.png")
    return Path("candidates.png")
