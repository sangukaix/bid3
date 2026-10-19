"""Camera drift regression checks independent of the neural renderer."""
import unittest
import numpy as np
from stabilize_presenter import camera_transforms, eye_geometry


class CameraStabilityTests(unittest.TestCase):
    def setUp(self):
        self.reference = np.full((478, 2), [256., 150.], np.float32)
        self.reference[[33, 133]] = [226., 150.]
        self.reference[[362, 263]] = [286., 150.]

    def test_camera_scale_and_lateral_drift_are_removed_without_mutating_input(self):
        phase = np.linspace(0, 2 * np.pi, 100)
        scales = 1 + .04 * np.sin(phase)
        points = self.reference[None] * scales[:, None, None]
        points += np.stack([8 * np.sin(phase), 4 * np.cos(phase)], axis=1)[:, None]
        original = points.copy()
        transforms = camera_transforms(points, self.reference)
        corrected = np.einsum('nij,nkj->nki', transforms[:, :, :2], points) + transforms[:, None, :, 2]
        centers, vectors = eye_geometry(corrected)
        self.assertLess(np.ptp(centers[:, 0]), 1.)
        self.assertLess(np.ptp(centers[:, 1]), .5)
        spans = np.linalg.norm(vectors, axis=1)
        self.assertLess(spans.max() / spans.min(), 1.005)
        np.testing.assert_array_equal(points, original)

    def test_reference_camera_has_identity_transform(self):
        points = np.repeat(self.reference[None], 20, axis=0)
        expected = np.repeat(np.array([[[1, 0, 0], [0, 1, 0]]], np.float32), 20, axis=0)
        np.testing.assert_allclose(camera_transforms(points, self.reference), expected, atol=1e-4)

    def test_extreme_camera_change_requires_review_instead_of_cropping_hands(self):
        points = np.repeat(self.reference[None], 20, axis=0) * .5
        with self.assertRaisesRegex(ValueError, 'bounded'):
            camera_transforms(points, self.reference)


if __name__ == '__main__':
    unittest.main()
