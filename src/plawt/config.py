from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - exercised on Python < 3.11
    import tomli as tomllib


class ConfigError(ValueError):
    """Raised when a machine profile is missing or contains unsafe values."""


@dataclass(frozen=True)
class PrinterConfig:
    x_min: float = 0.0
    x_max: float = 220.0
    y_min: float = 0.0
    y_max: float = 220.0
    z_min: float = 0.0
    z_max: float = 250.0


@dataclass(frozen=True)
class PenConfig:
    offset_x_mm: float = 0.0
    offset_y_mm: float = 0.0
    draw_z_mm: float | None = None
    lift_z_mm: float = 5.0
    z_feedrate: float = 300.0
    calibrated: bool = False


@dataclass(frozen=True)
class PlotConfig:
    origin_x_mm: float = 10.0
    origin_y_mm: float = 10.0
    draw_feedrate: float = 900.0
    travel_feedrate: float = 3000.0
    tolerance_mm: float = 0.002
    home_xy: bool = True
    home_z: bool = True
    park_x_mm: float | None = None
    park_y_mm: float | None = None


@dataclass(frozen=True)
class ToolConfig:
    executable: str = "svg2gcode"


@dataclass(frozen=True)
class Config:
    printer: PrinterConfig
    pen: PenConfig
    plot: PlotConfig
    tool: ToolConfig

    def validate_for_plot(self, allow_uncalibrated: bool = False) -> None:
        if self.pen.draw_z_mm is None:
            raise ConfigError(
                "pen.draw_z_mm is not set; choose a draw Z height and set it in the profile"
            )
        if not allow_uncalibrated and not self.pen.calibrated:
            raise ConfigError(
                "pen.calibrated is false; set it to true after choosing and verifying the Z heights"
            )
        if self.pen.lift_z_mm <= self.pen.draw_z_mm:
            raise ConfigError("pen.lift_z_mm must be greater than pen.draw_z_mm")
        if self.pen.z_feedrate <= 0:
            raise ConfigError("pen.z_feedrate must be positive")
        if self.plot.draw_feedrate <= 0:
            raise ConfigError("plot.draw_feedrate must be positive")
        if self.plot.travel_feedrate <= 0:
            raise ConfigError("plot.travel_feedrate must be positive")
        if self.plot.tolerance_mm <= 0:
            raise ConfigError("plot.tolerance_mm must be positive")

        z_values = (self.pen.draw_z_mm, self.pen.lift_z_mm)
        if min(z_values) < self.printer.z_min or max(z_values) > self.printer.z_max:
            raise ConfigError("pen Z values are outside the configured printer limits")

        if self.plot.park_x_mm is not None and not (
            self.printer.x_min <= self.plot.park_x_mm <= self.printer.x_max
        ):
            raise ConfigError("plot.park_x_mm is outside the configured printer limits")
        if self.plot.park_y_mm is not None and not (
            self.printer.y_min <= self.plot.park_y_mm <= self.printer.y_max
        ):
            raise ConfigError("plot.park_y_mm is outside the configured printer limits")


def _section(data: dict, name: str) -> dict:
    value = data.get(name, {})
    if not isinstance(value, dict):
        raise ConfigError(f"[{name}] must be a TOML table")
    return value


def _float(section: dict, name: str, default: float | None) -> float | None:
    value = section.get(name, default)
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ConfigError(f"{name} must be a number") from exc


def load_config(path: Path) -> Config:
    try:
        data = tomllib.loads(path.read_text())
    except FileNotFoundError as exc:
        raise ConfigError(f"configuration file not found: {path}") from exc
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"invalid TOML in {path}: {exc}") from exc

    printer = _section(data, "printer")
    pen = _section(data, "pen")
    plot = _section(data, "plot")
    tool = _section(data, "tool")

    return Config(
        printer=PrinterConfig(
            x_min=_float(printer, "x_min", 0.0),
            x_max=_float(printer, "x_max", 220.0),
            y_min=_float(printer, "y_min", 0.0),
            y_max=_float(printer, "y_max", 220.0),
            z_min=_float(printer, "z_min", 0.0),
            z_max=_float(printer, "z_max", 250.0),
        ),
        pen=PenConfig(
            offset_x_mm=_float(pen, "offset_x_mm", 0.0),
            offset_y_mm=_float(pen, "offset_y_mm", 0.0),
            draw_z_mm=_float(pen, "draw_z_mm", None),
            lift_z_mm=_float(pen, "lift_z_mm", 5.0),
            z_feedrate=_float(pen, "z_feedrate", 300.0),
            calibrated=bool(pen.get("calibrated", False)),
        ),
        plot=PlotConfig(
            origin_x_mm=_float(plot, "origin_x_mm", 10.0),
            origin_y_mm=_float(plot, "origin_y_mm", 10.0),
            draw_feedrate=_float(plot, "draw_feedrate", 900.0),
            travel_feedrate=_float(plot, "travel_feedrate", 3000.0),
            tolerance_mm=_float(plot, "tolerance_mm", 0.002),
            home_xy=bool(plot.get("home_xy", True)),
            home_z=bool(plot.get("home_z", True)),
            park_x_mm=_float(plot, "park_x_mm", None),
            park_y_mm=_float(plot, "park_y_mm", None),
        ),
        tool=ToolConfig(executable=str(tool.get("executable", "svg2gcode"))),
    )
