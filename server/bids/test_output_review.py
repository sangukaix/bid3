from io import BytesIO
from django.test import SimpleTestCase
from pptx import Presentation
from pptx.util import Inches,Pt
from .services.proposal_pptx_renderer import inspect_proposal_quality, _slide_elements


class OutputReviewTests(SimpleTestCase):
    def test_one_line_with_large_font_is_not_exempt_just_because_named_as_footer(self):
        prs=Presentation();page=prs.slides.add_slide(prs.slide_layouts[6])
        caption=page.shapes.add_textbox(0,Inches(5),Inches(3),Inches(.2));caption.name='footer-page-1'
        caption.text='01';caption.text_frame.paragraphs[0].runs[0].font.size=Pt(40)
        buffer=BytesIO();prs.save(buffer);result=inspect_proposal_quality(buffer.getvalue())
        self.assertEqual(len(result['severe_overflow_items']),1)

    def test_tight_single_line_page_label_is_not_reported_as_small_body_or_clipped(self):
        prs=Presentation();page=prs.slides.add_slide(prs.slide_layouts[6])
        caption=page.shapes.add_textbox(0,Inches(5),Inches(2),Inches(.2));caption.name='footer-page-1'
        caption.text='01';caption.text_frame.paragraphs[0].runs[0].font.size=Pt(8)
        buffer=BytesIO();prs.save(buffer);result=inspect_proposal_quality(buffer.getvalue())
        self.assertEqual(result['small_text_items'],[]);self.assertEqual(result['overflow_items'],[])
    def test_plain_template_guidance_is_flagged_but_real_proposal_text_is_allowed(self):
        prs=Presentation();page=prs.slides.add_slide(prs.slide_layouts[6])
        for i,text in enumerate(('사업명 제안서','회사 이미지 · 수행 실적 · 인증 자료','정보시스템 구축 제안서')):
            page.shapes.add_textbox(0,Inches(i),Inches(8),Inches(1)).text=text
        buffer=BytesIO();prs.save(buffer);quality=inspect_proposal_quality(buffer.getvalue())
        self.assertEqual([i['marker'] for i in quality['template_leftovers']],['사업명 제안서','회사 이미지 · 수행 실적 · 인증 자료'])
        self.assertFalse(quality['passed'])

    def test_cover_title_is_recognized_and_severe_overflow_is_not_a_small_caption(self):
        prs=Presentation();page=prs.slides.add_slide(prs.slide_layouts[6])
        title=page.shapes.add_textbox(0,0,Inches(3),Inches(.5));title.name='cover-title'
        title.text='집중형 외국어 교육 프로그램 운영 용역 제안서'
        title.text_frame.paragraphs[0].runs[0].font.size=Pt(40)
        buffer=BytesIO();prs.save(buffer);quality=inspect_proposal_quality(buffer.getvalue())
        self.assertEqual(_slide_elements(page)[0]['kind'],'title')
        self.assertEqual(len(quality['severe_overflow_items']),1)
