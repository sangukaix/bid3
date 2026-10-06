"""Conservative font measurements, shared by bid proposals and presentation edits.

This estimates text fit; it does not replace an Office-rendered visual check.
It never clips text or changes shapes.
"""
from functools import lru_cache
from pathlib import Path
from PIL import ImageFont


def frame_geometry(frame, width, height, fallback=18):
    runs = [run for paragraph in frame.paragraphs for run in paragraph.runs]
    size = next((run.font.size.pt for run in runs if run.font.size),
                next((p.font.size.pt for p in frame.paragraphs if p.font.size),fallback))
    family = next((run.font.name for run in runs if run.font.name),
                  next((p.font.name for p in frame.paragraphs if p.font.name),''))
    bold = next((run.font.bold for run in runs if run.font.bold is not None),
                next((p.font.bold for p in frame.paragraphs if p.font.bold is not None), False))
    paragraph = frame.paragraphs[0]
    spacing = paragraph.line_spacing
    leading = spacing.pt if hasattr(spacing, 'pt') else size * (spacing if isinstance(spacing, float) else 1.2)
    return {'width': round(width / 12700, 2), 'height': round(height / 12700, 2),
            'font_size': size, 'font_family': family, 'bold': bool(bold),
            'margin_left': frame.margin_left.pt, 'margin_right': frame.margin_right.pt,
            'margin_top': frame.margin_top.pt, 'margin_bottom': frame.margin_bottom.pt,
            'line_height_ratio': max(1, leading / size),
            'line_height_pt': spacing.pt if hasattr(spacing,'pt') else None,
            'paragraph_gap': (paragraph.space_before.pt if paragraph.space_before else 0)
                             + (paragraph.space_after.pt if paragraph.space_after else 0),
            'wrap': frame.word_wrap is not False}


@lru_cache(maxsize=64)
def font_path(family, bold=False):
    name = (family or '').lower().replace(' ', '')
    choices = {'맑은고딕': 'malgun.ttf', 'malgungothic': 'malgun.ttf',
               'arial': 'arial.ttf', 'calibri': 'calibri.ttf', 'segoeui': 'segoeui.ttf',
               'aptos': 'aptos.ttf', 'notosanskr': 'NotoSansKR-VF.ttf'}
    requested = Path('C:/Windows/Fonts') / choices.get(name, '__missing__')
    if bold:
        variants = {'malgun.ttf':'malgunbd.ttf', 'arial.ttf':'arialbd.ttf',
                    'calibri.ttf':'calibrib.ttf', 'segoeui.ttf':'segoeuib.ttf'}
        candidate = requested.with_name(variants.get(requested.name, requested.name))
        if candidate.is_file(): return str(candidate), True
    if requested.is_file(): return str(requested), True
    for candidate in (f'C:/Windows/Fonts/{"malgunbd.ttf" if bold else "malgun.ttf"}', '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'):
        if Path(candidate).is_file(): return candidate, False
    return '', False


@lru_cache(maxsize=256)
def load_font(path, size):
    return ImageFont.truetype(path, max(1, round(size * 4))) if path else ImageFont.load_default(size=max(1, round(size * 4)))


def measure_text(text, element, size=None):
    size = float(size or element.get('font_size') or element.get('font_size_pt') or 18)
    width = max(1, float(element.get('width', 0)) - element.get('margin_left', 3) - element.get('margin_right', 3))
    height = max(1, float(element.get('height', 0)) - element.get('margin_top', 2) - element.get('margin_bottom', 2))
    path, exact = font_path(element.get('font_family', ''), element.get('bold', False))
    # Theme/inherited fonts may render wider than the fallback; reserve room.
    if not exact: width *= .94
    font = load_font(path, size)
    def length(value): return font.getlength(value) / 4
    lines = []
    for paragraph in (str(text).replace('\v', '\n').split('\n') if str(text).strip() else []):
        if not element.get('wrap', True):
            lines.append(paragraph); continue
        current = ''
        for char in paragraph:
            if current and length(current + char) > width:
                # Prefer a word boundary without removing any content.
                boundary = current.rfind(' ')
                if boundary > 0:
                    lines.append(current[:boundary]); current = current[boundary + 1:] + char
                else:
                    lines.append(current); current = char
            else: current += char
        lines.append(current)
    required = len(lines) * (element.get('line_height_pt') or size * element.get('line_height_ratio', 1.2))
    required += (max(0, str(text).count('\n')) * element.get('paragraph_gap', 0)) if lines else 0
    widest = max((length(line) for line in lines), default=0)
    return {'fits': required <= height + 1 and widest <= width + 1,
            'font_size': size, 'line_count': len(lines), 'required_height': round(required, 1),
            'available_height': round(height, 1), 'available_width': round(width, 1),
            'measured_width': round(widest, 1), 'font_resolved': exact, 'estimated': True}


def fitting_size(text, element, minimum=11):
    original = float(element.get('font_size') or element.get('font_size_pt') or 18)
    # Small labels must not be enlarged or silently reduced below their original size.
    minimum = min(original, minimum)
    size = original
    while True:
        result = measure_text(text, element, size)
        if result['fits']: return size, result
        if size <= minimum: return None, result
        size = max(minimum, round(size - .5, 2))
