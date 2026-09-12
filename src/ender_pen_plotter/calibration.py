from __future__ import annotations


def pen_calibration_gcode(
    down_z: float = 2.0,
    up_z: float = 5.0,
    cycles: int = 2,
    start_x: float = 20.0,
    start_y: float = 20.0,
    line_length: float = 30.0,
    draw_feedrate: float = 600.0,
    z_feedrate: float = 300.0,
    travel_feedrate: float = 3000.0,
    home_xy: bool = True,
    home_z: bool = True,
) -> str:
    if down_z < 0:
        raise ValueError("down_z must not be below zero")
    if up_z <= down_z:
        raise ValueError("up_z must be greater than down_z")
    if cycles < 1:
        raise ValueError("cycles must be at least one")
    if line_length <= 0:
        raise ValueError("line_length must be positive")

    lines = [
        "; Ender 3 interactive pen calibration",
        f"; Down Z: {down_z:g}; Up Z: {up_z:g}; Cycles: {cycles}",
        "G21",
        "G90",
        "M117 Pen calibration",
    ]
    if home_xy or home_z:
        lines.append("M0 Make sure the pen is clear of the bed, then click to home axes")
    if home_xy:
        lines.append("G28 X Y")
    if home_z:
        lines.append("G28 Z")
    if not home_xy and not home_z:
        lines.append("M0 Home X/Y manually with the pen clear, then click")
    lines.extend(
        [
            "M0 Place paper, then click",
            f"G0 Z{up_z:g} F{travel_feedrate:g}",
            f"G0 X{start_x:g} Y{start_y:g} F{travel_feedrate:g}",
            f"M0 At UP Z={up_z:g}: confirm the pen is clear, then click",
        ]
    )
    for index in range(cycles):
        if index:
            lines.append(f"G0 X{start_x:g} Y{start_y:g} F{travel_feedrate:g}")
        lines.extend(
            [
                f"; Calibration cycle {index + 1}/{cycles}",
                f"G0 Z{down_z:g} F{z_feedrate:g}",
            ]
        )
        if index == 0:
            lines.append(
                f"M0 At DOWN Z={down_z:g}: adjust the pen to barely touch paper, then click"
            )
        else:
            lines.append(
                f"M0 At DOWN Z={down_z:g}: confirm contact, then click"
            )
        lines.extend(
            [
                f"G1 X{start_x + line_length:g} Y{start_y:g} F{draw_feedrate:g}",
                f"G0 Z{up_z:g} F{travel_feedrate:g}",
                f"M0 At UP Z={up_z:g}: confirm the pen clears paper, then click",
            ]
        )
    lines.extend([f"G0 Z{up_z:g} F{travel_feedrate:g}", "M2", ""])
    return "\n".join(lines)
