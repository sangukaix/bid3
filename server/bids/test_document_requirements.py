from unittest.mock import Mock
from django.test import SimpleTestCase
from pydantic import ValidationError
from bids.services.rag.document_requirements import (
    RequirementBatchSchema, _extract_requirement_batch,
)

class RequirementValidationRetryTests(SimpleTestCase):
    def invalid_result(self):
        try:
            RequirementBatchSchema.model_validate({
                "document_summary": "검증",
                "requirements": [{"category": "운영", "priority": "필수",
                                  "requirement": "가" * 241}],
            })
        except ValidationError as error:
            return error

    def test_retries_full_source_without_truncating_conditions(self):
        source = "[문서: 공고.pdf | 12페이지] 동시접속 150명 이상, 교육 30회"
        result = RequirementBatchSchema(document_summary="검증", requirements=[])
        chain = Mock()
        chain.invoke.side_effect = [self.invalid_result(), result]
        self.assertIs(_extract_requirement_batch(chain, source), result)
        self.assertEqual(chain.invoke.call_count, 2)
        second = chain.invoke.call_args_list[1].args[0]
        self.assertEqual(second["document_context"], source)
        self.assertIn("requirements.0.requirement", second["format_feedback"])
        self.assertIn("240", second["format_feedback"])

    def test_still_invalid_fails_after_one_retry(self):
        chain = Mock()
        chain.invoke.side_effect = self.invalid_result()
        with self.assertRaises(ValidationError):
            _extract_requirement_batch(chain, "원문")
        self.assertEqual(chain.invoke.call_count, 2)

    def test_connection_error_is_not_retried_as_format_error(self):
        chain = Mock()
        chain.invoke.side_effect = ConnectionError("offline")
        with self.assertRaises(ConnectionError):
            _extract_requirement_batch(chain, "원문")
        self.assertEqual(chain.invoke.call_count, 1)
