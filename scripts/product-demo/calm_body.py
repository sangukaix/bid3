"""Build a restrained body track from reviewed short gestures, never long drift.

The registered head/hair/neck/shoulders remain fixed. Only the lower arms and
hands use stabilized local gesture frames, with optical-flow transitions and
subpixel breathing below the chest. This deliberately reuses two short clips.
"""
import argparse
import hashlib
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
from stitch_body import blend_motion

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work-dir', type=Path, required=True)
    args = parser.parse_args()
    work = args.work_dir.resolve()
    output = work / 'body-calm'
    output.mkdir(exist_ok=True)
    if (output / 'gesture.mp4').exists():
        raise ValueError('Preserve completed candidates')
    config = json.loads((ROOT / 'web/features/product-demo/presenter-source.json').read_text('utf-8'))
    portrait = ROOT / config['portrait']
    if digest(portrait) != config['portrait_sha256']:
        raise ValueError('Portrait changed')
    neutral = cv2.resize(cv2.imread(str(portrait)), (512, 768), interpolation=cv2.INTER_AREA)
    cv2.setNumThreads(1)
    flow = cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_MEDIUM)
    clips, sources = {}, []
    # Exclude the first source's large torso lean; use only its upright palm gesture.
    for name, first, last in [('open', 75, 160), ('screen', 0, 192)]:
        folder = work / ('body-' + name)
        report = json.loads((folder / 'report.json').read_text('utf-8'))
        accepted = json.loads((folder / 'acceptance.json').read_text('utf-8'))
        if not accepted['accepted'] or accepted['video_sha256'] != digest(folder / 'gesture.mp4'):
            raise ValueError('Visual acceptance of stabilized input required')
        if report['source_sha256'] != config['portrait_sha256']:
            raise ValueError('Wrong gesture identity')
        frames = []
        for index in range(first, last + 1):
            p = folder / f'frame-{index:03}.png'
            if digest(p) != accepted['frame_sha256'][index]:
                raise ValueError('Reviewed input changed')
            frames.append(cv2.imread(str(p)))
        # Return each bounded gesture to the EXACT registered neutral at both ends.
        for index in range(len(frames)):
            weight = min(1, index / 24, (len(frames) - 1 - index) / 24)
            weight = weight * weight * (3 - 2 * weight)
            frames[index] = blend_motion(neutral, frames[index], weight, flow)
        clips[name] = frames
        sources.append({'clip': name, 'first': first, 'last': last, 'report_sha256': digest(folder / 'report.json')})
    # A calm authored schedule. Reuse is explicit; not90s of unique model generation.
    schedule = [('open', 11), ('screen', 12), ('open', 11), ('screen', 10),
                ('open', 12), ('screen', 11), ('open', 12), ('screen', 11)]
    y, x = np.mgrid[:768, :512].astype(np.float32)
    lower = np.clip((y - 360) / 70, 0, 1)
    lower = lower * lower * (3 - 2 * lower)
    index, hashes, segments = 0, [], []
    local = threading.local()
    upper_hash = hashlib.sha256(neutral[:360].tobytes()).hexdigest()

    def compose_one(item):
        frame_index, position, frames = item
        if not hasattr(local, 'flow'):
            local.flow = cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_MEDIUM)
        a = int(position)
        b = min(a + 1, len(frames) - 1)
        frame = blend_motion(frames[a], frames[b], float(position - a), local.flow)
        # At/above chest height preserve the source head, hair and shoulders.
        frame = np.rint(neutral * (1 - lower[..., None]) + frame * lower[..., None]).astype(np.uint8)
        breath = .6 * np.sin(2 * np.pi * frame_index / (25 * 5.7))
        frame = cv2.remap(frame, x, (y + breath * lower).astype(np.float32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        if hashlib.sha256(frame[:360].tobytes()).hexdigest() != upper_hash:
            raise ValueError('Registered head/hair/shoulders must remain pixel-identical before face animation')
        path = output / f'frame-{frame_index:03}.png'
        cv2.imwrite(str(path), frame)
        return digest(path)

    with ThreadPoolExecutor(max_workers=4) as pool:
        for name, seconds in schedule:
            frames = clips[name]
            segment_start = index
            positions = np.linspace(0, len(frames) - 1, seconds * 25)
            hashes.extend(pool.map(compose_one, ((index + n, p, frames) for n, p in enumerate(positions))))
            index += len(positions)
            segments.append({'clip': name, 'start_frame': segment_start, 'frames': seconds * 25})
            print('Composed', index, '/2250 body frames', flush=True)
    target = output / 'gesture.mp4'
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), '-v', 'error', '-n', '-framerate', '25',
        '-i', str(output / 'frame-%03d.png'), '-an', '-c:v', 'libx264', '-crf', '19', '-pix_fmt', 'yuv420p',
        '-movflags', '+faststart', str(target)], check=True)
    report = {'frames': index, 'fps': 25, 'duration': index / 25, 'continuous': True,
              'source_sha256': config['portrait_sha256'], 'end_image_sha256': config['portrait_sha256'],
              'video_sha256': digest(target), 'join_method': 'fixed upper body; bounded reused gestures; DIS motion interpolation',
              'stabilization': {'method': 'Fixed registered head/hair/neck/shoulders; lower-arm gestures only',
                                'fixed_above_y_px': 360, 'transition_ends_y_px': 430, 'breathing_max_px': .6,
                                'fixed_upper_body_pixel_sha256': upper_hash, 'fixed_upper_body_verified_frames': index,
                                'source_clips': sources, 'schedule': segments, 'unique_gesture_sources': 2,
                                'scope': 'Authored reuse, not unique continuous90s model generation'}}
    save(output / 'report.json', report)
    save(output / 'candidate.json', {'accepted': False, 'video_sha256': digest(target), 'frame_sha256': hashes,
                                      'scope': 'Awaiting visual/geometry review'})
    print('Finished', target, flush=True)


if __name__ == '__main__':
    main()
