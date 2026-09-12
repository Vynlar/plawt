"""Reusable pattern-generation machinery and built-in generators."""

from .core import euler_path, render_svg
from .generators import GENERATORS, PatternGenerator
from .generators.sierpinski import (
    sierpinski_path,
    sierpinski_svg,
    sierpinski_triangles,
)

__all__ = [
    "GENERATORS",
    "PatternGenerator",
    "euler_path",
    "render_svg",
    "sierpinski_path",
    "sierpinski_svg",
    "sierpinski_triangles",
]
