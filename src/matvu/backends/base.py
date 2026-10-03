"""Backend protocol: everything a renderer must implement."""

from __future__ import annotations

from abc import ABC, abstractmethod


class Backend(ABC):
    """A rendering backend.

    Backends receive a fully resolved :class:`~matvu.scene.Scene` and a
    :class:`~matvu.viewpoint.View`. They are responsible for output only;
    viewpoint selection happens before, in backend-independent code.
    """

    name = "backend"
    interactive = False

    @abstractmethod
    def render(self, scene, view, style, output=None, **kwargs):
        """Render ``scene`` from ``view``.

        Returns the output path when a file was written, a figure object when
        the backend produced an in-memory result, or ``None``.
        """
        raise NotImplementedError
