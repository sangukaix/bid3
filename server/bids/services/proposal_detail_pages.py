"""Editable, source-linked detail pages from the already generated writing briefs."""
from io import BytesIO
import re

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.util import Pt

from .proposal_pptx_renderer import MAX_OUTPUT_SLIDES, inspect_proposal_quality, _replace_text_frame
from .text_geometry import measure_text
from .proposal_evidence import requirement_rows

FONT = '맑은 고딕'
BODY_SIZE = 12
INK = '172C48'
ACCENT = '147D78'


def _height(text, width, size=BODY_SIZE):
    measured = measure_text(text, {'width':width, 'height':10000, 'font_size':size,
        'font_family':FONT, 'margin_left':0, 'margin_right':0,
        'margin_top':0, 'margin_bottom':0, 'line_height_ratio':1.25})
    return measured['required_height'] + 4


def _text(slide, name, text, x, y, width, height, size=BODY_SIZE, color=INK, bold=False):
    box = slide.shapes.add_textbox(Pt(x), Pt(y), Pt(width), Pt(height))
    box.name = name
    frame = box.text_frame
    frame.word_wrap = True
    frame.margin_left = frame.margin_right = frame.margin_top = frame.margin_bottom = 0
    frame.text = text
    for paragraph in frame.paragraphs:
        # Use the same point leading as the height calculation. Office's
        # proportional leading includes font metrics and can overrun the box.
        paragraph.line_spacing = Pt(size * 1.25)
        paragraph.space_before = paragraph.space_after = Pt(0)
        paragraph.font.name = FONT
        paragraph.font.size = Pt(size)
        paragraph.font.bold = bold
        paragraph.font.color.rgb = RGBColor.from_string(color)


def _card(row, width, wide=False):
    condition = f"공고 조건 · {row['id']}\n{row['requirement']}"
    answer = '\n'.join(f'{label}: {row.get(key) or "확인 필요"}' for key,label in (
        ('method','수행안'), ('responsible','담당'), ('schedule','일정'),
        ('deliverable','산출물'), ('verification','검증')))
    question = ('확인 필요: ' + row['question']) if row.get('question') else ''
    if row.get('evidence_ids'):
        answer += '\n대조할 회사 근거 후보: ' + ', '.join(row['evidence_ids'])
    widths = (width*.30,width*.70-16,width*.70-16) if wide else (width,)*3
    heights = [_height(text,space) if text else 0 for text,space in zip((condition,answer,question),widths)]
    content_height = max(heights[0],sum(heights[1:])) if wide else sum(heights)
    return (condition,answer,question), heights, content_height + 28


def prepare_default_template_output(file_result, register):
    """Clean known illustrative copy and schedules only in fresh built-in-template output."""
    prs = Presentation(BytesIO(file_result['file_bytes']))
    rows = [row for row in requirement_rows(register)
            if re.search(r'^(?:교육|사업|용역|과업|수행|계약|운영)\s*기간\s*(?:[:：]|은)',row.get('requirement',''))]
    changed = []
    neutral_copy = {
        '모든 제안 내용은 실제 보유한 실적, 인력, 인증 및 정량적 수치에 근거합니다.':'회사 실적·인력·인증을 검토 완료된 자료와 대조합니다.',
        '실제 수행 경험과 검증된 전문 인력이 사업의 성공을 보장합니다.':'회사 근거 확인 필요\n실적·인력·인증 자료를\n검토 후 반영합니다.',
        '사업과 직접 관련된 자료만 배치합니다.':'해당 사업의 회사 증빙 확인 필요',
    }
    for number,slide in enumerate(prs.slides,1):
        for shape in slide.shapes:
            if getattr(shape,'has_text_frame',False) and ' '.join(shape.text.split()) in neutral_copy:
                _replace_text_frame(shape.text_frame,neutral_copy[' '.join(shape.text.split())])
            if shape.name=='closing-title' and getattr(shape,'has_text_frame',False) and shape.text.strip()=='확인 필요':
                _replace_text_frame(shape.text_frame,'성과 목표와 검증 계획')
            if shape.name in {'understanding-source','closing-eyebrow'} and getattr(shape,'has_text_frame',False):
                for paragraph in shape.text_frame.paragraphs:
                    for run in paragraph.runs:
                        if run.font.size and run.font.size.pt < 11:
                            run.font.size = Pt(11)
            if shape.name.startswith('phase-output-') and getattr(shape,'has_text_frame',False):
                match = re.fullmatch(r'주요 산출물\s*\[([^\[\]]+)\]\s*',shape.text)
                if match:
                    _replace_text_frame(shape.text_frame,'주요 산출물\n'+match.group(1))
        names = {shape.name for shape in slide.shapes}
        if not {'schedule-header','week-0','schedule-bar-0'} <= names:
            continue
        # The built-in sample's fixed durations are not grounded in this RFP.
        for shape in list(slide.shapes):
            if shape.name.startswith(('schedule-','week-')):
                shape._element.getparent().remove(shape._element)
        width = prs.slide_width.pt - 108
        y, bottom = 160, prs.slide_height.pt - 70
        _text(slide,'schedule-source-heading','공고에 명시된 일정',54,y,width,23,16,ACCENT,True)
        y += 32
        for row in rows:
            text = row['requirement']
            height = _height(text,width)
            if y+height > bottom-45:
                break
            _text(slide,'bid3-requirement-schedule-'+row['id'],text,54,y,width,height)
            y += height+10
        message = '단계별 세부 기간은 착수 시 협의하여 확정합니다.'
        if not rows:
            message = '공고에서 사업·교육 기간을 확인하지 못했습니다. 단계별 세부 기간은 원문·담당자 확인 후 확정합니다.'
        _text(slide,'schedule-pending',message,54,min(y+8,bottom-40),width,40,12,'9A5B15')
        slide.notes_slide.notes_text_frame.text += '\n공고 일정 원문:\n'+'\n'.join(
            row['id']+' '+row['requirement']+' | '+' · '.join(row.get('sources',[])) for row in rows)
        changed.append(number)
    buffer=BytesIO();prs.save(buffer)
    result = {**file_result,'file_bytes':buffer.getvalue()}
    if changed:
        result['revision_log'] = [*file_result['revision_log'], *[
            {'source_slide_number':next((source for source,output in file_result.get('source_page_map',{}).items() if output==number),None),
             'output_slide_number':number,'action':'UPDATE',
             'title':'공고 일정 안내','reason':'고정 예시 주차·막대를 공고 원문 일정으로 교체',
             'changes':[],'warnings':[]} for number in changed]]
    result['quality_review'] = inspect_proposal_quality(result['file_bytes'],result['revision_log'])
    return result


def bind_existing_details(content, writing_plan):
    """Reconnect a read-only full review to actual named answer boxes, not old page numbers."""
    rows = {row['id']:row for row in writing_plan.get('items',[]) if row.get('channel')=='body'}
    placements = {}
    def shapes_in(shapes):
        for shape in shapes:
            if shape.shape_type == 6:
                yield from shapes_in(shape.shapes)
            else:
                yield shape
    for number,slide in enumerate(Presentation(BytesIO(content)).slides,1):
        for shape in shapes_in(slide.shapes):
            if not shape.name.startswith('bid3-answer-') or not getattr(shape,'has_text_frame',False) or not shape.text.strip():
                continue
            key = shape.name.removeprefix('bid3-answer-')
            if key in rows:
                placements.setdefault(key,[]).append(number)
    if not placements:
        return
    for key,numbers in placements.items():
        rows[key]['detail_slide_numbers'] = sorted(set(numbers))
        rows[key]['output_slide_numbers'] = list(dict.fromkeys([*numbers,*rows[key].get('output_slide_numbers',[])]))
    writing_plan['detail_pages'] = {'added_slide_count':len({n for numbers in placements.values() for n in numbers}),
        'placed_count':len(placements),'body_count':len(rows), 'placements':{key:min(numbers) for key,numbers in placements.items()},
        'omitted':[{'id':key,'reason':'현재 파일에 전용 상세 답변 상자가 없습니다. 기존 본문 답변을 별도 대조하세요.'} for key in rows if key not in placements],
        'source':'actual_pptx'}
    writing_plan.setdefault('notes',[]).append(f'현재 파일에서 본문 {len(rows)}개 중 {len(placements)}개의 상세 답변 위치를 다시 연결했습니다. 위치 연결은 조건 충족 판정이 아닙니다.')


def append_detail_pages(file_result, writing_plan, page_limit=None):
    """Never shorten a condition, shrink below 12pt, or silently omit an unplaced row.

    Template target counts are approximate; only verified RFP limits and the global
    output cap are hard bounds. Existing slides are preserved, not used as proof.
    """
    prs = Presentation(BytesIO(file_result['file_bytes']))
    original_count = len(prs.slides)
    layout = min(prs.slide_layouts, key=lambda item: len(item.placeholders))
    cap = min(MAX_OUTPUT_SLIDES, page_limit) if isinstance(page_limit,int) and not isinstance(page_limit,bool) and page_limit>0 else MAX_OUTPUT_SLIDES
    width, height = prs.slide_width.pt, prs.slide_height.pt
    margin, gap = 28, 16
    grid_width = (width - margin*2 - gap)/2
    column_width = grid_width
    top, bottom = 94, height - 34
    rows = [row for row in writing_plan.get('items',[]) if row.get('channel')=='body']
    rows = sorted(rows, key=lambda row: -(row.get('points') or 0))
    placements, omitted = {}, []
    slide = None
    wide = False
    columns = 2
    column, y = 0, top
    for row in rows:
        grid = _card(row, grid_width - 20)
        row_wide = grid[2] > (bottom-top)*.45 or grid_width < 140
        available_width = width-margin*2 if row_wide else grid_width
        proposed = _card(row,available_width-20,row_wide)
        if proposed[2] > bottom-top or available_width < 140:
            omitted.append({'id':row['id'], 'reason':'읽을 수 있는 크기로 한 칸에 배치할 수 없어 직접 편집이 필요합니다.'})
            continue
        texts, heights, card_height = _card(row, column_width - 20,wide)
        if slide is not None and card_height > bottom-top:
            column = columns
        if slide is not None and y + card_height > bottom:
            column += 1
            y = top
        if slide is None or column >= columns:
            if len(prs.slides) >= cap:
                omitted.append({'id':row['id'], 'reason':f'출력 상한 {cap}장으로 상세 페이지에 배치하지 못했습니다.'})
                continue
            slide = prs.slides.add_slide(layout)
            wide, column_width = row_wide,available_width
            columns = 1 if wide else 2
            texts, heights, card_height = proposed
            # Custom decks may have only one layout, with title/page placeholders.
            for shape in list(slide.shapes):
                shape._element.getparent().remove(shape._element)
            slide._element.set('showMasterSp','0')
            slide.background.fill.solid()
            slide.background.fill.fore_color.rgb = RGBColor(255,255,255)
            number = len(prs.slides)
            _text(slide,'section-label-detail','수행 계획 · 공고 조건별 상세 답변',margin,18,width-margin*2,18,11,ACCENT)
            heading = (row.get('category') or '세부 수행 계획').strip()
            if len(heading)>36:
                heading = heading[:35]+'…'
            _text(slide,'bid3-title',f'{heading} · {number-original_count:02d}',margin,43,width-margin*2,35,24,INK,True)
            _text(slide,'footer-detail','미래 수행 제안 · 회사 보유 사실 및 자격 증빙과 구분하여 검토',margin,height-24,width-margin*2-40,17,10)
            _text(slide,'footer-page-detail',str(number),width-margin-35,height-24,35,17,10)
            column, y = 0, top
        x = margin + column*(column_width+gap)
        card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE,Pt(x),Pt(y),Pt(column_width),Pt(card_height))
        card.fill.solid();card.fill.fore_color.rgb = RGBColor.from_string('F1F6F7')
        card.line.fill.background()
        current_y = y + 10
        for kind,text,text_height in zip(('requirement','answer','question'),texts,heights):
            if not text:
                continue
            text_width = column_width-20
            text_x = x+10
            if wide:
                if kind=='requirement':
                    text_width *= .30
                else:
                    text_x += (column_width-20)*.30+16
                    text_width = (column_width-20)*.70-16
                    if kind=='answer':
                        current_y = y+10
            _text(slide,f'bid3-{kind}-{row["id"]}',text,text_x,current_y,text_width,text_height,
                  color='9A5B15' if kind=='question' else INK)
            current_y += text_height
        placements[row['id']] = len(prs.slides)
        row['detail_slide_numbers'] = [len(prs.slides)]
        row['output_slide_numbers'] = list(dict.fromkeys([len(prs.slides),*row.get('output_slide_numbers',[])]))
        slide.notes_slide.notes_text_frame.text += '\n' + row['id'] + ' 원문 위치: ' + ' · '.join(row.get('sources',[]))
        y += card_height + gap
    added = len(prs.slides)-original_count
    summary = {'added_slide_count':added,'placed_count':len(placements),'body_count':len(rows),
               'placements':placements,'omitted':omitted,'page_cap':cap}
    writing_plan['detail_pages'] = summary
    writing_plan.setdefault('notes',[]).append(
        f'조건별 상세 수행안: 본문 {len(rows)}개 중 {len(placements)}개를 추가 {added}장에 배치했습니다. '
        '배치는 충족 판정이 아니며 수행안·확인 질문은 담당자가 검토해야 합니다.')
    if omitted:
        writing_plan['notes'].append('상세 페이지 미배치: '+', '.join(item['id'] for item in omitted)+'. 작성 계획의 해당 항목을 직접 보완하세요.')
    if not added:
        return file_result
    buffer = BytesIO();prs.save(buffer)
    result = {**file_result, 'file_bytes':buffer.getvalue(), 'output_slide_count':len(prs.slides),
        'revision_log':[*file_result['revision_log'], *[
            {'source_slide_number':None,'output_slide_number':number,'action':'ADD',
             'title':f'조건별 상세 수행안 {number-original_count}', 'reason':'공고 원문·작성 계획 기반 상세 답변',
             'changes':[],'warnings':[]} for number in range(original_count+1,len(prs.slides)+1)]]}
    result['quality_review'] = inspect_proposal_quality(result['file_bytes'],result['revision_log'])
    return result
