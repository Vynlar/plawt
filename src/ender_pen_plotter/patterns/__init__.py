"""Reusable pattern-generation machinery and built-in generators."""

from .core import euler_path, render_svg
from .generators import GENERATORS, PatternGenerator
from .generators.sierpinski import (
    sierpinski_path,
    sierpinski_svg,
    sierpinski_triangles,
)
from .path_optimizer import join_nearby_paths, optimize_path_order, optimize_paths

__all__ = [
    "GENERATORS",
    "PatternGenerator",
    "euler_path",
    "render_svg",
    "join_nearby_paths",
    "optimize_path_order",
    "optimize_paths",
    "sierpinski_path",
    "sierpinski_svg",
    "sierpinski_triangles",
]
