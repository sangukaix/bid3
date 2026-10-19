"""CPU regression checks for fast hand travel and smooth authored returns."""
import unittest
import numpy as np
from calm_body import gesture_positions


class HandPacingTests(unittest.TestCase):
    def frame(self, left):
        value = np.zeros((768, 512, 3), np.uint8)
        value[500:600, left:left + 60] = 180
        return value

    def test_fast_hand_travel_gets_more_frames_than_a_still_pose(self):
        frames = [self.frame(140) for _ in range(4)] + [self.frame(260)]
        positions = gesture_positions(frames, 100)
        self.assertEqual(positions[0], 0)
        self.assertEqual(positions[-1], 4)
        self.assertGreater(np.count_nonzero(positions > 3), 40)

    def test_authored_return_has_no_position_jump_at_the_turnaround(self):
        frames = [self.frame(140 + n * 20) for n in range(5)]
        positions = gesture_positions(frames, 151, returning=True)
        self.assertAlmostEqual(positions[0], 0)
        self.assertAlmostEqual(positions[-1], 0)
        self.assertAlmostEqual(positions[75], 4)
        self.assertLess(abs(positions[75] - positions[74]), .02)
        self.assertTrue(np.all((positions >= 0) & (positions <= 4)))


if __name__ == '__main__':
    unittest.main()
