"""Bounded local review and repair before a candidate becomes a revision."""
import hashlib
import json
from typing import Literal
from django.conf import settings
from pydantic import BaseModel, Field
from bids.services.text_geometry import fitting_size
from .ai import call, PageText, RULES, compact_slide

VERSION = 'studio-quality-v1'


class Finding(BaseModel):
    target: str
    problem: str = Field(max_length=400)
    severity: Literal['warning','error']


class Citation(BaseModel):
    target: str
    reference_id: str
    part: int = Field(ge=1)


class Review(BaseModel):
    findings: list[Finding] = Field(default_factory=list, max_length=20)
    citations: list[Citation] = Field(default_factory=list, max_length=80)


def normalize_edits(slide, edits):
    elements={e['target']:e for e in slide['elements']}
    result=[]; seen=set()
    for edit in edits:
        target=edit['target']
        if target not in elements or target in seen: raise ValueError('검수할 텍스트 위치가 없거나 중복되었습니다.')
        seen.add(target)
        text=str(edit['text'])
        if len(text)>3000: raise ValueError('AI 작성 문구가 너무 깁니다.')
        result.append({'target':target,'text':text})
    return result


def layout_review(slide, edits):
    elements={e['target']:e for e in slide['elements']}
    prepared=[]; findings=[]; measurements=[]
    for edit in edits:
        element=elements[edit['target']]
        font_size, result=fitting_size(edit['text'],element)
        prepared.append({**edit,**({'font_size':font_size} if font_size is not None and font_size != element['font_size'] else {})})
        measurements.append({'target':edit['target'],**result})
        if not result['fits']:
            findings.append({'target':edit['target'],'severity':'error','problem':'상자/표 셀 공간을 초과합니다. 사실·조건을 유지하며 짧게 작성하세요.'})
    return prepared, findings, measurements


def semantic_review(slide, edits, brief, packet):
    if not edits or not getattr(settings,'STUDIO_SEMANTIC_REVIEW',True): return {'findings':[],'citations':[],'_generation':{}}
    result=call(Review,RULES+'작성본 검수입니다. 요청에 대한 누락·모순·미제공 수치와 완료 주장, '
        '중요한 부정/미확인 조건의 삭제를 검사하세요. 사용자 설명을 바꾸거나 디자인을 재작성하지 마세요. '
        '실제 문제인 수정 target에만 findings를 쓰세요. severity는 error 또는 warning만 사용하세요. 근거가 충분하면 findings는 빈 배열입니다. '
        '출처가 없어도 단순 제목·개인 설명·명시된 목표/계획은 허용합니다. '
        '미측정·미구현 등 원문의 상태를 같은 뜻으로 간결하게 바꾼 것은 허용합니다. '
        '내용의 사실·조건이 유지된다면 소제목의 분류 취향만으로 문제를 만들지 마세요. '
        '공간·폰트·줄바꿈은 별도의 코드 검사가 처리합니다. 발생할 수 있다는 가정만으로 배치 경고를 만들지 마세요. '
        '참고자료가 직접 뒷받침하는 문구만 citations에 target, 실제 reference_id, 발췌의 part를 기록하세요. '
        '수치가 일치한다는 것만으로 인과/성과를 검증했다고 판단하지 마세요.',
        {**packet,'request':brief,'original_slide':compact_slide(slide),'proposed_edits':edits})
    targets={e['target'] for e in edits}
    if any(f['target'] not in targets for f in result['findings']): raise ValueError('검수 결과가 수정 범위를 벗어났습니다.')
    used=set(result.get('_generation',{}).get('source_ids',[r['id'] for r in packet.get('references',[])]))
    sources={r['id']:{part['part'] for part in r['excerpts']} for r in packet.get('references',[]) if r['id'] in used}
    for citation in result['citations']:
        if citation['target'] not in targets or citation['part'] not in sources.get(citation['reference_id'],set()):
            raise ValueError('검수 결과에 제공되지 않은 참고자료 또는 발췌 위치가 있습니다.')
    return result


def review_page(slide, edits, brief, packet):
    original=normalize_edits(slide,edits)
    prepared, layout, measurements=layout_review(slide,original)
    review=semantic_review(slide,original,brief,packet)
    before=[*layout,*review['findings']]
    repaired=False
    if any(f['severity']=='error' for f in before):
        targets={f['target'] for f in before if f['severity']=='error'}
        repair=call(PageText,RULES+'검사에서 지적한 target만 한 번 보완합니다. 나머지 문구는 그대로 두세요. '
            '수치·날짜·기간·부정·미확인 조건은 유지하고, 근거 없는 사실은 제거하세요. '
            '문장 중간을 잘라내지 마세요. 질문이 필요하면 questions에 적으세요.',
            {**packet,'request':brief,'slide':compact_slide(slide),'proposed_edits':original,'findings':before,
             'allowed_targets':sorted(targets)})
        if repair['questions']:
            error=ValueError('검수 보완에 추가 설명이 필요합니다: '+' / '.join(repair['questions']))
            error.questions=repair['questions']
            raise error
        fixes=normalize_edits(slide,repair['edits'])
        if {e['target'] for e in fixes}!=targets: raise ValueError('자동 보완의 수정 범위가 검사 대상과 다릅니다.')
        merged={e['target']:e for e in original}; merged.update({e['target']:e for e in fixes})
        original=list(merged.values()); repaired=True
        prepared,layout,measurements=layout_review(slide,original)
        review=semantic_review(slide,original,brief,packet)
    findings=[*layout,*review['findings']]
    audit={'version':VERSION,'page':slide['number'],'checked_targets':[e['target'] for e in original],
           'repaired_once':repaired,'initial_findings':before,'findings':findings,'layout_measurements':measurements,
           'semantic_checked':bool(original) and getattr(settings,'STUDIO_SEMANTIC_REVIEW',True),
           'citations':review['citations'],'review_generation':review.get('_generation',{}),
           'sources':[{'id':r['id'],'name':r['name'],'updated_at':r['updated_at'],
                       'parts':[p['part'] for p in r['excerpts']],
                       'excerpt_digest':hashlib.sha256(json.dumps(r['excerpts'],ensure_ascii=False).encode()).hexdigest()}
                      for r in packet.get('references',[]) if r['id'] in review.get('_generation',{}).get('source_ids',[r['id'] for r in packet.get('references',[])])],
           'omitted_reference_count':review.get('_generation',{}).get('omitted_reference_count',packet.get('omitted_reference_count',0)),
           'visual_check_required':True}
    if any(f['severity']=='error' for f in findings):
        error=ValueError('한 번 보완한 뒤에도 확인이 필요합니다: '+' / '.join(f['problem'] for f in findings if f['severity']=='error'))
        error.quality_review=audit
        raise error
    return prepared,audit
