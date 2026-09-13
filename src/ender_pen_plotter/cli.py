from __future__ import annotations

import argparse
from pathlib import Path
import sys

from .config import ConfigError, load_config
from .pipeline import convert


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Convert an SVG into safe pen-plotter G-code."
    )
    parser.add_argument("svg", type=Path, help="input SVG file")
    parser.add_argument("-c", "--config", type=Path, default=Path("config/ender3.toml"))
    parser.add_argument("-o", "--output", type=Path, help="output G-code path")
    parser.add_argument("--check-only", action="store_true", help="validate without writing G-code")
    parser.add_argument(
        "--allow-uncalibrated",
        action="store_true",
        help="permit output before the profile's Z heights are verified",
    )
    parser.add_argument("--svg2gcode", help="override the svg2gcode executable")
    parser.add_argument("--version", action="version", version="0.1.0")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
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
