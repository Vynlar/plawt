from __future__ import annotations

import argparse
from pathlib import Path
import sys

from .patterns import GENERATORS


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate SVG pen-plotter patterns.")
    subparsers = parser.add_subparsers(dest="pattern", required=True)
    for name, generator in GENERATORS.items():
        pattern_parser = subparsers.add_parser(name, help=generator.description)
        pattern_parser.add_argument("output", type=Path)
        generator.add_arguments(pattern_parser)
    args = parser.parse_args(argv)

    try:
        svg = GENERATORS[args.pattern].generate(args)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(svg)
        print(f"wrote pattern: {args.output}")
        return 0
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
