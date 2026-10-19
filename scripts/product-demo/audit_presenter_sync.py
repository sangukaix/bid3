"""Offline CPU SyncNet timing diagnostic; never auto-shift or grade naturalness.

Reuses the pinned local research helper/model. Crops are manually registered,
not the official full tracking benchmark. Audio embeddings can be reused for a
new video only when the decoded PCM and exact scene clock match.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import numpy as np


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--research-root', type=Path, required=True)
    parser.add_argument('--actor-work', type=Path, required=True)
    parser.add_argument('--audio-video', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--audio-cache', type=Path)
    args = parser.parse_args()
    sys.path.insert(0, str(args.research_root))
    from audit_av_sync import crop_face, curve, sha, WEIGHT_SHA
    import cv2
    import torch
    import python_speech_features
    torch.set_num_threads(4)
    cv2.setNumThreads(1)
    actor = args.actor_work / 'avatar.mp4'
    report = json.loads((args.actor_work / 'render.json').read_text('utf-8'))
    if sha(actor) != report['video_sha256']:
        raise ValueError('Reviewed actor provenance mismatch')
    checkpoint = args.research_root / 'models/sync-audit/syncnet_v2.model'
    if sha(checkpoint) != WEIGHT_SHA:
        raise ValueError('Pinned existing SyncNet checkpoint required')
    source = args.research_root / 'vendor/LatentSync/eval/syncnet/syncnet.py'
    spec = importlib.util.spec_from_file_location('bid3_cpu_syncnet', source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    model = module.S().cpu().eval()
    model.load_state_dict(torch.load(checkpoint, map_location='cpu', weights_only=True), strict=True)
    ffmpeg = args.research_root.parents[1] / '.research-tools/imageio_ffmpeg/binaries/ffmpeg-win-x86_64-v7.1.exe'
    pcm = subprocess.check_output([str(ffmpeg), '-v', 'error', '-i', str(args.audio_video),
        '-map', '0:a:0', '-ac', '1', '-ar', '16000', '-f', 's16le', '-'])
    import hashlib
    pcm_sha = hashlib.sha256(pcm).hexdigest()
    audio = np.frombuffer(pcm, '<i2')
    cases = [('intro', 0, 7), ('review', 35, 11), ('export', 76, 8), ('outro', 84, 6)]
    if (args.output / 'audit.json').exists():
        raise ValueError('Keep completed diagnostics; choose a new output')
    args.output.mkdir(parents=True, exist_ok=True)
    if args.audio_cache:
        previous = json.loads((args.audio_cache / 'audit.json').read_text('utf-8'))
        if previous['decoded_audio_sha256'] != pcm_sha:
            raise ValueError('Audio cache is for different decoded PCM')
        if previous['model_sha256'] != WEIGHT_SHA or previous['model_source_sha256'] != sha(source):
            raise ValueError('Audio cache was computed with a different model')
        if [(c['scene'], c['start'], c['duration']) for c in previous['cases']] != cases:
            raise ValueError('Audio cache uses a different scene clock')
    records = []
    cap = cv2.VideoCapture(str(actor))
    with torch.inference_mode():
        for name, start, duration in cases:
            count = duration * 25 - 5
            cap.set(cv2.CAP_PROP_POS_FRAMES, start * 25)
            images = []
            for n in range(duration * 25):
                ok, frame = cap.read()
                if not ok:
                    raise ValueError('Actor ended before the diagnostic interval')
                images.append(crop_face(frame, (174, 85, 345, 275)))
            cv2.imwrite(str(args.output / (name + '-model-crop.jpg')), images[25])
            if args.audio_cache:
                aud = torch.from_numpy(np.load(args.audio_cache / (name + '-audio.npy'), allow_pickle=False))
            else:
                values = audio[start * 16000:(start + duration) * 16000]
                mfcc = python_speech_features.mfcc(values, 16000).T
                cc = torch.from_numpy(mfcc.copy()).float()[None, None]
                aud = torch.cat([model.forward_aud(torch.cat([cc[:, :, :, n * 4:n * 4 + 20]
                    for n in range(i, min(i + 8, count))])) for i in range(0, count, 8)])
            np.save(args.output / (name + '-audio.npy'), aud.numpy(), allow_pickle=False)
            im = torch.from_numpy(np.stack(images).transpose(3, 0, 1, 2).copy()).float()[None]
            vid = torch.cat([model.forward_lip(torch.cat([im[:, :, n:n + 5]
                for n in range(i, min(i + 8, count))])) for i in range(0, count, 8)])
            np.save(args.output / (name + '-video.npy'), vid.numpy(), allow_pickle=False)
            diagnostic = curve(vid, aud, trim_edges=True)
            delayed = curve(vid, torch.cat([torch.zeros_like(aud[:5]), aud[:-5]]), trim_edges=True)
            record = {'scene': name, 'start': start, 'duration': duration, 'diagnostic': diagnostic,
                      'known200ms_audio_delay_offset_delta': delayed['offset_frames'] - diagnostic['offset_frames']}
            records.append(record)
            print(name, diagnostic['offset_frames'], diagnostic['confidence'], 'delay-control', record['known200ms_audio_delay_offset_delta'], flush=True)
    cap.release()
    result = {'actor_sha256': sha(actor), 'audio_video_sha256': sha(args.audio_video), 'decoded_audio_sha256': pcm_sha,
              'model_sha256': WEIGHT_SHA, 'model_source_sha256': sha(source), 'cpu_only': not torch.cuda.is_initialized(),
              'manual_face_box': [174, 85, 345, 275], 'cases': records,
              'scope': 'Manual-crop timing diagnostic, not phoneme accuracy, official benchmark, or human-naturalness acceptance; no automatic audio/video shift'}
    (args.output / 'audit.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
