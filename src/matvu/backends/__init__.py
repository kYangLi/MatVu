"""Backend registry.

Third-party backends plug in with::

    from matvu.backends import Backend, register_backend

    class MyBackend(Backend):
        name = "mybackend"
        ...

    register_backend(MyBackend)
"""

from __future__ import annotations

from .base import Backend
from . import mpl, tracer

_BACKENDS: dict[str, type[Backend]] = {}


def register_backend(backend_class: type[Backend], *, overwrite: bool = False) -> None:
    """Register a backend class under its ``name``."""
    key = str(backend_class.name).lower()
    if not overwrite and key in _BACKENDS:
        raise ValueError(f"a backend named {key!r} is already registered")
    _BACKENDS[key] = backend_class


def get_backend(name: str = "matplotlib") -> Backend:
    """Instantiate a registered backend by name."""
    key = str(name).lower()
    if key not in _BACKENDS:
        raise ValueError(
            f"unknown backend {name!r}; available: {available_backends()}"
        )
    return _BACKENDS[key]()


def available_backends() -> list[str]:
    """Names of all registered backends."""
    return sorted(_BACKENDS)


register_backend(mpl.MatplotlibBackend)
register_backend(tracer.TracerBackend)
