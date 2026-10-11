"""Render BID3's introduction from the same storyboard the web player uses.

No browser, user credentials, AI calls, or external media are used by this renderer.
Refresh the sanitized screenshots, edit storyboard.json, then render again.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import tempfile
import wave

import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parents[2]
STORY_PATH = ROOT / 'web/features/product-demo/storyboard.json'
PUBLIC = ROOT / 'web/public/product-demo'
COLORS = {'teal': '#69e1c3', 'blue': '#92b6ff', 'violet': '#cab3ff'}
W, H = 1920, 1080


def ease(value):
    value = max(0, min(1, value))
    return value * value * (3 - 2 * value)


def font_path(bold=False):
    custom = os.environ.get('BID_DEMO_FONT_BOLD' if bold else 'BID_DEMO_FONT')
    path = Path(custom or ('C:/Windows/Fonts/malgunbd.ttf' if bold else 'C:/Windows/Fonts/malgun.ttf'))
    if not path.is_file():
        raise ValueError('Set BID_DEMO_FONT and BID_DEMO_FONT_BOLD to local Korean font paths.')
    return str(path)


FONTS = {}


def font(size, bold=False):
    key = (size, bold)
    if key not in FONTS:
        FONTS[key] = ImageFont.truetype(font_path(bold), size)
    return FONTS[key]


def text(draw, position, value, size, fill='#f4f7fb', bold=False):
    draw.text(position, value, font=font(size, bold), fill=fill)


def fit_text(draw, position, value, size, max_width, fill='#f4f7fb', bold=False):
    while draw.textlength(value, font=font(size, bold)) > max_width and size > 18:
        size -= 1
    text(draw, position, value, size, fill, bold)


def pill(draw, x, y, label, color, dark=True, size=20):
    width = int(draw.textlength(label, font=font(size))) + 36
    draw.rounded_rectangle((x, y, x + width, y + 42), radius=21,
                           fill='#203a46' if dark else '#e8efeb', outline='#37525e' if dark else '#ceddd6')
    text(draw, (x + 18, y + 7), label, size, color)
    return x + width + 12


def background():
    yy, xx = np.mgrid[0:H, 0:W]
    glow = np.exp(-(((xx - 1520) / 900) ** 2 + ((yy - 200) / 650) ** 2))
    base = np.zeros((H, W, 3), dtype=np.uint8)
    for channel, (low, high) in enumerate([(13, 16), (28, 26), (38, 28)]):
        base[:, :, channel] = low + glow * high
    return Image.fromarray(base)


BACKGROUND = None
SCREENSHOTS = {}


def screenshot(scene):
    key = (scene['image'], tuple(scene['crop']))
    if key not in SCREENSHOTS:
        source = Image.open(PUBLIC / 'screens' / scene['image']).convert('RGB')
        x, y, width, height = scene['crop']
        if min(x, y) < 0 or width <= 0 or height <= 0 or x + width > source.width or y + height > source.height:
            raise ValueError(f"Invalid screenshot crop: {scene['id']}")
        SCREENSHOTS[key] = source.crop((x, y, x + width, y + height))
    return SCREENSHOTS[key]


def rounded_paste(canvas, picture, xy, radius=16):
    mask = Image.new('L', picture.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, picture.width, picture.height), radius=radius, fill=255)
    canvas.paste(picture, xy, mask)


def screen_card(canvas, scene, local, duration, box):
    x, y, width, height = box
    # Resize once per screenshot; camera movement uses the original aspect ratio.
    source = screenshot(scene)
    progress = ease((local - 1.0) / max(1, duration - 2))
    zoom = 1 + 0.035 * progress
    crop_w, crop_h = source.width / zoom, source.height / zoom
    anchor = scene.get('focus', [0.5, 0.5, 0, 0])
    center_x = (anchor[0] + anchor[2] / 2) * source.width
    center_y = (anchor[1] + anchor[3] / 2) * source.height
    left = max(0, min(source.width - crop_w, center_x - crop_w / 2))
    top = max(0, min(source.height - crop_h, center_y - crop_h / 2))
    # Contain keeps all of the captured UI visible, including button labels.
    picture = ImageOps.contain(source.crop((left, top, left + crop_w, top + crop_h)),
                               (width - 24, height - 56), Image.Resampling.LANCZOS)
    shadow = Image.new('RGBA', canvas.size)
    ImageDraw.Draw(shadow).rounded_rectangle((x - 8, y + 16, x + width + 8, y + height + 25),
                                             radius=26, fill=(0, 0, 0, 95))
    canvas.paste(Image.alpha_composite(canvas.convert('RGBA'), shadow.filter(ImageFilter.GaussianBlur(22))).convert('RGB'))
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle((x, y, x + width, y + height), radius=22, fill='#eff3f6', outline='#63727c', width=2)
    draw.rounded_rectangle((x + 2, y + 2, x + width - 2, y + 42), radius=20, fill='#edf1f3')
    draw.rectangle((x + 2, y + 24, x + width - 2, y + 44), fill='#edf1f3')
    for i, color in enumerate(['#dca6a3', '#dcc895', '#9cbfb1']):
        draw.ellipse((x + 19 + i * 23, y + 17, x + 28 + i * 23, y + 26), fill=color)
    text(draw, (x + 110, y + 10), 'AI비드  /  ' + scene['chapter'], 17, '#4e6472')
    text(draw, (x + width - 165, y + 10), '실제 서비스 화면', 16, '#647783')
    px = x + (width - picture.width) // 2
    py = y + 46 + (height - 56 - picture.height) // 2
    rounded_paste(canvas, picture, (px, py), 10)
    draw = ImageDraw.Draw(canvas)
    if scene.get('focus') and local > 2.5:
        fx, fy, fw, fh = scene['focus']
        sx, sy = picture.width / crop_w, picture.height / crop_h
        rect = (px + (fx * source.width - left) * sx, py + (fy * source.height - top) * sy,
                px + ((fx + fw) * source.width - left) * sx, py + ((fy + fh) * source.height - top) * sy)
        color = COLORS[scene['accent']]
        draw.rounded_rectangle(rect, radius=9, outline=color, width=3)
        # A deliberately slow cursor guides the eye; it does not simulate a real API result.
        arrival = ease((local - 2.5) / 1.3)
        cx = rect[2] - 20 + (1 - arrival) * 100
        cy = rect[3] - 10 + (1 - arrival) * 70
        draw.polygon([(cx, cy), (cx + 3, cy + 25), (cx + 10, cy + 17), (cx + 23, cy + 17)],
                     fill='#172c3a', outline='#ffffff', width=2)


def render_frame(story, scene, index, local, timeline, total):
    global BACKGROUND
    if BACKGROUND is None:
        BACKGROUND = background()
    canvas = BACKGROUND.copy()
    draw = ImageDraw.Draw(canvas)
    accent = COLORS[scene['accent']]
    # Fixed editorial grid avoids text/viewport drift across exports.
    draw.rounded_rectangle((76, 58, 124, 106), radius=13, fill=accent)
    text(draw, (85, 65), 'AI', 26, '#142e37', True)
    text(draw, (141, 63), 'AI비드', 29, '#edf8f7', True)
    text(draw, (1590, 70), 'PRODUCT WALKTHROUGH', 16, '#8ca3af')
    draw.line((76, 133, 1844, 133), fill='#31444f', width=1)

    if scene['id'] in ('intro', 'outro'):
        screen_card(canvas, scene, local, scene['duration'], (985, 260, 820, 550))
        draw = ImageDraw.Draw(canvas)
        text(draw, (88, 232), scene['eyebrow'], 20, accent)
        for row, line in enumerate(scene['title']):
            fit_text(draw, (84, 306 + row * 103), line, 76, 890,
                     accent if row == 1 else '#f4f7fb', True)
        for row, line in enumerate(scene['description']):
            text(draw, (90, 555 + row * 44), line, 29, '#adc0c9')
        x = 90
        for tag in scene['tags']:
            x = pill(draw, x, 700, tag, accent, size=24)
        text(draw, (90, 827), '자료 수집    →    작성 계획    →    함께 수정    →    검토 · 내보내기', 24, '#b5c7ce')
    else:
        text(draw, (88, 185), scene['eyebrow'], 18, accent)
        for row, line in enumerate(scene['title']):
            fit_text(draw, (84, 300 + row * 76), line, 49, 390,
                     accent if row == 1 else '#f4f7fb', True)
        draw.rounded_rectangle((88, 489, 142, 494), radius=2, fill=accent)
        for row, line in enumerate(scene['description']):
            fit_text(draw, (88, 529 + row * 41), line, 25, 368, '#adc0c9')
        y = 660
        for tag in scene['tags']:
            pill(draw, 88, y, tag, accent)
            y += 55
        screen_card(canvas, scene, local, scene['duration'], (490, 222, 1335, 707))
        draw = ImageDraw.Draw(canvas)
        if local > 1.5:
            text(draw, (515, 955), scene['detail'], 25, accent)

    # Visible disclosure remains present in every frame, not just an end disclaimer.
    text(draw, (88, 1004), '기능 시연 · 가상 회사/프로젝트 자료 · 작업 시간 편집', 19, '#8ca3af')
    text(draw, (1630, 1004), f"{index + 1:02d} / {len(story['scenes']):02d}", 19, '#a3b9c2')
    x, width, gap = 88, 1744, 8
    for i, item in enumerate(story['scenes']):
        segment = (width - gap * (len(story['scenes']) - 1)) * item['duration'] / total
        draw.rounded_rectangle((x, 1050, x + segment, 1054), radius=2, fill='#344954')
        completed = 1 if i < index else (local / item['duration'] if i == index else 0)
        if completed > 0:
            draw.rounded_rectangle((x, 1050, x + segment * completed, 1054), radius=2, fill=accent)
        x += segment + gap
    return canvas


def vtt_time(seconds):
    milliseconds = round(seconds * 1000)
    return f'{milliseconds // 3600000:02d}:{milliseconds // 60000 % 60:02d}:{milliseconds // 1000 % 60:02d}.{milliseconds % 1000:03d}'


def caption_text(story):
    cues = ['WEBVTT', '']
    offset, number = 0, 0
    for scene in story['scenes']:
        sentences = [part.strip() + '.' for part in scene['narration'].rstrip('.').split('. ') if part.strip()]
        wav = ROOT / '.local/product-demo/narration' / (scene['id'] + '.wav')
        span = scene['duration'] - .85
        if wav.is_file():
            with wave.open(str(wav)) as audio:
                span = min(span, audio.getnframes() / audio.getframerate())
        weights = sum(len(sentence) for sentence in sentences)
        elapsed = 0
        for sentence in sentences:
            length = span * len(sentence) / weights
            number += 1
            cues += [str(number), f'{vtt_time(offset + .45 + elapsed)} --> {vtt_time(offset + .45 + elapsed + length)}', sentence, '']
            elapsed += length
        offset += scene['duration']
    return '\n'.join(cues)


def build_audio(story, narration_folder, target, silent):
    if silent:
        return False
    rate = 48000
    total = sum(s['duration'] for s in story['scenes'])
    samples = np.zeros(int(total * rate), dtype=np.float32)
    # Original quiet electric-piano bed; no stock music or licensing dependency.
    chords = [(146.83, 220, 293.66), (130.81, 196, 261.63), (174.61, 261.63, 349.23), (164.81, 246.94, 329.63)]
    for beat in np.arange(0, total, 1.5):
        chord = chords[int(beat // 6) % len(chords)]
        frequency = chord[int(beat / 1.5) % 3]
        count = min(int(3.0 * rate), len(samples) - int(beat * rate))
        t = np.arange(count) / rate
        envelope = np.minimum(t / 0.025, 1) * np.exp(-t * 2)
        tone = (np.sin(2 * math.pi * frequency * t) + 0.25 * np.sin(2 * math.pi * frequency * 2 * t)) * envelope * 0.015
        start = int(beat * rate)
        samples[start:start + count] += tone
    offset = 0
    for scene in story['scenes']:
        wav_path = narration_folder / (scene['id'] + '.wav')
        if not wav_path.is_file():
            raise ValueError(f'Missing narration {wav_path}. Run narrate.ps1 or use --silent.')
        with wave.open(str(wav_path), 'rb') as source:
            if source.getsampwidth() != 2:
                raise ValueError('Narration must be PCM16 WAV.')
            data = np.frombuffer(source.readframes(source.getnframes()), dtype='<i2').astype(np.float32) / 32768
            data = data.reshape(-1, source.getnchannels()).mean(axis=1)
            source_rate = source.getframerate()
        allowed = scene['duration'] - 0.85
        actual = len(data) / source_rate
        if actual > allowed + 0.02:
            raise ValueError(f"Narration '{scene['id']}' is {actual:.2f}s; scene needs at least {math.ceil(actual + .85)}s. Shorten narration or lengthen storyboard duration.")
        resampled = np.interp(np.arange(int(actual * rate)) / rate, np.arange(len(data)) / source_rate, data)
        peak = max(0.001, float(np.max(np.abs(resampled))))
        resampled *= 0.68 / peak
        start = int((offset + 0.45) * rate)
        samples[start:start + len(resampled)] += resampled
        offset += scene['duration']
    fade_samples = int(1.2 * rate)
    samples[:fade_samples] *= np.linspace(0, 1, fade_samples)
    samples[-fade_samples:] *= np.linspace(1, 0, fade_samples)
    # Short fade prevents end truncation even when a replacement voice has trailing audio.
    stereo = np.repeat(np.clip(samples, -.95, .95)[:, None], 2, axis=1)
    with wave.open(str(target), 'wb') as output:
        output.setnchannels(2)
        output.setsampwidth(2)
        output.setframerate(rate)
        output.writeframes((stereo * 32767).astype('<i2').tobytes())
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--preview', action='store_true', help='Render each scene midpoint plus contact sheet only.')
    parser.add_argument('--silent', action='store_true', help='Export without narration/music.')
    args = parser.parse_args()
    story = json.loads(STORY_PATH.read_text(encoding='utf-8'))
    assert (story['width'], story['height']) == (W, H)
    ids = [s['id'] for s in story['scenes']]
    assert len(set(ids)) == len(ids)
    assert all(isinstance(s['duration'], int) and s['duration'] > 0 for s in story['scenes'])
    total = sum(s['duration'] for s in story['scenes'])
    qa = ROOT / '.local/product-demo/render'
    qa.mkdir(parents=True, exist_ok=True)
    thumbnails = []
    offset = 0
    for i, scene in enumerate(story['scenes']):
        frame = render_frame(story, scene, i, scene['duration'] / 2, offset, total)
        frame.save(qa / (scene['id'] + '.jpg'), quality=94)
        thumbnails.append(frame.resize((640, 360), Image.Resampling.LANCZOS))
        offset += scene['duration']
    contact = Image.new('RGB', (1280, 360 * math.ceil(len(thumbnails) / 2)), '#0d1c26')
    for i, thumb in enumerate(thumbnails):
        contact.paste(thumb, ((i % 2) * 640, (i // 2) * 360))
    contact.save(qa / 'contact-sheet.jpg', quality=94)
    print(f'Storyboard: {len(ids)} scenes, {total}s; preview saved to {qa}', flush=True)
    if args.preview:
        return
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    # Render to temporary files and publish all artifacts only after the encoder succeeds.
    with tempfile.TemporaryDirectory(prefix='bid3-demo-', dir=qa) as tmp:
        tmp = Path(tmp)
        audio_path = tmp / 'audio.wav'
        has_audio = build_audio(story, ROOT / '.local/product-demo/narration', audio_path, args.silent)
        command = [ffmpeg, '-hide_banner', '-loglevel', 'error', '-y', '-f', 'rawvideo', '-vcodec', 'rawvideo',
                   '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(story['fps']), '-i', '-']
        if has_audio:
            command += ['-i', str(audio_path), '-c:a', 'aac', '-b:a', '160k']
        command += ['-c:v', 'libx264', '-preset', 'fast', '-crf', '21', '-pix_fmt', 'yuv420p',
                    '-movflags', '+faststart', '-t', str(total), str(tmp / 'intro.mp4')]
        with (tmp / 'ffmpeg.log').open('w') as log:
            encoder = subprocess.Popen(command, stdin=subprocess.PIPE, stderr=log)
            try:
                offset = 0
                previous = None
                for index, scene in enumerate(story['scenes']):
                    print(f"Rendering {index + 1}/{len(ids)}: {scene['id']}", flush=True)
                    for n in range(scene['duration'] * story['fps']):
                        local = n / story['fps']
                        frame = render_frame(story, scene, index, local, offset, total)
                        if previous is not None and local < .4:
                            frame = Image.blend(previous, frame, ease(local / .4))
                        encoder.stdin.write(frame.tobytes())
                    previous = frame
                    offset += scene['duration']
                encoder.stdin.close()
                if encoder.wait() != 0:
                    raise RuntimeError((tmp / 'ffmpeg.log').read_text())
            finally:
                if encoder.poll() is None:
                    encoder.kill()
        # Also embed subtitles for the downloaded MP4; the web uses the same VTT.
        (tmp / 'captions.vtt').write_text(caption_text(story), encoding='utf-8')
        subprocess.run([ffmpeg, '-v', 'error', '-y', '-i', str(tmp / 'intro.mp4'), '-i', str(tmp / 'captions.vtt'),
                        '-c', 'copy', '-c:s', 'mov_text', '-metadata:s:s:0', 'language=kor',
                        '-disposition:s:0', 'default', '-movflags', '+faststart', str(tmp / 'captioned.mp4')], check=True)
        os.replace(tmp / 'captioned.mp4', PUBLIC / 'intro.mp4')
    render_frame(story, story['scenes'][0], 0, 3.5, 0, total).save(PUBLIC / 'poster.webp', quality=94)
    (PUBLIC / 'captions.ko.vtt').write_text(caption_text(story), encoding='utf-8')
    result = {'version': story['version'], 'duration': total, 'resolution': [W, H], 'fps': story['fps'],
              'storyboard_sha256': hashlib.sha256(json.dumps(story, sort_keys=True, ensure_ascii=False).encode('utf-8')).hexdigest(),
              'narration': has_audio, 'sha256': hashlib.sha256((PUBLIC / 'intro.mp4').read_bytes()).hexdigest(),
              'sources': {name: hashlib.sha256((PUBLIC / 'screens' / name).read_bytes()).hexdigest()
                          for name in sorted({s['image'] for s in story['scenes']})}}
    (PUBLIC / 'build.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f"Exported {PUBLIC / 'intro.mp4'} ({(PUBLIC / 'intro.mp4').stat().st_size / 1048576:.1f} MB)")


if __name__ == '__main__':
    main()
