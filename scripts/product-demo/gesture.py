"""One local, bounded hand-motion candidate for an explicit presenter portrait.

Reuses Speak's pinned LTX runtime read-only. Output is a silent motion candidate,
not an accepted gesture until hands, identity and continuity are visually checked.
"""
import argparse
import gc
import json
from pathlib import Path
import sys
import time


def main(argv=None, runtime=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--research-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--source-image', type=Path, required=True)
    parser.add_argument('--end-image', type=Path)
    parser.add_argument('--middle-image', type=Path)
    parser.add_argument('--prompt-file', type=Path)
    parser.add_argument('--character', default='BID3 Korean guide')
    parser.add_argument('--prefix-dir', type=Path)
    parser.add_argument('--prefix-start', type=int, default=0)
    parser.add_argument('--frames', type=int)
    parser.add_argument('--seed', type=int, default=7)
    args = parser.parse_args(argv)
    if runtime is None:
        runtime = {}
    research = args.research_root.resolve(strict=True)
    output = args.output.resolve()
    if output.exists():
        raise ValueError('Preserve previous candidate; choose a new output folder')
    sys.path.insert(0, str(research))
    import render_body as body
    from body_phase_profile import VaePhaseProfile
    if runtime:
        gc.collect()
        body.torch.cuda.empty_cache()  # This batch worker's unused allocations only.
    if not body.has_physical_gpu_headroom(12 * 1024) or body.torch.cuda.mem_get_info()[0] < 12 * 1024**3:
        raise RuntimeError('Need 12GiB physical/CUDA headroom; never unload another project')
    for item in ([] if runtime else json.loads((research / 'body-model-manifest.json').read_text('utf-8'))):
        if body.digest(Path(item['path'])) != item['sha256']:
            raise ValueError('Pinned model hash mismatch')
    portrait = args.source_image.resolve(strict=True)
    prompt = args.prompt_file.read_text('utf-8') if args.prompt_file else (
        'A fixed camera medium shot of the same friendly adult woman wearing '
        'exactly the same clothes, seated against the same softly lit '
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
    model_setup_reused = bool(runtime)
    if runtime:
        if runtime['key'] != (str(research), prompt):
            raise ValueError('Cached runtime is only for the same pinned models and exact prompt')
        pipe, vae, embedding, mask = (runtime[k] for k in ('pipe', 'vae', 'embedding', 'mask'))
    else:
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
        runtime.update(key=(str(research), prompt), pipe=pipe, vae=vae, embedding=embedding, mask=mask)
    frames, width, height, fps = args.frames or (193 if args.end_image else 129), 512, 768, 25
    if frames % 8 != 1 or not 33 <= frames <= 193:
        raise ValueError('Bounded frame count must be 8n+1, between33 and193')
    source = body.load_image_to_tensor_with_resize_and_crop(str(portrait), height, width)
    prefix_paths = []
    if args.prefix_dir:
        prefix_paths = [args.prefix_dir / f'frame-{i:03}.png' for i in range(args.prefix_start, args.prefix_start + 17)]
        prefix = body.np.stack([body.np.array(body.Image.open(path).convert('RGB')) for path in prefix_paths])
        if prefix.shape != (17, height, width, 3):
            raise ValueError('Continuation requires17 original-sized preceding frames')
        source = torch.from_numpy(prefix.astype(body.np.float32) / 127.5 - 1).permute(3, 0, 1, 2)[None]
    conditioning = [body.ConditioningItem(source, 0, 1.0)]
    if args.end_image:
        end = body.load_image_to_tensor_with_resize_and_crop(str(args.end_image.resolve(strict=True)), height, width)
        conditioning.append(body.ConditioningItem(end, frames - 1, 1.0))
    if args.middle_image:
        if not args.end_image:
            raise ValueError('An explanatory middle pose also requires an end pose')
        middle = body.load_image_to_tensor_with_resize_and_crop(str(args.middle_image.resolve(strict=True)), height, width)
        conditioning.append(body.ConditioningItem(middle, (frames - 1) // 2, 1.0))
    print('Rendering one greeting candidate:', frames, 'frames', flush=True)
    with VaePhaseProfile(vae, torch.cuda, release_own_cache_before_decode=True) as phases, torch.inference_mode():
        images = pipe(height=height, width=width, num_frames=frames, frame_rate=fps,
            prompt=None, negative_prompt=None, prompt_embeds=embedding, prompt_attention_mask=mask.cuda(),
            negative_prompt_embeds=torch.zeros_like(embedding), negative_prompt_attention_mask=mask.cuda(),
            num_inference_steps=8, guidance_scale=1, stg_scale=0, rescaling_scale=1,
            skip_layer_strategy=body.SkipLayerStrategy.AttentionValues, decode_timestep=.05,
            decode_noise_scale=.025, stochastic_sampling=True, conditioning_items=conditioning,
            generator=torch.Generator(device='cuda').manual_seed(args.seed), output_type='pt', is_video=True,
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
    report = {'character': args.character, 'frames': frames, 'fps': fps, 'duration': frames / fps,
              'source_sha256': body.digest(portrait), 'video_sha256': body.digest(output / 'gesture.mp4'),
              'end_image_sha256': body.digest(args.end_image) if args.end_image else None,
              'middle_image_sha256': body.digest(args.middle_image) if args.middle_image else None,
              'prompt': prompt, 'seconds': time.perf_counter() - started, 'seed': args.seed, 'vae_phases': phases.calls,
              'prefix_sha256': [body.digest(path) for path in prefix_paths],
              'frame_sha256': [body.digest(output / f'frame-{i:03}.png') for i in range(frames)],
              'model_setup_reused': model_setup_reused,
              'cloud_calls': 0, 'accepted': False, 'status': 'candidate-needs-hand-and-identity-review'}
    (output / 'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print('Candidate ready for visual review', flush=True)


if __name__ == '__main__':
    main()
