from __future__ import annotations

import argparse
from pathlib import Path
import sys

from .calibration import pen_calibration_gcode
from .config import ConfigError, load_config
from .pipeline import convert


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Convert an SVG into safe Ender 3 pen-plotter G-code."
    )
    parser.add_argument("svg", nargs="?", type=Path, help="input SVG file")
    parser.add_argument("-c", "--config", type=Path, default=Path("config/ender3.toml"))
    parser.add_argument("-o", "--output", type=Path, help="output G-code path")
    parser.add_argument("--check-only", action="store_true", help="validate without writing G-code")
    parser.add_argument(
        "--allow-uncalibrated",
        action="store_true",
        help="permit output while calibration is marked incomplete",
    )
    parser.add_argument("--svg2gcode", help="override the svg2gcode executable")
    parser.add_argument(
        "--calibrate-pen",
        "--calibrate-z",
        dest="calibrate_pen",
        type=Path,
        metavar="OUTPUT",
        help="write an interactive pen down/up calibration file instead of converting an SVG",
    )
    parser.add_argument("--down-z", type=float, help="nozzle Z height used for pen contact")
    parser.add_argument("--up-z", type=float, help="nozzle Z height used for pen travel")
    parser.add_argument("--calibration-cycles", type=int, default=2)
    parser.add_argument("--calibration-x", type=float, default=20.0)
    parser.add_argument("--calibration-y", type=float, default=20.0)
    parser.add_argument("--version", action="version", version="0.1.0")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.calibrate_pen is not None:
            config = load_config(args.config)
            down_z = args.down_z
            if down_z is None:
                down_z = config.pen.draw_z_mm if config.pen.draw_z_mm is not None else 2.0
            up_z = args.up_z if args.up_z is not None else config.pen.lift_z_mm
            text = pen_calibration_gcode(
                down_z=down_z,
                up_z=up_z,
                cycles=args.calibration_cycles,
                start_x=args.calibration_x,
                start_y=args.calibration_y,
                home_xy=config.plot.home_xy,
                home_z=config.plot.home_z,
            )
            args.calibrate_pen.parent.mkdir(parents=True, exist_ok=True)
            args.calibrate_pen.write_text(text)
            print(f"wrote interactive pen calibration file: {args.calibrate_pen}")
            print(
                f"calibration line: X{args.calibration_x:g}.."
                f"{args.calibration_x + 30:g}, Y{args.calibration_y:g}; "
                f"down Z={down_z:g}, up Z={up_z:g}"
            )
            return 0

        if args.svg is None:
            _parser().error("an SVG path is required unless --calibrate-pen is used")
        config = load_config(args.config)
        output = None if args.check_only else (args.output or args.svg.with_suffix(".gcode"))
        report, _ = convert(
            args.svg,
            output,
            config,
            allow_uncalibrated=args.allow_uncalibrated,
            executable_override=args.svg2gcode,
        )
        print(report)
        if output is not None:
            print(f"wrote {output}")
        return 0
    except (ConfigError, ValueError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
