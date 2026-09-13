"""Pen-up path ordering and orientation helpers."""

from __future__ import annotations

import math
from typing import Sequence


Point = tuple[float, float]
Polyline = Sequence[Point]
RouteItem = tuple[int, bool]


def _distance(first: Point, second: Point) -> float:
    return math.hypot(second[0] - first[0], second[1] - first[1])


def _start(path: Polyline, reversed_path: bool) -> Point:
    return path[-1] if reversed_path else path[0]


def _end(path: Polyline, reversed_path: bool) -> Point:
    return path[0] if reversed_path else path[-1]


def _point_segment_distance_squared(point: Point, first: Point, second: Point) -> float:
    dx = second[0] - first[0]
    dy = second[1] - first[1]
    if dx == 0 and dy == 0:
        return (point[0] - first[0]) ** 2 + (point[1] - first[1]) ** 2
    position = (
        ((point[0] - first[0]) * dx + (point[1] - first[1]) * dy)
        / (dx * dx + dy * dy)
    )
    position = max(0.0, min(1.0, position))
    nearest = (first[0] + position * dx, first[1] + position * dy)
    return (point[0] - nearest[0]) ** 2 + (point[1] - nearest[1]) ** 2


def simplify_polyline(path: Polyline, *, tolerance: float) -> list[Point]:
    """Reduce a polyline with Ramer-Douglas-Peucker simplification."""
    if tolerance < 0:
        raise ValueError("tolerance must not be negative")

    points = list(path)
    if len(points) < 3:
        return points

    tolerance_squared = tolerance * tolerance
    keep = [False] * len(points)
    keep[0] = keep[-1] = True
    sections = [(0, len(points) - 1)]
    while sections:
        first, last = sections.pop()
        furthest_distance = tolerance_squared
        furthest_index = None
        for index in range(first + 1, last):
            distance = _point_segment_distance_squared(
                points[index], points[first], points[last]
            )
            if distance > furthest_distance:
                furthest_distance = distance
                furthest_index = index
        if furthest_index is not None:
            keep[furthest_index] = True
            sections.extend(((first, furthest_index), (furthest_index, last)))
    return [point for index, point in enumerate(points) if keep[index]]


def simplify_paths(
    paths: Sequence[Polyline], *, tolerance: float
) -> list[list[Point]]:
    """Simplify each path independently without changing its endpoints."""
    return [simplify_polyline(path, tolerance=tolerance) for path in paths]


def optimize_path_order(
    paths: Sequence[Polyline],
    *,
    start_point: Point | None = None,
    two_opt_passes: int = 2,
) -> list[RouteItem]:
    """Return path indexes and orientations with short connecting travel.

    The initial route uses nearest-endpoint insertion. Each 2-opt pass applies
    first-improvement reversals to the route; reversing a route section also
    reverses every polyline in that section so drawing direction remains valid.
    The input paths are never mutated.
    """
    if two_opt_passes < 0:
        raise ValueError("two_opt_passes must not be negative")

    valid_paths = [index for index, path in enumerate(paths) if len(path) >= 2]
    if not valid_paths:
        return []

    route: list[RouteItem] = []
    remaining = valid_paths.copy()
    current = start_point
    while remaining:
        if current is None:
            index = remaining.pop(0)
            reversed_path = False
        else:
            index, reversed_path = min(
                (
                    (candidate, reverse)
                    for candidate in remaining
                    for reverse in (False, True)
                ),
                key=lambda item: _distance(
                    current, _start(paths[item[0]], item[1])
                ),
            )
            remaining.remove(index)
        route.append((index, reversed_path))
        current = _end(paths[index], reversed_path)

    for _ in range(two_opt_passes):
        improved = False
        for first in range(len(route)):
            for last in range(first, len(route)):
                previous_end = (
                    start_point
                    if first == 0
                    else _end(paths[route[first - 1][0]], route[first - 1][1])
                )
                next_start = (
                    None
                    if last == len(route) - 1
                    else _start(paths[route[last + 1][0]], route[last + 1][1])
                )
                old_start = _start(paths[route[first][0]], route[first][1])
                old_end = _end(paths[route[last][0]], route[last][1])
                new_start = old_end
                new_end = old_start

                old_boundary = 0.0
                new_boundary = 0.0
                if previous_end is not None:
                    old_boundary += _distance(previous_end, old_start)
                    new_boundary += _distance(previous_end, new_start)
                if next_start is not None:
                    old_boundary += _distance(old_end, next_start)
                    new_boundary += _distance(new_end, next_start)

                if new_boundary + 1e-9 < old_boundary:
                    route[first : last + 1] = [
                        (index, not reversed_path)
                        for index, reversed_path in reversed(route[first : last + 1])
                    ]
                    improved = True
                    break
            if improved:
                break
        if not improved:
            break

    return route


def join_nearby_paths(
    paths: Sequence[Polyline],
    *,
    max_gap: float,
) -> list[list[Point]]:
    """Join adjacent paths when their pen-up gap is below ``max_gap``.

    Paths must already be in drawing order and oriented for that order. A
    connector is intentionally drawn between endpoints that are close enough;
    larger gaps remain separate paths and therefore retain their pen lift.
    """
    if max_gap < 0:
        raise ValueError("max_gap must not be negative")

    joined: list[list[Point]] = []
    for path in paths:
        if len(path) < 2:
            continue
        current = list(path)
        if (
            joined
            and _distance(joined[-1][-1], current[0]) <= max_gap
        ):
            if joined[-1][-1] == current[0]:
                joined[-1].extend(current[1:])
            else:
                joined[-1].extend(current)
        else:
            joined.append(current)
    return joined


def optimize_paths(
    paths: Sequence[Polyline],
    *,
    start_point: Point | None = None,
    two_opt_passes: int = 2,
) -> list[list[Point]]:
    """Return copied, ordered, and oriented polylines."""
    return [
        list(reversed(paths[index])) if reversed_path else list(paths[index])
        for index, reversed_path in optimize_path_order(
            paths, start_point=start_point, two_opt_passes=two_opt_passes
        )
    ]
