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
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
PUBLIC = ROOT / 'web/public/product-demo'
WORK = ROOT / '.local/product-demo/presenter'
STORY = ROOT / 'web/features/product-demo/storyboard.json'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--preview', action='store_true')
    args = parser.parse_args()
    story = json.loads(STORY.read_text('utf-8'))
    inputs = json.loads((WORK / 'inputs.json').read_text('utf-8'))
    recorded = [(s['id'], s['duration']) for s in inputs['scenes']]
    if recorded != [(s['id'], s['duration']) for s in story['scenes']]:
        raise ValueError('Timeline changed; regenerate the narrator')
    for scene in inputs['scenes']:
        audio = ROOT / '.local/product-demo/narration' / (scene['id'] + '.wav')
        if digest(audio) != scene['narration_sha256']:
            raise ValueError('Narration changed; regenerate the narrator')
    avatar = WORK / ('avatar-preview.mp4' if args.preview else 'avatar.mp4')
    render = json.loads((WORK / ('preview.json' if args.preview else 'render.json')).read_text('utf-8'))
    if digest(avatar) != render['video_sha256']:
        raise ValueError('Avatar track hash mismatch')
    panel = Image.new('RGB', (640, 1080), '#eeeae3')
    draw = ImageDraw.Draw(panel)
    fonts = Path('C:/Windows/Fonts')
    normal = lambda size: ImageFont.truetype(str(fonts / 'malgun.ttf'), size)
    bold = lambda size: ImageFont.truetype(str(fonts / 'malgunbd.ttf'), size)
    draw.rectangle((0, 0, 3, 1080), fill='#8ee0c7')
    draw.rounded_rectangle((48, 51, 303, 101), radius=25, fill='#d2e5dc')
    draw.text((72, 61), 'AI BID · GUIDE', font=bold(22), fill='#255148')
    draw.text((48, 122), '함께 살펴볼까요?', font=bold(36), fill='#18312f')
    draw.line((48, 911, 592, 911), fill='#c9c8bd', width=2)
    draw.text((48, 940), 'Alex', font=bold(37), fill='#18312f')
    draw.text((48, 999), 'AI 캐릭터 · 한국어 서비스 안내', font=normal(23), fill='#566962')
    panel.save(WORK / 'panel.png')
    destination = WORK / 'preview-with-guide.mp4' if args.preview else PUBLIC / 'intro-with-guide.mp4'
    temporary = destination.with_suffix('.building.mp4')
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    subprocess.run([ffmpeg, '-v', 'error', '-y', '-i', str(PUBLIC / 'intro.mp4'), '-loop', '1',
        '-framerate', '24', '-i', str(WORK / 'panel.png'), '-i', str(avatar),
        # Cover the 25→24fps endpoint rounding; final -t keeps the exact timeline.
        '-filter_complex', '[2:v]scale=544:680,fps=24,tpad=stop_mode=clone:stop_duration=0.1,setsar=1[face];'
        '[1:v][face]overlay=48:194:shortest=1[panel];[0:v][panel]hstack=inputs=2:shortest=1[v]',
        '-map', '[v]', '-map', '0:a:0', '-map', '0:s?', '-c:v', 'libx264', '-preset', 'fast',
        '-crf', '20', '-pix_fmt', 'yuv420p', '-c:a', 'copy', '-c:s', 'copy', '-movflags', '+faststart',
        '-t', str(render['duration']), str(temporary)], check=True)
    subprocess.run([ffmpeg, '-v', 'error', '-i', str(temporary), '-f', 'null', '-'], check=True)
    temporary.replace(destination)
    poster = WORK / 'preview-with-guide.webp' if args.preview else PUBLIC / 'poster-with-guide.webp'
    subprocess.run([ffmpeg, '-v', 'error', '-y', '-ss', '2.5', '-i', str(destination),
                    '-frames:v', '1', str(poster)], check=True)
    if not args.preview:
        report = {'version': digest(destination)[:12], 'storyboard_version': story['version'], 'character': 'Alex',
            'video': '/product-demo/intro-with-guide.mp4', 'poster': '/product-demo/poster-with-guide.webp',
            'width': 2560, 'height': 1080, 'duration': render['duration'],
            'main_video_sha256': digest(PUBLIC / 'intro.mp4'), 'storyboard_sha256': digest(STORY),
            'avatar_sha256': digest(avatar), 'video_sha256': digest(destination),
            'portrait_sha256': inputs['portrait_sha256'], 'narration': inputs['audio'],
            'single_original_audio': True, 'cloud_calls': 0,
            'limitations': ['Offline generated face motion; static shoulders; no hand gestures',
                            'Korean articulation and naturalness require human review',
                            'Original fictional character; model chain not commercially cleared by this demo']}
        (PUBLIC / 'presenter.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('Composed', destination, f'{destination.stat().st_size / 1048576:.1f} MiB', flush=True)


if __name__ == '__main__':
    main()
