"""Build an offline narrator from BID3's audio and an explicitly registered portrait.

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


def portrait_for(tutor):
    if tutor == 'alex':
        from tutor_profiles import resolve_portrait
        return resolve_portrait(tutor)
    from portrait_revisions import resolve_revision
    return resolve_revision(tutor)


def load_gestures(gesture_dir, timeline_file, portrait_sha256, total_frames):
    """Validate reviewed clips once, then map scheduled frames onto the audio clock."""
    if not gesture_dir and not timeline_file:
        return {}, None
    if timeline_file:
        timeline = json.loads(timeline_file.read_text('utf-8'))
        if timeline['fps'] != 25 or timeline['portrait_sha256'] != portrait_sha256:
            raise ValueError('Gesture timeline portrait/fps mismatch')
        schedule = [(item['start_seconds'], timeline_file.parent / item['clip']) for item in timeline['segments']]
    else:
        schedule = [(0, gesture_dir)]
    cache, frames, segments = {}, {}, []
    for seconds, folder in schedule:
        start = round(seconds * 25)
        if seconds < 0 or abs(start / 25 - seconds) > 1e-6:
            raise ValueError('Gesture must begin on an in-range video frame')
        if folder not in cache:
            report = json.loads((folder / 'report.json').read_text('utf-8'))
            accepted = json.loads((folder / 'acceptance.json').read_text('utf-8'))
            video_sha = digest(folder / 'gesture.mp4')
            if not accepted.get('accepted') or accepted['video_sha256'] != video_sha or report['video_sha256'] != video_sha:
                raise ValueError('Hand/identity visual acceptance required before use')
            maximum = total_frames if report.get('continuous') else 250
            if report['fps'] != 25 or not 1 <= report['frames'] <= maximum:
                raise ValueError('Only bounded reviewed gesture clips are supported')
            if (report.get('end_image_sha256') or report['source_sha256']) != portrait_sha256:
                raise ValueError('Gesture resting portrait differs from the registered character')
            if timeline_file and report['source_sha256'] != portrait_sha256:
                raise ValueError('Scheduled explanation must start and finish at the same neutral pose')
            paths = [folder / f'frame-{i:03}.png' for i in range(report['frames'])]
            if [digest(path) for path in paths] != accepted['frame_sha256']:
                raise ValueError('Gesture frames changed after review')
            cache[folder] = (paths, video_sha)
        paths, video_sha = cache[folder]
        if start + len(paths) > total_frames or any(i in frames for i in range(start, start + len(paths))):
            raise ValueError('Gesture segments overlap or exceed the narration')
        frames.update({start + i: path for i, path in enumerate(paths)})
        segments.append({'start_seconds': seconds, 'duration': len(paths) / 25, 'clip': folder.name, 'video_sha256': video_sha})
    source_sha = digest(timeline_file) if timeline_file else segments[0]['video_sha256']
    continuous = bool(not timeline_file and report.get('continuous'))
    return frames, {'duration': len(frames) / 25, 'video_sha256': source_sha, 'segments': segments,
                    'continuous': continuous, 'join_method': report.get('join_method') if continuous else None,
                    'body_tempo_ratio': report.get('body_tempo_ratio', 1) if continuous else 1}


def speech_activity(inputs):
    """Close the mouth in genuine pauses; preserve120ms around quiet consonants."""
    result = []
    narration = Path(inputs['narration_dir'])
    for scene in inputs['scenes']:
        with wave.open(str(narration / (scene['id'] + '.wav'))) as audio:
            samples = np.frombuffer(audio.readframes(audio.getnframes()), '<i2').astype(np.float32) / 32768
            samples = samples.reshape(-1, audio.getnchannels()).mean(axis=1)
            rate = audio.getframerate()
        start = round(.45 * rate)
        padded = np.zeros(round(scene['duration'] * rate), np.float32)
        padded[start:start + len(samples)] = samples
        for frame in range(scene['duration'] * 25):
            window = padded[round(frame * rate / 25):round((frame + 1) * rate / 25)]
            result.append(float(np.sqrt(np.mean(window**2))) > .0015)
    active = np.array(result, np.float32)
    extended = np.maximum.reduce([np.pad(active, (2, 2))[i:i + len(active)] for i in range(5)])
    return np.convolve(extended, [.25, .5, .25], mode='same').astype(np.float32)


def restrained_expression(info, first, activity, gain=.72):
    """Retain acoustic articulation, reducing exaggerated lip motion and silence chatter."""
    result = dict(info)
    expression = info['exp'].copy().reshape(1, 21, 3)
    initial = first['exp'].reshape(1, 21, 3)
    lips = [6, 12, 14, 17, 19, 20]
    expression[:, lips] = initial[:, lips] + (expression[:, lips] - initial[:, lips]) * gain * activity
    result['exp'] = expression.reshape(info['exp'].shape)
    return result


def blink_envelope(frames):
    """Irregular authored blinks, independent of speech and body-model eye noise."""
    seconds = np.arange(frames) / 25
    envelope = np.zeros(frames, np.float32)
    rng = np.random.default_rng(43)
    center = 3.6
    while center < frames / 25:
        distance = np.abs(seconds - center)
        envelope = np.maximum(envelope, np.where(distance < .16,
            .5 + .5 * np.cos(np.pi * np.minimum(distance, .16) / .16), 0))
        center = round((center + rng.uniform(3.8, 6.2)) * 25) / 25
    return envelope.astype(np.float32)


def face_blend_mask(side, keep_greeting_hand=False):
    yy, xx = np.mgrid[:side, :side].astype(np.float32)
    radius = ((xx - side * .5) / (side * .43))**2 + ((yy - side * .47) / (side * .48))**2
    alpha = np.clip((1 - radius) / .25, 0, 1)[..., None]
    if keep_greeting_hand:
        lower = np.clip((yy / side - .50) / .10, 0, 1)
        safe_x = np.clip((xx / side - .30) / .10, 0, 1)
        alpha *= (1 - lower * (1 - safe_x))[..., None]
    return alpha


def prepare(research, tutor, narration, source_config=None):
    from ditto_audio_worker import load_session
    from ditto_contract import extract_features

    if tutor == 'bid3-guide' and not source_config:
        raise ValueError('BID3 guide requires its own source config; no Speak character fallback')
    story = json.loads(STORY.read_text('utf-8'))
    WORK.mkdir(parents=True, exist_ok=True)
    session, _ = load_session()
    records = []
    for scene in story['scenes']:
        source = narration / (scene['id'] + '.wav')
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
    custom = json.loads(source_config.read_text('utf-8')) if source_config else None
    portrait = ROOT / custom['portrait'] if custom else portrait_for(tutor)
    if custom and digest(portrait) != custom['portrait_sha256']:
        raise ValueError('Custom character source hash mismatch')
    voice_info = narration / 'voice.json'
    voice = json.loads(voice_info.read_text('utf-8')) if voice_info.exists() else {'engine': 'Windows SAPI', 'voice': 'ko-KR'}
    save(WORK / 'inputs.json', {'storyboard_sha256': digest(STORY), 'main_video_sha256': digest(PUBLIC / 'intro.mp4'),
         'portrait_sha256': digest(portrait), 'character': custom['character'] if custom else ('Alex' if tutor == 'alex' else 'Zoe'), 'tutor_id': tutor,
         'narration_dir': str(narration.resolve()), 'voice': voice, 'audio': voice['engine'] + ' ' + voice['voice'],
         'custom_source': custom,
         'cloud_calls': 0, 'scenes': records})


def render(research, preview, gesture_dir=None, gesture_timeline=None, face_style='natural', preview_seconds=15):
    from gpu_guard import has_physical_gpu_headroom
    if not has_physical_gpu_headroom(12 * 1024):
        raise RuntimeError('Less than 12GiB physical GPU free; no eviction or fallback')
    import torch
    import cv2
    from ditto_contract import audit_architecture_prefix, build_conditioning
    from prepare_ditto_motion import SOURCE_REV, FILES, digest as file_digest
    from render_ditto_pair import load_renderer, eye_condition

    inputs = json.loads((WORK / 'inputs.json').read_text('utf-8'))
    if digest(STORY) != inputs['storyboard_sha256']:
        raise ValueError('Storyboard changed; prepare a new narrator')
    tutor = inputs.get('tutor_id', 'alex')
    custom = inputs.get('custom_source')
    portrait = ROOT / custom['portrait'] if custom else portrait_for(tutor)
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
    from core.atomic_components.motion_stitch import MotionStitch, transform_keypoint, bin66_to_degree

    torch.set_num_threads(4)
    torch.manual_seed(43)
    if torch.cuda.mem_get_info()[0] < 12 * 1024**3:
        raise RuntimeError('CUDA headroom check failed')
    started = time.perf_counter()
    appearance, extractor, warper, decoder = load_renderer()
    original = cv2.cvtColor(cv2.imread(str(portrait)), cv2.COLOR_BGR2RGB)
    registration = 'ditto-original-registration.json' if tutor == 'alex' else 'ditto-revised-registration-20261011.json'
    reg = custom['registration'] if custom else json.loads((research / registration).read_text('utf-8'))['tutors'][tutor]
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
    motion_cache_reused = motion_file.exists()
    if motion_cache_reused:
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
    count = min(round(preview_seconds * 25), expected_frames) if preview else expected_frames
    converter = Audio2Motion.__new__(Audio2Motion)
    converter.v_min_max_for_clip = None
    driving = converter.cvt_fmt(sequence[:, :count])
    stitch = MotionStitch.__new__(MotionStitch)
    has_gestures = bool(gesture_dir or gesture_timeline)
    natural = face_style == 'natural'
    stitch.setup(N_d=count, flag_stitching=False, x_s_info=source, is_image_flag=not has_gestures,
                 drive_eye=False if natural else None,
                 delta_eye_arr=None, relative_d=True, overall_ctrl_info={})
    activity = speech_activity(inputs) if natural else np.ones(expected_frames)
    original_keypoints = transform_keypoint(source)
    blink = blink_envelope(count)
    closed_eye_delta = None
    if natural:
        eye_path = research / 'models/liveportrait-lip-research/stitching_retargeting_module.pth'
        if digest(eye_path) != '3652d5a3f95099141a56986aaddec92fadf0a73c87a20fac9a2c07c32b28b611':
            raise ValueError('Pinned existing eye retargeter required')
        eye_vendor = research / 'vendor/LivePortrait'
        if subprocess.check_output(['git', '-C', str(eye_vendor), 'rev-parse', 'HEAD'], text=True).strip() != '9b294b3d0536135442ea73cb01e6cb3ca7029dd3':
            raise ValueError('Pinned LivePortrait eye source required')
        sys.path.insert(0, str(eye_vendor))
        from src.modules.stitching_retargeting_network import StitchingRetargetingNetwork
        eye_model = StitchingRetargetingNetwork(66, [256, 256, 128, 128, 64], 63)
        eye_state = torch.load(eye_path, map_location='cpu', weights_only=True)['retarget_eye']
        eye_model.load_state_dict({k.removeprefix('module.'): v for k, v in eye_state.items()}, strict=True)
        eye_model.eval().cuda()
        ratios = []
        for eye in reg['eyes']:
            corners = np.array(eye['corners'], np.float32)
            upper, lower = np.array(eye['vertical_pairs'][1], np.float32)
            ratios.append(float(np.linalg.norm(upper - lower) / np.linalg.norm(corners[0] - corners[1])))
        features = np.concatenate([original_keypoints.reshape(1, 63), np.array([[*ratios, 0]], np.float32)], axis=1)
        with torch.inference_mode():
            closed_eye_delta = eye_model(torch.from_numpy(features).cuda()).cpu().numpy().reshape(1, 21, 3)
        del eye_model, eye_state
    # Her hands stay below the face. A legacy wave mask would expose a second
    # body-model eye through the lower-left eyelid, creating a dark double eye.
    alpha = face_blend_mask(side, keep_greeting_hand=has_gestures and not natural)
    ffmpeg = research.parents[1] / '.research-tools/imageio_ffmpeg/binaries/ffmpeg-win-x86_64-v7.1.exe'
    target = WORK / ('avatar-preview.mp4' if preview else 'avatar.mp4')
    if target.exists():
        raise ValueError('Completed narrator already exists; do not overwrite')
    width, height = reg['output_size']
    body_frames, body_report = load_gestures(gesture_dir, gesture_timeline, inputs['portrait_sha256'], expected_frames)
    if body_report and body_report['continuous'] and any(i not in body_frames for i in range(count)):
        raise ValueError('Continuous motion must cover every rendered frame; never hold a missing body')
    body_cache = None
    reference_body = None
    command = [str(ffmpeg), '-v', 'error', '-n', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{width}x{height}',
               '-r', '25', '-i', 'pipe:0', '-an', '-c:v', 'libx264', '-preset', 'fast', '-crf', '19',
               '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(target)]
    with (WORK / 'encoder.log').open('w') as log:
        encoder = subprocess.Popen(command, stdin=subprocess.PIPE, stderr=log)
        try:
            with torch.inference_mode(), torch.autocast('cuda', dtype=torch.float16):
                for index, info in enumerate(driving):
                    if body_frames:
                        if index in body_frames or body_cache is None:
                            frame = cv2.cvtColor(cv2.imread(str(body_frames[index])), cv2.COLOR_BGR2RGB) if index in body_frames else cv2.resize(original, (width, height))
                            if frame.shape != (height, width, 3):
                                raise ValueError('Gesture frame dimensions changed')
                            scale = width / original.shape[1]
                            bx, by, bs = (round(v * scale) for v in (x, y, side))
                            body_crop = frame[by:by + bs, bx:bx + bs]
                            body_image = cv2.resize(body_crop, (256, 256), interpolation=cv2.INTER_AREA)
                            body_tensor = torch.from_numpy(body_image.copy()).permute(2, 0, 1)[None].cuda().float() / 255
                            body_volume = volume if natural else appearance(body_tensor)
                            body_extracted = extractor(body_tensor)
                            body_source = {key: value.float().cpu().numpy() for key, value in zip(
                                ('pitch', 'yaw', 'roll', 't', 'exp', 'scale', 'kp'), body_extracted)}
                            if reference_body is None:
                                reference_body = {key: value.copy() for key, value in body_source.items()}
                            body_alpha = cv2.resize(alpha, (bs, bs), interpolation=cv2.INTER_LINEAR)[..., None]
                            body_cache = (frame, body_crop, body_volume, body_source, body_alpha, bx, by, bs)
                        base, active_crop, active_volume, active_source, active_alpha, px, py, patch_side = body_cache
                        frame = base.copy()
                    else:
                        frame = original.copy()
                        active_crop, active_volume, active_source, active_alpha, px, py, patch_side = crop, volume, source, alpha, x, y, side
                    if natural:
                        anchor = dict(source)
                        baseline = reference_body or source
                        for key in ('pitch', 'yaw', 'roll'):
                            anchor[key] = bin66_to_degree(source[key]) + .65 * (
                                bin66_to_degree(active_source[key]) - bin66_to_degree(baseline[key]))
                        anchor['t'] = source['t'] + .65 * (active_source['t'] - baseline['t'])
                        anchor['scale'] = source['scale'] * np.clip(active_source['scale'] / baseline['scale'], .95, 1.05)
                        anchor['exp'] = source['exp']
                        info = restrained_expression(info, driving[0], activity[index])
                        _, target_kp = stitch(anchor, info)
                        target_kp = target_kp + closed_eye_delta * blink[index]
                        source_kp, active_volume = original_keypoints, volume
                    else:
                        source_kp, target_kp = stitch(active_source, info)
                    warped = warper(active_volume, torch.from_numpy(source_kp).cuda(), torch.from_numpy(target_kp).cuda())
                    generated = decoder(warped)[0].float().clamp(0, 1)
                    if not torch.isfinite(generated).all():
                        raise ValueError('Non-finite rendered frame')
                    patch = (generated.permute(1, 2, 0).cpu().numpy() * 255).astype(np.uint8)
                    patch = cv2.resize(patch, (patch_side, patch_side), interpolation=cv2.INTER_LINEAR)
                    frame[py:py + patch_side, px:px + patch_side] = np.clip(
                        patch * active_alpha + active_crop * (1 - active_alpha), 0, 255).astype(np.uint8)
                    frame = cv2.resize(frame, (width, height), interpolation=cv2.INTER_AREA)
                    encoder.stdin.write(frame.tobytes())
                    if index in {0, 25, 50, 75, 86, 90, 94, 100, 150, 190, 192, 193, 195, 200} or index % 250 == 0:
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
        'cloud_calls': 0, 'static_torso': not bool(body_frames), 'gesture_control': bool(body_frames),
        'gesture_duration': body_report['duration'] if body_report else 0,
        'gesture_video_sha256': body_report['video_sha256'] if body_report else None,
        'gesture_segments': body_report['segments'] if body_report else [],
        'continuous_body': bool(body_report and body_report['continuous']),
        'body_join_method': body_report.get('join_method') if body_report else None,
        'body_tempo_ratio': body_report.get('body_tempo_ratio', 1) if body_report else 1,
        'face_style': face_style, 'stable_reference_appearance': natural,
        'motion_cache_reused': motion_cache_reused,
        'lip_gain': .72 if natural else 1, 'silence_mouth_gate': natural,
        'eye_control': 'pinned LivePortrait eye retargeter with authored blink timing' if natural else 'legacy',
        'scope': 'offline synthetic narrator; Korean lip motion requires human review'})


def main():
    global WORK
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=['prepare', 'render'])
    parser.add_argument('--research-root', type=Path, required=True)
    parser.add_argument('--preview', action='store_true')
    parser.add_argument('--preview-seconds', type=float, default=15)
    parser.add_argument('--face-style', choices=['natural', 'legacy'], default='natural')
    parser.add_argument('--work-dir', type=Path, default=WORK)
    parser.add_argument('--tutor', choices=['alex', 'zoe', 'bid3-guide'], default='alex')
    parser.add_argument('--narration-dir', type=Path, default=ROOT / '.local/product-demo/narration')
    parser.add_argument('--source-config', type=Path)
    gestures = parser.add_mutually_exclusive_group()
    gestures.add_argument('--gesture-dir', type=Path)
    gestures.add_argument('--gesture-timeline', type=Path)
    args = parser.parse_args()
    WORK = args.work_dir.resolve()
    research = args.research_root.resolve(strict=True)
    sys.path.insert(0, str(research))
    if args.stage == 'prepare':
        prepare(research, args.tutor, args.narration_dir.resolve(strict=True), args.source_config)
    else:
        render(research, args.preview, args.gesture_dir, args.gesture_timeline, args.face_style, args.preview_seconds)


if __name__ == '__main__':
    main()
