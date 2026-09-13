from __future__ import annotations

from collections import defaultdict
from typing import Hashable, Iterable, TypeVar


Vertex = TypeVar("Vertex", bound=Hashable)
SvgPoint = tuple[float, float]


def euler_path(edges: Iterable[tuple[Vertex, Vertex]]) -> list[Vertex]:
    """Return one continuous path containing every edge exactly once."""
    edge_list = list(edges)
    if not edge_list:
        raise ValueError("cannot build an Euler path from no edges")

    adjacency: dict[Vertex, list[tuple[int, Vertex]]] = defaultdict(list)
    for edge_id, (first, second) in enumerate(edge_list):
        adjacency[first].append((edge_id, second))
        adjacency[second].append((edge_id, first))

    odd_vertices = [vertex for vertex, neighbors in adjacency.items() if len(neighbors) % 2]
    if len(odd_vertices) not in (0, 2):
        raise ValueError("edge graph does not have an Euler path")

    used = [False] * len(edge_list)
    stack = [odd_vertices[0] if odd_vertices else edge_list[0][0]]
    circuit: list[Vertex] = []
    while stack:
        vertex = stack[-1]
        while adjacency[vertex] and used[adjacency[vertex][-1][0]]:
            adjacency[vertex].pop()
        if not adjacency[vertex]:
            circuit.append(stack.pop())
            continue
        edge_id, other = adjacency[vertex].pop()
        if used[edge_id]:
            continue
        used[edge_id] = True
        stack.append(other)

    if len(circuit) != len(edge_list) + 1:
        raise ValueError("edge graph is not connected")
    return list(reversed(circuit))


def render_svg(
    points: Iterable[SvgPoint],
    width_mm: float,
    height_mm: float,
    *,
    description: str,
    stroke_width_mm: float = 0.2,
) -> str:
    """Render a path of millimeter points as a minimal, plotter-ready SVG."""
    if width_mm <= 0:
        raise ValueError("width_mm must be positive")
    if height_mm <= 0:
        raise ValueError("height_mm must be positive")
    if stroke_width_mm <= 0:
        raise ValueError("stroke_width_mm must be positive")

    path_points = list(points)
    if not path_points:
        raise ValueError("an SVG path needs at least one point")
    path_data = "M " + " L ".join(
        f"{x:.6f},{y:.6f}" for x, y in path_points
    )
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{width_mm:g}mm" height="{height_mm:.6f}mm" viewBox="0 0 {width_mm:g} {height_mm:.6f}">
  <!-- {description} -->
  <path fill="none" stroke="black" stroke-width="{stroke_width_mm:g}" d="{path_data}" />
</svg>
'''
