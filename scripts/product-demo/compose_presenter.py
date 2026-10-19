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
    captions.write_text('\n'.join(line + ' position:36.36% size:70%' if ' --> ' in line else line
                                 for line in cues.split('\n')), encoding='utf-8')
    # Replace only audio/captions in the screen-only companion. Keep the base intact.
    subprocess.run([ffmpeg, '-v', 'error', '-y', '-i', str(PUBLIC / 'intro.mp4'), '-i', str(mix),
        '-i', str(screen_captions), '-map', '0:v:0', '-map', '1:a:0', '-map', '2:s:0',
        '-c:v', 'copy', '-c:a', 'aac', '-b:a', '160k', '-c:s', 'mov_text',
        '-metadata:s:s:0', 'language=kor', '-disposition:s:0', 'default', '-movflags', '+faststart',
        '-t', str(sum(s['duration'] for s in story['scenes'])), str(screen)], check=True)
    subprocess.run([ffmpeg, '-v', 'error', '-y', '-i', str(screen), '-i', str(avatar),
        # Preserve every25fps avatar frame; only the original24fps screen is resampled.
        '-filter_complex', '[0:v]fps=25,tpad=stop_mode=clone:stop_duration=0.04,setsar=1[screen];'
        '[1:v]scale=720:1080,setsar=1[face];[screen][face]hstack=inputs=2:shortest=1[v]',
        '-map', '[v]', '-map', '0:a:0', '-map', '0:s?', '-c:v', 'libx264', '-preset', 'fast',
        '-crf', '20', '-pix_fmt', 'yuv420p', '-c:a', 'copy', '-c:s', 'copy', '-movflags', '+faststart',
        '-t', str(render['duration']), str(temporary)], check=True)
    subprocess.run([ffmpeg, '-v', 'error', '-i', str(temporary), '-f', 'null', '-'], check=True)
    temporary.replace(destination)
    poster = WORK / 'preview-with-guide.webp' if args.preview else PUBLIC / 'poster-with-guide.webp'
    subprocess.run([ffmpeg, '-v', 'error', '-y', '-ss', '6', '-i', str(destination),
                    '-frames:v', '1', str(poster)], check=True)
    if not args.preview:
        version = hashlib.sha256((digest(destination) + digest(captions) + digest(screen_captions) + digest(poster)).encode()).hexdigest()[:12]
        reused_gestures = (render.get('body_stabilization') or {}).get('unique_gesture_sources')
        motion_scope = ('Offline authored reuse of reviewed short gestures and optical-flow interpolation; not live or unique90s body generation'
                        if reused_gestures else 'Offline chained body generation with17-frame continuation; not a live avatar'
                        if render.get('continuous_body') else 'Offline generated face motion; scheduled gestures, resting between segments')
        report = {'version': version, 'storyboard_version': story['version'], 'character': inputs['character'],
            'video': '/product-demo/intro-with-guide.mp4', 'poster': '/product-demo/poster-with-guide.webp',
            'poster_sha256': digest(poster),
            'screen_video': '/product-demo/intro-screen.mp4', 'screen_video_sha256': digest(screen),
            'captions': '/product-demo/captions-with-guide.ko.vtt',
            'captions_sha256': digest(captions),
            'screen_captions': '/product-demo/captions-screen.ko.vtt', 'screen_captions_sha256': digest(screen_captions),
            'width': 2640, 'height': 1080, 'fps': 25, 'duration': render['duration'],
            'main_video_sha256': digest(PUBLIC / 'intro.mp4'), 'storyboard_sha256': digest(STORY),
            'avatar_sha256': digest(avatar), 'video_sha256': digest(destination),
            'portrait_sha256': inputs['portrait_sha256'], 'narration': inputs['audio'],
            'single_audio_track': True, 'voice': inputs.get('voice'), 'cloud_inference_calls': 0,
            'cloud_inference_scope': 'Offline motion, voice and composition; excludes source/background image authoring',
            'gesture_duration': render.get('gesture_duration', 0),
            'gesture_segments': render.get('gesture_segments', []),
            'continuous_body': render.get('continuous_body', False),
            'body_join_method': render.get('body_join_method'), 'body_tempo_ratio': render.get('body_tempo_ratio', 1),
            'face_style': render.get('face_style', 'legacy'),
            'fixed_head_geometry': render.get('fixed_head_geometry', False),
            'body_stabilization': render.get('body_stabilization'),
            'stable_reference_appearance': render.get('stable_reference_appearance', False),
            'lip_gain': render.get('lip_gain', 1), 'silence_mouth_gate': render.get('silence_mouth_gate', False),
            'eye_control': render.get('eye_control', 'legacy'),
            'background': render.get('background'),
            'source_image_generation': (inputs.get('custom_source') or {}).get('origin', 'legacy fictional portrait'),
            'limitations': [motion_scope,
                            'Korean articulation and naturalness require human review',
                            'Reference-based synthetic presenter; not footage or speech of the reference person']}
        (PUBLIC / 'presenter.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('Composed', destination, f'{destination.stat().st_size / 1048576:.1f} MiB', flush=True)


if __name__ == '__main__':
    main()
