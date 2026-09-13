# Plawt

Plawt converts SVG paths into G-code for configurable pen plotters. It uses
[`sameer/svg2gcode`](https://github.com/sameer/svg2gcode) for SVG conversion
and adds configurable pen motion, tool offsets, homing, feedrates, and machine
envelope safety checks around it.

## Install

Install the converter:

```sh
cargo install svg2gcode-cli
```

If `cargo` is not installed, use Rust's official `rustup` installer first:

```sh
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
rustup default stable
```

Cargo installs the executable under `~/.cargo/bin`. If that directory is not
already on your shell PATH, add it before using the wrapper:

```sh
export PATH="$HOME/.cargo/bin:$PATH"
```

The wrapper also checks that standard Cargo location automatically.

Install this wrapper in a virtual environment:

```sh
python3 -m venv .venv
.venv/bin/pip install -e .
```

The Cargo package installs the `svg2gcode` executable. The wrapper supports
Python 3.9 and newer. Python 3.11 and newer use the
standard-library TOML reader; older Python versions install `tomli`.

## Configure

Start with `config/ender3.toml` as an example machine profile, or create a
profile for your own printer. Profiles define the machine envelope, pen offset,
Z heights, feedrates, origin, and homing behavior.

The example profile uses `draw_z_mm = 2`, `lift_z_mm = 3.5`, the current tool
offset, and `calibrated = true`. Choose these values for your own tool and
update them whenever the tool or its mount changes.

`offset_x_mm` and `offset_y_mm` are the tool tip's position relative to the
nozzle in printer coordinates. If the tool tip is 10 mm in +X from the nozzle,
set `offset_x_mm = 10`. The wrapper compensates by moving the nozzle to the
desired tool position minus that offset.

`origin_x_mm` and `origin_y_mm` are the desired lower-left corner of the SVG
page on the bed. The wrapper derives the corresponding nozzle origin. Any
margin between the page edge and the artwork comes from the SVG itself.

## Convert

```sh
.venv/bin/ender-pen-plotter drawing.svg -o drawing.gcode
```

Use another profile with `--config`:

```sh
.venv/bin/ender-pen-plotter drawing.svg \
  --config config/my-pen.toml \
  -o output/drawing.gcode
```

The generated file uses:

- `G1 ... F<draw_feedrate>` for drawing moves.
- `G0 ... F<travel_feedrate>` for travel moves.
- `G1 Z<draw_z_mm> F<z_feedrate>` to lower the pen.
- `G1 Z<lift_z_mm> F<z_feedrate>` to lift the pen.

Speeds are in mm/min. The example profile draws at 1170 mm/min; tune this for
your machine, tool, and material.

Before writing a file, the wrapper checks the commanded nozzle envelope, the
actual pen envelope after offset compensation, and all explicit Z values
against the configured machine limits.

## Preview

Render any generated G-code over the configured build plate:

```sh
.venv/bin/ender-pen-preview \
  output/sierpinski-2in-depth3.gcode \
  --config config/ender3.toml \
  -o output/sierpinski-2in-depth3.html
```

The result is a self-contained HTML file. It shows the compensated pen path,
travel moves, a 10 mm grid, the build plate, drawing bounds, pen offset, and a
warning if the drawing leaves the configured machine limits.

## Choose Z Heights

The profile has two absolute nozzle Z heights:

- `draw_z_mm` is the height used while the tool is drawing.
- `lift_z_mm` is the height used while the tool is moving without drawing.

Choose both with the printer's normal controls and jogging workflow. With paper
on the bed, lower the tool until it draws cleanly without excessive pressure;
that is the draw height. Raise it until the tool clears the paper reliably
during travel; that is the lift height. Record those values in the profile:

```toml
draw_z_mm = 2.0
lift_z_mm = 3.5
calibrated = true
```

The values are absolute machine Z coordinates, not a relative hop distance.
Keep the machine attended while checking them, and set `calibrated = true` only
after both heights work with the mounted tool. `lift_z_mm` must be greater than
`draw_z_mm`.

Enable Z homing only when the mounted tool is clear of the bed and safe to home.
Set `home_z = false` if the tool or machine setup requires it.

## SVG Preparation

Use millimeter units in the SVG. Convert text and ordinary shapes to paths in
Inkscape. The converter is intended for stroked paths; it does not generate
filled regions as pen hatching. Inspect the resulting G-code before sending
it to the printer.

## Developing Patterns

Shared pattern machinery lives in `src/plawt/patterns/core.py`.
Design-specific geometry belongs in its own module under
`src/plawt/patterns/generators/`. A generator can build points or
edges with its own algorithm, then use `euler_path` and `render_svg` when those
operations fit the design. Register its CLI adapter in
`patterns/generators/__init__.py`; the adapter supplies the design's arguments
and returns an SVG string.

For example, the Sierpinski implementation keeps triangle subdivision in
`generators/sierpinski.py`, while Euler traversal and SVG serialization remain
independent and reusable by new designs. The command line uses one subcommand
per registered generator:

```sh
.venv/bin/ender-pen-pattern sierpinski output/pattern.svg \
  --width-mm 101.6 --depth 5
```

The wrapper homes X/Y first and Z second by default, then raises to the
configured lift height. Keep the machine attended for the first runs and test
with the tool lifted before allowing contact with paper.
