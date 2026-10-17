"""Printable internal review, separate from the audience-facing proposal."""
from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, LongTable, TableStyle

from .text_geometry import font_path


def review_pdf(report, writing_plan=None):
    font,_=font_path('맑은 고딕')
    if not font:
        raise ValueError('검수 PDF를 만들려면 한글 글꼴을 설치해야 합니다.')
    family='BID3Review'
    if family not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont(family,font))
    text=ParagraphStyle('review',fontName=family,fontSize=9,leading=13,wordWrap='CJK',spaceAfter=4)
    heading=ParagraphStyle('heading',parent=text,fontSize=17,leading=24,spaceAfter=10)
    def paragraph(value,style=text):
        return Paragraph(escape(str(value or '')).replace('\n','<br/>'),style)
    buffer=BytesIO()
    doc=SimpleDocTemplate(buffer,pagesize=landscape(A4),leftMargin=28,rightMargin=28,
                          topMargin=30,bottomMargin=30,title='BID3 내부 검수표 · 제출용 제안서와 별도')
    story=[paragraph('내부 검수표 · 제출용 제안서와 별도',heading),
           paragraph(report.get('bid_title','')),paragraph(report.get('bid_number','')),
           paragraph('대상 파일 SHA-256: '+report['file_sha256']),
           paragraph(report['limitation']),Spacer(1,10)]
    labels={'checked':'검사상 확인','attention':'확인 필요','unchecked':'미검수'}
    for item in report['automatic_checks']:
        story.append(paragraph(f"{item['title']} · {labels[item['status']]}\n{item['detail']}"))
    for item in report['manual_checks']:
        story.append(paragraph(item['title']+' · '+item['detail']))
    story += [Spacer(1,12),paragraph('공고 조건별 답변·증빙 대조',heading),
              paragraph('중복 원문 조건을 포함합니다. 답변 인용은 자격·증빙의 진위나 별도 서류 제출 완료를 인증하지 않습니다.')]
    briefs={r['id']:r for r in (writing_plan or {}).get('items',[])}
    rows=[[paragraph(x) for x in ['ID / 구분','공고 원문 조건 · 출처','작성 계획 · 확인할 사항','실제 출력 대조']]]
    for item in report['output_review']['checks']:
        brief=briefs.get(item['id'],{})
        plan='\n'.join(label+': '+str(brief[key]) for key,label in (
            ('method','수행안'),('responsible','담당'),('schedule','일정'),
            ('deliverable','산출물'),('verification','검증'),('question','질문')) if brief.get(key))
        verdict=('본문 인용 확인' if item['covered'] else '자동 대조 실패' if item.get('status')=='unverified' else '재검토 필요')
        details='\n'.join(filter(None,[verdict,str(item.get('slide_number') or '')+'쪽' if item.get('slide_number') else '',item.get('quote'),item.get('reason')]))
        rows.append([paragraph(item['id']+'\n'+item.get('channel_label','')),
                     paragraph(item['requirement']+'\n'+' · '.join(item.get('sources',[]))),
                     paragraph(plan),paragraph(details)])
    table=LongTable(rows,colWidths=[66,235,260,224],repeatRows=1,hAlign='LEFT')
    table.setStyle(TableStyle([
        ('VALIGN',(0,0),(-1,-1),'TOP'),('BACKGROUND',(0,0),(-1,0),colors.HexColor('#E8EDDF')),
        ('GRID',(0,0),(-1,-1),.35,colors.HexColor('#BFC8BE')),
        ('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7),
        ('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7)]))
    story.append(table)
    def footer(canvas,document):
        canvas.setFont(family,8);canvas.drawString(28,16,'BID3 내부 검수 기록 · 제안서 본문에 포함하지 않음')
        canvas.drawRightString(813,16,str(document.page))
    doc.build(story,onFirstPage=footer,onLaterPages=footer)
    return buffer.getvalue()
