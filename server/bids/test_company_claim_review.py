from unittest.mock import patch, Mock
from django.test import SimpleTestCase
from bids.services.company_claim_review import review_company_claims, Verdict

def plan(text):
    return {"slide_changes":[{"slide_number":1,"action":"UPDATE","text_changes":[
        {"target":"shape-1","revised_text":text}]}],"final_review_items":[]}

class CompanyClaimTests(SimpleTestCase):
    @patch("bids.services.company_claim_review.build_text_model")
    def test_no_company_evidence_does_not_call_model(self, build):
        p=plan("강사 경력 10년 보유")
        r=review_company_claims(p,"","")
        self.assertEqual(r["review_required_count"],1)
        build.assert_not_called()
        self.assertIn("회사 근거 확인 필요",p["final_review_items"][0])

    @patch("bids.services.company_claim_review.build_text_model")
    def test_exact_company_quote_is_required(self, build):
        invoke=build.return_value.with_structured_output.return_value.invoke
        invoke.return_value=Verdict(supported=True,evidence_quote="강사 3명을 보유하고 있습니다.",reason="직접 명시")
        r=review_company_claims(plan("강사 3명 보유"),"강사 3명을 보유하고 있습니다.","")
        self.assertEqual(r["items"][0]["status"],"source_matched")
        self.assertEqual(r["items"][0]["reference_passages"][0]["text"],"강사 3명을 보유하고 있습니다.")
        invoke.return_value=Verdict(supported=True,evidence_quote="강사 10명 보유",reason="확인")
        r=review_company_claims(plan("강사 10명 보유"),"강사 3명을 보유하고 있습니다.","")
        self.assertEqual(r["review_required_count"],1)

    @patch("bids.services.company_claim_review.build_text_model")
    def test_negative_quote_and_model_failure_stay_unverified(self, build):
        invoke=build.return_value.with_structured_output.return_value.invoke
        invoke.return_value=Verdict(supported=True,evidence_quote="경력증명서 미제공",reason="있음")
        r=review_company_claims(plan("강사 경력증명서 보유"),"강사 경력증명서 미제공","")
        self.assertEqual(r["review_required_count"],1)
        invoke.side_effect=TimeoutError()
        r=review_company_claims(plan("강사 3명 보유"),"강사 3명","")
        self.assertEqual(r["review_required_count"],1)
        self.assertIn("실패",r["items"][0]["reason"])

    @patch("bids.services.company_claim_review.build_text_model")
    def test_bid_and_strategy_are_not_company_evidence(self, build):
        p=plan("30일간 20명 교육 수행 경험 보유")
        p["bid_context"]="30일간 20명 교육 수행 경험 보유"
        p["strategy"]="30일간 20명 교육 수행 경험 보유"
        r=review_company_claims(p,"","")
        self.assertEqual(r["review_required_count"],1)
        build.assert_not_called()
