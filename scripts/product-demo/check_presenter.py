"""Verify published narrator provenance, full decoding and unchanged single audio."""
import hashlib
import argparse
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
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work-dir', type=Path, default=WORK)
    args = parser.parse_args()
    manifest = json.loads((PUBLIC / 'presenter.json').read_text('utf-8'))
    inputs = json.loads((args.work_dir / 'inputs.json').read_text('utf-8'))
    assert manifest['character'] == inputs['character'], 'Published character differs from this render'
    assert manifest['portrait_sha256'] == inputs['portrait_sha256']
    if inputs.get('custom_source'):
        assert digest(ROOT / inputs['custom_source']['portrait']) == manifest['portrait_sha256']
    story_file = ROOT / 'web/features/product-demo/storyboard.json'
    story = json.loads(story_file.read_text('utf-8'))
    video = PUBLIC / 'intro-with-guide.mp4'
    assert manifest['main_video_sha256'] == digest(PUBLIC / 'intro.mp4'), 'Recompose after changing the main video'
    assert manifest['storyboard_sha256'] == digest(story_file), 'Recompose after changing the storyboard'
    assert manifest['video_sha256'] == digest(video)
    assert manifest['duration'] == sum(s['duration'] for s in story['scenes'])
    if manifest.get('continuous_body'):
        render = json.loads((args.work_dir / 'render.json').read_text('utf-8'))
        assert render['continuous_body'] and render['frames'] == manifest['duration'] * 25
        assert render['gesture_duration'] == manifest['duration'], 'No held body gaps in a continuous version'
        assert render['stable_reference_appearance'] and render['silence_mouth_gate']
    assert manifest['storyboard_version'] == story['version']
    if 'captions' in manifest:
        captions = PUBLIC / Path(manifest['captions']).name
        assert digest(captions) == manifest['captions_sha256']
        assert captions.read_text('utf-8').count(' --> ') == sum(
            len(s['narration'].rstrip('.').split('. ')) for s in story['scenes'])
        assert 'position:36.36% size:70%' in captions.read_text('utf-8'), 'Keep captions off the avatar'
        assert digest(PUBLIC / Path(manifest['screen_captions']).name) == manifest['screen_captions_sha256']
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    probe = subprocess.run([ffmpeg, '-hide_banner', '-i', str(video)], capture_output=True, text=True)
    assert len(re.findall(r'Stream #0:\d+.*Audio:', probe.stderr)) == 1, 'Exactly one audio track required'
    assert f"{manifest['width']}x{manifest['height']}" in probe.stderr
    decoded = subprocess.run([ffmpeg, '-v', 'error', '-i', str(video), '-progress', 'pipe:1',
                             '-f', 'null', '-'], capture_output=True, text=True, check=True)
    assert not decoded.stderr.strip(), decoded.stderr
    assert 'progress=end' in decoded.stdout
    frames = int(re.findall(r'^frame=(\d+)', decoded.stdout, re.MULTILINE)[-1])
    assert frames == manifest['duration'] * manifest.get('fps', 24), frames
    audio_hashes = []
    screen = PUBLIC / Path(manifest.get('screen_video', 'intro.mp4')).name
    if 'screen_video_sha256' in manifest:
        assert manifest['screen_video_sha256'] == digest(screen)
    for source in [screen, video]:
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
    assert digest(PUBLIC / 'poster-with-guide.webp') == manifest['poster_sha256']
    result = {'frames_decoded': frames, 'duration': manifest['duration'], 'single_audio_track': True,
              'screen_decoded_audio_sha256': audio_hashes[0], 'composite_decoded_audio_sha256': audio_hashes[1],
              'main_video_preserved': True, 'fast_start': True, 'source_and_storyboard_match': True,
              'continuous_body': manifest.get('continuous_body', False), 'face_style': manifest.get('face_style', 'legacy')}
    args.work_dir.mkdir(parents=True, exist_ok=True)
    (args.work_dir / 'verification.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print('PASS:', frames, 'frames; identical screen/composite narration; source hashes; single audio; fast-start.')


if __name__ == '__main__':
    main()
