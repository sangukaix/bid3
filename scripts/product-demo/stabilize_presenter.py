"""Measure and stabilize a standing presenter's camera geometry, offline on CPU.

Use the existing pinned MediaPipe CPU authoring environment, never the web/API
runtime. Keep the original clips and cache landmark estimates before rendering.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import numpy as np

MODEL_SHA = '64184e229b263107bc2b804c6625db1341ff2bb731874b0bcc2fe6544e0bc9ff'
ROOT = Path(__file__).resolve().parents[2]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')


def eye_geometry(points):
    left = points[..., [33, 133], :].mean(axis=-2)
    right = points[..., [362, 263], :].mean(axis=-2)
    return (left + right) / 2, right - left


def camera_transforms(points, reference):
    """Invert generated camera scale/roll/translation; retain hand/body motion."""
    centers, vectors = eye_geometry(points)
    target, axis = eye_geometry(reference)
    # Symmetric five-frame smoothing suppresses detector noise without a phase lag.
    kernel = np.array([1, 2, 3, 2, 1], np.float32) / 9
    smooth = lambda a: np.stack([np.convolve(np.pad(a[:, i], (2, 2), mode='reflect', reflect_type='odd'), kernel, 'valid') for i in range(2)], axis=1)
    centers, vectors = smooth(centers), smooth(vectors)
    scales = np.linalg.norm(axis) / np.linalg.norm(vectors, axis=1)
    angles = np.arctan2(axis[1], axis[0]) - np.arctan2(vectors[:, 1], vectors[:, 0])
    if not np.isfinite(scales).all() or np.any((scales < .8) | (scales > 1.25)) or np.any(np.abs(angles) > .2):
        raise ValueError('Camera deviation exceeds bounded stabilization; review rather than crop blindly')
    c, s = np.cos(angles) * scales, np.sin(angles) * scales
    linear = np.stack([c, -s, s, c], axis=1).reshape(-1, 2, 2)
    translation = target - np.einsum('nij,nj->ni', linear, centers)
    return np.concatenate([linear, translation[..., None]], axis=2).astype(np.float32)


def summary(points):
    centers, vectors = eye_geometry(points)
    span = np.linalg.norm(vectors, axis=1)
    return {'frames': len(points), 'eye_span_px_min': float(span.min()), 'eye_span_px_max': float(span.max()),
            'eye_span_p95_over_p05': float(np.quantile(span, .95) / np.quantile(span, .05)),
            'eye_center_x_peak_to_peak_px': float(np.ptp(centers[:, 0])),
            'eye_center_y_peak_to_peak_px': float(np.ptp(centers[:, 1]))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=['measure', 'stabilize'])
    parser.add_argument('--research-root', type=Path, required=True)
    inputs = parser.add_mutually_exclusive_group(required=True)
    inputs.add_argument('--video', type=Path)
    inputs.add_argument('--body-dir', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    sys.path.insert(0, str(args.research_root / 'face-landmark-deps-cp310'))
    import cv2
    cv2.setNumThreads(2)
    config = json.loads((ROOT / 'web/features/product-demo/presenter-source.json').read_text('utf-8'))
    portrait = ROOT / config['portrait']
    if digest(portrait) != config['portrait_sha256']:
        raise ValueError('Registered source portrait changed')
    video = args.body_dir / 'gesture.mp4' if args.body_dir else args.video
    cap = cv2.VideoCapture(str(video))
    width, height = (int(cap.get(p)) for p in [cv2.CAP_PROP_FRAME_WIDTH, cv2.CAP_PROP_FRAME_HEIGHT])
    frames, fps = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)), cap.get(cv2.CAP_PROP_FPS)
    if (width, height) != (512, 768) or fps != 25:
        raise ValueError('Expected the reviewed 512x768/25fps actor/body')
    args.output.mkdir(parents=True, exist_ok=True)
    records = args.output / 'landmarks.npy'
    metadata = {'source_video_sha256': digest(video), 'portrait_sha256': config['portrait_sha256'],
                'frames': frames, 'fps': fps, 'model_sha256': MODEL_SHA, 'cpu_only': True,
                'input': 'original PNG body frames' if args.body_dir else 'decoded video',
                'scope': 'Estimated face geometry, not human naturalness or phoneme ground truth'}
    if args.stage == 'measure':
        if records.exists():
            raise ValueError('Keep existing measurements; use a new output folder')
        import mediapipe as mp
        model = args.research_root / 'models/face-landmark/face_landmarker.task'
        if digest(model) != MODEL_SHA:
            raise ValueError('Pinned existing CPU face landmark model required')
        options = mp.tasks.vision.FaceLandmarkerOptions
        base = mp.tasks.BaseOptions(model_asset_path=str(model), delegate=mp.tasks.BaseOptions.Delegate.CPU)
        def extract(result):
            if len(result.face_landmarks) != 1:
                raise ValueError('Exactly one tracked face required; do not conceal missing detections')
            p = np.array([[p.x * width, p.y * height] for p in result.face_landmarks[0]], np.float32)
            if not np.isfinite(p).all():
                raise ValueError('Non-finite landmarks')
            return p
        with mp.tasks.vision.FaceLandmarker.create_from_options(options(base_options=base, num_faces=1)) as detector:
            image = cv2.cvtColor(cv2.resize(cv2.imread(str(portrait)), (width, height)), cv2.COLOR_BGR2RGB)
            reference = extract(detector.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=image)))
        points, redetected = [], []
        with mp.tasks.vision.FaceLandmarker.create_from_options(options(base_options=base, num_faces=1,
                running_mode=mp.tasks.vision.RunningMode.VIDEO)) as detector, \
                mp.tasks.vision.FaceLandmarker.create_from_options(options(base_options=base, num_faces=1)) as fallback:
            for index in range(frames):
                frame = cv2.imread(str(args.body_dir / f'frame-{index:03}.png')) if args.body_dir else cap.read()[1]
                if frame is None:
                    raise ValueError(f'Input ended at {index}')
                image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                sample = mp.Image(image_format=mp.ImageFormat.SRGB, data=image)
                result = detector.detect_for_video(sample, index * 40)
                if not result.face_landmarks:
                    result = fallback.detect(sample)
                    redetected.append(index)
                if not result.face_landmarks:
                    np.save(args.output / 'incomplete.npy', np.stack(points), allow_pickle=False)
                    raise ValueError(f'No face even after independent image detection at frame {index}')
                points.append(extract(result))
                if index % 250 == 0:
                    print('Measured', index, '/', frames, flush=True)
        points = np.stack(points)
        np.save(records, points, allow_pickle=False)
        np.save(args.output / 'reference.npy', reference, allow_pickle=False)
        metadata.update(landmarks_sha256=digest(records), reference_sha256=digest(args.output / 'reference.npy'),
                        independent_redetection_frames=redetected, **summary(points))
        save(args.output / 'measurement.json', metadata)
        print(json.dumps(metadata), flush=True)
    else:
        if not args.body_dir:
            raise ValueError('Stabilization is only for the original body, before face synthesis/matting')
        measurement = json.loads((args.output / 'measurement.json').read_text('utf-8'))
        for key, value in metadata.items():
            if measurement[key] != value:
                raise ValueError(f'Measurement provenance changed: {key}')
        if digest(records) != measurement['landmarks_sha256'] or digest(args.output / 'reference.npy') != measurement['reference_sha256']:
            raise ValueError('Cached measurements changed')
        accepted = json.loads((args.body_dir / 'acceptance.json').read_text('utf-8'))
        if not accepted['accepted'] or accepted['video_sha256'] != digest(video):
            raise ValueError('Reviewed original body required')
        if (args.output / 'gesture.mp4').exists():
            raise ValueError('Keep completed candidates; use a new output folder')
        points = np.load(records, allow_pickle=False)
        transforms = camera_transforms(points, np.load(args.output / 'reference.npy', allow_pickle=False))
        frame_hashes = []
        for index, matrix in enumerate(transforms):
            path = args.body_dir / f'frame-{index:03}.png'
            if digest(path) != accepted['frame_sha256'][index]:
                raise ValueError('Reviewed source body frame changed')
            stabilized = cv2.warpAffine(cv2.imread(str(path)), matrix, (width, height),
                                       flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
            dest = args.output / path.name
            cv2.imwrite(str(dest), stabilized)
            frame_hashes.append(digest(dest))
        import imageio_ffmpeg
        dest = args.output / 'gesture.mp4'
        subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), '-v', 'error', '-n', '-framerate', '25',
            '-i', str(args.output / 'frame-%03d.png'), '-an', '-c:v', 'libx264', '-crf', '19', '-pix_fmt', 'yuv420p',
            '-movflags', '+faststart', str(dest)], check=True)
        original_report = json.loads((args.body_dir / 'report.json').read_text('utf-8'))
        scales = np.linalg.norm(transforms[:, 0, :2], axis=1)
        stabilization = {**metadata, 'method': 'reference-eye similarity camera stabilization; symmetric5-frame filter',
                         'scale_min': float(scales.min()), 'scale_max': float(scales.max()),
                         'measurement_sha256': digest(args.output / 'measurement.json')}
        original_report.update(video_sha256=digest(dest), stabilization=stabilization)
        save(args.output / 'report.json', original_report)
        # No automatic visual acceptance. Review the candidate, then write acceptance.json.
        save(args.output / 'candidate.json', {'video_sha256': digest(dest), 'frame_sha256': frame_hashes,
                                            'accepted': False, 'scope': 'Awaiting visual and independent geometry review'})
        print(json.dumps(stabilization), flush=True)
    cap.release()


if __name__ == '__main__':
    main()
