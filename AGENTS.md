# Agent Instructions

## Project Shape

- This is a Python 3.9+ package under `src/plawt`; run commands from the repository root because the default config path is relative.
- `ender-pen-plotter` wraps the external Rust `svg2gcode` executable; it adds configurable homing, Z pen lift, XY offset compensation, feedrates, and machine-bound validation.
- `ender-pen-preview` renders existing G-code as self-contained HTML;
  `ender-pen-pattern` generates reusable SVG patterns. Shared pattern
  machinery is in `src/plawt/patterns/core.py`; design-specific generators are
  modules under `src/plawt/patterns/generators/`.
- `config/ender3.toml` is the active machine profile. `.work/` and `output/` are ignored generated/test artifacts, not source-of-truth files.

## Setup

- Install the official converter package with `cargo install svg2gcode-cli`; this installs the executable named `svg2gcode` under `~/.cargo/bin`.
- Install the Python package with `python3 -m venv .venv` followed by `.venv/bin/pip install -e .`.
- The wrapper can find `~/.cargo/bin/svg2gcode` automatically, but Cargo must still be installed.

## Commands

- Run all tests: `.venv/bin/python -m unittest discover -s tests -v`.
- Convert an SVG: `.venv/bin/ender-pen-plotter drawing.svg -c config/ender3.toml -o output/drawing.gcode`.
- Check conversion without writing: add `--check-only`.
- Render a preview: `.venv/bin/ender-pen-preview output/drawing.gcode -c config/ender3.toml -o output/drawing.html`.
- Generate a Sierpinski SVG: `.venv/bin/ender-pen-pattern sierpinski examples/pattern.svg --width-mm 101.6 --depth 5`.
- Add a pattern by creating a module under `patterns/generators/`, exposing a
  design-specific SVG function plus CLI argument and generation adapters, and
  registering a `PatternGenerator` in `patterns/generators/__init__.py`.

## Machine Constraints

- G-code uses absolute millimeter coordinates. `draw_z_mm` and `lift_z_mm` are absolute nozzle Z heights; speeds are mm/min.
- `offset_x_mm` and `offset_y_mm` describe the pen tip relative to the nozzle. The converter subtracts these offsets when deriving the nozzle path.
- `origin_x_mm` and `origin_y_mm` place the SVG page's lower-left corner for the pen, not necessarily the artwork bounds.
- With the current profile, G-code homes X/Y first, then Z (`G28 X Y` followed by `G28 Z`), then moves to lift height. `home_xy` and `home_z` control this; enable Z homing only when the mounted tool is safely clear of the bed.
- Choose absolute `draw_z_mm` and `lift_z_mm` heights with the printer's normal controls, verify drawing contact and travel clearance, then set `calibrated = true` in the profile.
- Conversion must pass both nozzle and compensated pen bounds checks before writing output. Use the HTML preview to inspect placement before sending G-code to the printer.

## Pattern Optimization

- The Sierpinski generator builds one Euler path through the edge graph to avoid a Z-hop for every small triangle. Preserve that single-path approach when changing its size or depth.
- Reuse `patterns.core.euler_path` for connected edge graphs and
  `patterns.core.render_svg` for standard path-based SVG output; keep geometry
  and design-specific options in the individual generator module.
