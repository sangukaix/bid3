"""Synthetic CPU checks for motion interpolation, not avatar-quality scores."""
from pathlib import Path
import sys
import unittest

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from stitch_body import blend_motion


class MotionJoinTests(unittest.TestCase):
    def setUp(self):
        cv2.setNumThreads(2)
        self.flow = cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_MEDIUM)
        self.a = np.full((96, 96, 3), 30, np.uint8)
        self.a[32:64, 20:52] = np.random.default_rng(4).integers(80, 240, (32, 32, 3), dtype=np.uint8)
        self.b = np.roll(self.a, 8, axis=1)

    def test_original_endpoints_are_preserved(self):
        np.testing.assert_array_equal(blend_motion(self.a, self.b, 0, self.flow), self.a)
        np.testing.assert_array_equal(blend_motion(self.a, self.b, 1, self.flow), self.b)

    def test_identical_motion_does_not_change_pixels(self):
        np.testing.assert_array_equal(blend_motion(self.a, self.a, .5, self.flow), self.a)

    def test_translating_texture_is_better_than_ghosted_dissolve(self):
        expected = np.roll(self.a, 4, axis=1).astype(np.float32)
        joined = blend_motion(self.a, self.b, .5, self.flow).astype(np.float32)
        dissolve = (self.a.astype(np.float32) + self.b.astype(np.float32)) / 2
        self.assertLess(np.abs(joined - expected).mean(), np.abs(dissolve - expected).mean())

    def test_unmatched_occluded_object_is_not_a_translucent_duplicate(self):
        class ZeroFlow:
            def calc(self, a, b, initial):
                return np.zeros((*a.shape, 2), np.float32)
        a, b = np.zeros_like(self.a), np.zeros_like(self.a)
        a[30:60, 10:30] = 255
        b[30:60, 60:80] = 255
        result = blend_motion(a, b, .25, ZeroFlow())
        np.testing.assert_array_equal(result[40, 20], [255, 255, 255])
        np.testing.assert_array_equal(result[40, 70], [0, 0, 0])


if __name__ == '__main__':
    unittest.main()
