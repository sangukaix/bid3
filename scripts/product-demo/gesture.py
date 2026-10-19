"""One local, bounded greeting-hand candidate for the existing fictional Zoe.

Reuses Speak's pinned LTX runtime read-only. Output is a silent motion candidate,
not an accepted gesture until hands, identity and continuity are visually checked.
"""
import argparse
import gc
import json
from pathlib import Path
import sys
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--research-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--source-image', type=Path)
    parser.add_argument('--end-image', type=Path)
    args = parser.parse_args()
    research = args.research_root.resolve(strict=True)
    output = args.output.resolve()
    if output.exists():
        raise ValueError('Preserve previous candidate; choose a new output folder')
    sys.path.insert(0, str(research))
    import render_body as body
    from portrait_revisions import resolve_revision
    if not body.has_physical_gpu_headroom(12 * 1024) or body.torch.cuda.mem_get_info()[0] < 12 * 1024**3:
        raise RuntimeError('Need 12GiB physical/CUDA headroom; never unload another project')
    for item in json.loads((research / 'body-model-manifest.json').read_text('utf-8')):
        if body.digest(Path(item['path'])) != item['sha256']:
            raise ValueError('Pinned model hash mismatch')
    portrait = args.source_image.resolve(strict=True) if args.source_image else resolve_revision('zoe')
    prompt = (
        'A fixed camera medium shot of the same friendly adult blonde woman wearing '
        'the same blue linen shirt over a white top, seated against the same softly lit '
        'room. Her right hand is already raised in an open greeting pose. '
        'She moves her right wrist gently side to side in one small welcoming wave, then '
        'lowers her hand back to her lap. Five natural fingers, relaxed wrist and arm. '
        'Her head stays upright, face and hair stay consistent, with a soft closed-mouth '
        'smile and eye contact. Her hand stays well below her chin. The other hand stays '
        'relaxed. The camera and background remain stationary. One continuous calm greeting.'
    )
    output.mkdir(parents=True)
    torch = body.torch
    torch.set_num_threads(6)
    started = time.perf_counter()
    text_root = research / 'models/ltx-text'
    print('Encoding one local gesture prompt', flush=True)
    tokenizer = body.T5Tokenizer.from_pretrained(str(text_root), subfolder='tokenizer', local_files_only=True)
    encoder = body.T5EncoderModel.from_pretrained(str(text_root), subfolder='text_encoder', local_files_only=True,
        use_safetensors=True, torch_dtype=torch.bfloat16, low_cpu_mem_usage=True).eval().cuda()
    tokens = tokenizer([prompt], padding='max_length', max_length=256, truncation=True, return_tensors='pt')
    if len(tokenizer.encode(prompt)) > 256:
        raise ValueError('Gesture prompt would be truncated')
    with torch.inference_mode():
        embedding = encoder(tokens.input_ids.cuda(), attention_mask=tokens.attention_mask.cuda())[0].cpu()
    mask = tokens.attention_mask.cpu()
    del encoder, tokenizer, tokens
    gc.collect()
    torch.cuda.empty_cache()  # Only this worker's unused allocator cache.
    checkpoint = research / 'models/ltx/ltxv-2b-0.9.6-distilled-04-25.safetensors'
    with body.safe_open(checkpoint, framework='pt', device='cpu') as handle:
        config = json.loads(handle.metadata()['config'])
    vae = body.CausalVideoAutoencoder.from_pretrained(checkpoint, torch_dtype=torch.bfloat16).eval().cuda()
    transformer = body.Transformer3DModel.from_pretrained(checkpoint).eval().to(dtype=torch.bfloat16, device='cuda')
    pipe = body.LTXVideoPipeline(tokenizer=None, text_encoder=None, vae=vae, transformer=transformer,
        scheduler=body.RectifiedFlowScheduler.from_pretrained(checkpoint),
        patchifier=body.SymmetricPatchifier(patch_size=1), prompt_enhancer_image_caption_model=None,
        prompt_enhancer_image_caption_processor=None, prompt_enhancer_llm_model=None,
        prompt_enhancer_llm_tokenizer=None, allowed_inference_steps=config.get('allowed_inference_steps'))
    frames, width, height, fps = (193 if args.end_image else 129), 512, 768, 25
    source = body.load_image_to_tensor_with_resize_and_crop(str(portrait), height, width)
    conditioning = [body.ConditioningItem(source, 0, 1.0)]
    if args.end_image:
        end = body.load_image_to_tensor_with_resize_and_crop(str(args.end_image.resolve(strict=True)), height, width)
        conditioning.append(body.ConditioningItem(end, frames - 1, 1.0))
    print('Rendering one greeting candidate:', frames, 'frames', flush=True)
    with torch.inference_mode():
        images = pipe(height=height, width=width, num_frames=frames, frame_rate=fps,
            prompt=None, negative_prompt=None, prompt_embeds=embedding, prompt_attention_mask=mask.cuda(),
            negative_prompt_embeds=torch.zeros_like(embedding), negative_prompt_attention_mask=mask.cuda(),
            num_inference_steps=8, guidance_scale=1, stg_scale=0, rescaling_scale=1,
            skip_layer_strategy=body.SkipLayerStrategy.AttentionValues, decode_timestep=.05,
            decode_noise_scale=.025, stochastic_sampling=True, conditioning_items=conditioning,
            generator=torch.Generator(device='cuda').manual_seed(7), output_type='pt', is_video=True,
            vae_per_channel_normalize=True, image_cond_noise_scale=.15, mixed_precision=False,
            offload_to_cpu=True, device='cuda', enhance_prompt=False).images
    pixels = (images[0].permute(1, 2, 3, 0).float().cpu().clamp(0, 1).numpy() * 255).astype(body.np.uint8)
    if pixels.shape != (frames, height, width, 3):
        raise ValueError('Unexpected gesture shape')
    import os
    os.environ['IMAGEIO_FFMPEG_EXE'] = str(research.parents[1] / '.research-tools/imageio_ffmpeg/binaries/ffmpeg-win-x86_64-v7.1.exe')
    with body.imageio.get_writer(str(output / 'gesture.mp4'), fps=fps, codec='libx264', quality=8,
                                ffmpeg_params=['-movflags', '+faststart']) as writer:
        for index, frame in enumerate(pixels):
            writer.append_data(frame)
            body.Image.fromarray(frame).save(output / f'frame-{index:03}.png')
    report = {'character': 'Zoe', 'frames': frames, 'fps': fps, 'duration': frames / fps,
              'source_sha256': body.digest(portrait), 'video_sha256': body.digest(output / 'gesture.mp4'),
              'end_image_sha256': body.digest(args.end_image) if args.end_image else None,
              'prompt': prompt, 'seconds': time.perf_counter() - started, 'seed': 7,
              'cloud_calls': 0, 'accepted': False, 'status': 'candidate-needs-hand-and-identity-review'}
    (output / 'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print('Candidate ready for visual review', flush=True)


if __name__ == '__main__':
    main()
