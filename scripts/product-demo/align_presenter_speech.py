"""CPU composition of a reviewed fixed-head face track and speech-timed hands.

An explicit 0..2 frame face delay is a reviewed timing correction, not an
automatic claim of phoneme accuracy. Neither the narration nor head geometry
is regenerated. Completed candidates are preserved.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

import cv2
import imageio_ffmpeg
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from presenter import digest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-work', type=Path, required=True)
    parser.add_argument('--body-dir', type=Path, required=True)
    parser.add_argument('--work-dir', type=Path, required=True)
    parser.add_argument('--timing-audit', type=Path, required=True)
    parser.add_argument('--face-delay-frames', type=int, choices=range(3), default=1)
    args = parser.parse_args()
    source, body, work = args.source_work, args.body_dir, args.work_dir
    report = json.loads((source / 'render.json').read_text('utf-8'))
    timing = json.loads(args.timing_audit.read_text('utf-8'))
    body_report = json.loads((body / 'report.json').read_text('utf-8'))
    accepted = json.loads((body / 'acceptance.json').read_text('utf-8'))
    if not report['fixed_head_geometry'] or report['face_style'] != 'steady':
        raise ValueError('Only a reviewed fixed-head track can be reused')
    actor_sha = digest(source / 'avatar.mp4')
    if actor_sha != report['video_sha256'] or actor_sha != timing['actor_sha256']:
        raise ValueError('Source actor/timing audit mismatch')
    if not accepted['accepted'] or digest(body / 'gesture.mp4') != accepted['video_sha256']:
        raise ValueError('Reviewed body acceptance required')
    if (body_report['frames'], body_report['fps']) != (report['frames'], report['fps']):
        raise ValueError('Body/face clocks differ')
    stable = body_report['stabilization']
    if stable['speech_inputs_sha256'] != digest(source / 'inputs.json'):
        raise ValueError('Body uses different narration timing')
    if any(c['diagnostic']['offset_frames'] != -args.face_delay_frames or
           c['known200ms_audio_delay_offset_delta'] != -5 for c in timing['cases']):
        raise ValueError('Explicit face delay must agree with all reviewed timing/control cases')
    work.mkdir(parents=True, exist_ok=True)
    destination = work / 'avatar.mp4'
    if destination.exists():
        raise ValueError('Preserve completed candidate')
    cap = cv2.VideoCapture(str(source / 'avatar.mp4'))
    cv2.setNumThreads(1)
    encoder = subprocess.Popen([imageio_ffmpeg.get_ffmpeg_exe(), '-v', 'error', '-n',
        '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-s', '512x768', '-r', '25', '-i', 'pipe:0',
        '-an', '-c:v', 'libx264', '-preset', 'fast', '-crf', '17', '-pix_fmt', 'yuv420p',
        '-movflags', '+faststart', str(destination)], stdin=subprocess.PIPE)
    # The rendered face patch ends at y=280. Feather well below it, entirely
    # inside the pixel-verified fixed upper body (y<360); never overlap hands.
    alpha = np.clip((355 - np.arange(768, dtype=np.float32)) / 30, 0, 1)[:, None, None]
    history = []
    try:
        for index in range(report['frames']):
            ok, face = cap.read()
            if not ok:
                raise ValueError('Face track ended early')
            history.append(face)
            if len(history) > args.face_delay_frames + 1:
                history.pop(0)
            path = body / f'frame-{index:03}.png'
            if digest(path) != accepted['frame_sha256'][index]:
                raise ValueError('Reviewed body frame changed')
            frame = cv2.imread(str(path))
            if hashlib.sha256(frame[:360].tobytes()).hexdigest() != stable['fixed_upper_body_pixel_sha256']:
                raise ValueError('Fixed head geometry changed')
            composite = np.rint(history[0] * alpha + frame * (1 - alpha)).astype(np.uint8)
            encoder.stdin.write(composite.tobytes())
        if cap.read()[0]:
            raise ValueError('Unexpected extra face frames')
    finally:
        cap.release()
        encoder.stdin.close()
        encoder.wait()
    if encoder.returncode:
        raise RuntimeError('Encoder failed')
    report.update(video_sha256=digest(destination), gesture_video_sha256=digest(body / 'gesture.mp4'),
        body_stabilization=stable, gesture_segments=[{'start_seconds': 0, 'duration': report['duration'],
        'clip': body.name, 'video_sha256': digest(body / 'gesture.mp4')}],
        speech_sync={'face_delay_frames': args.face_delay_frames, 'face_delay_ms': args.face_delay_frames * 40,
        'source_actor_sha256': actor_sha, 'before_audit_sha256': digest(args.timing_audit),
        'method': 'Explicit fixed-head face-track delay; narration and body clock unchanged',
        'scope': 'Four manual-crop SyncNet intervals and known-delay control; not phoneme accuracy'})
    (work / 'render.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    shutil.copy2(source / 'inputs.json', work / 'inputs.json')
    print('Finished', destination, flush=True)


if __name__ == '__main__':
    main()
