# OpenStreetMap Road PoC

This standalone experiment fetches roads around downtown Providence from the
Overpass API and renders them as a plotter-ready SVG. It adds no dependencies
and reuses the package's generic path optimizer.

Run it from the repository root:

```sh
python3 .work/osm-poc/fetch_roads.py
```

The first run downloads one small response and stores it in
`.work/osm-poc/cache/roads.json`. Later runs use that cache. To fetch fresh
data:

```sh
python3 .work/osm-poc/fetch_roads.py --refresh
```

Convert and preview it with the project tools:

```sh
.venv/bin/ender-pen-plotter .work/osm-poc/downtown-providence-roads.svg \
  -c .work/osm-poc/ender3-centered.toml -o .work/osm-poc/downtown-providence-roads.gcode
.venv/bin/ender-pen-preview .work/osm-poc/downtown-providence-roads.gcode \
  -c .work/osm-poc/ender3-centered.toml -o .work/osm-poc/downtown-providence-roads.html
```

The map covers a fixed bounding box around downtown Providence, including the
nearby street grids of College Hill, Federal Hill, and the Jewelry District.
The output is scaled to 140 mm by 160 mm with an 8 mm margin. The narrower
page leaves room for the pen's 39 mm negative X offset when the artwork is
centered on the bed using `ender3-centered.toml`. Each OSM way is a separate
SVG path, preventing pen lines from connecting unrelated roads.

Before rendering, the paths are ordered with a nearest-endpoint heuristic and
two bounded 2-opt refinement passes. The reusable implementation lives in
`src/ender_pen_plotter/patterns/path_optimizer.py`. Adjacent paths with gaps up
to `0.2 mm` are joined with a short drawing connector instead of a Z-hop. Path
detail is simplified with a `0.05 mm` Ramer-Douglas-Peucker tolerance.

Data attribution: [OpenStreetMap contributors](https://www.openstreetmap.org/copyright).
