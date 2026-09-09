from pathlib import Path
import tempfile

from django.test import SimpleTestCase, override_settings

from bids.services.document_paths import portable_document_source, resolve_document_source
from bids.services.rag.extract_document import extract_document


class PortableDocumentTests(SimpleTestCase):
    def test_school_path_and_portable_path_read_the_same_document(self):
        with tempfile.TemporaryDirectory() as directory, override_settings(MEDIA_ROOT=directory):
            path = Path(directory) / "bid_documents" / "BID1" / "notice.txt"
            path.parent.mkdir(parents=True)
            path.write_text("Full original document for the relocated bid.", encoding="utf-8")
            old = r"C:\Users\Admin\mbca\bid2\server\media\bid_documents\BID1\notice.txt"
            portable = portable_document_source(old)
            self.assertEqual(portable, "media://bid_documents/BID1/notice.txt")
            self.assertEqual(resolve_document_source(portable), path.resolve())
            for source in (old, portable):
                result = extract_document(source)
                self.assertEqual(result.failed_files, [])
                self.assertIn("Full original", result.documents[0].page_content)
                self.assertEqual(result.documents[0].metadata["source"], portable)

    def test_portable_source_cannot_escape_media_directory(self):
        with tempfile.TemporaryDirectory() as directory, override_settings(MEDIA_ROOT=directory):
            for path in ("media://../secret.txt", "media://C:/secret.txt", "media:///outside.txt"):
                with self.subTest(path=path), self.assertRaises(ValueError):
                    resolve_document_source(path)

    def test_context_limit_includes_source_labels(self):
        from langchain_core.documents import Document
        from bids.services.rag.chatbot import build_full_page_context
        documents = [Document(page_content="a" * 300, metadata={"source": "media://long-document.txt", "location": "page 1"})]
        context, sources = build_full_page_context(documents, max_context_chars=100)
        self.assertLessEqual(len(context), 100)
        self.assertEqual(len(sources), 1)

    def test_non_media_files_keep_their_actual_path(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "temporary.txt"
            self.assertEqual(resolve_document_source(path), path.resolve())
