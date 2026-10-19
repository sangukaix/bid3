"""Build a restrained body track from reviewed short gestures, never long drift.

Before face rendering, registered head/hair/neck/shoulders remain fixed. Lower arms and
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
from presenter import digest, save, speech_gesture_schedule
from stitch_body import blend_motion

ROOT = Path(__file__).resolve().parents[2]


def gesture_positions(frames, count, returning=False):
    """Spread fast hand travel over time instead of prolonging frozen poses."""
    # A bounded pixel-change proxy in the hand/forearm area. It is a timing
    # heuristic, not a naturalness score or a synthetic hand reconstruction.
    crops = [f[430:720, 70:442].astype(np.float32) for f in frames]
    travel = [max(.2, float(np.sqrt(max(0, np.abs(b - a).mean() - .2))))
              for a, b in zip(crops, crops[1:])]
    distance = np.r_[0, np.cumsum(travel)]
    phase = np.linspace(0, 1, count)
    progress = np.sin(np.pi * phase) if returning else phase * phase * (3 - 2 * phase)
    return np.interp(progress * distance[-1], distance, np.arange(len(frames)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work-dir', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path)
    parser.add_argument('--speech-inputs', type=Path)
    args = parser.parse_args()
    work = args.work_dir.resolve()
    output = args.output_dir.resolve() if args.output_dir else work / 'body-calm'
    output.mkdir(parents=True, exist_ok=True)
    if (output / 'gesture.mp4').exists():
        raise ValueError('Preserve completed candidates')
    config = json.loads((ROOT / 'web/features/product-demo/presenter-source.json').read_text('utf-8'))
    portrait = ROOT / config['portrait']
    if digest(portrait) != config['portrait_sha256']:
        raise ValueError('Portrait changed')
    neutral = cv2.resize(cv2.imread(str(portrait)), (512, 768), interpolation=cv2.INTER_AREA)
    cv2.setNumThreads(1)
    flow = cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_MEDIUM)
    clips, sources = {'neutral': [neutral]}, []
    resting_body = neutral
    # The open source leans and develops malformed fingers. Do not use it on
    # the new clock. Two authored variants use the cleaner screen source:
    # a small lift with eased return, and its complete generated lift/return.
    specs = [('open', 'screen', 0, 64), ('screen', 'screen', 0, 192)] if args.speech_inputs else [
        ('open', 'open', 75, 160), ('screen', 'screen', 0, 192)]
    for name, source_name, first, last in specs:
        folder = work / ('body-' + source_name)
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
        if args.speech_inputs:
            # Keep ONE reconstructed body as the resting reference. Mixing
            # that body with the original still photo changes blazer width
            # and hand registration at every transition.
            resting_body = frames[0]
            clips['neutral'] = [resting_body]
        # Only register the already-near-neutral endpoints. Never morph a
        # raised palm to the resting hands across the middle of the gesture.
        transition = 8 if args.speech_inputs else 24
        for index in range(len(frames)):
            weight = min(1, index / transition)
            if not args.speech_inputs or name != 'open':
                weight = min(weight, (len(frames) - 1 - index) / transition)
            weight = weight * weight * (3 - 2 * weight)
            frames[index] = blend_motion(resting_body, frames[index], weight, flow)
        clips[name] = frames
        sources.append({'clip': name, 'source_clip': source_name, 'first': first, 'last': last,
                        'report_sha256': digest(folder / 'report.json')})
    # A calm authored schedule. Reuse is explicit; not90s of unique model generation.
    schedule = [('open', 275), ('screen', 300), ('open', 275), ('screen', 250),
                ('open', 300), ('screen', 275), ('open', 300), ('screen', 275)]
    if args.speech_inputs:
        inputs = json.loads(args.speech_inputs.read_text('utf-8'))
        if inputs['portrait_sha256'] != config['portrait_sha256']:
            raise ValueError('Speech inputs reference a different presenter')
        schedule = speech_gesture_schedule(inputs, minimum_frames=150)
    total = sum(count for _, count in schedule)
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
        for name, count in schedule:
            frames = clips[name]
            segment_start = index
            positions = np.linspace(0, len(frames) - 1, count)
            if args.speech_inputs and name != 'neutral':
                positions = gesture_positions(frames, count, returning=name == 'open')
            hashes.extend(pool.map(compose_one, ((index + n, p, frames) for n, p in enumerate(positions))))
            index += len(positions)
            segments.append({'clip': name, 'start_frame': segment_start, 'frames': count})
            print('Composed', index, '/', total, 'body frames', flush=True)
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
                                'source_clips': sources, 'schedule': segments,
                                'unique_gesture_sources': len({s['report_sha256'] for s in sources}),
                                'speech_aligned': bool(args.speech_inputs),
                                'speech_inputs_sha256': digest(args.speech_inputs) if args.speech_inputs else None,
                                'gesture_anticipation_frames': 3, 'gesture_release_frames': 5,
                                'hand_transition_method': 'clean short lift with eased authored return; complete screen lift/return; no raised-to-neutral morph' if args.speech_inputs else 'legacy neutral morph',
                                'minimum_gesture_frames': 150 if args.speech_inputs else 0,
                                'resting_reference': 'reviewed screen source frame0; original registered upper body' if args.speech_inputs else 'registered portrait',
                                'motion_pacing': 'hand-region pixel-change travel; smooth endpoint speed' if args.speech_inputs else 'legacy linear',
                                'scope': 'Authored reuse, not unique continuous90s model generation'}}
    save(output / 'report.json', report)
    save(output / 'candidate.json', {'accepted': False, 'video_sha256': digest(target), 'frame_sha256': hashes,
                                      'scope': 'Awaiting visual/geometry review'})
    print('Finished', target, flush=True)


if __name__ == '__main__':
    main()
