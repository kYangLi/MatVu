"""MatVu: automatic viewpoint optimization and visualization.

MatVu analyses a materials structure, finds a clear viewing direction
automatically and renders a publication-ready ball-and-stick figure::

    from matvu import render

    render("POSCAR", view="auto")
"""

__version__ = "0.1.1"

from .backends import available_backends, register_backend
from .gallery import rank_candidates, render_candidates
from .io import available_formats, load_structure, register_reader
from .palettes import palette_names
from .render import auto_view, render, render_array, resolve_view
from .structure import Structure
from .style import Style, style_preset
from .theme import Theme, export_theme, load_theme
from .viewpoint import View, pick_view
from .viewpoint import score as score_view

__all__ = [
    "__version__",
    "Structure",
    "Style",
    "View",
    "auto_view",
    "available_backends",
    "available_formats",
    "export_theme",
    "load_structure",
    "load_theme",
    "palette_names",
    "pick_view",
    "rank_candidates",
    "register_backend",
    "register_reader",
    "render",
    "render_array",
    "render_candidates",
    "resolve_view",
    "score_view",
    "style_preset",
]
