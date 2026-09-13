from __future__ import annotations

import argparse
from pathlib import Path
import sys

from .config import ConfigError, load_config
from .preview import render_preview_html


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Render generated pen-plotter G-code over a build-plate preview."
    )
    parser.add_argument("gcode", type=Path)
    parser.add_argument("-c", "--config", type=Path, default=Path("config/ender3.toml"))
    parser.add_argument("-o", "--output", type=Path, help="HTML output path")
    parser.add_argument("--title", default=None)
    args = parser.parse_args(argv)

    try:
        config = load_config(args.config)
        if not args.gcode.is_file():
            raise ConfigError(f"G-code file not found: {args.gcode}")
        output = args.output or args.gcode.with_suffix(".html")
        output.parent.mkdir(parents=True, exist_ok=True)
        html = render_preview_html(
            args.gcode.read_text(),
            config,
            title=args.title or args.gcode.stem,
        )
        output.write_text(html)
        print(f"wrote preview: {output}")
        return 0
    except (ConfigError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
