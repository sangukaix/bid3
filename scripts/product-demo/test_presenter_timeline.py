"""CPU-only checks for reviewed gesture scheduling and source integrity."""
import json
from pathlib import Path
import tempfile
import unittest
import wave

import numpy as np

from presenter import blink_envelope, digest, face_blend_mask, load_gestures, restrained_expression, speech_activity, speech_gesture_schedule


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

    def test_continuous_reviewed_body_can_cover_more_than_a_short_gesture(self):
        paths = [self.clip / f'frame-{i:03}.png' for i in range(300)]
        for i, path in enumerate(paths):
            path.write_bytes(str(i).encode())
        report = json.loads((self.clip / 'report.json').read_text('utf-8'))
        report.update(frames=300, continuous=True)
        self.write(self.clip / 'report.json', report)
        self.acceptance['frame_sha256'] = [digest(path) for path in paths]
        self.write(self.clip / 'acceptance.json', self.acceptance)
        frames, result = load_gestures(self.clip, None, 'neutral', 300)
        self.assertEqual(list(frames), list(range(300)))
        self.assertTrue(result['continuous'])

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

    def test_restrained_lips_preserve_eyes_and_cached_motion(self):
        first = {'exp': np.full((1, 63), .1, np.float32)}
        speech = {'exp': np.full((1, 63), .3, np.float32)}
        original = speech['exp'].copy()
        quiet = restrained_expression(speech, first, 0)['exp'].reshape(21, 3)
        speaking = restrained_expression(speech, first, 1)['exp'].reshape(21, 3)
        np.testing.assert_allclose(quiet[6], .1)
        self.assertTrue(np.all(speaking[6] > quiet[6]))
        self.assertTrue(np.all(speaking[6] < .3))
        np.testing.assert_allclose(speaking[11], .3)
        np.testing.assert_array_equal(speech['exp'], original)

    def test_blink_clock_is_bounded_float32_for_the_renderer(self):
        value = blink_envelope(170)
        self.assertEqual(value.dtype, np.float32)
        self.assertTrue(np.all((value >= 0) & (value <= 1)))
        self.assertTrue(np.all(value[:80] == 0))
        self.assertEqual(value[90], 1)

    def test_waist_up_mask_does_not_expose_a_second_eye_below_the_lid(self):
        mask = face_blend_mask(540)
        self.assertEqual(mask.shape, (540, 540, 1))
        for x, y in [(204, 282), (200, 310), (316, 300)]:
            self.assertEqual(mask[y, x, 0], 1)
        self.assertTrue(np.all((mask >= 0) & (mask <= 1)))

    def test_long_silence_closes_mouth_without_clipping_voice(self):
        rate = 16000
        samples = np.zeros(rate * 3, np.float32)
        samples[rate // 2:rate] = .05 * np.sin(np.arange(rate // 2) * 2 * np.pi * 220 / rate)
        with wave.open(str(self.root / 'test.wav'), 'wb') as audio:
            audio.setnchannels(1)
            audio.setsampwidth(2)
            audio.setframerate(rate)
            audio.writeframes((samples * 32767).astype('<i2').tobytes())
        activity = speech_activity({'narration_dir': str(self.root), 'scenes': [{'id': 'test', 'duration': 4}]})
        self.assertEqual(len(activity), 100)
        self.assertTrue(np.all(activity[:15] == 0))
        self.assertTrue(np.all(activity[25:33] == 1))
        self.assertTrue(np.all(activity[50:] == 0))
        schedule = speech_gesture_schedule({'narration_dir': str(self.root), 'scenes': [{'id': 'test', 'duration': 4}]})
        self.assertEqual(sum(count for _, count in schedule), 100)
        self.assertEqual(schedule[0][0], 'neutral')
        self.assertEqual(schedule[1][0], 'open')
        self.assertEqual(schedule[-1][0], 'neutral')
        # The voice starts at .95s (WAV .5s + scene .45s), stops at1.45s.
        self.assertIn(schedule[0][1], range(20, 22))
        self.assertIn(sum(n for _, n in schedule[:2]), range(41, 43))

    def test_silent_scene_never_triggers_explanation_gestures(self):
        with wave.open(str(self.root / 'silent.wav'), 'wb') as audio:
            audio.setnchannels(1)
            audio.setsampwidth(2)
            audio.setframerate(16000)
            audio.writeframes(bytes(16000))
        schedule = speech_gesture_schedule({'narration_dir': str(self.root),
            'scenes': [{'id': 'silent', 'duration': 2}, {'id': 'silent', 'duration': 2}]})
        self.assertEqual(schedule, [('neutral', 100)])


if __name__ == '__main__':
    unittest.main()
