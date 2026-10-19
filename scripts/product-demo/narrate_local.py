"""Generate the public storyboard with local Korean female Supertonic2/F2.

One explicitly downloaded, pinned ONNX model; no voice clone, OpenAI or inference
API. Install the optional authoring dependency into an isolated environment only.
"""
import argparse
import hashlib
import json
from pathlib import Path
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
REVISION = '75e6727618a02f323c720cba9478152d4bc16ca4'
REPOSITORY = 'Supertone/supertonic-2'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--model-dir', type=Path, required=True)
    parser.add_argument('--download', action='store_true')
    parser.add_argument('--speed', type=float, default=1.13)
    args = parser.parse_args()
    if not 1.0 <= args.speed <= 1.2:
        raise ValueError('Use a natural narration pace between 1.0 and 1.2')
    model_dir = args.model_dir.resolve()
    if args.download:
        from huggingface_hub import HfApi, hf_hub_download
        info = HfApi(token=False).model_info(REPOSITORY, revision=REVISION, files_metadata=True)
        files = [f for f in info.siblings if f.rfilename.startswith('onnx/') or f.rfilename in
                 {'voice_styles/F2.json', 'LICENSE', 'README.md'}]
        if sum(f.size or 0 for f in files) > 400 * 1024**2:
            raise ValueError('Unexpected download size')
        records = []
        for item in files:
            path = Path(hf_hub_download(REPOSITORY, item.rfilename, revision=REVISION,
                                       local_dir=model_dir, token=False))
            checksum = digest(path)
            if item.lfs and checksum != item.lfs.sha256:
                raise ValueError('Publisher model hash mismatch')
            records.append({'file': item.rfilename, 'sha256': checksum, 'bytes': path.stat().st_size})
            print('Verified', item.rfilename, flush=True)
        (model_dir / 'provenance.json').write_text(json.dumps({'repository': REPOSITORY,
            'revision': REVISION, 'files': records}, indent=2), encoding='utf-8')
    from supertonic import TTS
    tts = TTS(model='supertonic-2', model_dir=model_dir, auto_download=False,
              intra_op_num_threads=4, inter_op_num_threads=1)
    style = tts.get_voice_style('F2')
    story = json.loads((ROOT / 'web/features/product-demo/storyboard.json').read_text('utf-8'))
    args.output.mkdir(parents=True, exist_ok=True)
    records = []
    for scene in story['scenes']:
        target = args.output / (scene['id'] + '.wav')
        if target.exists():
            raise ValueError('Previous narration is preserved; use a new output folder')
        text = scene['narration'].replace('AI비드', '에이아이 비드').replace('IT', '아이티')
        started = time.perf_counter()
        wav, duration = tts.synthesize(text, voice_style=style, lang='ko', total_steps=12, speed=args.speed)
        samples = wav.reshape(-1)
        # Remove synthesis padding only; preserve every non-silent speech sample.
        audible = np.flatnonzero(np.abs(samples) > .001)
        if not len(audible) or not np.isfinite(samples).all():
            raise ValueError('Empty or non-finite narration')
        margin = int(tts.sample_rate * .08)
        samples = samples[max(0, audible[0] - margin):min(len(samples), audible[-1] + margin + 1)]
        actual = len(samples) / tts.sample_rate
        if actual > scene['duration'] - .85:
            raise ValueError(f"{scene['id']} needs {actual:.2f}s; revise narration/timeline instead of truncating")
        tts.save_audio(samples, str(target))
        records.append({'id': scene['id'], 'sha256': digest(target), 'duration': actual,
                        'synthesis_seconds': time.perf_counter() - started})
        print(scene['id'], f'{actual:.2f}s', flush=True)
    report = {'engine': 'Supertonic2 local CPU', 'voice': 'F2', 'language': 'ko',
              'model_repository': REPOSITORY, 'model_revision': REVISION, 'package': 'supertonic==1.3.1',
              'cloud_inference': False, 'openai_calls': 0, 'speed': args.speed, 'steps': 12, 'scenes': records}
    (args.output / 'voice.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
