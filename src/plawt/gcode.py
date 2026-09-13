from __future__ import annotations

from dataclasses import dataclass
import re

from .config import PrinterConfig


_COMMAND = re.compile(r"^\s*G(\d+)\b", re.IGNORECASE)
_FIELD = re.compile(r"([XYZ])\s*(-?(?:\d+(?:\.\d*)?|\.\d+))", re.IGNORECASE)
_FEED = re.compile(r"\bF\s*-?(?:\d+(?:\.\d*)?|\.\d+)", re.IGNORECASE)


@dataclass(frozen=True)
class Bounds:
    x_min: float
    x_max: float
    y_min: float
    y_max: float


@dataclass(frozen=True)
class GCodeAnalysis:
    nozzle: Bounds
    pen: Bounds
    z_min: float | None
    z_max: float | None


@dataclass(frozen=True)
class Segment:
    start: tuple[float, float]
    end: tuple[float, float]
    drawing: bool


def add_travel_feedrate(text: str, feedrate: float) -> str:
    """Make every G0 use the configured travel speed instead of modal F."""
    output: list[str] = []
    for line in text.splitlines(keepends=True):
        code = line.split(";", 1)[0]
        if re.match(r"^\s*G0\b", code, re.IGNORECASE) and not _FEED.search(code):
            newline = "\n" if line.endswith("\n") else ""
            body = line[:-1] if newline else line
            comment = ""
            if ";" in body:
                body, comment = body.split(";", 1)
                comment = ";" + comment
            body = body.rstrip() + f" F{feedrate:g}"
            output.append(body + comment + newline)
        else:
            output.append(line)
    return "".join(output)


def _bounds(points: list[tuple[float, float]]) -> Bounds:
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    return Bounds(min(xs), max(xs), min(ys), max(ys))


def analyze(text: str, offset_x: float, offset_y: float) -> GCodeAnalysis:
    """Analyze absolute/relative XY and Z motion emitted by the converter."""
    x: float | None = None
    y: float | None = None
    z: float | None = None
    absolute = True
    nozzle_points: list[tuple[float, float]] = []
    z_values: list[float] = []

    for raw_line in text.splitlines():
        code = raw_line.split(";", 1)[0]
        command = _COMMAND.match(code)
        if not command:
            continue
        number = int(command.group(1))
        if number == 90:
            absolute = True
            continue
        if number == 91:
            absolute = False
            continue
        if number == 28:
            # Homing establishes a machine position that is not represented by
            # coordinates in the line, so it is intentionally excluded.
            continue
        if number not in (0, 1, 2, 3):
            continue

        fields = {name.lower(): float(value) for name, value in _FIELD.findall(code)}
        if absolute:
            if "x" in fields:
                x = fields["x"]
            if "y" in fields:
                y = fields["y"]
            if "z" in fields:
                z = fields["z"]
        else:
            if "x" in fields:
                x = (x or 0.0) + fields["x"]
            if "y" in fields:
                y = (y or 0.0) + fields["y"]
            if "z" in fields:
                z = (z or 0.0) + fields["z"]

        if x is not None and y is not None:
            nozzle_points.append((x, y))
        if z is not None and "z" in fields:
            z_values.append(z)

    if not nozzle_points:
        raise ValueError("G-code contains no XY motion to validate")

    pen_points = [(x + offset_x, y + offset_y) for x, y in nozzle_points]
    return GCodeAnalysis(
        nozzle=_bounds(nozzle_points),
        pen=_bounds(pen_points),
        z_min=min(z_values) if z_values else None,
        z_max=max(z_values) if z_values else None,
    )


def extract_segments(
    text: str, draw_z: float, offset_x: float, offset_y: float
) -> list[Segment]:
    """Extract pen and travel segments from absolute/relative G-code motion."""
    x: float | None = None
    y: float | None = None
    z: float | None = None
    absolute = True
    segments: list[Segment] = []

    for raw_line in text.splitlines():
        code = raw_line.split(";", 1)[0]
        command = _COMMAND.match(code)
        if not command:
            continue
        number = int(command.group(1))
        if number == 90:
            absolute = True
            continue
        if number == 91:
            absolute = False
            continue
        if number == 28:
            continue
        if number not in (0, 1, 2, 3):
            continue

        fields = {name.lower(): float(value) for name, value in _FIELD.findall(code)}
        old_position = (x, y)
        if absolute:
            if "x" in fields:
                x = fields["x"]
            if "y" in fields:
                y = fields["y"]
            if "z" in fields:
                z = fields["z"]
        else:
            if "x" in fields:
                x = (x or 0.0) + fields["x"]
            if "y" in fields:
                y = (y or 0.0) + fields["y"]
            if "z" in fields:
                z = (z or 0.0) + fields["z"]

        if (
            x is None
            or y is None
            or old_position[0] is None
            or old_position[1] is None
            or not ({"x", "y"} & fields.keys())
            or (x == old_position[0] and y == old_position[1])
        ):
            continue

        start = (old_position[0] + offset_x, old_position[1] + offset_y)
        end = (x + offset_x, y + offset_y)
        drawing = number != 0 and z is not None and abs(z - draw_z) < 1e-6
        segments.append(Segment(start=start, end=end, drawing=drawing))

    return segments


def validate(analysis: GCodeAnalysis, printer: PrinterConfig) -> list[str]:
    errors: list[str] = []
    for label, bounds in (("nozzle", analysis.nozzle), ("pen", analysis.pen)):
        if bounds.x_min < printer.x_min or bounds.x_max > printer.x_max:
            errors.append(
                f"{label} X bounds {bounds.x_min:g}..{bounds.x_max:g} "
                f"exceed {printer.x_min:g}..{printer.x_max:g}"
            )
        if bounds.y_min < printer.y_min or bounds.y_max > printer.y_max:
            errors.append(
                f"{label} Y bounds {bounds.y_min:g}..{bounds.y_max:g} "
                f"exceed {printer.y_min:g}..{printer.y_max:g}"
            )
    if analysis.z_min is not None and analysis.z_min < printer.z_min:
        errors.append(f"Z minimum {analysis.z_min:g} is below {printer.z_min:g}")
    if analysis.z_max is not None and analysis.z_max > printer.z_max:
        errors.append(f"Z maximum {analysis.z_max:g} exceeds {printer.z_max:g}")
    return errors
