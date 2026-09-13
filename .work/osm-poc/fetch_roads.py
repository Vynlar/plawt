#!/usr/bin/env python3
"""Fetch a small OSM road extract and render it as an SVG.

This is intentionally standalone. If the result is useful, the projection,
filtering, and SVG path handling can be moved into a real pattern generator.
"""

from __future__ import annotations

import argparse
import html
import json
import math
from pathlib import Path
import sys
from typing import Iterable, Sequence
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from ender_pen_plotter.patterns.path_optimizer import (
    join_nearby_paths,
    optimize_path_order,
    simplify_paths,
)


EARTH_RADIUS_M = 6_378_137.0
OVERPASS_ENDPOINT = "https://overpass-api.de/api/interpreter"

# This covers streets and useful downtown pedestrian streets without turning
# the first plot into a dense collection of paths and steps.
HIGHWAY_TYPES = (
    "motorway",
    "trunk",
    "primary",
    "secondary",
    "tertiary",
    "unclassified",
    "residential",
    "living_street",
    "pedestrian",
)

# South, west, north, east. This includes downtown Providence, College Hill,
# Federal Hill, the Jewelry District, and the surrounding street grid.
DEFAULT_BBOX = (41.806, -71.436, 41.839, -71.389)
DEFAULT_OUTPUT = Path(__file__).with_name("downtown-providence-roads.svg")
DEFAULT_CACHE = Path(__file__).with_name("cache") / "roads.json"


Point = tuple[float, float]
Polyline = list[Point]


def overpass_query(bbox: Sequence[float]) -> str:
    south, west, north, east = bbox
    highway_pattern = "|".join(HIGHWAY_TYPES)
    return f"""[out:json][timeout:60];
way[highway~\"^({highway_pattern})$\"]({south:.6f},{west:.6f},{north:.6f},{east:.6f});
out geom;"""


def fetch_osm(query: str, cache_path: Path, *, refresh: bool) -> dict:
    query_cache_path = cache_path.with_suffix(cache_path.suffix + ".query")
    if (
        cache_path.is_file()
        and query_cache_path.is_file()
        and not refresh
        and query_cache_path.read_text() == query
    ):
        print(f"using cached Overpass response: {cache_path}")
        return json.loads(cache_path.read_text())

    payload = urlencode({"data": query}).encode("utf-8")
    request = Request(
        OVERPASS_ENDPOINT,
        data=payload,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "ender-pen-plotter-osm-poc/0.1",
        },
        method="POST",
    )
    print(f"fetching road data from {OVERPASS_ENDPOINT}")
    try:
        with urlopen(request, timeout=90) as response:
            data = response.read()
    except (HTTPError, URLError, TimeoutError) as exc:
        raise RuntimeError(f"Overpass request failed: {exc}") from exc

    try:
        result = json.loads(data)
    except json.JSONDecodeError as exc:
        raise RuntimeError("Overpass returned invalid JSON") from exc
    if not isinstance(result, dict) or not isinstance(result.get("elements"), list):
        raise RuntimeError("Overpass response did not contain an elements list")

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_bytes(data)
    query_cache_path.write_text(query)
    print(f"cached Overpass response: {cache_path}")
    return result


def project_point(latitude: float, longitude: float, bbox: Sequence[float]) -> Point:
    south, west, north, east = bbox
    latitude0 = math.radians((south + north) / 2)
    x = math.radians(longitude - west) * EARTH_RADIUS_M * math.cos(latitude0)
    y = math.radians(latitude - south) * EARTH_RADIUS_M
    return x, y


def clip_segment(first: Point, second: Point, width: float, height: float) -> tuple[Point, Point] | None:
    """Clip one segment to the local projected bbox using Liang-Barsky."""
    x1, y1 = first
    x2, y2 = second
    dx = x2 - x1
    dy = y2 - y1
    parameters = ((-dx, x1), (dx, width - x1), (-dy, y1), (dy, height - y1))
    lower = 0.0
    upper = 1.0
    for coefficient, constant in parameters:
        if coefficient == 0:
            if constant < 0:
                return None
            continue
        value = constant / coefficient
        if coefficient < 0:
            lower = max(lower, value)
        else:
            upper = min(upper, value)
        if lower > upper:
            return None
    return (
        (x1 + lower * dx, y1 + lower * dy),
        (x1 + upper * dx, y1 + upper * dy),
    )


def clipped_polylines(points: Sequence[Point], width: float, height: float) -> list[Polyline]:
    """Clip a way while preserving gaps where it leaves the bbox."""
    paths: list[Polyline] = []
    current: Polyline = []
    for first, second in zip(points, points[1:]):
        clipped = clip_segment(first, second, width, height)
        if clipped is None:
            if len(current) >= 2:
                paths.append(current)
            current = []
            continue
        clipped_first, clipped_second = clipped
        if not current or current[-1] != clipped_first:
            if len(current) >= 2:
                paths.append(current)
            current = [clipped_first]
        current.append(clipped_second)
    if len(current) >= 2:
        paths.append(current)
    return paths


def osm_polylines(data: dict, bbox: Sequence[float]) -> list[tuple[str, list[Polyline]]]:
    south, west, north, east = bbox
    map_width = math.radians(east - west) * EARTH_RADIUS_M * math.cos(
        math.radians((south + north) / 2)
    )
    map_height = math.radians(north - south) * EARTH_RADIUS_M
    roads: list[tuple[str, list[Polyline]]] = []
    for element in data["elements"]:
        if element.get("type") != "way":
            continue
        geometry = element.get("geometry")
        if not isinstance(geometry, list) or len(geometry) < 2:
            continue
        points = [
            project_point(node["lat"], node["lon"], bbox)
            for node in geometry
            if isinstance(node, dict) and "lat" in node and "lon" in node
        ]
        if len(points) < 2:
            continue
        tags = element.get("tags", {})
        highway = tags.get("highway", "road") if isinstance(tags, dict) else "road"
        paths = clipped_polylines(points, map_width, map_height)
        if paths:
            roads.append((highway, paths))
    return roads


def svg_path(points: Iterable[Point]) -> str:
    commands = []
    for index, (x, y) in enumerate(points):
        commands.append(f"{'M' if index == 0 else 'L'} {x:.3f},{y:.3f}")
    return " ".join(commands)


def render_svg(
    roads: Sequence[tuple[str, list[Polyline]]],
    bbox: Sequence[float],
    width_mm: float,
    height_mm: float,
    margin_mm: float,
    stroke_width_mm: float,
    join_gap_mm: float,
    simplify_tolerance_mm: float,
) -> str:
    if width_mm <= 2 * margin_mm or height_mm <= 2 * margin_mm:
        raise ValueError("page dimensions must leave room for the margin")
    south, west, north, east = bbox
    map_width = math.radians(east - west) * EARTH_RADIUS_M * math.cos(
        math.radians((south + north) / 2)
    )
    map_height = math.radians(north - south) * EARTH_RADIUS_M
    scale = min(
        (width_mm - 2 * margin_mm) / map_width,
        (height_mm - 2 * margin_mm) / map_height,
    )
    x_offset = (width_mm - map_width * scale) / 2
    y_offset = (height_mm - map_height * scale) / 2
    page_paths = [
        [
            (x_offset + x * scale, height_mm - (y_offset + y * scale))
            for x, y in path
        ]
        for _, paths in roads
        for path in paths
    ]
    simplified_paths = simplify_paths(page_paths, tolerance=simplify_tolerance_mm)
    joined_paths = join_nearby_paths(simplified_paths, max_gap=join_gap_mm)
    path_elements = [
        f'  <path fill="none" stroke="black" stroke-width="{stroke_width_mm:g}" '
        f'stroke-linecap="round" stroke-linejoin="round" d="{svg_path(path)}" />'
        for path in joined_paths
    ]
    description = (
        "Downtown Providence roads from OpenStreetMap; "
        f"{len(page_paths)} optimized paths, "
        f"{len(joined_paths)} joined SVG paths, "
        f"simplification tolerance {simplify_tolerance_mm:g} mm"
    )
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{width_mm:g}mm" height="{height_mm:g}mm" viewBox="0 0 {width_mm:g} {height_mm:g}">
  <title>{html.escape(description)}</title>
  <!-- {html.escape(description)} -->
  <!-- Data © OpenStreetMap contributors, https://www.openstreetmap.org/copyright -->
{chr(10).join(path_elements)}
</svg>
'''


def optimize_roads(roads: Sequence[tuple[str, list[Polyline]]]) -> list[tuple[str, list[Polyline]]]:
    road_paths = [(highway, path) for highway, paths in roads for path in paths]
    route = optimize_path_order(
        [path for _, path in road_paths], start_point=(0.0, 0.0), two_opt_passes=2
    )
    return [
        (
            road_paths[index][0],
            [list(reversed(road_paths[index][1])) if reversed_path else road_paths[index][1]],
        )
        for index, reversed_path in route
    ]


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--refresh", action="store_true", help="ignore the cached response")
    # The centered PoC profile uses a 39 mm negative X pen offset, so a 140 mm
    # page leaves safe nozzle clearance after centering on the 220 mm bed.
    parser.add_argument("--width-mm", type=float, default=140.0)
    parser.add_argument("--height-mm", type=float, default=160.0)
    parser.add_argument("--margin-mm", type=float, default=8.0)
    parser.add_argument("--stroke-width-mm", type=float, default=0.18)
    parser.add_argument(
        "--join-gap-mm",
        type=float,
        default=0.2,
        help="draw connectors instead of hopping across gaps up to this size",
    )
    parser.add_argument(
        "--simplify-tolerance-mm",
        type=float,
        default=0.05,
        help="remove path detail within this final SVG tolerance",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        query = overpass_query(DEFAULT_BBOX)
        data = fetch_osm(query, args.cache, refresh=args.refresh)
        roads = optimize_roads(osm_polylines(data, DEFAULT_BBOX))
        if not roads:
            raise RuntimeError("the response contained no roads in the requested bbox")
        svg = render_svg(
            roads,
            DEFAULT_BBOX,
            args.width_mm,
            args.height_mm,
            args.margin_mm,
            args.stroke_width_mm,
            args.join_gap_mm,
            args.simplify_tolerance_mm,
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(svg)
    except (OSError, RuntimeError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(f"wrote {len(roads)} optimized road paths to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
