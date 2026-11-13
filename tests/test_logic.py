import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "laptop_vision"))
from logic import area_growth, arm_extended, next_signal, should_alarm, update_arm_counts  # noqa: E402


class ArmTests(unittest.TestCase):
    def test_extended(self):
        self.assertTrue(arm_extended((0.8, 0.3), (0.6, 0.32)))
        self.assertFalse(arm_extended((0.62, 0.3), (0.6, 0.3)))   # too close horizontally
        self.assertFalse(arm_extended((0.8, 0.8), (0.6, 0.3)))    # arm down

    def test_counts_and_signal(self):
        l = r = 0
        state = "off"
        for _ in range(11):
            l, r = update_arm_counts(l, r, True, False)
            state = next_signal(state, l, r, 10)
        self.assertEqual(state, "left")
        l, r = update_arm_counts(l, r, False, False)
        self.assertEqual(next_signal(state, l, r, 10), "off")

    def test_both_arms_reset(self):
        self.assertEqual(update_arm_counts(5, 5, True, True), (0, 0))


class CollisionTests(unittest.TestCase):
    def test_growth(self):
        hist = [(0.0, 100), (0.5, 120), (0.9, 140)]
        self.assertAlmostEqual(area_growth(hist, 1.0, 1.0), 1.4)
        self.assertIsNone(area_growth([(0.0, 100)], 1.0, 1.0))
        self.assertIsNone(area_growth([(0.0, 100), (5.0, 200)], 5.5, 1.0))  # old sample outside window

    def test_alarm_cooldown(self):
        self.assertTrue(should_alarm(1.4, 10.0, 0.0, 1.3, 5.0))
        self.assertFalse(should_alarm(1.4, 10.0, 7.0, 1.3, 5.0))
        self.assertFalse(should_alarm(1.2, 10.0, 0.0, 1.3, 5.0))
        self.assertFalse(should_alarm(None, 10.0, 0.0, 1.3, 5.0))


if __name__ == "__main__":
    unittest.main()
