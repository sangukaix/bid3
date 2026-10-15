import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings
from langchain_core.documents import Document

from bids.services.download_bid_attachment import download_bid_attachment
from bids.services.get_bid_attachments import fetch_bid_attachments
from bids.services.rag.prepare_docs_for_ai import prepare_docs_for_ai


class NoticeFreshnessTests(SimpleTestCase):
    def test_buyer_selection_is_not_written_as_contractor_delivery(self):
        from .services.proposal_planning import channel_for
        self.assertEqual(channel_for({'requirement':'협상적격자 중 종합평가 점수 순서대로 협상 진행'}), 'manual')
        self.assertEqual(channel_for({'requirement':'평가위원회 구성 후 제안서 심사'}), 'manual')
        self.assertEqual(channel_for({'requirement':'본 사업은 안전보건수준평가 대상 아님'}), 'manual')
        self.assertEqual(channel_for({'requirement':'제안사는 강사 선정 기준과 강사 관리 방안을 제시한다'}), 'body')
        self.assertEqual(channel_for({'requirement':'제안사는 학습자 평가를 실시하고 교육과정을 추천한다'}), 'body')
        self.assertEqual(channel_for({'category':'제안서 형식','requirement':'표지에 정식 공고명을 기재'}), 'manual')
        self.assertEqual(channel_for({'category':'가격 및 산출','requirement':'언어별 할인 단가표를 작성'}), 'price')

    def test_submission_preflight_flags_changed_notice_without_mutating_saved_plan(self):
        from hashlib import sha256
        from .test_artifact_evidence import deck
        from .services.proposal_submission_check import submission_report
        content = deck('교육 운영 계획을 제안합니다.')
        plan = {'document_processing':{'bid_ntce_ord':'000','processed_files':['rfp.pdf'],
                'failed_files':[], 'attachment_checked_at':'2026-10-15T00:00:00Z'},
                'final_document_review':{'file_sha256':sha256(content).hexdigest(),
                    'company_evidence_sha256':sha256(b'').hexdigest(),
                    'review_required_count':0,'failures':[], 'stale':False}}
        report = submission_report(content, plan, '', current_ord='001')
        source = next(item for item in report['automatic_checks'] if item['id']=='sources')
        self.assertEqual(source['status'], 'attention')
        self.assertIn('차수', source['detail'])
        self.assertTrue(report['final_document_review']['stale'])
        self.assertFalse(plan['final_document_review']['stale'])

    def test_cached_failures_remain_visible_and_new_generation_retries(self):
        with tempfile.TemporaryDirectory() as directory, override_settings(BASE_DIR=Path(directory)), \
             patch('bids.services.rag.prepare_docs_for_ai.search_mode', return_value='keyword'), \
             patch('bids.services.rag.prepare_docs_for_ai.BidNotice') as notices, \
             patch('bids.services.rag.prepare_docs_for_ai.fetch_bid_attachments') as fetch, \
             patch('bids.services.rag.prepare_docs_for_ai.download_bid_attachment') as download, \
             patch('bids.services.rag.prepare_docs_for_ai.extract_documents') as extract:
            notices.objects.filter.return_value.order_by.return_value.first.return_value = SimpleNamespace(
                bid_ntce_no='BID1', bid_ntce_ord='000', business_type='용역')
            fetch.return_value = [{'filename':'rfp.txt','download_url':'https://example.com/rfp'}]
            download.return_value = Path(directory) / 'rfp.txt'
            extract.return_value = SimpleNamespace(
                documents=[Document(page_content='교육 기간 30일', metadata={'file_name':'rfp.txt'})],
                processed_files=['rfp.txt'], failed_files=[{'file_name':'terms.pdf','reason':'스캔 문서'}])
            prepare_docs_for_ai('BID1')
            cached = prepare_docs_for_ai('BID1')
            self.assertFalse(cached['created'])
            self.assertEqual(cached['failed_files'][0]['file_name'], 'terms.pdf')
            self.assertEqual(fetch.call_count, 1)
            self.assertTrue(prepare_docs_for_ai('BID1', refresh=True)['created'])
            self.assertEqual(fetch.call_count, 2)

    def test_live_list_is_checked_but_unchanged_complete_cache_is_reused(self):
        with tempfile.TemporaryDirectory() as directory, override_settings(BASE_DIR=Path(directory)), \
             patch('bids.services.rag.prepare_docs_for_ai.search_mode', return_value='keyword'), \
             patch('bids.services.rag.prepare_docs_for_ai.BidNotice') as notices, \
             patch('bids.services.rag.prepare_docs_for_ai.fetch_bid_attachments') as fetch, \
             patch('bids.services.rag.prepare_docs_for_ai.download_bid_attachment') as download, \
             patch('bids.services.rag.prepare_docs_for_ai.extract_documents') as extract:
            notice = SimpleNamespace(bid_ntce_no='BID1', bid_ntce_ord='000', business_type='용역')
            notices.objects.filter.return_value.order_by.return_value.first.return_value = notice
            fetch.return_value = [{'filename':'rfp.txt','download_url':'https://example.com/v1'}]
            download.return_value = Path(directory) / 'rfp.txt'
            extract.return_value = SimpleNamespace(
                documents=[Document(page_content='교육 기간 30일', metadata={'file_name':'rfp.txt'})],
                processed_files=['rfp.txt'], failed_files=[])
            prepare_docs_for_ai('BID1')
            checked = prepare_docs_for_ai('BID1', refresh=True)
            self.assertFalse(checked['created'])
            self.assertTrue(checked['attachment_checked_at'])
            self.assertEqual(download.call_count, 1)
            fetch.side_effect = RuntimeError('offline')
            with self.assertRaises(RuntimeError):
                prepare_docs_for_ai('BID1', refresh=True)
            fetch.side_effect = None
            fetch.return_value = [{'filename':'rfp.txt','download_url':'https://example.com/v2'}]
            self.assertTrue(prepare_docs_for_ai('BID1', refresh=True)['created'])
            notice.bid_ntce_ord = '001'
            with self.assertRaisesMessage(ValueError, '최신 공고를 다시 저장'):
                prepare_docs_for_ai('BID1', refresh=True, expected_ord='000')
            self.assertTrue(prepare_docs_for_ai('BID1')['created'])
            self.assertEqual(download.call_count, 3)

    @override_settings(G2B_API_KEY='test')
    @patch('bids.services.get_bid_attachments.requests.get')
    def test_newer_notice_is_not_silently_ignored(self, get):
        get.return_value.json.return_value = {'response':{'header':{'resultCode':'00'},
            'body':{'items':[{'bidNtceOrd':'000'}, {'bidNtceOrd':'001'}]}}}
        with self.assertRaisesMessage(ValueError, '정정'):
            fetch_bid_attachments('BID1', '용역', '000')

    @patch('bids.services.download_bid_attachment.requests.get')
    def test_interrupted_download_preserves_existing_original(self, get):
        with tempfile.TemporaryDirectory() as directory, override_settings(MEDIA_ROOT=Path(directory)):
            original = Path(directory) / 'bid_documents' / 'BID1' / 'rfp.pdf'
            original.parent.mkdir(parents=True)
            original.write_bytes(b'original')
            def interrupted(**kwargs):
                yield b'partial'
                raise RuntimeError('connection lost')
            get.return_value.iter_content.side_effect = interrupted
            with self.assertRaises(RuntimeError):
                download_bid_attachment('BID1', {'filename':'rfp.pdf','download_url':'https://example.com/rfp'})
            self.assertEqual(original.read_bytes(), b'original')
            self.assertEqual(list(original.parent.iterdir()), [original])
            get.return_value.close.assert_called_once()

    @patch('bids.services.download_bid_attachment.requests.get')
    def test_attachment_folder_cannot_escape_media(self, get):
        with tempfile.TemporaryDirectory() as directory, override_settings(MEDIA_ROOT=Path(directory)):
            with self.assertRaises(ValueError):
                download_bid_attachment('../../outside', {'filename':'rfp.pdf','download_url':'https://example.com/rfp'})
            get.assert_not_called()
