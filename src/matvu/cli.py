"""Command line interface: ``matvu render`` and ``matvu info``."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from .backends import available_backends
from .gallery import rank_candidates, render_candidate_sheet
from .geometry import cell_params
from .io import load_structure
from .render import render, resolve_view
from .scene import build_scene
from .style import Style


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
    render_parser.add_argument("--atom-scale", type=float, default=None)
    render_parser.add_argument("--bond-radius", type=float, default=None)
    render_parser.add_argument("--width", type=float, default=None, help="figure width in inches")
    render_parser.add_argument("--dpi", type=int, default=None)
    render_parser.add_argument("--transparent", action="store_true")
    render_parser.add_argument("--no-bonds", action="store_true")
    render_parser.add_argument(
        "--metal-bonds",
        action="store_true",
        help="draw metal-metal bonds (default: off)",
    )
    render_parser.add_argument(
        "--no-cell",
        action="store_true",
        help="hide the unit cell frame",
    )
    render_parser.add_argument(
        "--boundary-padding",
        type=float,
        default=None,
        help="fractional margin of mirrored periodic boundary atoms (default 0.10, 0 disables)",
    )
    render_parser.add_argument(
        "--perspective",
        type=float,
        default=None,
        help="perspective strength (0 = orthographic, default 0.25)",
    )
    render_parser.add_argument(
        "--supersample",
        type=int,
        default=None,
        help="anti-aliasing factor for the tracer backend (default 2)",
    )
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
    parser.print_help()
    return 1


def _cmd_render(args) -> int:
    if not os.environ.get("DISPLAY"):
        import matplotlib

        matplotlib.use("Agg")

    style = Style()
    if args.atom_scale is not None:
        style.atom_scale = args.atom_scale
    if args.bond_radius is not None:
        style.bond_radius = args.bond_radius
    if args.width is not None:
        style.width_in = args.width
    if args.dpi is not None:
        style.dpi = args.dpi
    if args.transparent:
        style.transparent = True
    if args.no_bonds:
        style.draw_bonds = False
    if args.metal_bonds:
        style.metal_metal_bonds = True
    if args.no_cell:
        style.draw_cell = False
    if args.perspective is not None:
        style.perspective = args.perspective
    if args.boundary_padding is not None:
        style.boundary_padding = args.boundary_padding
    if args.supersample is not None:
        style.supersample = args.supersample

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
    if not os.environ.get("DISPLAY"):
        import matplotlib

        matplotlib.use("Agg")

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
