# Ender 3 Pen Plotter

This project converts SVG paths into G-code for an original Ender 3 with a
spring-loaded pen attachment. It uses
[`sameer/svg2gcode`](https://github.com/sameer/svg2gcode) for SVG conversion
and adds the Ender-specific pen motion and safety checks around it.

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

Edit `config/ender3.toml`. The profile defaults to the original Ender 3's
nominal 220 x 220 x 250 mm volume.

The profile uses the measured Z values (`draw_z_mm = 2` and `lift_z_mm = 3.5`),
the measured pen offset, and `calibrated = true`. Update these values whenever
the attachment is remounted or mechanically changed.

`offset_x_mm` and `offset_y_mm` are the pen tip's position relative to the
nozzle in printer coordinates. If the pen is 10 mm in +X from the nozzle, set
`offset_x_mm = 10`. The wrapper compensates by moving the nozzle to the desired
pen position minus that offset.

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

Speeds are in mm/min. The active profile draws at 1170 mm/min; reduce this if
line quality suffers after changing the pen.

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

## Pen Calibration

Calibration is interactive rather than a blind Z sweep. Generate a calibration
file with the desired nominal down and up heights:

```sh
.venv/bin/ender-pen-plotter \
  --config config/ender3.toml \
  --calibrate-pen .work/pen-calibration.gcode \
  --down-z 2.0 \
  --up-z 5.0 \
  --calibration-cycles 3
```

The file uses Marlin `M0` pauses. With the pen clear of the bed, continue the
file from the LCD and it will home X/Y and then Z through the limit switches
using separate `G28 X Y` and `G28 Z` commands. Place paper after homing. It
moves to `down_z`, pauses so you can slide the pen in its holder until it
barely touches the paper, and draws a short test line. It then moves to
`up_z` so you can confirm the pen clears the paper. The process repeats for
the requested number of cycles.

The profile enables Z homing because this attachment overhangs the bed safely.
Set `home_z = false` if the attachment changes. Inspect the file before
running it and keep the printer attended. `--calibrate-z` remains an alias for
`--calibrate-pen`.

After confirming the heights, put them in the profile:

```toml
draw_z_mm = 2.0
lift_z_mm = 3.5
calibrated = true
```

## SVG Preparation

Use millimeter units in the SVG. Convert text and ordinary shapes to paths in
Inkscape. The converter is intended for stroked paths; it does not generate
filled regions as pen hatching. Inspect the resulting G-code before sending
it to the printer.

## Developing Patterns

Shared pattern machinery lives in `src/ender_pen_plotter/patterns/core.py`.
Design-specific geometry belongs in its own module under
`src/ender_pen_plotter/patterns/generators/`. A generator can build points or
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
configured lift height. Keep the printer attended for the first runs and test
with the pen lifted before allowing contact with paper.
