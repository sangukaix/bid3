"""CPU-only checks for reviewed gesture scheduling and source integrity."""
import json
from pathlib import Path
import tempfile
import unittest

from presenter import digest, load_gestures


class GestureTimelineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.clip = self.root / 'explain'
        self.clip.mkdir()
        (self.clip / 'gesture.mp4').write_bytes(b'test-video')
        for index in range(2):
            (self.clip / f'frame-{index:03}.png').write_bytes(bytes([index]))
        self.write(self.clip / 'report.json', {
            'fps': 25, 'frames': 2, 'source_sha256': 'neutral', 'end_image_sha256': 'neutral',
            'video_sha256': digest(self.clip / 'gesture.mp4')})
        self.acceptance = {'accepted': True, 'video_sha256': digest(self.clip / 'gesture.mp4'),
                           'frame_sha256': [digest(self.clip / f'frame-{i:03}.png') for i in range(2)]}
        self.write(self.clip / 'acceptance.json', self.acceptance)

    def write(self, path, value):
        path.write_text(json.dumps(value), encoding='utf-8')
        return path

    def timeline(self, starts):
        return self.write(self.root / 'timeline.json', {'fps': 25, 'portrait_sha256': 'neutral',
            'segments': [{'start_seconds': s, 'clip': 'explain'} for s in starts]})

    def test_separated_segments_keep_absolute_audio_positions(self):
        frames, report = load_gestures(None, self.timeline([0, 1]), 'neutral', 50)
        self.assertEqual(list(frames), [0, 1, 25, 26])
        self.assertEqual(report['duration'], 4 / 25)
        self.assertEqual(len(report['segments']), 2)

    def test_legacy_single_clip(self):
        frames, _ = load_gestures(self.clip, None, 'neutral', 50)
        self.assertEqual(list(frames), [0, 1])

    def test_overlap_out_of_range_and_subframe_starts_are_rejected(self):
        for starts in ([0, 0.04], [1.96], [-1], [0.01]):
            with self.subTest(starts=starts), self.assertRaises(ValueError):
                load_gestures(None, self.timeline(starts), 'neutral', 50)

    def test_wrong_identity_is_rejected_even_with_valid_clip_hashes(self):
        report = json.loads((self.clip / 'report.json').read_text('utf-8'))
        report['end_image_sha256'] = 'different-person'
        self.write(self.clip / 'report.json', report)
        with self.assertRaisesRegex(ValueError, 'portrait'):
            load_gestures(None, self.timeline([0]), 'neutral', 50)

    def test_unreviewed_and_changed_frames_are_rejected(self):
        self.acceptance['accepted'] = False
        self.write(self.clip / 'acceptance.json', self.acceptance)
        with self.assertRaisesRegex(ValueError, 'acceptance'):
            load_gestures(None, self.timeline([0]), 'neutral', 50)
        self.acceptance['accepted'] = True
        self.write(self.clip / 'acceptance.json', self.acceptance)
        (self.clip / 'frame-001.png').write_bytes(b'changed-after-review')
        with self.assertRaisesRegex(ValueError, 'changed'):
            load_gestures(None, self.timeline([0]), 'neutral', 50)


if __name__ == '__main__':
    unittest.main()
