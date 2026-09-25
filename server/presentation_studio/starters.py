"""Neutral placeholders for bundled designs; never applied to user uploads."""
from .decks import Deck, inventory

TITLES=['발표 제목','발표 구성','핵심 내용','주제 이해와 질문','목표와 범위','주요 내용 정리',
        '접근 방법','구성 및 흐름','실행 계획','프로젝트 구성','수행 일정','역할과 협업',
        '확인할 사항','검토 및 검증','준비와 운영','자료 및 근거','결과 정리','활용 방안','마무리','질문과 답변']


def starter_content(content):
    deck=Deck(content)
    for slide in inventory(content):
        edits=[]; main_title=next((e['target'] for e in slide['elements'] if e['name']=='bid3-title'),None)
        if main_title is None and slide['elements']: main_title=slide['elements'][0]['target']
        for element in slide['elements']:
            text=element['text'].strip(); name=element['name']
            if not text or text.isdigit(): continue
            if element['target']==main_title: replacement=TITLES[(slide['number']-1)%len(TITLES)]
            elif name=='bid3-fixed-page': continue
            elif name=='bid3-fixed-footer': replacement='나의 발표자료'
            elif name=='bid3-fixed-eyebrow': replacement='프로젝트 발표'
            elif element['height']<30 or len(text)<16: replacement='내용 입력'
            else: replacement='이곳에 발표 내용을 작성하세요.'
            edits.append({'target':element['target'],'text':replacement})
        deck.edit(slide['number'],edits)
    return deck.bytes()
