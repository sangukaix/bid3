import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings
from langchain_core.documents import Document

from bids.services.rag.keyword_store import save_keyword_documents, search_keyword_documents
from bids.services.rag.prepare_docs_for_ai import prepare_docs_for_ai
from bids.services.rag.retriever import search_bid_documents


class KeywordSearchTests(SimpleTestCase):
    @patch.dict("os.environ", {"RAG_SEARCH_MODE": "keyword"})
    @patch("bids.services.rag.retriever.get_bid_vector_store")
    def test_keyword_search_uses_no_embedding_and_preserves_sources(self, vector):
        with tempfile.TemporaryDirectory() as directory, override_settings(BASE_DIR=Path(directory)):
            documents = [
                Document(page_content="교육 운영 용역의 목적은 학생 교육입니다.", metadata={"source": "media://education.txt"}),
                Document(page_content="서버 유지보수와 장비 교체", metadata={"source": "media://server.txt"}),
            ]
            save_keyword_documents("BID1", documents)
            result = search_bid_documents("BID1", "교육 목적")
            self.assertEqual(result[0].metadata["source"], "media://education.txt")
            vector.assert_not_called()

    @patch.dict("os.environ", {"RAG_SEARCH_MODE": "keyword"})
    @patch("bids.services.rag.prepare_docs_for_ai.create_or_load_vector_store")
    @patch("bids.services.rag.prepare_docs_for_ai.download_bid_attachment")
    @patch("bids.services.rag.prepare_docs_for_ai.fetch_bid_attachments")
    @patch("bids.services.rag.prepare_docs_for_ai.BidNotice")
    def test_first_keyword_index_does_not_require_openai(self, notice, attachments, download, vector):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            media = root / "media"
            media.mkdir()
            source = media / "notice.txt"
            source.write_text("교육 운영 기간은 30일입니다.", encoding="utf-8")
            notice.objects.filter.return_value.order_by.return_value.first.return_value = SimpleNamespace(
                bid_ntce_no="BID1", bid_ntce_ord="00", business_type="service",
            )
            attachments.return_value = [{"filename": "notice.txt"}]
            download.return_value = source
            with override_settings(BASE_DIR=root, MEDIA_ROOT=media):
                result = prepare_docs_for_ai("BID1")
                self.assertEqual(result["search_mode"], "keyword")
                self.assertGreater(result["chunk_count"], 0)
                self.assertFalse(prepare_docs_for_ai("BID1")["created"])
                self.assertIn("30일", search_keyword_documents("BID1", "기간")[0].page_content)
                vector.assert_not_called()
                attachments.assert_called_once()

    @patch.dict("os.environ", {"AI_MODE": "hybrid", "RAG_SEARCH_MODE": "vector"})
    @patch("bids.services.rag.prepare_docs_for_ai.fetch_bid_attachments", side_effect=RuntimeError("offline"))
    @patch("bids.services.rag.prepare_docs_for_ai.BidNotice")
    def test_failed_download_does_not_destroy_legacy_index(self, notice, fetch):
        with tempfile.TemporaryDirectory() as directory, override_settings(BASE_DIR=Path(directory)):
            folder = Path(directory) / "chroma_db" / "BID1"
            folder.mkdir(parents=True)
            original = folder / "chroma.sqlite3"
            original.write_bytes(b"preserve-existing-index")
            (folder / "index_info.json").write_text(json.dumps({"version": 0}))
            notice.objects.filter.return_value.order_by.return_value.first.return_value = SimpleNamespace(
                bid_ntce_no="BID1", bid_ntce_ord="00", business_type="service",
            )
            with self.assertRaises(RuntimeError):
                prepare_docs_for_ai("BID1")
            self.assertEqual(original.read_bytes(), b"preserve-existing-index")
