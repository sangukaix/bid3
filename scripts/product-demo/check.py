"""Check that the published video still matches its editable source assets."""
import hashlib
import json
from pathlib import Path
import subprocess

import imageio_ffmpeg

ROOT = Path(__file__).resolve().parents[2]
PUBLIC = ROOT / 'web/public/product-demo'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    story = json.loads((ROOT / 'web/features/product-demo/storyboard.json').read_text('utf-8'))
    build = json.loads((PUBLIC / 'build.json').read_text('utf-8'))
    fingerprint = hashlib.sha256(json.dumps(story, sort_keys=True, ensure_ascii=False).encode('utf-8')).hexdigest()
    assert build['storyboard_sha256'] == fingerprint, 'Storyboard changed; regenerate the video.'
    assert story['version'] == build['version']
    assert build['duration'] == sum(s['duration'] for s in story['scenes'])
    assert build['sha256'] == digest(PUBLIC / 'intro.mp4'), 'Video does not match build manifest.'
    for name, expected in build['sources'].items():
        assert digest(PUBLIC / 'screens' / name) == expected, f'Screenshot changed: {name}; regenerate video.'
    # Fast-start MP4 places moov before media data, allowing range playback immediately.
    data = (PUBLIC / 'intro.mp4').read_bytes()
    boxes = []
    offset = 0
    while offset + 8 <= len(data):
        size = int.from_bytes(data[offset:offset + 4], 'big')
        kind = data[offset + 4:offset + 8]
        assert size >= 8, 'Unexpected MP4 box.'
        boxes.append(kind)
        offset += size
    assert boxes.index(b'moov') < boxes.index(b'mdat'), 'MP4 is not optimized for streaming.'
    cues = (PUBLIC / 'captions.ko.vtt').read_text('utf-8')
    assert cues.startswith('WEBVTT') and cues.count(' --> ') == sum(len(s['narration'].rstrip('.').split('. ')) for s in story['scenes'])
    assert (PUBLIC / 'poster.webp').stat().st_size > 0
    # Decode every frame and audio packet, not just the first screenshot.
    result = subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), '-v', 'error', '-i', str(PUBLIC / 'intro.mp4'),
                             '-f', 'null', '-'], capture_output=True, text=True)
    assert result.returncode == 0 and not result.stderr.strip(), result.stderr
    print(f"PASS: {build['duration']}s, {len(story['scenes'])} scenes, sources/captions/fast-start and full audio/video decode.")


if __name__ == '__main__':
    main()
