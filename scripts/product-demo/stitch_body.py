"""Join reconstructed LTX prefixes with motion-compensated17-frame overlaps.

Keep the raw chunks/frame sequence. Correct only overlapping reconstructions of
the same motion, never insert a held frame, retime speech or loop a gesture.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor

import cv2
import imageio_ffmpeg
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from presenter import digest, save


def blend_motion(a, b, alpha, flow):
    """Interpolate corresponding motion before dissolving, avoiding double edges."""
    if alpha <= 0:
        return a.copy()
    if alpha >= 1:
        return b.copy()
    h, w = a.shape[:2]
    small_a = cv2.resize(cv2.cvtColor(a, cv2.COLOR_BGR2GRAY), (w // 2, h // 2))
    small_b = cv2.resize(cv2.cvtColor(b, cv2.COLOR_BGR2GRAY), (w // 2, h // 2))
    forward = cv2.resize(flow.calc(small_a, small_b, None), (w, h)) * 2
    backward = cv2.resize(flow.calc(small_b, small_a, None), (w, h)) * 2
    yy, xx = np.mgrid[:h, :w].astype(np.float32)
    moving_a = cv2.remap(a, xx - alpha * forward[..., 0], yy - alpha * forward[..., 1],
                        cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT_101)
    moving_b = cv2.remap(b, xx - (1 - alpha) * backward[..., 0], yy - (1 - alpha) * backward[..., 1],
                        cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT_101)
    a_float, b_float = moving_a.astype(np.float32), moving_b.astype(np.float32)
    mixed = a_float * (1 - alpha) + b_float * alpha
    # Flow is ambiguous around disoccluded fingers. Do not dissolve two separate
    # hands into a translucent double hand: retain one motion-warped observation.
    disagreement = np.abs(a_float - b_float).mean(axis=2)
    unreliable = np.clip((disagreement - 12) / 12, 0, 1)
    unreliable = cv2.GaussianBlur(unreliable, (3, 3), .6)[..., None]
    observation = a_float if alpha < .5 else b_float
    mixed = mixed * (1 - unreliable) + observation * unreliable
    return np.rint(mixed).clip(0, 255).astype(np.uint8)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('Preserve earlier joins; choose a new output folder')
    report = json.loads((args.source / 'report.json').read_text('utf-8'))
    if not report['continuous'] or report['frames'] != report['expected_frames']:
        raise ValueError('Complete reviewed-source motion is required before joining')
    args.output.mkdir(parents=True)
    cv2.setNumThreads(1)
    flow = cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_MEDIUM)
    overlap_folder = args.output / 'overlaps'
    overlap_folder.mkdir()
    sequence = []
    joins = []
    for chunk in report['chunks']:
        folder = args.source / f"chunk-{chunk['index']:03}"
        prefix = chunk['prefix_frames']
        paths = [folder / f'frame-{i:03}.png' for i in range(prefix, prefix + chunk['frames_used'])]
        if sequence:
            start = len(sequence) - 17
            for j in range(17):
                a = cv2.imread(str(sequence[start + j]))
                b = cv2.imread(str(paths[j]))
                t = j / 16
                alpha = t * t * (3 - 2 * t)
                joined = blend_motion(a, b, alpha, flow)
                target = overlap_folder / f"join-{chunk['index']:02}-{j:02}.png"
                if not cv2.imwrite(str(target), joined):
                    raise RuntimeError('Could not save joined frame')
                sequence[start + j] = target
            sequence.extend(paths[17:])
            joins.append({'compact_frame': start, 'overlap_frames': 17})
            print('Aligned overlapping generated motion', chunk['index'], flush=True)
        else:
            sequence.extend(paths)
    # Overlapping clips shorten body motion only. Interpolate back onto the exact
    # original clock instead of holding/duplicating frames or retiming speech.
    thread_state = threading.local()

    def write_motion_frame(item):
        index, position = item
        left = int(position)
        if not hasattr(thread_state, 'flow'):
            thread_state.flow = cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_MEDIUM)
        a = cv2.imread(str(sequence[left]))
        b = cv2.imread(str(sequence[min(left + 1, len(sequence) - 1)]))
        frame = blend_motion(a, b, float(position - left), thread_state.flow)
        if not cv2.imwrite(str(args.output / f'frame-{index:03}.png'), frame):
            raise RuntimeError('Could not save interpolated motion')
        return index

    with ThreadPoolExecutor(max_workers=4) as pool:
        positions = enumerate(np.linspace(0, len(sequence) - 1, report['frames']))
        for index in pool.map(write_motion_frame, positions):
            if index % 500 == 0:
                print('Motion clock', index, '/', report['frames'], flush=True)
    video = args.output / 'gesture.mp4'
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), '-v', 'error', '-n', '-framerate', '25',
        '-i', str(args.output / 'frame-%03d.png'), '-frames:v', str(report['frames']), '-an',
        '-c:v', 'libx264', '-preset', 'fast', '-crf', '18', '-pix_fmt', 'yuv420p',
        '-movflags', '+faststart', str(video)], check=True)
    report.update(source_motion_sha256=report['video_sha256'], video_sha256=digest(video),
                  join_method='DIS optical-flow17-frame overlaps with occlusion guard', joins=joins,
                  compact_body_frames=len(sequence), body_tempo_ratio=len(sequence) / report['frames'],
                  body_clock_interpolation=True, audio_retimed=False)
    save(args.output / 'report.json', report)
    print('Joined motion ready for visual review', flush=True)


if __name__ == '__main__':
    main()
