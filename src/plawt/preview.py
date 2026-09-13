from __future__ import annotations

from html import escape

from .config import Config
from .gcode import Segment, extract_segments


def _number(value: float) -> str:
    return f"{value:.3f}".rstrip("0").rstrip(".") or "0"


def _path_data(segments: list[Segment]) -> str:
    return " ".join(
        f"M {_number(segment.start[0])},{_number(segment.start[1])} "
        f"L {_number(segment.end[0])},{_number(segment.end[1])}"
        for segment in segments
    )


def _drawing_bounds(segments: list[Segment]) -> tuple[float, float, float, float] | None:
    points = [point for segment in segments for point in (segment.start, segment.end)]
    if not points:
        return None
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    return min(xs), max(xs), min(ys), max(ys)


def _outside(bounds: tuple[float, float, float, float], config: Config) -> bool:
    x_min, x_max, y_min, y_max = bounds
    printer = config.printer
    return (
        x_min < printer.x_min
        or x_max > printer.x_max
        or y_min < printer.y_min
        or y_max > printer.y_max
    )


def render_preview_html(gcode: str, config: Config, title: str = "Pen plot preview") -> str:
    segments = extract_segments(
        gcode,
        draw_z=config.pen.draw_z_mm if config.pen.draw_z_mm is not None else 0.0,
        offset_x=config.pen.offset_x_mm,
        offset_y=config.pen.offset_y_mm,
    )
    drawing = [segment for segment in segments if segment.drawing]
    travel = [segment for segment in segments if not segment.drawing]
    bounds = _drawing_bounds(drawing)
    printer = config.printer
    bed_width = printer.x_max - printer.x_min
    bed_height = printer.y_max - printer.y_min
    warning = ""
    if bounds is None:
        warning = "No drawing moves were found at the configured draw Z."
    elif _outside(bounds, config):
        warning = "The drawing extends outside the configured build plate."

    if bounds is None:
        bounds_text = "none"
    else:
        x_min, x_max, y_min, y_max = bounds
        bounds_text = (
            f"X {_number(x_min)}..{_number(x_max)} mm, "
            f"Y {_number(y_min)}..{_number(y_max)} mm"
        )

    status_class = "warning" if warning else "ok"
    warning_html = f'<div class="{status_class}">{escape(warning or "Within configured build plate")}</div>'
    viewbox = (
        f"{_number(printer.x_min)} {_number(printer.y_min)} "
        f"{_number(bed_width)} {_number(bed_height)}"
    )
    transform = f"translate(0 {_number(printer.y_min + printer.y_max)}) scale(1 -1)"

    return f'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(title)}</title>
  <style>
    :root {{ color-scheme: light dark; font-family: system-ui, sans-serif; }}
    body {{ margin: 0; padding: 2rem; background: #f4f1eb; color: #25231f; }}
    main {{ max-width: 960px; margin: 0 auto; }}
    h1 {{ margin: 0 0 .4rem; font-size: 1.4rem; }}
    .meta {{ color: #68635b; margin-bottom: 1rem; }}
    .preview {{ background: #fffdf9; border: 1px solid #d6d0c6; padding: 1rem; box-shadow: 0 8px 24px #2d251414; }}
    svg {{ display: block; width: 100%; height: auto; max-height: 75vh; }}
    .bed {{ fill: url(#grid); stroke: #34312b; stroke-width: .7; }}
    .travel {{ fill: none; stroke: #9d978e; stroke-width: .35; stroke-dasharray: 1.5 1.5; opacity: .65; }}
    .drawing {{ fill: none; stroke: #c44b2f; stroke-width: .8; stroke-linecap: round; stroke-linejoin: round; }}
    .legend {{ display: flex; gap: 1.25rem; margin-top: .8rem; color: #68635b; font-size: .9rem; }}
    .swatch {{ display: inline-block; width: 1.5rem; border-top: 3px solid; vertical-align: middle; margin-right: .35rem; }}
    .swatch.draw {{ border-color: #c44b2f; }}
    .swatch.travel {{ border-color: #9d978e; border-top-style: dashed; }}
    .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: .6rem; margin-top: 1rem; }}
    .stat {{ background: #fffdf9; border: 1px solid #d6d0c6; padding: .7rem; }}
    .label {{ display: block; color: #68635b; font-size: .75rem; text-transform: uppercase; letter-spacing: .06em; }}
    .ok, .warning {{ margin: 1rem 0 0; padding: .7rem .8rem; border-radius: .3rem; }}
    .ok {{ background: #e5f1e8; color: #245b35; }}
    .warning {{ background: #f8e4df; color: #8a2f22; }}
    @media (prefers-color-scheme: dark) {{ body {{ background: #24221f; color: #f4f1eb; }} .preview, .stat {{ background: #302d29; border-color: #554f47; }} .meta, .legend, .label {{ color: #bdb5a9; }} }}
  </style>
</head>
<body>
  <main>
    <h1>{escape(title)}</h1>
    <div class="meta">Machine coordinates in millimeters. The red path is the compensated pen path.</div>
    <div class="preview">
      <svg viewBox="{viewbox}" role="img" aria-label="Build plate preview">
        <defs>
          <pattern id="grid" width="10" height="10" patternUnits="userSpaceOnUse">
            <path d="M 10 0 L 0 0 0 10" fill="none" stroke="#d8d2c8" stroke-width=".35" />
          </pattern>
        </defs>
        <g transform="{transform}">
          <rect class="bed" x="{_number(printer.x_min)}" y="{_number(printer.y_min)}" width="{_number(bed_width)}" height="{_number(bed_height)}" />
          <path class="travel" d="{_path_data(travel)}" />
          <path class="drawing" d="{_path_data(drawing)}" />
        </g>
      </svg>
      <div class="legend"><span><span class="swatch draw"></span>pen path</span><span><span class="swatch travel"></span>travel moves</span></div>
    </div>
    {warning_html}
    <div class="stats">
      <div class="stat"><span class="label">Build plate</span>{_number(bed_width)} x {_number(bed_height)} mm</div>
      <div class="stat"><span class="label">Drawing bounds</span>{escape(bounds_text)}</div>
      <div class="stat"><span class="label">Segments</span>{len(drawing)} drawing / {len(travel)} travel</div>
      <div class="stat"><span class="label">Pen offset</span>X {_number(config.pen.offset_x_mm)}, Y {_number(config.pen.offset_y_mm)} mm</div>
    </div>
  </main>
</body>
</html>
'''
