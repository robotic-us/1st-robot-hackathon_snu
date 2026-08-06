import unittest

from webcam_kimi_shoe_detector import (
    normalized_box_to_pixels,
    normalized_point_to_pixels,
    pair_colors,
    parse_shoe_response,
    shoe_angle_degrees,
)


class BoxConversionTests(unittest.TestCase):
    def test_normalized_box_is_converted_and_clamped(self) -> None:
        shoe = {"x_min": -20, "y_min": 250, "x_max": 750, "y_max": 1100}
        self.assertEqual(normalized_box_to_pixels(shoe, 1280, 720), (0, 180, 960, 720))

    def test_reversed_coordinates_are_sorted(self) -> None:
        shoe = {"x_min": 800, "y_min": 900, "x_max": 200, "y_max": 100}
        self.assertEqual(normalized_box_to_pixels(shoe, 1000, 500), (200, 50, 800, 450))

    def test_normalized_point_is_converted_and_clamped(self) -> None:
        self.assertEqual(normalized_point_to_pixels(-20, 1100, 1280, 720), (0, 720))

    def test_shoe_angle_uses_heel_to_toe_image_direction(self) -> None:
        self.assertEqual(shoe_angle_degrees((110, 50), (10, 50)), 0.0)
        self.assertEqual(shoe_angle_degrees((10, 110), (10, 10)), 90.0)
        self.assertEqual(shoe_angle_degrees((10, 10), (10, 10)), None)

    def test_each_pair_gets_a_distinct_color(self) -> None:
        colors = pair_colors([{"pair_id": "pair_1"}, {"pair_id": "pair_2"}, {"pair_id": "pair_1"}])
        self.assertEqual(colors["pair_1"], colors["pair_1"])
        self.assertNotEqual(colors["pair_1"], colors["pair_2"])

    def test_response_parser_repairs_a_trailing_comma(self) -> None:
        self.assertEqual(parse_shoe_response('{"shoes": [],}'), [])

    def test_response_parser_reports_truncation(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "ran out of output tokens"):
            parse_shoe_response('{"shoes": [', finish_reason="MAX_TOKENS")


if __name__ == "__main__":
    unittest.main()
