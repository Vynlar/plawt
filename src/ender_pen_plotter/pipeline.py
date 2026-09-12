from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import tempfile

from .config import Config, ConfigError
from .gcode import GCodeAnalysis, add_travel_feedrate, analyze, validate


def _number(value: float) -> str:
    return f"{value:g}"


def _resolve_executable(executable: str) -> str | None:
    if Path(executable).is_file():
        return executable
    resolved = shutil.which(executable)
    if resolved:
        return resolved
    cargo_executable = Path.home() / ".cargo" / "bin" / executable
    if cargo_executable.is_file():
        return str(cargo_executable)
    return None


def _sequences(config: Config) -> tuple[str, str, str, str]:
    pen = config.pen
    plot = config.plot
    safe_z = _number(pen.lift_z_mm)
    travel_f = _number(plot.travel_feedrate)
    z_f = _number(pen.z_feedrate)

    begin_lines = []
    if plot.home_xy:
        begin_lines.append("G28 X Y")
    if plot.home_z:
        begin_lines.append("G28 Z")
    begin_lines.append(f"G0 Z{safe_z} F{travel_f}")

    end_lines = [f"G0 Z{safe_z} F{travel_f}"]
    if plot.park_x_mm is not None and plot.park_y_mm is not None:
        end_lines.append(
            f"G0 X{_number(plot.park_x_mm)} Y{_number(plot.park_y_mm)} F{travel_f}"
        )
    end_lines.append("M2")

    return (
        "\n".join(begin_lines),
        f"G1 Z{_number(pen.draw_z_mm)} F{z_f}",
        f"G1 Z{safe_z} F{z_f}",
        "\n".join(end_lines),
    )


def _report(analysis: GCodeAnalysis) -> str:
    def bounds(value) -> str:
        return (
            f"X {value.x_min:g}..{value.x_max:g}, "
            f"Y {value.y_min:g}..{value.y_max:g}"
        )

    z = "unknown"
    if analysis.z_min is not None:
        z = f"{analysis.z_min:g}..{analysis.z_max:g}"
    return f"nozzle [{bounds(analysis.nozzle)}]; pen [{bounds(analysis.pen)}]; Z {z}"


def convert(
    svg_path: Path,
    output_path: Path | None,
    config: Config,
    allow_uncalibrated: bool = False,
    executable_override: str | None = None,
) -> tuple[str, GCodeAnalysis]:
    config.validate_for_plot(allow_uncalibrated=allow_uncalibrated)
    if not svg_path.is_file():
        raise ConfigError(f"SVG file not found: {svg_path}")

    executable = executable_override or config.tool.executable
    resolved_executable = _resolve_executable(executable)
    if resolved_executable is None:
        raise ConfigError(
            f"could not find {executable!r}; install it with "
            "cargo install svg2gcode-cli (which installs svg2gcode) or pass "
            "--svg2gcode"
        )
    executable = resolved_executable

    begin, tool_on, tool_off, end = _sequences(config)
    # svg2gcode's origin places the SVG page's lower-left corner. The pen,
    # rather than the nozzle, should land at the configured page origin.
    origin_x = config.plot.origin_x_mm - config.pen.offset_x_mm
    origin_y = config.plot.origin_y_mm - config.pen.offset_y_mm

    with tempfile.TemporaryDirectory(prefix="ender-pen-plotter-") as directory:
        temporary_output = Path(directory) / "output.gcode"
        command = [
            executable,
            str(svg_path),
            "--out",
            str(temporary_output),
            "--feedrate",
            _number(config.plot.draw_feedrate),
            "--tolerance",
            _number(config.plot.tolerance_mm),
            "--origin",
            f"{_number(origin_x)},{_number(origin_y)}",
            "--on",
            tool_on,
            "--off",
            tool_off,
            "--begin",
            begin,
            "--end",
            end,
        ]
        try:
            result = subprocess.run(command, capture_output=True, text=True)
        except OSError as exc:
            raise ConfigError(f"could not execute {executable!r}: {exc}") from exc
        if result.returncode != 0:
            details = result.stderr.strip() or result.stdout.strip()
            raise ConfigError(f"svg2gcode failed: {details}")

        text = add_travel_feedrate(
            temporary_output.read_text(), config.plot.travel_feedrate
        )
        analysis = analyze(
            text, config.pen.offset_x_mm, config.pen.offset_y_mm
        )
        errors = validate(analysis, config.printer)
        if errors:
            raise ConfigError("generated G-code is outside machine limits:\n- " + "\n- ".join(errors))

        if output_path is not None:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(text)
        return _report(analysis), analysis
