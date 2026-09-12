# OpenStreetMap Road PoC

This standalone experiment fetches roads around downtown Providence from the
Overpass API and renders them as a plotter-ready SVG. It intentionally does
not modify the package or add dependencies.

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
  -c config/ender3.toml -o .work/osm-poc/downtown-providence-roads.gcode
.venv/bin/ender-pen-preview .work/osm-poc/downtown-providence-roads.gcode \
  -c config/ender3.toml -o .work/osm-poc/downtown-providence-roads.html
```

The map covers a fixed bounding box around downtown Providence, including the
nearby street grids of College Hill, Federal Hill, and the Jewelry District.
The output is scaled to 160 mm by 180 mm with an 8 mm margin. The narrower
page leaves room for the active profile's 39 mm negative X pen offset. Each OSM
way is a separate SVG path, preventing pen lines from connecting unrelated
roads.

Data attribution: [OpenStreetMap contributors](https://www.openstreetmap.org/copyright).
