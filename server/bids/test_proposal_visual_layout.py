"""Regressions from the photo template's real automatic-generation output."""
import json
from pathlib import Path
from unittest.mock import Mock, patch

from django.conf import settings
from django.test import SimpleTestCase

from .services.proposal_pptx_renderer import extract_pptx_inventory
from .services.proposal_text_fit import fit_slide_edits, layout_fits, preserves_phrases, protected_phrases
from .services.proposal_evidence import slot_evidence


class PhotoTextLayoutTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.inventory = extract_pptx_inventory(Path(settings.PROPOSAL_TEMPLATES['education_photo']['path']))

    def test_reference_copy_fits_without_reducing_photo_typography(self):
        for slide in self.inventory:
            for element in slide['elements']:
                if not element.get('label'):
                    self.assertTrue(layout_fits(element['text'], element), (slide['slide_number'], element['target']))

    def test_large_value_cannot_be_replaced_by_a_small_paragraph(self):
        value = next(e for e in self.inventory[2]['elements'] if e['target'] == 'shape-7')
        self.assertEqual(value['copy_role'], 'value')
        self.assertEqual(value['max_lines'], 1)
        long_text = '주 30분 또는 50분 교육과정 운영 및 학습 성과 확인'
        self.assertLess(len(long_text), value['max_chars'])
        self.assertFalse(layout_fits(long_text, value))
        self.assertTrue(layout_fits('주 30분·50분', value))

    def test_shortening_cannot_keep_250_as_a_substring_of_1250(self):
        self.assertFalse(preserves_phrases('교육 인원 1250명', ['250명']))
        self.assertFalse(preserves_phrases('주 130분 수업', ['30분']))
        self.assertTrue(preserves_phrases('주 30분·50분 수업', ['30분','50분']))

    def test_one_to_one_conversation_is_not_one_occurrence(self):
        from .services.proposal_coverage import CoverageVerdict, confirmed_quote
        self.assertEqual(protected_phrases('원어민 1:1 회화'),['1:1'])
        for text,expected in [('원어민 1:1 전화·화상 회화 제공',True),
                              ('원어민 1:2 전화·화상 회화 제공',False),
                              ('원어민 1회 전화·화상 회화 제공',False)]:
            verdict=CoverageVerdict(covered=True,slide_number=1,quote=text)
            self.assertEqual(confirmed_quote(verdict,'원어민 1:1 회화 제공',{1:text}),expected)

    def test_shortening_keeps_contract_entities_articles_and_scope(self):
        text='최저임금법 제10조 제1항 고시액 이상, 상생결제(우리은행), 2차 이하 협력, 최근 3개년 물량·부가세 면제'
        phrases=protected_phrases(text)
        for phrase in ['최저임금법','제10조 제1항','고시액 이상','상생결제','우리은행','2차','이하','3개년','최근 3개년','면제']:
            self.assertIn(phrase,phrases)
        self.assertFalse(preserves_phrases('고시액 이상 계약·대금 지급 협력',phrases))

    @patch('bids.services.rag.proposal.build_proposal_model')
    @patch('bids.services.rag.proposal.structured_chain')
    @patch('bids.services.proposal_text_fit.structured_chain')
    def test_explicit_feedback_preserves_the_requested_pending_condition(self, shorten, factory, model):
        from .services.rag.proposal import build_local_slide_plan
        def main_chain(prompt,model,schema):
            edits=schema.model_fields['edits'].annotation
            self.assertIs(edits.model_fields['shape-0'].annotation,str)
            return Mock(invoke=lambda inputs:schema.model_validate({
                'edits':{'shape-0':'운영 기록 확인 가능'},'review_notes':[]}))
        def short_chain(prompt,model,schema):
            return Mock(invoke=lambda inputs:schema.model_validate({'shape-0':[
                '운영 기록 확인 필요','운영 내용 확인 필요','현행 기록 확인 필요']}))
        factory.side_effect=main_chain;shorten.side_effect=short_chain
        result=build_local_slide_plan({'slide_number':18,'title':'지원','elements':[
            {'target':'shape-0','text':'운영 기록력 확인 필요','max_chars':35}]},
            {'instruction':'shape-0의 기록력을 자연스럽게 수정하고 확인 필요 조건을 유지하세요.'},feedback=True)
        self.assertIn('확인 필요',result.slide_changes[0].text_changes[0].revised_text)

    @patch('bids.services.proposal_text_fit.structured_chain')
    def test_readable_mixed_script_copy_is_not_shortened_for_a_character_estimate(self, factory):
        element=next(e for e in self.inventory[7]['elements'] if e['target']=='shape-9')
        text='원어민 1:1 회화, 전화·화상 모두 제공, 모바일·PC 접속 지원'
        self.assertGreater(len(text),element['max_chars'])
        self.assertTrue(layout_fits(text,element))
        self.assertEqual(fit_slide_edits({'body':text},{'body':element},Mock()),{'body':text})
        factory.assert_not_called()

    def test_new_body_copy_cannot_leave_a_single_korean_syllable_on_its_own_line(self):
        element=next(e for e in self.inventory[6]['elements'] if e['target']=='shape-7')
        self.assertFalse(layout_fits('자연스러운 대\n화',element))
        self.assertTrue(layout_fits('생활 표현으로 자연스럽게 대화',element))

    def test_narrow_sequence_labels_keep_their_role(self):
        numbers = [e for e in self.inventory[6]['elements'] if e['text'] in {'01','02','03'}]
        self.assertEqual(len(numbers), 3)
        self.assertTrue(all(e.get('label') and e.get('copy_role') == 'sequence' for e in numbers))

    def test_numeric_slots_have_explicit_semantic_contracts(self):
        summary = {e['target']:e for e in self.inventory[2]['elements']}
        self.assertIn('주당 수업시간', summary['shape-7']['content_hint'])
        self.assertIn('사업기간', summary['shape-9']['content_hint'])
        for target in ['shape-5','shape-7','shape-9']:
            self.assertEqual(summary[target]['value_type'], 'number')
        self.assertEqual(summary['shape-5']['copy_role'], 'value')

    def test_slot_sources_keep_short_numeric_rows_next_to_long_overview(self):
        register={'requirements':[
            {'requirement':'사업기간: 2027년부터 2028년까지 운영'},
            {'requirement':'수업유형: 주 30분 또는 주 50분 기준'},
            {'requirement':'학습형태: 원어민 1:1 전화·화상 회화'},
            {'requirement':'사업의 효율적 운영과 성과 관리 및 지원 방안을 구체적으로 제안'}]}
        text=slot_evidence(self.inventory[2]['elements'],register)
        self.assertIn('주 30분 또는 주 50분',text)
        self.assertIn('2027년부터 2028년',text)
        self.assertIn('원어민 1:1',text)
        self.assertLessEqual(len(text.encode('utf-8')),5700)

    @patch('bids.services.rag.proposal.build_proposal_model')
    @patch('bids.services.rag.proposal.structured_chain')
    def test_missing_currency_retries_the_money_slot(self, factory, model):
        from .services.rag.proposal import build_local_slide_plan
        values=iter(['287,910,000','287,910,000원'])
        def chain(prompt, model, schema):
            return Mock(invoke=lambda inputs:schema.model_validate({
                'edits':{'shape-0':next(values)},'review_notes':[]}))
        factory.side_effect=chain
        result=build_local_slide_plan({'slide_number':13,'title':'예산','role':'metrics','elements':[
            {'target':'shape-0','text':'[총사업예산]','max_chars':35,'value_type':'money'}]},
            {'requirement_context':'사업예산: 287,910,000원'})
        self.assertEqual(factory.call_count,2)
        self.assertEqual(result.slide_changes[0].text_changes[0].revised_text,'287,910,000원')

    @patch('bids.services.proposal_coverage.structured_chain')
    def test_separate_documents_are_preserved_without_inferred_completion(self, factory):
        from .services.proposal_coverage import review_requirement_coverage
        report=review_requirement_coverage({'requirements':[
            {'requirement':'서명한 참가신청서 제출'}, {'requirement':'가격입찰서 별도 제출'}]},
            {'writing_plan':{'items':[{'id':'R0001','channel':'form'},{'id':'R0002','channel':'price'}]}},Mock())
        factory.assert_not_called()
        self.assertEqual(report['total_count'],2)
        self.assertEqual(report['covered_count'],0)
        self.assertEqual(report['unverified_count'],0)
        self.assertTrue(all(r['status']=='separate_confirmation' and not r['covered'] for r in report['checks']))

    @patch('bids.services.proposal_coverage.structured_chain')
    def test_official_name_is_an_identity_check_not_a_delivery_method(self, factory):
        from .services.proposal_coverage import review_requirement_coverage
        name='2027-2028년 KOTRA 전화외국어 교육과정 운영 위탁'
        register={'requirements':[{'requirement':'과업명: '+name}]}
        plan={'slide_changes':[{'slide_number':1,'action':'UPDATE','text_changes':[
            {'revised_text':name.replace('전화외국어','\n전화외국어')}]}]}
        good=review_requirement_coverage(register,plan,Mock())
        self.assertEqual(good['covered_count'],1)
        self.assertEqual(good['checks'][0]['quote'],name)
        plan['slide_changes'][0]['text_changes'][0]['revised_text']=name.replace('KOTRA','다른 기관')
        bad=review_requirement_coverage(register,plan,Mock())
        self.assertEqual(bad['covered_count'],0)
        factory.assert_not_called()

    @patch('bids.services.proposal_coverage.structured_chain')
    def test_planned_pages_do_not_hide_the_actual_timeline_answer(self, factory):
        from .services.proposal_coverage import review_requirement_coverage
        answer='2027.01.01부터 2028.12.31까지 연차별 운영하며 입찰 일정에 따라 착수일 조정이 가능합니다.'
        def chain(prompt,model,schema):
            def invoke(inputs):
                rows=json.loads(inputs['review_context'])
                self.assertIn(14,[p['slide_number'] for p in rows[0]['candidates']])
                return schema.model_validate({'R0001':{'covered':True,'slide_number':14,'quote':answer}})
            return Mock(invoke=invoke)
        factory.side_effect=chain
        plan={'writing_plan':{'items':[{'id':'R0001','channel':'body','output_slide_numbers':[3,8]}]},
              'slide_changes':[{'slide_number':n,'action':'UPDATE','text_changes':[{'revised_text':t}]}
                  for n,t in [(3,'2027-2028년 교육 운영'),(8,'주 30분 또는 50분 수업'),(14,answer)]]}
        report=review_requirement_coverage({'requirements':[{'requirement':
            '과업기간: 2027. 1. 1. ~ 2028. 12. 31. (입찰 일정에 따라 착수일 조정 가능)'}]},plan,Mock())
        self.assertTrue(report['checks'][0]['covered'])

    @patch('bids.services.proposal_coverage.structured_chain')
    def test_local_readback_does_not_mix_independent_source_conditions(self, factory):
        from .services.proposal_coverage import review_requirement_coverage
        from .services.llm import OllamaChatModel
        sizes=[]
        def chain(prompt,model,schema):
            sizes.append(len(schema.model_fields))
            return Mock(invoke=lambda inputs:schema.model_validate({key:{'covered':False} for key in schema.model_fields}))
        factory.side_effect=chain
        report=review_requirement_coverage({'requirements':[{'requirement':f'조건 {n}'} for n in range(3)]},
            {},OllamaChatModel(model='gemma4:26b'))
        self.assertEqual(sizes,[1,1,1])
        self.assertEqual(report['total_count'],3)
        self.assertEqual(report['unverified_count'],0)

    @patch('bids.services.proposal_text_fit.structured_chain')
    def test_geometric_retry_keeps_quantities_and_accepted_sibling_copy(self, factory):
        element = next(e for e in self.inventory[2]['elements'] if e['target'] == 'shape-7')
        contexts = []
        def chain(prompt, model, schema):
            def invoke(values):
                contexts.append(json.loads(values['edit_context']))
                return schema.model_validate({'value':['주 30분', '주 30분·50분', '주 50분']})
            return Mock(invoke=invoke)
        factory.side_effect = chain
        result = fit_slide_edits({'value':'주 30분 또는 50분 교육과정 운영 및 학습 성과 확인', 'sibling':'수업시간 기록 대조'},
                                {'value':element,'sibling':{'text':'수업시간 기록 대조','max_chars':30}},Mock())
        self.assertEqual(result['value'], '주 30분·50분')
        self.assertEqual(result['sibling'], '수업시간 기록 대조')
        self.assertEqual(contexts[0]['accepted_edits'], {'sibling':'수업시간 기록 대조'})
        self.assertEqual(contexts[0]['targets']['value']['required_phrases'], ['30분','50분'])
