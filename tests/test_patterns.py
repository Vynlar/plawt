import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from ender_pen_plotter.pattern_cli import main as pattern_main
from ender_pen_plotter.patterns import (
    euler_path,
    optimize_path_order,
    optimize_paths,
    render_svg,
    sierpinski_svg,
)
from ender_pen_plotter.patterns.generators.sierpinski import sierpinski_triangles


class PatternTests(unittest.TestCase):
    def test_shared_euler_path_handles_a_reusable_graph(self):
        self.assertEqual(euler_path([("a", "b"), ("b", "c"), ("c", "a")]), ["a", "c", "b", "a"])

    def test_shared_euler_path_rejects_graphs_without_a_continuous_traversal(self):
        with self.assertRaisesRegex(ValueError, "does not have an Euler path"):
            euler_path([(0, 1), (0, 2), (0, 3), (0, 4)])

    def test_shared_svg_renderer_does_not_depend_on_a_specific_generator(self):
        svg = render_svg([(0, 0), (10, 5)], 10, 5, description="custom design")
        self.assertIn("custom design", svg)
        self.assertIn("M 0.000000,0.000000 L 10.000000,5.000000", svg)

    def test_path_optimizer_orders_and_orients_paths_from_a_start_point(self):
        paths = [[(100, 0), (110, 0)], [(20, 0), (10, 0)], [(0, 0), (1, 0)]]
        self.assertEqual(
            optimize_paths(paths, start_point=(0, 0), two_opt_passes=0),
            [[(0, 0), (1, 0)], [(10, 0), (20, 0)], [(100, 0), (110, 0)]],
        )

    def test_path_optimizer_returns_route_metadata_without_mutating_paths(self):
        paths = [[(0, 0), (1, 0)], [(10, 0), (9, 0)]]
        route = optimize_path_order(paths, start_point=(0, 0))
        self.assertEqual(route, [(0, False), (1, True)])
        self.assertEqual(paths, [[(0, 0), (1, 0)], [(10, 0), (9, 0)]])

    def test_path_optimizer_rejects_negative_refinement_passes(self):
        with self.assertRaisesRegex(ValueError, "must not be negative"):
            optimize_paths([], two_opt_passes=-1)

    def test_sierpinski_generator_exposes_geometry_before_rendering(self):
        self.assertEqual(len(sierpinski_triangles(2)), 9)

    def test_cli_dispatches_to_the_registered_generator(self):
        with TemporaryDirectory() as directory:
            output = Path(directory) / "pattern.svg"
            result = pattern_main(
                ["sierpinski", str(output), "--width-mm", "25", "--depth", "1"]
            )
            self.assertEqual(result, 0)
            self.assertTrue(output.is_file())
            self.assertIn("Sierpinski triangle", output.read_text())

    def test_sierpinski_depth_three_is_one_continuous_path(self):
        svg = sierpinski_svg(50.8, 3)
        self.assertEqual(svg.count("M "), 1)
        self.assertIn("one Euler path", svg)
        self.assertIn('width="50.8mm"', svg)

    def test_invalid_pattern_dimensions_are_rejected(self):
        with self.assertRaises(ValueError):
            sierpinski_svg(0, 3)
        with self.assertRaises(ValueError):
            sierpinski_svg(50.8, -1)


if __name__ == "__main__":
    unittest.main()
