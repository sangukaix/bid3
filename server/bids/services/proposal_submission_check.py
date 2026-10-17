"""Read-only preflight of the current file; never certifies eligibility or submission."""
from copy import deepcopy
from hashlib import sha256
from .proposal_evidence import requirement_rows
from .proposal_planning import channel_for, CHANNELS
from .proposal_output_review import refresh_output_review
from .proposal_final_review import invalidate_final_review
from .proposal_pptx_renderer import inspect_proposal_quality


def submission_report(content, saved_plan, knowledge, *, current_ord=None):
    plan=deepcopy(saved_plan or {})
    output=refresh_output_review(content,plan)
    invalidate_final_review(content,plan,knowledge)
    final=plan.get('final_document_review')
    processing=plan.get('document_processing')
    changed_source=bool(current_ord is not None and processing and
                        processing.get('bid_ntce_ord') is not None and
                        processing['bid_ntce_ord'] != current_ord)
    if changed_source and final:
        final['stale']=True
    quality=inspect_proposal_quality(content)
    rows=requirement_rows(plan.get('requirement_register',{}))
    separate=[{**row,'channel':channel_for(row),'channel_label':CHANNELS[channel_for(row)]}
              for row in rows if channel_for(row)!='body']
    checks=[]
    def add(key,title,status,detail):
        checks.append({'id':key,'title':title,'status':status,'detail':detail})
    add('requirements','본문 요구사항 인용',
        'unchecked' if not rows or not output['body_total_count'] else 'attention' if output['body_review_required_count'] else 'checked',
        f"본문 조건 {output['body_total_count']}개 중 현재 답변 인용 {output['body_matched_count']}개. 본문 외 서식·증빙·가격·절차 {output['separate_count']}개는 별도 확인 대상입니다. 인용은 별도 서류의 제출 완료 판정이 아닙니다."
        if rows else '공고 요구사항 목록이 없습니다. 공고 원문 확인 후 생성·검수가 필요합니다.')
    add('claims','회사 주장·문서 내 모순',
        'unchecked' if not final or final.get('stale') else 'attention' if final['review_required_count'] else 'checked',
        '현재 파일·회사 근거·공고 조건에 맞는 전체 AI 검수가 필요합니다.' if not final or final.get('stale')
        else f"회사 주장·모순 확인 대상 {final['review_required_count']}건, 자동 검수 실패 {len(final['failures'])}건. AI 분류의 오판·누락 가능성이 있습니다.")
    add('unfinished','미완성·확인 필요 문구',
        'attention' if output['open_text_items'] or quality['unresolved_placeholders'] or quality['template_leftovers'] else 'checked',
        f"확인 필요 문구 {len(output['open_text_items'])}개, 미완성 자리표시자 {len(quality['unresolved_placeholders'])}개, 양식 안내 {len(quality['template_leftovers'])}개.")
    add('layout','분량·글자·빈 페이지',
        'attention' if quality['review_items'] or output['page_limit_exceeded'] else 'checked',
        ' / '.join([*quality['review_items'],*(['저장된 분량 제한 초과'] if output['page_limit_exceeded'] else [])])
        or '코드 검사에서 출력 이상을 찾지 못했습니다. PPTX와 PDF의 글자·표·이미지는 직접 확인하세요.')
    materials=plan.get('company_material_usage')
    if materials is not None:
        used=materials.get('used_assets',[])
        add('company_materials','회사 원문 이미지·도식',
            'attention' if used or materials.get('failed_files') or materials.get('warnings') else 'unchecked',
            f"회사 원문 시각 자료 {len(used)}개를 사용했습니다. 이미지 안의 수치·대상·현행 적용 범위는 직접 확인해야 하며 텍스트 AI 검수에 포함되지 않습니다. "
            f"회사 자료 읽기 실패 {len(materials.get('failed_files',[]))}개.")
    add('sources','등록된 공고 첨부 읽기',
        'unchecked' if not processing or not processing.get('processed_files') else 'attention' if changed_source or processing.get('failed_files') or not processing.get('attachment_checked_at') else 'checked',
        ('생성에 사용한 공고 차수와 현재 공고 차수가 다릅니다. 최신 공고로 다시 생성·검수하세요. ' if changed_source else '') +
        f"읽기 실패 {len(processing.get('failed_files',[]))}개. 첨부 목록 대조: {processing.get('attachment_checked_at') or '기록 없음'}. 새 첨부·정정공고와 원문 전체는 제출 직전에 별도 확인해야 합니다."
        if processing else '첨부 처리 기록이 없습니다. 공고 원문과 요구사항 목록의 범위를 직접 확인하세요.')
    return {'version':'submission-preflight-v1','file_sha256':sha256(content).hexdigest(),
        'automatic_checks':checks,'separate_requirements':separate,
        'manual_checks':[
            {'title':'최신 공고·정정공고','detail':'나라장터 원문에서 마감·변경·추가 첨부와 전체 요구사항을 확인하세요.'},
            {'title':'참가 자격·회사 증빙','detail':'실적·인력·인증의 진위와 유효기간, 필수 자격 충족을 확인하세요. 사진·회사 화면·도식의 출처와 과거 수치·현행 적용 범위도 직접 대조하세요.'},
            {'title':'별도 서식·가격·제출 방법','detail':'지정 서식·서명·날인·가격·부가세·제출 파일 형식과 제출 방법을 확인하세요.'},
        ],'output_review':output,'final_document_review':final,'quality_review':quality,
        'limitation':'자동 점검은 제출 가능성 인증이나 담당자의 최종 검토 완료가 아닙니다. 본문 인용만으로 별도 서식·증빙·가격을 완료 처리하지 않습니다.'}
