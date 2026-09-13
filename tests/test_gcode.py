import unittest

from plawt.config import PrinterConfig
from plawt.gcode import add_travel_feedrate, analyze, validate


class GCodeTests(unittest.TestCase):
    def test_travel_feedrate_is_added_without_overwriting_existing_feedrate(self):
        text = "G0 X1 Y2\nG0 X3 Y4 F1200\nG1 X5 Y6 F900\n"
        result = add_travel_feedrate(text, 3000)
        self.assertIn("G0 X1 Y2 F3000", result)
        self.assertIn("G0 X3 Y4 F1200", result)
        self.assertIn("G1 X5 Y6 F900", result)

    def test_analysis_tracks_pen_offset(self):
        text = "G90\nG0 X10 Y20\nG1 X30 Y40 F900\n"
        result = analyze(text, 2, -3)
        self.assertEqual((result.nozzle.x_min, result.nozzle.x_max), (10, 30))
        self.assertEqual((result.nozzle.y_min, result.nozzle.y_max), (20, 40))
        self.assertEqual((result.pen.x_min, result.pen.x_max), (12, 32))
        self.assertEqual((result.pen.y_min, result.pen.y_max), (17, 37))

    def test_bounds_report_both_nozzle_and_pen(self):
        text = "G90\nG0 X1 Y1\nG1 X10 Y10\n"
        result = analyze(text, -2, 0)
        errors = validate(result, PrinterConfig(x_min=0, x_max=10, y_min=0, y_max=10))
        self.assertTrue(any(error.startswith("pen X bounds") for error in errors))


if __name__ == "__main__":
    unittest.main()
