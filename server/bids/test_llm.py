import os
from unittest.mock import patch

from django.test import SimpleTestCase
from pydantic import BaseModel, ValidationError
import requests

from bids.services.llm import OllamaChatModel, build_text_model, model_selection


class Notice(BaseModel):
    days: int


class ModelRoutingTests(SimpleTestCase):
    @patch.dict(os.environ, {"CHAT_PROVIDER": "ollama", "LOCAL_LLM_MODEL": "qwen3:14b", "PROPOSAL_PROVIDER": "openai"}, clear=True)
    def test_local_chat_and_cloud_proposal_are_independent(self):
        self.assertEqual(model_selection("CHAT", "gpt-4o-mini"), ("ollama", "qwen3:14b"))
        self.assertEqual(model_selection("PROPOSAL", "gpt-5.6-sol"), ("openai", "gpt-5.6-sol"))
        self.assertIsInstance(build_text_model("CHAT", "gpt-4o-mini", 800), OllamaChatModel)

    @patch.dict(os.environ, {"CHAT_PROVIDER": "ollama", "LOCAL_LLM_MODEL": "qwen3:32b", "CHAT_LOCAL_MODEL": "qwen3:14b"}, clear=True)
    def test_explicit_project_model_is_not_upgraded_by_default(self):
        self.assertEqual(model_selection("CHAT", "gpt-4o-mini"), ("ollama", "qwen3:14b"))

    @patch.dict(os.environ, {"CHAT_PROVIDER": "typo"}, clear=True)
    def test_invalid_provider_is_rejected(self):
        with self.assertRaises(ValueError):
            build_text_model("CHAT", "gpt-4o-mini", 800)

    @patch("bids.services.llm.requests.post")
    def test_native_local_api_enforces_schema_and_context_without_cloud_key(self, post):
        post.return_value.json.return_value = {"message": {"content": '{"days":30}'}, "done_reason": "stop"}
        model = OllamaChatModel(model="qwen3:14b", num_ctx=16384, num_predict=200)
        result = model.with_structured_output(Notice).invoke("The duration is 30 days.")
        self.assertEqual(result.days, 30)
        args, kwargs = post.call_args
        self.assertEqual(args[0], "http://127.0.0.1:11434/api/chat")
        self.assertEqual(kwargs["json"]["options"]["num_ctx"], 16384)
        self.assertFalse(kwargs["json"]["think"])
        self.assertNotIn("headers", kwargs)
        post.return_value.json.return_value["message"]["content"] = '{"days":"wrong"}'
        with self.assertRaises(ValidationError):
            model.with_structured_output(Notice).invoke("The duration is unknown.")

    @patch("bids.services.llm.requests.post", side_effect=requests.Timeout)
    @patch("bids.services.llm.ChatOpenAI")
    def test_timeout_does_not_send_documents_to_cloud(self, cloud, post):
        with self.assertRaises(requests.Timeout):
            OllamaChatModel(model="qwen3:14b").invoke("Private document")
        cloud.assert_not_called()

    @patch("bids.services.llm.requests.post")
    def test_oversized_input_is_rejected_before_request(self, post):
        with self.assertRaises(ValueError):
            OllamaChatModel(model="qwen3:14b", num_ctx=1024).invoke("A" * 2048)
        post.assert_not_called()

    @patch("bids.services.llm.requests.post")
    def test_truncated_response_is_not_accepted(self, post):
        post.return_value.json.return_value = {"message": {"content": "partial"}, "done_reason": "length"}
        with self.assertRaises(ValueError):
            OllamaChatModel(model="qwen3:14b").invoke("Question")
