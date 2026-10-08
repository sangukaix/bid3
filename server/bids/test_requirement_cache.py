from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from django.test import SimpleTestCase
from langchain_core.documents import Document
from langchain_core.runnables import RunnableLambda
from .services.rag import document_requirements as mod


class RequirementCacheTests(SimpleTestCase):
    def test_current_original_pages_replace_stale_chunks_including_added_and_removed_pages(self):
        from .services.rag.extract_document import ExtractionResult
        chunks=[Document(page_content='오래된 내용',metadata={'source':'request.pdf','element_index':1,'location':'옛 위치'}),
                Document(page_content='삭제된 내용',metadata={'source':'request.pdf','element_index':2})]
        current=[Document(page_content='수정된 조건',metadata={'location':'1페이지'}),
                 Document(page_content='새로운 제출 조건',metadata={'location':'2페이지'}),
                 Document(page_content='추가 평가 조건',metadata={'location':'3페이지'})]
        with patch.object(mod,'extract_document',return_value=ExtractionResult(documents=current)) as extract:
            rebuilt=mod._unique_source_documents(chunks)
            self.assertEqual([item.page_content for item in rebuilt],[item.page_content for item in current])
            self.assertEqual(rebuilt[2].metadata['location'],'3페이지')
            self.assertEqual(extract.call_count,1)
        with patch.object(mod,'extract_document',return_value=ExtractionResult(documents=current[:1])):
            self.assertEqual(len(mod._unique_source_documents(chunks)),1)
        with patch.object(mod,'extract_document',return_value=ExtractionResult()):
            with self.assertRaises(ValueError):mod._unique_source_documents(chunks)

    def test_changed_or_removed_source_invalidates_full_register_cache(self):
        doc=lambda text,location:Document(page_content=text,metadata={'location':location})
        with TemporaryDirectory() as folder, patch.object(mod,'get_bid_db_path',return_value=Path(folder)), \
            patch.object(mod,'model_selection',return_value=('ollama','gemma4:26b')), \
            patch.object(mod,'_build_requirement_model',return_value=RunnableLambda(lambda _:None)), \
            patch.object(mod,'_extract_requirement_batch') as extract:
            def result(_,batch):
                return mod.RequirementBatchSchema(document_summary='검토',requirements=[mod.RequirementItem(
                    category='과업',requirement=batch,priority='필수')])
            extract.side_effect=result
            first,_=mod.build_document_requirement_register('NOTICE',[doc('30분 수업','1쪽')])
            same,info=mod.build_document_requirement_register('NOTICE',[doc('30분 수업','1쪽')])
            self.assertFalse(info['created']);self.assertEqual(first,same);self.assertEqual(extract.call_count,1)
            changed,info=mod.build_document_requirement_register('NOTICE',[doc('30시간 수업','1쪽'),doc('보고서 제출','2쪽')])
            self.assertTrue(info['created']);self.assertIn('30시간',changed['requirements'][0]['requirement'])
            removed,info=mod.build_document_requirement_register('NOTICE',[doc('30시간 수업','1쪽')])
            self.assertTrue(info['created']);self.assertNotIn('보고서 제출',removed['requirements'][0]['requirement'])

    def test_decimals_ranges_priorities_and_points_are_not_deduplicated_as_identical(self):
        items=[mod.RequirementItem(category='과업',requirement=text,priority=priority,evaluation_points=points)
               for text,priority,points in [('1.5시간','필수','10점'),('15시간','필수','10점'),
                 ('3~5회','필수','10점'),('35회','필수','10점'),('1.5시간','평가','20점')]]
        register=mod._merge_batch_results([mod.RequirementBatchSchema(document_summary='조건',requirements=items)])
        self.assertEqual(len(register['requirements']),5)
