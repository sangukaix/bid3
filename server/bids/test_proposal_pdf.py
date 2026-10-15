from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase, override_settings
from pypdf import PdfReader
from reportlab.pdfgen import canvas
from rest_framework.test import APIClient

from .models import BidNotice, BidProposal, SavedBid
from .services.proposal_pdf import a4_pdf


def source_pdf():
    stream = BytesIO()
    document = canvas.Canvas(stream, pagesize=(960, 540))
    for text in ('First page: 30 minutes per week', 'Second page: final handover'):
        document.drawString(30, 500, text)
        document.showPage()
    document.save()
    return stream.getvalue()


class ProposalPdfTests(SimpleTestCase):
    def test_a4_size_preserves_all_pages_and_selectable_text(self):
        original = source_pdf()
        for orientation, dimensions in [('portrait',(595.2756,841.8898)), ('landscape',(841.8898,595.2756))]:
            with self.subTest(orientation=orientation):
                output = PdfReader(BytesIO(a4_pdf(original, orientation)))
                self.assertEqual(len(output.pages), 2)
                for index, page in enumerate(output.pages):
                    self.assertAlmostEqual(float(page.mediabox.width), dimensions[0], places=3)
                    self.assertAlmostEqual(float(page.mediabox.height), dimensions[1], places=3)
                    self.assertEqual(page.extract_text(), PdfReader(BytesIO(original)).pages[index].extract_text())
        with self.assertRaises(ValueError):
            a4_pdf(original, 'invalid')


class ProposalPdfApiTests(TestCase):
    def test_pdf_download_keeps_owner_and_final_status_guards_and_original(self):
        with TemporaryDirectory() as directory, override_settings(MEDIA_ROOT=directory):
            user = get_user_model().objects.create_user(username='pdf-owner')
            foreign = get_user_model().objects.create_user(username='pdf-foreign')
            notice = BidNotice.objects.create(bid_ntce_no='PDF-001', title='교육 운영', business_type='용역')
            saved = SavedBid.objects.create(user=user, bid_notice=notice)
            proposal = BidProposal.objects.create(saved_bid=saved, output_format='pptx', revision_plan={'status':'draft'})
            proposal.generated_file.save('original.pptx', SimpleUploadedFile('original.pptx', b'preserved source'))
            preview = Path(directory) / 'preview.pdf'
            preview.write_bytes(source_pdf())
            client = APIClient()
            client.force_authenticate(user)
            endpoint = '/api/bids/PDF-001/proposal/download/'
            self.assertEqual(client.get(endpoint+'?file_format=pdf').status_code, 409)
            proposal.revision_plan = {'status':'final'}
            proposal.save()
            with patch('bids.services.proposal_preview.create_proposal_preview', return_value=preview):
                response = client.get(endpoint+'?file_format=pdf&orientation=portrait')
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response['Content-Type'], 'application/pdf')
                self.assertIn('A4-portrait.pdf', response['Content-Disposition'])
                self.assertEqual(len(PdfReader(BytesIO(response.content)).pages), 2)
                self.assertEqual(client.get(endpoint+'?file_format=pdf&orientation=unknown').status_code, 400)
                preview.write_bytes(b'invalid pdf')
                self.assertEqual(client.get(endpoint+'?file_format=pdf').status_code, 422)
                client.force_authenticate(foreign)
                self.assertEqual(client.get(endpoint+'?file_format=pdf').status_code, 404)
            self.assertEqual(Path(proposal.generated_file.path).read_bytes(), b'preserved source')
