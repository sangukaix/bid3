"""Compose a silent narrator beside the unchanged walkthrough; keep ONE audio.

CPU-only. After screenshot/design changes, rebuild the main video and run this
again. Narration/timing changes also require regenerating presenter.py's track.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

import imageio_ffmpeg
from render import build_audio, caption_text

ROOT = Path(__file__).resolve().parents[2]
PUBLIC = ROOT / 'web/public/product-demo'
WORK = ROOT / '.local/product-demo/presenter'
STORY = ROOT / 'web/features/product-demo/storyboard.json'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    global WORK
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--preview', action='store_true')
    parser.add_argument('--work-dir', type=Path, default=WORK)
    args = parser.parse_args()
    WORK = args.work_dir.resolve()
    story = json.loads(STORY.read_text('utf-8'))
    inputs = json.loads((WORK / 'inputs.json').read_text('utf-8'))
    recorded = [(s['id'], s['duration']) for s in inputs['scenes']]
    if recorded != [(s['id'], s['duration']) for s in story['scenes']]:
        raise ValueError('Timeline changed; regenerate the narrator')
    narration = Path(inputs.get('narration_dir', ROOT / '.local/product-demo/narration'))
    for scene in inputs['scenes']:
        audio = narration / (scene['id'] + '.wav')
        if digest(audio) != scene['narration_sha256']:
            raise ValueError('Narration changed; regenerate the narrator')
    avatar = WORK / ('avatar-preview.mp4' if args.preview else 'avatar.mp4')
    render = json.loads((WORK / ('preview.json' if args.preview else 'render.json')).read_text('utf-8'))
    if digest(avatar) != render['video_sha256']:
        raise ValueError('Avatar track hash mismatch')
    destination = WORK / 'preview-with-guide.mp4' if args.preview else PUBLIC / 'intro-with-guide.mp4'
    temporary = destination.with_suffix('.building.mp4')
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    screen = PUBLIC / 'intro-screen.mp4'
    mix = WORK / 'narration-mix.wav'
    build_audio(story, narration, mix, False)
    captions = PUBLIC / 'captions-with-guide.ko.vtt'
    screen_captions = PUBLIC / 'captions-screen.ko.vtt'
    cues = caption_text(story, narration)
    screen_captions.write_text(cues, encoding='utf-8')
    # Keep browser captions over the walkthrough, leaving the character unobstructed.
    captions.write_text('\n'.join(line + ' position:37.5% size:72%' if ' --> ' in line else line
                                 for line in cues.split('\n')), encoding='utf-8')
    # Replace only audio/captions in the screen-only companion. Keep the base intact.
    subprocess.run([ffmpeg, '-v', 'error', '-y', '-i', str(PUBLIC / 'intro.mp4'), '-i', str(mix),
        '-i', str(screen_captions), '-map', '0:v:0', '-map', '1:a:0', '-map', '2:s:0',
        '-c:v', 'copy', '-c:a', 'aac', '-b:a', '160k', '-c:s', 'mov_text',
        '-metadata:s:s:0', 'language=kor', '-disposition:s:0', 'default', '-movflags', '+faststart',
        '-t', str(sum(s['duration'] for s in story['scenes'])), str(screen)], check=True)
    subprocess.run([ffmpeg, '-v', 'error', '-y', '-i', str(screen), '-i', str(avatar),
        # Cover the 25→24fps endpoint rounding; final -t keeps the exact timeline.
        '-filter_complex', '[1:v]scale=640:1080:force_original_aspect_ratio=increase,crop=640:1080,'
        'fps=24,tpad=stop_mode=clone:stop_duration=0.1,setsar=1[face];[0:v][face]hstack=inputs=2:shortest=1[v]',
        '-map', '[v]', '-map', '0:a:0', '-map', '0:s?', '-c:v', 'libx264', '-preset', 'fast',
        '-crf', '20', '-pix_fmt', 'yuv420p', '-c:a', 'copy', '-c:s', 'copy', '-movflags', '+faststart',
        '-t', str(render['duration']), str(temporary)], check=True)
    subprocess.run([ffmpeg, '-v', 'error', '-i', str(temporary), '-f', 'null', '-'], check=True)
    temporary.replace(destination)
    poster = WORK / 'preview-with-guide.webp' if args.preview else PUBLIC / 'poster-with-guide.webp'
    subprocess.run([ffmpeg, '-v', 'error', '-y', '-ss', '2.5', '-i', str(destination),
                    '-frames:v', '1', str(poster)], check=True)
    if not args.preview:
        version = hashlib.sha256((digest(destination) + digest(captions) + digest(screen_captions)).encode()).hexdigest()[:12]
        report = {'version': version, 'storyboard_version': story['version'], 'character': inputs['character'],
            'video': '/product-demo/intro-with-guide.mp4', 'poster': '/product-demo/poster-with-guide.webp',
            'screen_video': '/product-demo/intro-screen.mp4', 'screen_video_sha256': digest(screen),
            'captions': '/product-demo/captions-with-guide.ko.vtt',
            'captions_sha256': digest(captions),
            'screen_captions': '/product-demo/captions-screen.ko.vtt', 'screen_captions_sha256': digest(screen_captions),
            'width': 2560, 'height': 1080, 'duration': render['duration'],
            'main_video_sha256': digest(PUBLIC / 'intro.mp4'), 'storyboard_sha256': digest(STORY),
            'avatar_sha256': digest(avatar), 'video_sha256': digest(destination),
            'portrait_sha256': inputs['portrait_sha256'], 'narration': inputs['audio'],
            'single_audio_track': True, 'voice': inputs.get('voice'), 'cloud_inference_calls': 0,
            'gesture_duration': render.get('gesture_duration', 0),
            'source_image_generation': 'built-in image_gen; original fictional Zoe identity reference',
            'limitations': ['Offline generated face motion; one bounded greeting gesture, then resting posture',
                            'Korean articulation and naturalness require human review',
                            'Original fictional character; model chain not commercially cleared by this demo']}
        (PUBLIC / 'presenter.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('Composed', destination, f'{destination.stat().st_size / 1048576:.1f} MiB', flush=True)


if __name__ == '__main__':
    main()
