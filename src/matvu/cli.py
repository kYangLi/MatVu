"""Command line interface: render, info, candidates, batch, animate, theme."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from .animate import render_orbit
from .backends import available_backends
from .batch import render_batch
from .gallery import rank_candidates, render_candidate_sheet
from .geometry import cell_params
from .io import load_structure
from .palettes import palette_names
from .render import render, resolve_view
from .scene import build_scene
from .style import Style, style_preset
from .theme import export_theme, load_theme


def _add_style_options(parser: argparse.ArgumentParser) -> None:
    """Every option that modifies the :class:`Style` of a figure."""
    parser.add_argument(
        "--style",
        default="3d",
        choices=["3d", "toon", "flat"],
        help="look preset: 3d (shaded), toon (animation/cel style) or flat",
    )
    parser.add_argument(
        "--theme",
        default=None,
        help="built-in theme name or path to a .toml theme file",
    )
    parser.add_argument(
        "--palette",
        default=None,
        choices=palette_names(),
        help="quick palette switch (overrides the theme palette)",
    )
    parser.add_argument(
        "--canvas",
        nargs=2,
        type=float,
        metavar=("W", "H"),
        default=None,
        help="fixed view-plane size in Angstrom (uniform scale across figures)",
    )
    parser.add_argument("--atom-scale", type=float, default=None)
    parser.add_argument("--bond-radius", type=float, default=None)
    parser.add_argument("--width", type=float, default=None, help="figure width in inches")
    parser.add_argument("--dpi", type=int, default=None)
    parser.add_argument(
        "--opaque",
        action="store_true",
        help="opaque background (default: transparent)",
    )
    parser.add_argument("--no-bonds", action="store_true")
    parser.add_argument(
        "--metal-bonds",
        action="store_true",
        help="draw metal-metal bonds (default: off)",
    )
    parser.add_argument(
        "--cell",
        default=None,
        choices=("auto", "always", "never"),
        help="unit-cell frame: auto (skip molecular boxes and 2D slabs), always, never",
    )
    parser.add_argument(
        "--force-cell",
        dest="cell",
        action="store_const",
        const="always",
        help="alias for --cell always (frame only, the viewpoint is unchanged)",
    )
    parser.add_argument(
        "--no-cell",
        dest="cell",
        action="store_const",
        const="never",
        help="alias for --cell never",
    )
    parser.add_argument(
        "--boundary-padding",
        type=float,
        default=None,
        help="fractional margin of mirrored periodic boundary atoms (default 0.10, 0 disables)",
    )
    parser.add_argument(
        "--perspective",
        type=float,
        default=None,
        help="perspective strength (0 = orthographic, default 0.25)",
    )
    parser.add_argument(
        "--supersample",
        type=int,
        default=None,
        help="anti-aliasing factor for the tracer backend (default 2)",
    )


def _style_from_args(args) -> Style:
    style = style_preset(args.style)
    if args.theme is not None:
        style = load_theme(args.theme, base=style).style
    if args.palette is not None:
        style.palette = args.palette
    if args.canvas is not None:
        style.canvas = (float(args.canvas[0]), float(args.canvas[1]))
    if args.atom_scale is not None:
        style.atom_scale = args.atom_scale
    if args.bond_radius is not None:
        style.bond_radius = args.bond_radius
    if args.width is not None:
        style.width_in = args.width
    if args.dpi is not None:
        style.dpi = args.dpi
    if args.opaque:
        style.transparent = False
    if args.no_bonds:
        style.draw_bonds = False
    if args.metal_bonds:
        style.metal_metal_bonds = True
    if args.cell is not None:
        style.cell = args.cell
    if args.perspective is not None:
        style.perspective = args.perspective
    if args.boundary_padding is not None:
        style.boundary_padding = args.boundary_padding
    if args.supersample is not None:
        style.supersample = args.supersample
    return style


def _ensure_headless() -> None:
    if not os.environ.get("DISPLAY"):
        import matplotlib

        matplotlib.use("Agg")


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(Path.cwd()))
    except ValueError:
        return str(path)


def _split_option(text: str) -> list[str]:
    return [item.strip() for item in str(text).split(",") if item.strip()]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="matvu",
        description=(
            "Automatic viewpoint optimization and visualization "
            "for materials structures."
        ),
    )
    from . import __version__

    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subcommands = parser.add_subparsers(dest="command", required=True)

    render_parser = subcommands.add_parser("render", help="render a structure to an image")
    render_parser.add_argument("structure", help="path to a structure file (POSCAR first)")
    render_parser.add_argument("-o", "--output", default=None, help="output file (PNG/PDF/SVG)")
    render_parser.add_argument(
        "--view",
        default="auto",
        help="auto | a | b | c | [h,k,l] | explicit 'x y z' direction",
    )
    render_parser.add_argument(
        "--backend",
        default="tracer",
        choices=available_backends(),
        help="tracer (default, exact occlusion) | matplotlib (fast preview)",
    )
    render_parser.add_argument(
        "--supercell",
        nargs=3,
        type=int,
        default=None,
        metavar=("NX", "NY", "NZ"),
        help="repeat the cell before rendering",
    )
    _add_style_options(render_parser)
    render_parser.add_argument("--print-view", action="store_true", help="print the resolved view")
    render_parser.add_argument("--seed", type=int, default=0, help="auto view search seed")

    info_parser = subcommands.add_parser("info", help="print basic structure information")
    info_parser.add_argument("structure")

    candidates_parser = subcommands.add_parser(
        "candidates",
        help="render a contact sheet of the best candidate viewpoints",
    )
    candidates_parser.add_argument("structure")
    candidates_parser.add_argument("-o", "--output", default=None)
    candidates_parser.add_argument(
        "-n", type=int, default=12, help="number of viewpoints in the sheet"
    )
    candidates_parser.add_argument(
        "--n-surface",
        type=int,
        default=240,
        help="size of the Fibonacci sampling (more = finer search)",
    )
    candidates_parser.add_argument("--cols", type=int, default=None)
    candidates_parser.add_argument("--tile-width", type=float, default=2.0)
    candidates_parser.add_argument("--dpi", type=int, default=200)
    candidates_parser.add_argument("--seed", type=int, default=0, help="auto view search seed")
    candidates_parser.add_argument(
        "--supercell",
        nargs=3,
        type=int,
        default=None,
        metavar=("NX", "NY", "NZ"),
    )

    theme_parser = subcommands.add_parser(
        "theme", help="list or export built-in themes"
    )
    theme_sub = theme_parser.add_subparsers(dest="theme_command", required=True)
    theme_sub.add_parser("list", help="list built-in themes")
    export_parser = theme_sub.add_parser(
        "export", help="write a built-in theme as a TOML file you can edit"
    )
    export_parser.add_argument("name", choices=palette_names())
    export_parser.add_argument("-o", "--output", default=None)

    batch_parser = subcommands.add_parser(
        "batch",
        help="render every structure of a project tree (e.g. dft/**/POSCAR)",
    )
    batch_parser.add_argument(
        "sources",
        nargs="+",
        help="directories, files or glob patterns (e.g. dft/ or 'dft/**/POSCAR')",
    )
    batch_parser.add_argument(
        "-o",
        "--output",
        default=None,
        metavar="DIR",
        help="write the figures under DIR (mirroring the tree) instead of next to each structure",
    )
    batch_parser.add_argument(
        "--pattern",
        default="POSCAR",
        help="file name/glob searched recursively inside directories (default: POSCAR; comma-separated for several)",
    )
    batch_parser.add_argument(
        "--format",
        default="png",
        metavar="EXT",
        help="output format(s): png, pdf, svg, ... (comma-separated; default: png)",
    )
    batch_parser.add_argument(
        "-j",
        "--jobs",
        type=int,
        default=1,
        help="worker processes (0 = all cores; default 1)",
    )
    batch_parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="keep existing outputs and only render missing ones",
    )
    batch_parser.add_argument(
        "--view",
        default="auto",
        help="auto | a | b | c | [h,k,l] | explicit 'x y z' direction",
    )
    batch_parser.add_argument("--seed", type=int, default=0, help="auto view search seed")
    batch_parser.add_argument(
        "--backend",
        default="tracer",
        choices=available_backends(),
        help="tracer (default, exact occlusion) | matplotlib (fast preview)",
    )
    _add_style_options(batch_parser)

    animate_parser = subcommands.add_parser(
        "animate",
        help="render a 360-degree orbit animation (GIF/WebP) from the automatic view",
    )
    animate_parser.add_argument("structure")
    animate_parser.add_argument(
        "-o",
        "--output",
        default=None,
        help="output .gif or .webp (default: <name>_spin.gif)",
    )
    animate_parser.add_argument(
        "--view",
        default="auto",
        help="auto | a | b | c | [h,k,l] | explicit 'x y z' direction",
    )
    animate_parser.add_argument(
        "--orbit", type=float, default=360.0, help="orbit angle in degrees (default 360)"
    )
    animate_parser.add_argument(
        "--frames", type=int, default=60, help="number of frames (default 60)"
    )
    animate_parser.add_argument(
        "--fps", type=float, default=12.0, help="animation speed (default 12)"
    )
    animate_parser.add_argument(
        "--axis",
        default="auto",
        choices=("auto", "x", "y", "z"),
        help="Cartesian axis to orbit around; auto (default) picks the axis most perpendicular to the view",
    )
    animate_parser.add_argument(
        "--frames-dir",
        default=None,
        metavar="DIR",
        help="also/only write transparent PNG frames to DIR",
    )
    animate_parser.add_argument(
        "--background",
        default=None,
        help="GIF background colour (default: white while the style is transparent)",
    )
    animate_parser.add_argument(
        "--supercell",
        nargs=3,
        type=int,
        default=None,
        metavar=("NX", "NY", "NZ"),
    )
    animate_parser.add_argument("--seed", type=int, default=0, help="auto view search seed")
    _add_style_options(animate_parser)

    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "render":
        return _cmd_render(args)
    if args.command == "info":
        return _cmd_info(args)
    if args.command == "candidates":
        return _cmd_candidates(args)
    if args.command == "batch":
        return _cmd_batch(args)
    if args.command == "animate":
        return _cmd_animate(args)
    if args.command == "theme":
        return _cmd_theme(args)
    parser.print_help()
    return 1


def _cmd_render(args) -> int:
    _ensure_headless()
    style = _style_from_args(args)

    structure = load_structure(args.structure)
    if args.supercell is not None:
        structure = structure.supercell(tuple(args.supercell))
    scene = build_scene(structure, style)
    view = resolve_view(scene, args.view, seed=args.seed)

    output = Path(args.output) if args.output else Path(f"{_stem(args.structure)}_view.png")
    result = render(structure, output=output, view=view, backend=args.backend, style=style)

    print(
        f"[matvu] {structure.formula} | {structure.n_atoms} atoms "
        f"| {scene.n_bonds} bonds"
    )
    if args.print_view:
        azimuth, elevation = view.angles_deg()
        d = view.direction
        print(
            f"[matvu] view: azimuth {azimuth:.1f} deg, elevation {elevation:.1f} deg "
            f"| direction [{d[0]:+.3f} {d[1]:+.3f} {d[2]:+.3f}]"
        )
    print(f"[matvu] wrote {result}")
    return 0


def _cmd_candidates(args) -> int:
    _ensure_headless()

    structure = load_structure(args.structure)
    if args.supercell is not None:
        structure = structure.supercell(tuple(args.supercell))
    style = Style()
    scene = build_scene(structure, style)
    ranking = rank_candidates(scene, n=args.n, n_surface=args.n_surface, seed=args.seed)

    output = Path(args.output) if args.output else Path(f"{_stem(args.structure)}_candidates.png")
    path = render_candidate_sheet(
        scene,
        ranking,
        output,
        cols=args.cols,
        tile_width=args.tile_width,
        dpi=args.dpi,
        style=style,
    )

    auto = ranking.auto
    print(
        f"[matvu] {structure.formula} | {structure.n_atoms} atoms "
        f"| {scene.n_bonds} bonds"
    )
    if auto is not None:
        azimuth, elevation = auto.view.angles_deg()
        print(
            f"[matvu] candidates: evaluated {ranking.n_evaluated} | auto view "
            f"az {azimuth:.1f} deg, el {elevation:.1f} deg (score {auto.score:.3f})"
        )
    print(f"[matvu] wrote {path}")
    return 0


def _cmd_batch(args) -> int:
    _ensure_headless()
    style = _style_from_args(args)
    formats = _split_option(args.format) or ["png"]
    patterns = _split_option(args.pattern) or ["POSCAR"]

    def report(result, done: int, total: int) -> None:
        name = _display_path(result.source)
        if result.skipped:
            print(f"[batch] {done}/{total} skip  {name}")
        elif result.ok:
            print(
                f"[batch] {done}/{total} {result.formula:<10} "
                f"az {result.azimuth:6.1f} el {result.elevation:5.1f}  "
                f"-> {_display_path(result.outputs[0])}"
            )
        else:
            print(f"[batch] {done}/{total} FAIL  {name}: {result.error}")

    results = render_batch(
        args.sources,
        args.output,
        patterns=patterns,
        formats=formats,
        style=style,
        view=args.view,
        seed=args.seed,
        backend=args.backend,
        jobs=args.jobs,
        skip_existing=args.skip_existing,
        progress=report,
    )
    if not results:
        print("[batch] no structures found")
        return 1
    rendered = [item for item in results if item.ok and not item.skipped]
    skipped = [item for item in results if item.skipped]
    failed = [item for item in results if not item.ok]
    print(
        f"[batch] {len(rendered)} rendered, {len(skipped)} skipped, "
        f"{len(failed)} failed"
    )
    return 1 if failed else 0


def _cmd_animate(args) -> int:
    _ensure_headless()
    style = _style_from_args(args)
    if args.width is None:
        style.width_in = 3.0  # preview-sized animation by default
    if args.dpi is None:
        style.dpi = 120

    structure = load_structure(args.structure)
    output = (
        Path(args.output) if args.output else Path(f"{_stem(args.structure)}_spin.gif")
    )
    written = render_orbit(
        args.structure,
        output,
        view=args.view,
        style=style,
        orbit=args.orbit,
        frames=args.frames,
        fps=args.fps,
        axis=args.axis,
        supercell=tuple(args.supercell) if args.supercell is not None else None,
        seed=args.seed,
        frames_dir=args.frames_dir,
        background=args.background,
    )
    print(
        f"[matvu] {structure.formula} | {structure.n_atoms} atoms "
        f"| {args.frames} frames, {args.fps:g} fps, orbit {args.orbit:g} deg "
        f"around {args.axis}"
    )
    print(f"[matvu] wrote {output}")
    if args.frames_dir is not None:
        print(f"[matvu] frames -> {Path(args.frames_dir)} ({len(written) - 1} files)")
    return 0


def _cmd_theme(args) -> int:
    if args.theme_command == "list":
        print("Built-in themes (one per palette):")
        for name in palette_names():
            print(f"  {name}")
        print("Use: matvu render POSCAR --theme NAME   (or a path/to/theme.toml)")
        return 0
    if args.theme_command == "export":
        path = export_theme(args.name, args.output)
        print(f"[matvu] wrote theme {path}")
        return 0
    return 1


def _cmd_info(args) -> int:
    structure = load_structure(args.structure)
    params = cell_params(structure.lattice)
    print(f"formula      : {structure.formula}")
    print(f"atoms        : {structure.n_atoms}")
    print(
        f"lattice a,b,c: {params['a']:.4f}, {params['b']:.4f}, {params['c']:.4f} A"
    )
    print(
        f"angles       : {params['alpha']:.2f}, {params['beta']:.2f}, "
        f"{params['gamma']:.2f} deg"
    )
    print(f"cell volume  : {structure.volume:.4f} A^3")
    comment = structure.info.get("comment")
    if comment:
        print(f"comment      : {comment}")
    return 0


def _stem(source) -> str:
    return Path(str(source)).stem or "preview"
