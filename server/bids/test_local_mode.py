import os
import json
from io import BytesIO
import tempfile
from unittest.mock import patch
from django.test import SimpleTestCase, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from langchain_core.messages import AIMessage
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel
from PIL import Image
from bids.services.llm import cloud_options, model_selection, OllamaChatModel
from bids.services.local_context import fit_inputs, summarize_evidence, split_bytes
from bids.services.business_registration import extract_business_registration
from bids.services.web_references import SearchParser, search_public_references
from bids.services.rag.keyword_store import search_mode

class Result(BaseModel):
    answer: str

@patch.dict(os.environ, {"AI_MODE": "local"})
class LocalModeTests(SimpleTestCase):
    def test_local_mode_blocks_cloud_and_vector(self):
        with patch.dict(os.environ, {"ANALYSIS_PROVIDER": "openai", "RAG_SEARCH_MODE": "vector"}):
            self.assertEqual(model_selection("ANALYSIS", "gpt-4o-mini")[0], "ollama")
            self.assertEqual(search_mode(), "keyword")
            with self.assertRaises(ValueError):
                cloud_options()

    def test_invalid_mode_does_not_enable_cloud(self):
        with patch.dict(os.environ, {"AI_MODE": "locla"}):
            with self.assertRaises(ValueError):
                cloud_options()

    def test_ollama_schema_preserves_properties_but_drops_grammar_bounds(self):
        from bids.services.llm import ollama_schema
        from pydantic import Field, ValidationError
        class Bounded(BaseModel):
            content: str = Field(max_length=2)
        schema = ollama_schema(Bounded.model_json_schema())
        self.assertNotIn("maxLength", schema["properties"]["content"])
        self.assertIn("content", schema["properties"])
        with self.assertRaises(ValidationError):
            Bounded.model_validate_json('{"content":"long"}')

    def test_uncertain_and_manual_values_are_not_completed(self):
        from bids.services.rag.quantitative import add_completion_summary
        report = add_completion_summary({"forms": [{"fields": [
            {"label":"성명", "value":"성명 미제공", "status":"작성 완료"},
            {"label":"서명", "value":"홍길동", "status":"직접 확인"},
            {"label":"회사명", "value":"테스트교육", "status":"작성 완료"},
        ]}]})
        self.assertEqual(report["completion"]["completed_fields"], 1)
        self.assertEqual(report["completion"]["direct_review_fields"], 2)

    @patch("bids.services.web_references._download_html",
           return_value=("https://example.com/", "<title>자료</title><p>기간 30일</p>"))
    def test_public_url_returns_page_text_and_real_source(self, download):
        text, sources = search_public_references("https://example.com/")
        self.assertIn("기간 30일", text)
        self.assertEqual(sources[0]["url"], "https://example.com/")

    @patch("bids.services.rag.proposal.structured_chain")
    def test_local_slide_output_maps_exact_targets_and_rejects_invented_targets(self, chain_factory):
        from bids.services.rag.proposal import build_local_slide_plan
        from pydantic import ValidationError
        def create_chain(prompt, model, schema):
            with self.assertRaises(ValidationError):
                schema.model_validate({"edits":{"invented":"수정","shape-0":None},"review_notes":[]})
            from unittest.mock import Mock
            chain = Mock()
            chain.invoke.return_value = schema.model_validate({
                "edits":{"shape-0":"새 제목"},"review_notes":[]})
            return chain
        chain_factory.side_effect = create_chain
        result = build_local_slide_plan({
            "slide_number":1, "title":"기존", "elements":[{"target":"shape-0","text":"기존"}]}, {})
        self.assertEqual(result.slide_changes[0].action, "UPDATE")
        self.assertEqual(result.slide_changes[0].text_changes[0].original_text, "기존")
        self.assertEqual(result.slide_changes[0].text_changes[0].revised_text, "새 제목")
        self.assertEqual(result.added_slides, [])

    @patch("bids.services.rag.proposal.structured_chain")
    def test_oversized_text_retries_before_accepting_plan(self, factory):
        from unittest.mock import Mock
        from bids.services.rag.proposal import build_local_slide_plan
        def setup(prompt, model, schema):
            chain=Mock()
            chain.invoke.side_effect=[
                schema.model_validate({"edits":{"shape-0":"너무 긴 문구" * 10},"review_notes":[]}),
                schema.model_validate({"edits":{"shape-0":"짧은 제목"},"review_notes":[]})]
            factory.chain=chain
            return chain
        factory.side_effect=setup
        result=build_local_slide_plan({"slide_number":1,"title":"표지",
            "elements":[{"target":"shape-0","text":"[사업명]","max_chars":10}]},{})
        self.assertEqual(factory.chain.invoke.call_count,2)
        self.assertEqual(result.slide_changes[0].text_changes[0].revised_text,"짧은 제목")

    @patch("bids.services.rag.proposal.structured_chain")
    def test_null_placeholder_is_flagged_but_static_text_can_stay(self, factory):
        from unittest.mock import Mock
        from bids.services.rag.proposal import build_local_slide_plan
        def setup(prompt, model, schema):
            return Mock(invoke=Mock(return_value=schema.model_validate({
                "edits":{"shape-0":None,"shape-1":None},"review_notes":[]})))
        factory.side_effect=setup
        slide={"slide_number":1,"title":"표지","elements":[
            {"target":"shape-0","text":"[회사명]"},{"target":"shape-1","text":"제안서"}]}
        result=build_local_slide_plan(slide,{})
        self.assertEqual(len(result.slide_changes[0].text_changes),1)
        self.assertEqual(result.slide_changes[0].text_changes[0].revised_text,"확인 필요")
        self.assertTrue(any("shape-0" in note for note in result.final_review_items))
        slide["elements"][0]["text"]="회사 개요"
        result=build_local_slide_plan(slide,{})
        self.assertEqual(result.slide_changes[0].action,"REVIEW")
        self.assertEqual(result.slide_changes[0].text_changes,[])

    @patch("bids.services.rag.proposal.structured_chain")
    def test_persistently_oversized_text_fails_without_silent_skip(self, factory):
        from unittest.mock import Mock
        from bids.services.rag.proposal import build_local_slide_plan
        def setup(prompt, model, schema):
            chain=Mock(invoke=Mock(return_value=schema.model_validate({
                "edits":{"shape-0":"긴 문구" * 30},"review_notes":[]})))
            factory.chain=chain
            return chain
        factory.side_effect=setup
        with self.assertRaisesRegex(ValueError,"상자 크기"):
            build_local_slide_plan({"slide_number":1,"title":"표지",
                "elements":[{"target":"shape-0","text":"제목","max_chars":10}]},{})
        self.assertEqual(factory.chain.invoke.call_count,2)

    def test_explicit_page_preservation_limits_model_scope(self):
        from bids.services.rag.proposal import restrict_feedback_inventory
        inventory = [{"slide_number":i} for i in (1,2,3)]
        selected = restrict_feedback_inventory(inventory,
            "첫 페이지 제목 변경. 다른 페이지는 그대로 두세요.")
        self.assertEqual(selected, [inventory[0]])
        selected = restrict_feedback_inventory(inventory,
            "2페이지 제목 변경. 다른 슬라이드는 수정하지 마세요.")
        self.assertEqual(selected, [inventory[1]])
        with self.assertRaises(ValueError):
            restrict_feedback_inventory(inventory, "제목 변경. 다른 페이지는 그대로.")

    def test_unicode_chunks_preserve_every_character(self):
        text = "가나다ABC😀" * 100
        chunks = split_bytes(text, 101)
        self.assertEqual("".join(chunks), text)
        self.assertTrue(all(len(c.encode()) <= 101 for c in chunks))

    @patch.object(OllamaChatModel, "invoke", return_value=AIMessage(content="출처 1: 기간 30일."))
    def test_summary_reads_all_chunks_and_caches(self, invoke):
        with tempfile.TemporaryDirectory() as directory, override_settings(MEDIA_ROOT=directory):
            model = OllamaChatModel(model="qwen3:14b", num_ctx=32768)
            summarize_evidence("가" * 8000, 1500, model)
            self.assertEqual(invoke.call_count, 3)
            summarize_evidence("가" * 8000, 1500, model)
            self.assertEqual(invoke.call_count, 3)

    @patch("bids.services.local_context.summarize_evidence", return_value="요약 근거")
    def test_slide_targets_and_user_instruction_are_not_summarized(self, summarize):
        prompt = ChatPromptTemplate.from_template("{instruction}\n{slide_inventory}\n{bid_context}")
        values = {"instruction": "shape-2 수정", "slide_inventory": "shape-2 원문", "bid_context": "가"*10000}
        fitted = fit_inputs(prompt, values, OllamaChatModel(model="qwen3:14b",num_ctx=8192,num_predict=1000), Result)
        self.assertEqual(fitted["instruction"],values["instruction"])
        self.assertEqual(fitted["slide_inventory"],values["slide_inventory"])
        self.assertEqual(values["bid_context"],"가"*10000)

    @patch("bids.services.local_vision.requests.post")
    @patch("bids.services.business_registration.cloud_client")
    def test_image_only_goes_to_local_vision(self, cloud, post):
        buffer=BytesIO()
        Image.new("RGB",(50,50),"white").save(buffer,format="PNG")
        post.return_value.json.return_value={"message":{"content":json.dumps({
            "company_name":"테스트","business_registration_number":None,
            "representative_name":None,"address":None})},"done_reason":"stop"}
        result=extract_business_registration(SimpleUploadedFile("sample.png",buffer.getvalue(),content_type="image/png"))
        self.assertEqual(result["company_name"],"테스트")
        self.assertIn("images",post.call_args.kwargs["json"]["messages"][0])
        cloud.assert_not_called()

    def test_search_results_parse_redirects(self):
        p=SearchParser()
        p.feed('<a class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.com%2F">자료</a>')
        self.assertEqual(p.items,[{"url":"https://example.com/","title":"자료"}])

    @patch.dict(os.environ,{"LOCAL_WEB_SEARCH":"disabled"})
    @patch("bids.services.web_references.requests.Session")
    def test_disabled_search_has_no_network(self, session):
        result,sources=search_public_references("웹 검색")
        self.assertEqual(sources,[])
        session.assert_not_called()
