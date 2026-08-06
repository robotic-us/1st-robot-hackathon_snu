import unittest

from kimi_shoe_photo import normalized_box_to_pixels


class BoxConversionTests(unittest.TestCase):
    def test_normalized_box_is_converted_and_clamped(self) -> None:
        shoe = {"x_min": -20, "y_min": 250, "x_max": 750, "y_max": 1100}
        self.assertEqual(normalized_box_to_pixels(shoe, 1280, 720), (0, 180, 960, 720))

    def test_reversed_coordinates_are_sorted(self) -> None:
        shoe = {"x_min": 800, "y_min": 900, "x_max": 200, "y_max": 100}
        self.assertEqual(normalized_box_to_pixels(shoe, 1000, 500), (200, 50, 800, 450))


if __name__ == "__main__":
    unittest.main()
