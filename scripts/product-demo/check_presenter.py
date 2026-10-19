"""Verify published narrator provenance, full decoding and unchanged single audio."""
import hashlib
import json
from pathlib import Path
import re
import subprocess

import imageio_ffmpeg

ROOT = Path(__file__).resolve().parents[2]
PUBLIC = ROOT / 'web/public/product-demo'
WORK = ROOT / '.local/product-demo/presenter'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    manifest = json.loads((PUBLIC / 'presenter.json').read_text('utf-8'))
    story_file = ROOT / 'web/features/product-demo/storyboard.json'
    story = json.loads(story_file.read_text('utf-8'))
    video = PUBLIC / 'intro-with-guide.mp4'
    assert manifest['main_video_sha256'] == digest(PUBLIC / 'intro.mp4'), 'Recompose after changing the main video'
    assert manifest['storyboard_sha256'] == digest(story_file), 'Recompose after changing the storyboard'
    assert manifest['video_sha256'] == digest(video)
    assert manifest['duration'] == sum(s['duration'] for s in story['scenes'])
    assert manifest['storyboard_version'] == story['version']
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    probe = subprocess.run([ffmpeg, '-hide_banner', '-i', str(video)], capture_output=True, text=True)
    assert len(re.findall(r'Stream #0:\d+.*Audio:', probe.stderr)) == 1, 'Exactly one audio track required'
    assert '2560x1080' in probe.stderr
    decoded = subprocess.run([ffmpeg, '-v', 'error', '-i', str(video), '-progress', 'pipe:1',
                             '-f', 'null', '-'], capture_output=True, text=True, check=True)
    assert not decoded.stderr.strip(), decoded.stderr
    assert 'progress=end' in decoded.stdout
    frames = int(re.findall(r'^frame=(\d+)', decoded.stdout, re.MULTILINE)[-1])
    assert frames == manifest['duration'] * 24, frames
    audio_hashes = []
    for source in [PUBLIC / 'intro.mp4', video]:
        pcm = subprocess.check_output([ffmpeg, '-v', 'error', '-i', str(source), '-map', '0:a:0',
              '-t', str(manifest['duration']), '-f', 's16le', '-ac', '2', '-ar', '48000', 'pipe:1'])
        audio_hashes.append(hashlib.sha256(pcm).hexdigest())
    assert audio_hashes[0] == audio_hashes[1], 'Narration/music changed or was played twice'
    data = video.read_bytes()
    boxes, offset = [], 0
    while offset + 8 <= len(data):
        size = int.from_bytes(data[offset:offset + 4], 'big')
        assert size >= 8
        boxes.append(data[offset + 4:offset + 8])
        offset += size
    assert boxes.index(b'moov') < boxes.index(b'mdat')
    assert (PUBLIC / 'poster-with-guide.webp').stat().st_size > 0
    result = {'frames_decoded': frames, 'duration': manifest['duration'], 'single_audio_track': True,
              'original_decoded_audio_sha256': audio_hashes[0], 'composite_decoded_audio_sha256': audio_hashes[1],
              'main_video_preserved': True, 'fast_start': True, 'source_and_storyboard_match': True}
    WORK.mkdir(parents=True, exist_ok=True)
    (WORK / 'verification.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print('PASS:', frames, 'frames; exact original audio; source hashes; single audio; fast-start.')


if __name__ == '__main__':
    main()
