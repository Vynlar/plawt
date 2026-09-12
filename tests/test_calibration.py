import unittest

from ender_pen_plotter.calibration import pen_calibration_gcode


class CalibrationTests(unittest.TestCase):
    def test_interactive_calibration_contains_down_up_pauses_and_repeats(self):
        text = pen_calibration_gcode(down_z=2, up_z=5, cycles=2)
        self.assertIn("M0 At DOWN Z=2: adjust", text)
        self.assertIn("M0 At UP Z=5: confirm", text)
        self.assertIn("G28 X Y", text)
        self.assertIn("G28 Z", text)
        self.assertIn("; Calibration cycle 2/2", text)
        self.assertEqual(text.count("G1 X50 Y20 F600"), 2)

    def test_up_height_must_be_above_down_height(self):
        with self.assertRaises(ValueError):
            pen_calibration_gcode(down_z=5, up_z=5)


if __name__ == "__main__":
    unittest.main()
