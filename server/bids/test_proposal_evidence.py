import json
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings
from langchain_core.messages import AIMessage
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel

from bids.services.llm import OllamaChatModel
from bids.services.local_context import fit_inputs, structured_chain
from bids.services.proposal_evidence import evidence_units, select_evidence
from bids.services.proposal_coverage import CoverageVerdict, confirmed_quote


class Answer(BaseModel):
    answer: str


class ProposalEvidenceTests(SimpleTestCase):
    def test_short_requirement_packets_keep_all_evidence_when_context_is_available(self):
        prompt = ChatPromptTemplate.from_template("{instruction}\n{requirement_context}\n{company_knowledge_context}")
        fact = "교육 10회, 계약기간 3개월. 강사 자격의 구체적 기준은 미제공."
        for requirement_context in (fact, json.dumps({"requirements": [{"requirement": fact}]}, ensure_ascii=False)):
            with self.subTest(requirement_context=requirement_context):
                reports = []
                fitted = fit_inputs(prompt, {
                    "instruction": "요구사항 작성", "requirement_context": requirement_context,
                    "company_knowledge_context": "인력 증빙 미확인", "_evidence_query": "요구사항",
                    "_evidence_reports": reports,
                }, OllamaChatModel(model="gemma4:26b", num_ctx=8192, num_predict=1000), Answer)
                self.assertIn(fact, fitted["requirement_context"])
                self.assertIn("인력 증빙 미확인", fitted["company_knowledge_context"])
                self.assertEqual(reports[0]["fields"]["requirement_context"]["omitted_ids"], [])
                self.assertLessEqual(reports[0]["input_bytes"], reports[0]["budget_bytes"])

    def test_internal_packet_metadata_is_not_in_the_cloud_output_schema(self):
        from bids.services.rag.proposal import ProposalRevisionPlanSchema, LocalProposalRevisionPlanSchema
        self.assertNotIn("evidence_selection", ProposalRevisionPlanSchema.model_json_schema()["properties"])
        self.assertIn("evidence_selection", LocalProposalRevisionPlanSchema.model_json_schema()["properties"])

    def test_core_quantities_survive_generic_slide_queries(self):
        from bids.services.proposal_evidence import core_project_requirements
        register = {"requirements": [
            {"requirement": "평가 관련 항목", "category": "평가"},
            {"requirement": "교육인원: 250명 (청소년 180명, 성인 70명)", "category": "사업내용", "sources": ["RFP 2페이지"]},
            {"requirement": "교육기간: 15주 (일부 변동 가능)", "category": "사업내용", "sources": ["RFP 2페이지"]},
        ]}
        result = core_project_requirements(register)
        self.assertIn("250명", result)
        self.assertIn("일부 변동 가능", result)
        self.assertIn("RFP 2페이지", result)
        self.assertNotIn("평가 관련 항목", result)

    def test_short_text_rejects_cutoff_and_preserves_verification_condition(self):
        from bids.services.proposal_text_fit import usable_short_text
        self.assertFalse(usable_short_text("우리 회사는 해남군 교", "우리 회사는 해남군 교육사업을 수행합니다", 35))
        self.assertFalse(usable_short_text("운영 실적", "운영 실적 확인 필요", 35))
        self.assertFalse(usable_short_text("증빙(서식", "증빙(서식 12)을 제출", 35))
        self.assertTrue(usable_short_text("실적 확인 필요", "운영 실적 확인 필요", 35))

    def test_page_limit_requires_explicit_original_limit_not_copies_or_minutes(self):
        from bids.services.proposal_text_fit import verified_page_limit
        self.assertIsNone(verified_page_limit(10, "제안서 10부 제출, 제안 설명 10분"))
        self.assertIsNone(verified_page_limit(10, "제안서 30페이지 이내"))
        self.assertIsNone(verified_page_limit(10, "제안서 110페이지 이내"))
        self.assertEqual(verified_page_limit(30, "제안서 본문은 30페이지 이내 작성"), 30)
        self.assertEqual(verified_page_limit(30, "제안서 본문 30매 미만"), 29)

    @patch("bids.services.proposal_coverage.structured_chain")
    def test_full_register_is_reviewed_even_when_one_batch_fails(self, factory):
        from unittest.mock import Mock
        from bids.services.proposal_coverage import review_requirement_coverage
        requested = []
        def create_chain(prompt, model, schema):
            def invoke(inputs):
                payload = json.loads(inputs["review_context"])
                requested.extend(item["id"] for item in payload)
                if len(requested) == 4:
                    raise ValueError("failed batch")
                return schema.model_validate({item["id"]: {"covered": False} for item in payload})
            return Mock(invoke=invoke)
        factory.side_effect = create_chain
        register = {"requirements": [{"requirement": f"조건 {n}"} for n in range(9)]}
        result = review_requirement_coverage(register, {"slide_changes": []},
                                             OllamaChatModel(model="qwen3:14b"))
        self.assertEqual(len(set(requested)), 9)
        self.assertEqual(result["total_count"], 9)
        self.assertEqual(len(result["checks"]), 9)
        self.assertEqual(result["unverified_count"], 4)
        self.assertEqual(result["covered_count"], 0)

    def test_late_relevant_source_is_selected_with_provenance(self):
        source = "[출처 1: 일반.pdf, 1페이지]\n" + "일반 행정 안내. " * 100
        source += "\n[출처 2: 강사.pdf, 12페이지]\n강사 결원 시 대체 강사 배정."
        units = evidence_units(source, "bid_context")
        selected, report = select_evidence(units, "강사 결원 대체", 800)
        self.assertIn("강사.pdf, 12페이지", selected)
        self.assertIn("강사 결원 시 대체 강사 배정", selected)
        self.assertGreater(len(report["omitted_ids"]), 0)

    @patch("bids.services.local_context.summarize_evidence", side_effect=AssertionError("No LLM compression"))
    def test_large_packet_fits_without_summary_and_accounts_for_every_requirement(self, summarize):
        rows = [{"requirement": f"교육 과정 {n}: 수강생 250명, 주 2회, 30분", "sources": ["RFP 3페이지"]}
                for n in range(199)]
        text = json.dumps({"requirements": rows}, ensure_ascii=False)
        prompt = ChatPromptTemplate.from_template("{instruction}\n{slide_inventory}\n{requirement_context}")
        reports = []
        inputs = {"instruction": "이 페이지 작성", "slide_inventory": "shape-1 원문",
                  "requirement_context": text, "_evidence_query": "교육 과정 150",
                  "_evidence_reports": reports, "company_context": "unused" * 100000}
        model = OllamaChatModel(model="qwen3:14b", num_ctx=8192, num_predict=1000)
        fitted = fit_inputs(prompt, inputs, model, Answer)
        self.assertEqual(fitted["instruction"], inputs["instruction"])
        self.assertEqual(fitted["slide_inventory"], inputs["slide_inventory"])
        self.assertEqual(inputs["requirement_context"], text)
        self.assertIn("250명, 주 2회, 30분", fitted["requirement_context"])
        report = reports[0]["fields"]["requirement_context"]
        self.assertEqual(len(set(report["selected_ids"] + report["omitted_ids"])), 199)
        self.assertLessEqual(reports[0]["input_bytes"], reports[0]["budget_bytes"])
        self.assertNotIn("company_context", reports[0]["fields"])
        summarize.assert_not_called()

    def test_company_evidence_is_not_replaced_by_bid_facts(self):
        prompt = ChatPromptTemplate.from_template("회사: {company_knowledge_context}\n공고: {bid_context}")
        result = fit_inputs(prompt, {
            "company_knowledge_context": "[회사 자료]\n강사 보유인원 미확인",
            "bid_context": "[공고]\n원어민 강사 70명 이상 보유 평가" * 100,
            "_evidence_query": "강사 70명",
        }, OllamaChatModel(model="qwen3:14b", num_ctx=8192, num_predict=1000), Answer)
        self.assertNotIn("70명", result["company_knowledge_context"])
        self.assertIn("미확인", result["company_knowledge_context"])

    def test_success_cache_reuses_only_identical_model_prompt_and_inputs(self):
        prompt = ChatPromptTemplate.from_template("{instruction} {bid_context}")
        values = {"instruction": "작성", "bid_context": "사업비 1억원", "_evidence_query": "사업비"}
        model = OllamaChatModel(model="qwen3:14b", num_ctx=8192)
        with TemporaryDirectory() as folder, override_settings(MEDIA_ROOT=folder):
            with patch.object(OllamaChatModel, "_generate") as generate:
                from langchain_core.outputs import ChatGeneration, ChatResult
                generate.return_value = ChatResult(generations=[ChatGeneration(message=AIMessage(content='{"answer":"ok"}'))])
                chain = structured_chain(prompt, model, Answer)
                self.assertEqual(chain.invoke(values).answer, "ok")
                chain.invoke(values)
                self.assertEqual(generate.call_count, 1)
                chain.invoke({**values, "bid_context": "사업비 2억원"})
                self.assertEqual(generate.call_count, 2)

    def test_coverage_requires_real_passage_on_the_correct_page_and_all_numbers(self):
        pages = {1: "수강생 250명에게 주 2회 30분 수업을 제공한다.", 2: "운영 계획"}
        verdict = CoverageVerdict(covered=True, slide_number=1, quote=pages[1])
        self.assertTrue(confirmed_quote(verdict, "250명 주 2회 30분 수업", pages))
        self.assertFalse(confirmed_quote(verdict, "250명 주 3회 30분 수업", pages))
        self.assertFalse(confirmed_quote(verdict.model_copy(update={"slide_number": 2}), "250명", pages))
        self.assertFalse(confirmed_quote(verdict.model_copy(update={"quote": "근거 없는 250명 수업"}), "250명", pages))

    def test_missing_page_is_recovered_only_from_a_unique_exact_quote(self):
        from bids.services.proposal_coverage import quote_page
        text = "수강생 250명에게 주 2회 30분 수업을 제공한다."
        verdict = CoverageVerdict(covered=True, quote=text)
        self.assertEqual(quote_page(verdict, {26: text}), 26)
        self.assertTrue(confirmed_quote(verdict, "250명 주 2회 30분", {26: text}))
        self.assertIsNone(quote_page(verdict, {1: text, 26: text}))
        self.assertFalse(confirmed_quote(verdict, "250명", {1: text, 26: text}))
        self.assertFalse(confirmed_quote(verdict.model_copy(update={"slide_number": 99}), "250명", {26: text}))
