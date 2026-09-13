from __future__ import annotations

from argparse import ArgumentParser, Namespace
from fractions import Fraction
import math

from ..core import euler_path, render_svg


Point = tuple[Fraction, Fraction, Fraction]
Triangle = tuple[Point, Point, Point]


def _midpoint(first: Point, second: Point) -> Point:
    return tuple((a + b) / 2 for a, b in zip(first, second))  # type: ignore[return-value]


def sierpinski_triangles(depth: int) -> list[Triangle]:
    """Return the small triangles making up a Sierpinski triangle."""
    if depth < 0:
        raise ValueError("depth must not be negative")

    triangles: list[Triangle] = [
        (
            (Fraction(1), Fraction(0), Fraction(0)),
            (Fraction(0), Fraction(1), Fraction(0)),
            (Fraction(0), Fraction(0), Fraction(1)),
        )
    ]
    for _ in range(depth):
        next_triangles: list[Triangle] = []
        for first, second, third in triangles:
            first_second = _midpoint(first, second)
            first_third = _midpoint(first, third)
            second_third = _midpoint(second, third)
            next_triangles.extend(
                [
                    (first, first_second, first_third),
                    (first_second, second, second_third),
                    (first_third, second_third, third),
                ]
            )
        triangles = next_triangles
    return triangles


def sierpinski_path(depth: int) -> list[Point]:
    """Return one Euler path through all Sierpinski triangle edges."""
    edges = []
    for first, second, third in sierpinski_triangles(depth):
        edges.extend(zip((first, second, third), (second, third, first)))
    return euler_path(edges)


def sierpinski_svg(
    width_mm: float,
    depth: int,
    stroke_width_mm: float = 0.2,
) -> str:
    """Return an SVG whose Sierpinski edge graph is one continuous path."""
    if width_mm <= 0:
        raise ValueError("width_mm must be positive")

    height_mm = width_mm * math.sqrt(3) / 2

    def svg_point(point: Point) -> tuple[float, float]:
        _, right, top = point
        x = width_mm * float(right + top / 2)
        y_up = height_mm * float(top)
        return x, height_mm - y_up

    description = (
        f"Sierpinski triangle: width={width_mm:g}mm, depth={depth}, one Euler path"
    )
    return render_svg(
        (svg_point(point) for point in sierpinski_path(depth)),
        width_mm,
        height_mm,
        description=description,
        stroke_width_mm=stroke_width_mm,
    )


def add_sierpinski_arguments(parser: ArgumentParser) -> None:
    parser.add_argument("--width-mm", type=float, required=True)
    parser.add_argument("--depth", type=int, required=True)
    parser.add_argument("--stroke-width-mm", type=float, default=0.2)


def generate_sierpinski(args: Namespace) -> str:
    return sierpinski_svg(args.width_mm, args.depth, args.stroke_width_mm)
