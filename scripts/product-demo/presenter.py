"""Build an offline narrator from BID3's existing audio and Speak's original Alex.

Reuses an explicitly supplied, pinned local research runtime; installs/downloads
nothing and never edits Speak. The published player uses one composited video,
so captions, chapter seeking, fullscreen and the single original audio stay in sync.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
import wave

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
PUBLIC = ROOT / 'web/public/product-demo'
WORK = ROOT / '.local/product-demo/presenter'
STORY = ROOT / 'web/features/product-demo/storyboard.json'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def prepare(research):
    from ditto_audio_worker import load_session
    from ditto_contract import extract_features
    from tutor_profiles import resolve_portrait

    story = json.loads(STORY.read_text('utf-8'))
    WORK.mkdir(parents=True, exist_ok=True)
    session, _ = load_session()
    records = []
    for scene in story['scenes']:
        source = ROOT / '.local/product-demo/narration' / (scene['id'] + '.wav')
        target = WORK / (scene['id'] + '-features.npy')
        with wave.open(str(source)) as audio:
            if audio.getsampwidth() != 2:
                raise ValueError('Existing PCM16 narration required')
            raw = np.frombuffer(audio.readframes(audio.getnframes()), '<i2').astype(np.float32) / 32768
            raw = raw.reshape(-1, audio.getnchannels()).mean(axis=1)
            rate = audio.getframerate()
        count = scene['duration'] * 16000
        voice = np.interp(np.arange(round(len(raw) / rate * 16000)) / 16000,
                          np.arange(len(raw)) / rate, raw)
        if len(voice) > count - 13600:
            raise ValueError('Narration exceeds existing scene timing')
        samples = np.zeros(count, np.float32)
        samples[7200:7200 + len(voice)] = voice  # Same 450ms start as render.py.
        if target.exists():
            raise ValueError('Prepared features already exist; preserve them in a separate run folder')
        features = extract_features(samples, lambda chunk: session.run(
            None, {'input_values': chunk.reshape(1, -1)})[0], max_seconds=12)
        np.save(target, features, allow_pickle=False)
        records.append({'id': scene['id'], 'duration': scene['duration'],
                        'narration_sha256': digest(source), 'features_sha256': digest(target)})
        print('Prepared', scene['id'], features.shape, flush=True)
    portrait = resolve_portrait('alex')
    save(WORK / 'inputs.json', {'storyboard_sha256': digest(STORY), 'main_video_sha256': digest(PUBLIC / 'intro.mp4'),
         'portrait_sha256': digest(portrait), 'character': 'Alex', 'audio': 'existing BID3 Korean Windows narration',
         'cloud_calls': 0, 'scenes': records})


def render(research, preview):
    from gpu_guard import has_physical_gpu_headroom
    if not has_physical_gpu_headroom(12 * 1024):
        raise RuntimeError('Less than 12GiB physical GPU free; no eviction or fallback')
    import torch
    import cv2
    from ditto_contract import audit_architecture_prefix, build_conditioning
    from prepare_ditto_motion import SOURCE_REV, FILES, digest as file_digest
    from render_ditto_pair import load_renderer, eye_condition
    from tutor_profiles import resolve_portrait

    inputs = json.loads((WORK / 'inputs.json').read_text('utf-8'))
    if digest(STORY) != inputs['storyboard_sha256']:
        raise ValueError('Storyboard changed; prepare a new narrator')
    portrait = resolve_portrait('alex')
    if digest(portrait) != inputs['portrait_sha256']:
        raise ValueError('Original character changed')
    for scene in inputs['scenes']:
        if digest(WORK / (scene['id'] + '-features.npy')) != scene['features_sha256']:
            raise ValueError('Audio feature changed')
    vendor = research / 'vendor/Ditto'
    if subprocess.check_output(['git', '-C', str(vendor), 'rev-parse', 'HEAD'], text=True).strip() != SOURCE_REV:
        raise ValueError('Pinned renderer source required')
    if subprocess.check_output(['git', '-C', str(vendor), 'status', '--porcelain'], text=True).strip():
        raise ValueError('Renderer source has local changes')
    audit_architecture_prefix()
    sys.path.insert(0, str(vendor))
    from core.models.modules.LMDM import LMDM
    from core.atomic_components.audio2motion import Audio2Motion
    from core.atomic_components.motion_stitch import MotionStitch

    torch.set_num_threads(4)
    torch.manual_seed(43)
    if torch.cuda.mem_get_info()[0] < 12 * 1024**3:
        raise RuntimeError('CUDA headroom check failed')
    started = time.perf_counter()
    appearance, extractor, warper, decoder = load_renderer()
    original = cv2.cvtColor(cv2.imread(str(portrait)), cv2.COLOR_BGR2RGB)
    reg = json.loads((research / 'ditto-original-registration.json').read_text('utf-8'))['tutors']['alex']
    if reg['portrait_sha256'] != digest(portrait):
        raise ValueError('Character registration mismatch')
    x, y, side = reg['crop']
    crop = original[y:y + side, x:x + side]
    image = cv2.resize(crop, (256, 256), interpolation=cv2.INTER_AREA)
    tensor = torch.from_numpy(image.copy()).permute(2, 0, 1)[None].cuda().float() / 255
    with torch.inference_mode(), torch.autocast('cuda', dtype=torch.float16):
        volume = appearance(tensor)
        extracted = extractor(tensor)
    source = {key: value.float().cpu().numpy() for key, value in zip(
        ('pitch', 'yaw', 'roll', 't', 'exp', 'scale', 'kp'), extracted)}
    values = np.concatenate([np.load(WORK / (s['id'] + '-features.npy'), allow_pickle=False) for s in inputs['scenes']])
    expected_frames = sum(s['duration'] for s in inputs['scenes']) * 25
    assert len(values) == expected_frames
    motion_file = WORK / 'motion.npy'
    if motion_file.exists():
        record = json.loads((WORK / 'motion.json').read_text('utf-8'))
        if record['inputs_sha256'] != digest(WORK / 'inputs.json') or record['sha256'] != digest(motion_file):
            raise ValueError('Cached motion provenance mismatch')
        sequence = np.load(motion_file, allow_pickle=False)
    else:
        checkpoint = research / 'models/ditto-motion/lmdm_v0.4_hubert.pth'
        if file_digest(checkpoint) != FILES[checkpoint.name][2]:
            raise ValueError('Motion model mismatch')
        diffusion = LMDM(motion_feat_dim=265, audio_feat_dim=1103, seq_frames=80, device='cuda')
        diffusion.model.load_state_dict(torch.load(checkpoint, map_location='cpu', weights_only=True)['model_state_dict'], strict=True)
        diffusion.eval().cuda()

        class Bridge:
            seq_frames = 80

            def setup(self, steps):
                diffusion.setup(steps)

            def __call__(self, pose, condition, steps):
                with torch.inference_mode():
                    return diffusion.ddim_sample(torch.from_numpy(pose).cuda(),
                        torch.from_numpy(condition).cuda(), steps).cpu().numpy()

        eyes, gaze = eye_condition(reg['eyes'], side)
        condition = build_conditioning(values, source['kp'], eyes, gaze)
        motion = Audio2Motion.__new__(Audio2Motion)
        motion.lmdm = Bridge()
        motion.setup(source, overlap_v2=10, fix_kp_cond=1, fix_kp_cond_dim=[0, 202],
                     sampling_timesteps=50, online_mode=False, smo_k_d=3)
        sequence = None
        for index in range(0, len(condition), 70):
            window = condition[index:index + 80]
            if len(window) < 80:
                window = np.concatenate([window, np.repeat(window[-1:], 80 - len(window), axis=0)])
            sequence = motion(window[None], sequence)
        sequence = motion._smo(sequence[:, :len(values)], 0, len(values))
        if not np.isfinite(sequence).all():
            raise ValueError('Non-finite predicted motion')
        np.save(motion_file, sequence, allow_pickle=False)
        save(WORK / 'motion.json', {'inputs_sha256': digest(WORK / 'inputs.json'), 'sha256': digest(motion_file)})
        del diffusion
    if sequence.shape != (1, expected_frames, 265) or not np.isfinite(sequence).all():
        raise ValueError('Motion shape/finite validation failed')
    count = inputs['scenes'][0]['duration'] * 25 if preview else expected_frames
    converter = Audio2Motion.__new__(Audio2Motion)
    converter.v_min_max_for_clip = None
    driving = converter.cvt_fmt(sequence[:, :count])
    stitch = MotionStitch.__new__(MotionStitch)
    stitch.setup(N_d=count, flag_stitching=False, x_s_info=source,
                 delta_eye_arr=None, relative_d=True, overall_ctrl_info={})
    yy, xx = np.mgrid[:side, :side].astype(np.float32)
    radius = ((xx - side * .5) / (side * .43))**2 + ((yy - side * .47) / (side * .48))**2
    alpha = np.clip((1 - radius) / .25, 0, 1)[..., None]
    ffmpeg = research.parents[1] / '.research-tools/imageio_ffmpeg/binaries/ffmpeg-win-x86_64-v7.1.exe'
    target = WORK / ('avatar-preview.mp4' if preview else 'avatar.mp4')
    if target.exists():
        raise ValueError('Completed narrator already exists; do not overwrite')
    command = [str(ffmpeg), '-v', 'error', '-n', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', '512x640',
               '-r', '25', '-i', 'pipe:0', '-an', '-c:v', 'libx264', '-preset', 'fast', '-crf', '19',
               '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(target)]
    with (WORK / 'encoder.log').open('w') as log:
        encoder = subprocess.Popen(command, stdin=subprocess.PIPE, stderr=log)
        try:
            with torch.inference_mode(), torch.autocast('cuda', dtype=torch.float16):
                for index, info in enumerate(driving):
                    source_kp, target_kp = stitch(source, info)
                    warped = warper(volume, torch.from_numpy(source_kp).cuda(), torch.from_numpy(target_kp).cuda())
                    generated = decoder(warped)[0].float().clamp(0, 1)
                    if not torch.isfinite(generated).all():
                        raise ValueError('Non-finite rendered frame')
                    patch = (generated.permute(1, 2, 0).cpu().numpy() * 255).astype(np.uint8)
                    patch = cv2.resize(patch, (side, side), interpolation=cv2.INTER_LINEAR)
                    frame = original.copy()
                    frame[y:y + side, x:x + side] = np.clip(patch * alpha + crop * (1 - alpha), 0, 255).astype(np.uint8)
                    frame = cv2.resize(frame, (512, 640), interpolation=cv2.INTER_AREA)
                    encoder.stdin.write(frame.tobytes())
                    if index in {0, 25, 50, 75, 100, 150} or index % 250 == 0:
                        cv2.imwrite(str(WORK / f'frame-{index:04}.jpg'), cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))
                        print('Frame', index, '/', count, flush=True)
            encoder.stdin.close()
            if encoder.wait(timeout=60):
                raise RuntimeError('Encoder failed; see encoder.log')
        finally:
            if encoder.poll() is None:
                encoder.terminate()
                encoder.wait(timeout=10)
    save(WORK / ('preview.json' if preview else 'render.json'), {
        'frames': count, 'fps': 25, 'duration': count / 25, 'video_sha256': digest(target),
        'seconds_including_model_setup': time.perf_counter() - started,
        'peak_torch_mib': torch.cuda.max_memory_allocated() / 1024**2,
        'cloud_calls': 0, 'static_torso': True, 'gesture_control': False,
        'scope': 'offline original fictional narrator; Korean lip motion requires human review'})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=['prepare', 'render'])
    parser.add_argument('--research-root', type=Path, required=True)
    parser.add_argument('--preview', action='store_true')
    args = parser.parse_args()
    research = args.research_root.resolve(strict=True)
    sys.path.insert(0, str(research))
    if args.stage == 'prepare':
        prepare(research)
    else:
        render(research, args.preview)


if __name__ == '__main__':
    main()
