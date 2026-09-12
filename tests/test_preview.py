import unittest

from ender_pen_plotter.config import Config, PenConfig, PlotConfig, PrinterConfig, ToolConfig
from ender_pen_plotter.gcode import extract_segments
from ender_pen_plotter.preview import render_preview_html


class PreviewTests(unittest.TestCase):
    def setUp(self):
        self.config = Config(
            printer=PrinterConfig(),
            pen=PenConfig(offset_x_mm=2, offset_y_mm=-1, draw_z_mm=0, lift_z_mm=1),
            plot=PlotConfig(),
            tool=ToolConfig(),
        )

    def test_extracts_draw_and_travel_segments_with_offset(self):
        gcode = "G90\nG0 X0 Y0\nG0 X10 Y20\nG1 Z0\nG1 X30 Y20 F600\nG1 Z1\n"
        segments = extract_segments(gcode, 0, 2, -1)
        self.assertEqual(len(segments), 2)
        self.assertFalse(segments[0].drawing)
        self.assertTrue(segments[1].drawing)
        self.assertEqual(segments[1].start, (12, 19))
        self.assertEqual(segments[1].end, (32, 19))

    def test_preview_contains_build_plate_and_bounds(self):
        gcode = "G90\nG0 X0 Y0\nG0 X10 Y20\nG1 Z0\nG1 X30 Y20 F600\nG1 Z1\n"
        html = render_preview_html(gcode, self.config, title="Test preview")
        self.assertIn("Test preview", html)
        self.assertIn('viewBox="0 0 220 220"', html)
        self.assertIn("X 12..32 mm, Y 19..19 mm", html)
        self.assertIn("Within configured build plate", html)


if __name__ == "__main__":
    unittest.main()
