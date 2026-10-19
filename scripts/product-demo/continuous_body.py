"""Continue bounded local LTX clips using17 preceding frames; never hold/loop a body.

Checkpoint each chunk so a short pilot can be reviewed before continuing the90s.
Uses existing pinned runtime/models, never unloads another application's model.
"""
import argparse
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys
from contextlib import redirect_stdout, redirect_stderr

import imageio_ffmpeg
sys.path.insert(0, str(Path(__file__).resolve().parent))
from presenter import ROOT, STORY, digest, save


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--research-root', type=Path, required=True)
    parser.add_argument('--body-python', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--max-new-chunks', type=int, default=100)
    parser.add_argument('--in-process', action='store_true', help='Reuse one pinned GPU runtime across chunks')
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    config_file = ROOT / 'web/features/product-demo/presenter-source.json'
    config = json.loads(config_file.read_text('utf-8'))
    portrait = ROOT / config['portrait']
    if digest(portrait) != config['portrait_sha256']:
        raise ValueError('Registered portrait changed')
    story = json.loads(STORY.read_text('utf-8'))
    total = sum(scene['duration'] for scene in story['scenes']) * 25
    written, index, generated = 0, 0, 0
    chunks = []
    previous = None
    runtime = {}
    if args.in_process and Path(sys.executable).resolve() != args.body_python.resolve():
        raise ValueError('In-process rendering requires the explicitly selected body interpreter')
    while written < total:
        folder = output / f'chunk-{index:03}'
        overlap = 17 if previous else 0
        frames = min(193, max(33, math.ceil((total - written + overlap - 1) / 8) * 8 + 1))
        middle = ROOT / ('web/public/product-demo/presenter/standing-explain.png' if index % 2 == 0
                         else 'web/public/product-demo/presenter/standing-screen.png')
        prompt = ('Locked camera waist-up shot of the same adult Korean woman standing in the same navy blazer '
                  'and ivory blouse in the same bright studio. Continue her preceding natural body movement. '
                  'She explains calmly with small flowing open-palm gestures below her chest, gently shifts '
                  'her shoulders and breathes between points. Hands remain fully visible. She does not stop '
                  'moving or pose for a photograph. Her head stays almost upright and her lips softly together. '
                  'Same face, hair, clothing, room and lighting. No camera motion, no large gestures.')
        prompt_file = output / f'prompt-{index:03}.txt'
        if (folder / 'report.json').exists():
            report = json.loads((folder / 'report.json').read_text('utf-8'))
            if report['source_sha256'] != digest(portrait) or report['middle_image_sha256'] != digest(middle):
                raise ValueError('Cannot reuse a chunk from a different source')
            if report['frames'] != frames or report['seed'] != 107 + index * 13 or report['prompt'] != prompt:
                raise ValueError('Cached chunk conditions changed; choose a separate output folder')
            if digest(folder / 'gesture.mp4') != report['video_sha256']:
                raise ValueError('Cached chunk video changed')
        else:
            if generated >= args.max_new_chunks:
                break
            if folder.exists():
                raise ValueError('Incomplete chunk preserved; inspect before resuming')
            prompt_file.write_text(prompt, encoding='utf-8')
            command = [str(args.body_python), '-I', str(ROOT / 'scripts/product-demo/gesture.py'),
                       '--research-root', str(args.research_root), '--source-image', str(portrait),
                       '--end-image', str(portrait), '--middle-image', str(middle), '--frames', str(frames),
                       '--character', config['character'], '--seed', str(107 + index * 13),
                       '--prompt-file', str(prompt_file), '--output', str(folder)]
            if previous:
                command += ['--prefix-dir', str(previous[0]), '--prefix-start', str(previous[1] - 17)]
            print('Generating continuation chunk', index, 'at frame', written, flush=True)
            with (output / f'chunk-{index:03}.log').open('w') as log:
                if args.in_process:
                    from gesture import main as render_motion
                    with redirect_stdout(log), redirect_stderr(log):
                        render_motion(command[3:], runtime)
                else:
                    subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True)
            report = json.loads((folder / 'report.json').read_text('utf-8'))
            generated += 1
        paths = [folder / f'frame-{i:03}.png' for i in range(report['frames'])]
        if [digest(path) for path in paths] != report['frame_sha256']:
            raise ValueError('Cached chunk frames changed')
        expected_prefix = [] if not previous else [digest(previous[0] / f'frame-{i:03}.png')
            for i in range(previous[1] - 17, previous[1])]
        if report['prefix_sha256'] != expected_prefix:
            raise ValueError('Continuation no longer matches preceding motion')
        count = min(report['frames'] - overlap, total - written)
        for local in range(count):
            source = paths[overlap + local]
            target = output / f'frame-{written + local:03}.png'
            if target.exists() and digest(target) != digest(source):
                raise ValueError('Preserve an earlier output rather than overwrite changed motion')
            if not target.exists():
                shutil.copyfile(source, target)
        chunks.append({'index': index, 'start_frame': written, 'frames_used': count,
                       'prefix_frames': overlap, 'video_sha256': report['video_sha256']})
        previous = (folder, report['frames'])
        written += count
        index += 1
    video = output / f'motion-{written:04}.mp4'
    if not video.exists():
        subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), '-v', 'error', '-n', '-framerate', '25',
            '-i', str(output / 'frame-%03d.png'), '-frames:v', str(written), '-an', '-c:v', 'libx264',
            '-crf', '18', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(video)], check=True)
    shutil.copyfile(video, output / 'gesture.mp4')
    save(output / 'report.json', {'continuous': True, 'frames': written, 'expected_frames': total,
        'fps': 25, 'duration': written / 25, 'source_sha256': digest(portrait),
        'end_image_sha256': digest(portrait), 'video_sha256': digest(video), 'chunks': chunks,
        'cloud_calls': 0, 'accepted': False, 'status': 'candidate-needs-continuity-and-identity-review'})
    print('Ready for review:', written, '/', total, 'unique generated body frames', flush=True)


if __name__ == '__main__':
    main()
