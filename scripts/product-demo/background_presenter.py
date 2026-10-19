"""Replace only the offline presenter's room using recurrent CPU video matting.

No model downloads, GPU use, speech synthesis, face generation or app dependency
changes. Download the official RVM v1.0.0 FP32 TorchScript separately (see docs).
Run in the isolated authoring runtime with torch, OpenCV and imageio-ffmpeg.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import time

import cv2
import imageio_ffmpeg
import numpy as np
import torch

MODEL_SHA256 = 'f01e0c9338b9a6a31b881ea6d4360d70c1e549701b3792e14c9ed88d6196c5a1'
ROOT = Path(__file__).resolve().parents[2]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-work', type=Path, required=True)
    parser.add_argument('--work-dir', type=Path, required=True)
    parser.add_argument('--background', type=Path, required=True)
    parser.add_argument('--checkpoint', type=Path, required=True)
    parser.add_argument('--max-frames', type=int, help='Private pilot only; never replaces the full track')
    args = parser.parse_args()
    source, work = args.source_work.resolve(), args.work_dir.resolve()
    if source == work or args.max_frames is not None and args.max_frames <= 0:
        raise ValueError('Use a separate work folder and a positive pilot frame count')
    report = json.loads((source / 'render.json').read_text('utf-8'))
    actor = source / 'avatar.mp4'
    if digest(actor) != report['video_sha256']:
        raise ValueError('Source actor does not match the reviewed render')
    if digest(args.checkpoint) != MODEL_SHA256:
        raise ValueError('Expected the pinned official RVM v1.0.0 FP32 MobileNetv3 checkpoint')
    background = cv2.imread(str(args.background))
    if background is None:
        raise ValueError('Cannot decode the background plate')
    cap = cv2.VideoCapture(str(actor))
    width, height = (int(cap.get(p)) for p in [cv2.CAP_PROP_FRAME_WIDTH, cv2.CAP_PROP_FRAME_HEIGHT])
    fps = cap.get(cv2.CAP_PROP_FPS)
    frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if frames != report['frames'] or fps != report['fps']:
        raise ValueError('Source video clock differs from its render report')
    target = min(frames, args.max_frames) if args.max_frames else frames
    work.mkdir(parents=True, exist_ok=True)
    samples = work / ('pilot-samples' if args.max_frames else 'samples')
    samples.mkdir(exist_ok=True)
    destination = work / ('avatar-preview.mp4' if args.max_frames else 'avatar.mp4')
    temporary = destination.with_suffix('.building.mp4')
    # Preserve the approved 2:3 framing; never crop the face, elbows or fingers.
    background = cv2.cvtColor(cv2.resize(background, (width, height), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2RGB)
    bg = background.astype(np.float32) / 255
    torch.set_num_threads(4)
    cv2.setNumThreads(1)
    started = time.perf_counter()
    model = torch.jit.freeze(torch.jit.load(str(args.checkpoint), map_location='cpu').eval())
    rec = [None] * 4
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    encoder = subprocess.Popen([ffmpeg, '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24',
        '-s', f'{width}x{height}', '-r', str(fps), '-i', 'pipe:0', '-an', '-c:v', 'libx264',
        '-preset', 'fast', '-crf', '17', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(temporary)],
        stdin=subprocess.PIPE)
    reviewed = []
    try:
        with torch.inference_mode():
            for index in range(target):
                ok, frame = cap.read()
                if not ok:
                    raise ValueError(f'Actor ended early at frame {index}')
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                src = torch.from_numpy(rgb).permute(2, 0, 1).unsqueeze(0).float().div_(255)
                # Recycle states for the ENTIRE clip, including across gesture joins.
                fgr, pha, *rec = model(src, *rec, 0.5)
                alpha = pha[0].permute(1, 2, 0).numpy()
                foreground = fgr[0].permute(1, 2, 0).numpy()
                # Keep the actual source pixels in opaque face/clothing interiors.
                opaque = alpha >= .995
                alpha = np.where(opaque, 1, alpha)
                foreground = np.where(opaque, rgb.astype(np.float32) / 255, foreground)
                composite = np.rint((foreground * alpha + bg * (1 - alpha)) * 255).clip(0, 255).astype(np.uint8)
                encoder.stdin.write(composite.tobytes())
                if index % 250 == 0 or index in [25, 50, 86, 90, 94, 150, 190, 192, 193, 195, target - 1]:
                    cv2.imwrite(str(samples / f'frame-{index:04}.jpg'), cv2.cvtColor(composite, cv2.COLOR_RGB2BGR))
                    cv2.imwrite(str(samples / f'alpha-{index:04}.png'), np.rint(alpha * 255).astype(np.uint8))
                    reviewed.append(index)
                if (index + 1) % 250 == 0:
                    print(f'{index + 1}/{target} frames; {time.perf_counter() - started:.1f}s; CPU only', flush=True)
    finally:
        cap.release()
        encoder.stdin.close()
        encoder.wait()
    if encoder.returncode:
        raise RuntimeError(f'Video encoder failed: {encoder.returncode}')
    subprocess.run([ffmpeg, '-v', 'error', '-i', str(temporary), '-f', 'null', '-'], check=True)
    temporary.replace(destination)
    background_report = {
        'plate': args.background.resolve().relative_to(ROOT).as_posix(),
        'plate_sha256': digest(args.background),
        'origin': 'Built-in image_gen generated selected empty background plate; no reference person in plate',
        'method': 'RVM MobileNetv3 recurrent video matting; CPU; opaque source pixels retained',
        'model_repository': 'https://github.com/PeterL1n/RobustVideoMatting',
        'model_release': 'v1.0.0', 'model_license': 'GPL-3.0',
        'model_sha256': MODEL_SHA256, 'downsample_ratio': 0.5,
        'source_actor_sha256': digest(actor), 'gpu_used': False,
        'sample_frames': reviewed, 'seconds': round(time.perf_counter() - started, 3),
        'scope': 'Background replacement only. Hair/finger edge quality requires visual review.'}
    report.update(video_sha256=digest(destination), frames=target, duration=target / fps,
                  background=background_report)
    save(work / ('preview.json' if args.max_frames else 'render.json'), report)
    shutil.copy2(source / 'inputs.json', work / 'inputs.json')
    print(f'Finished {destination}; {target} frames', flush=True)


if __name__ == '__main__':
    main()
