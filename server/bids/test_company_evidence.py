from datetime import timedelta
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from .models import CompanyDocument, CompanyKnowledgeItem, CompanyWebsitePage
from .services.company_evidence import effective_review_status, evidence_fingerprint
from .services.company_knowledge import build_company_knowledge_context


class CompanyEvidenceTests(TestCase):
    def setUp(self):
        directory=TemporaryDirectory();self.addCleanup(directory.cleanup)
        override=override_settings(MEDIA_ROOT=directory.name);override.enable();self.addCleanup(override.disable)
        self.user=get_user_model().objects.create_user(username='evidence-owner')
        self.other=get_user_model().objects.create_user(username='evidence-other')
        self.document=CompanyDocument.objects.create(user=self.user,document_type='evidence',
            original_name='원문.docx',file=SimpleUploadedFile('source.docx',b'original evidence'))
        self.item=CompanyKnowledgeItem.objects.create(user=self.user,source_document=self.document,
            category='performance',title='교육 운영',content='250명 대상 교육을 수행했습니다.',
            source_locations=['2쪽'],evidence_excerpt='2025년 250명 대상 교육을 수행했습니다.')
        self.client=APIClient();self.client.force_authenticate(self.user)

    def review(self, **values):
        return self.client.patch(f'/api/company-evidence/{self.item.pk}/',{
            'review_status':'approved','confirm_source_review':True,
            'expected_updated_at':self.item.updated_at.isoformat(),**values},format='json')

    def approve(self):
        self.assertEqual(self.review().status_code,200)
        self.item.refresh_from_db()

    def test_new_items_remain_pending_and_approval_records_the_owner(self):
        self.assertEqual(effective_review_status(self.item),'pending')
        with patch('bids.services.company_knowledge.build_company_knowledge_model') as model:
            self.approve();self.client.get('/api/company-evidence/')
            model.assert_not_called()
        self.assertEqual(self.item.reviewed_by,self.user)
        self.assertTrue(self.item.reviewed_at)
        self.assertEqual(effective_review_status(self.item),'approved')
        self.assertEqual(self.item.review_fingerprint,evidence_fingerprint(self.item))

    def test_approval_requires_source_acknowledgment_and_locations(self):
        self.assertEqual(self.review(confirm_source_review=False).status_code,400)
        self.item.evidence_excerpt='';self.item.save()
        self.assertEqual(self.review().status_code,400)
        self.item.refresh_from_db();self.assertEqual(self.item.review_status,'pending')

    def test_missing_source_and_cross_owner_source_cannot_be_approved(self):
        Path(self.document.file.path).unlink()
        self.assertEqual(self.review().status_code,400)
        self.document.user=self.other;self.document.save()
        self.assertEqual(self.review().status_code,400)

    def test_owner_isolation_in_list_review_analysis_and_download(self):
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.get('/api/company-evidence/').data['count'],0)
        self.assertEqual(self.review().status_code,404)
        self.assertEqual(self.client.post(f'/api/company-documents/{self.document.pk}/knowledge/').status_code,404)
        self.assertEqual(self.client.get(f'/api/company-documents/{self.document.pk}/download/').status_code,404)
        self.client.force_authenticate(None)
        self.assertIn(self.client.get('/api/company-evidence/').status_code,(401,403))

    def test_stale_update_and_injected_reviewer_fields_are_rejected(self):
        old=self.item.updated_at
        CompanyKnowledgeItem.objects.filter(pk=self.item.pk).update(title='새 제목',updated_at=old+timedelta(seconds=1))
        self.assertEqual(self.review(expected_updated_at=old.isoformat()).status_code,409)
        self.assertEqual(self.review(reviewed_by=self.other.pk).status_code,400)
        self.item.refresh_from_db();self.assertEqual(self.item.review_status,'pending')

    def test_same_clock_tick_still_invalidates_an_old_review_form(self):
        old=self.item.updated_at
        with patch('bids.company_evidence_views.timezone.now',return_value=old):
            self.assertEqual(self.review().status_code,200)
        self.assertEqual(self.review(expected_updated_at=old.isoformat()).status_code,409)

    def test_corrections_are_bound_to_the_reviewed_content_and_source_is_unchanged(self):
        original=Path(self.document.file.path).read_bytes()
        self.assertEqual(self.review(content='2025년 250명 대상 교육을 수행했습니다.',review_note='원문 확인').status_code,200)
        self.item.refresh_from_db()
        self.assertEqual(effective_review_status(self.item),'approved')
        self.assertEqual(Path(self.document.file.path).read_bytes(),original)
        CompanyKnowledgeItem.objects.filter(pk=self.item.pk).update(content='500명 교육을 수행했습니다.')
        self.item.refresh_from_db();self.assertEqual(effective_review_status(self.item),'changed')

    def test_changed_document_and_changed_website_invalidate_approval(self):
        self.approve()
        Path(self.document.file.path).write_bytes(b'changed evidence')
        self.assertEqual(effective_review_status(self.item),'changed')
        page=CompanyWebsitePage.objects.create(user=self.user,url='https://example.com/about',
            extracted_text='기존 사실',content_hash='a'*64)
        self.item.source_document=None;self.item.source_website_page=page;self.item.save()
        self.approve()
        page.extracted_text='변경된 사실';page.save()
        self.item.refresh_from_db();self.assertEqual(effective_review_status(self.item),'changed')

    def test_expiry_is_inclusive_and_expired_reapproval_is_rejected(self):
        today=timezone.localdate()
        self.assertEqual(self.review(valid_until=(today-timedelta(days=1)).isoformat()).status_code,400)
        self.assertEqual(self.review(valid_until=today.isoformat()).status_code,200)
        self.item.refresh_from_db()
        self.assertEqual(effective_review_status(self.item),'approved')
        with patch('bids.services.company_evidence.timezone.localdate',return_value=today+timedelta(days=1)):
            self.assertEqual(effective_review_status(self.item),'expired')
            listing=self.client.get('/api/company-evidence/?status=expired').data
            self.assertEqual(listing['count'],1)

    @patch('bids.services.company_knowledge.prepare_user_company_knowledge',return_value={'item_count':3})
    def test_only_current_approved_items_are_included_without_truncating_evidence(self,prepare):
        pending=CompanyKnowledgeItem.objects.create(user=self.user,source_document=self.document,
            category='certification',title='미검토 인증',content='미검토 인증은 본문에 없어야 합니다.')
        self.approve()
        context,info=build_company_knowledge_context(self.user)
        self.assertIn(self.item.content,context);self.assertIn(self.item.evidence_excerpt,context)
        self.assertNotIn(pending.content,context)
        self.assertEqual(info['included_reviewed_count'],1)
        self.assertEqual(info['review_counts']['pending'],1)
        context,info=build_company_knowledge_context(self.user,max_chars=10)
        self.assertNotIn(self.item.content,context);self.assertEqual(info['included_reviewed_count'],0)
        Path(self.document.file.path).write_bytes(b'changed evidence')
        context,_=build_company_knowledge_context(self.user)
        self.assertNotIn(self.item.content,context)

    def test_exclusion_and_return_to_pending_remove_approval(self):
        self.approve()
        self.assertEqual(self.review(review_status='excluded').status_code,200)
        self.item.refresh_from_db();self.assertEqual(effective_review_status(self.item),'excluded')
        self.assertEqual(self.review(review_status='pending').status_code,200)
        self.item.refresh_from_db()
        self.assertIsNone(self.item.reviewed_by);self.assertEqual(self.item.review_fingerprint,'')

    def test_source_download_returns_original_bytes(self):
        response=self.client.get(f'/api/company-documents/{self.document.pk}/download/')
        self.assertEqual(response.status_code,200)
        self.assertEqual(b''.join(response.streaming_content),b'original evidence');response.close()

    def test_valid_pdf_evidence_upload_and_invalid_pdf_rejection(self):
        from pypdf import PdfWriter
        writer=PdfWriter();writer.add_blank_page(300,300);buffer=BytesIO();writer.write(buffer)
        response=self.client.post('/api/company-documents/',{'document_type':'evidence',
            'file':SimpleUploadedFile('proof.pdf',buffer.getvalue(),content_type='application/pdf')},format='multipart')
        self.assertEqual(response.status_code,201)
        response=self.client.post('/api/company-documents/',{'document_type':'evidence',
            'file':SimpleUploadedFile('broken.pdf',b'not PDF')},format='multipart')
        self.assertEqual(response.status_code,400)

    @patch('bids.services.company_knowledge.prepare_company_knowledge')
    def test_explicit_analysis_is_owner_scoped_and_does_not_approve(self,prepare):
        prepare.return_value={'item_count':1,'reused':True}
        response=self.client.post(f'/api/company-documents/{self.document.pk}/knowledge/',{},format='json')
        self.assertEqual(response.status_code,200);self.assertTrue(response.data['reused'])
        self.item.refresh_from_db();self.assertEqual(self.item.review_status,'pending')
        self.assertFalse(prepare.call_args.kwargs['force'])
