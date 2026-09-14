from tempfile import TemporaryDirectory
from unittest.mock import patch
from django.test import SimpleTestCase, override_settings
from langchain_core.messages import AIMessage
from bids.services.llm import OllamaChatModel, LocalOutputLimitError
from bids.services.local_context import summarize_evidence

class EvidenceRecoveryTests(SimpleTestCase):
    def test_output_limit_retries_complete_source_with_larger_allowance(self):
        calls = []
        def invoke(model, messages, **kwargs):
            calls.append((model.num_predict, messages))
            if len(calls) == 1:
                raise LocalOutputLimitError("partial")
            return AIMessage(content="250명, 30회")
        with TemporaryDirectory() as folder, override_settings(MEDIA_ROOT=folder):
            with patch.object(OllamaChatModel, "invoke", invoke):
                model = OllamaChatModel(model="qwen3:14b", num_ctx=32768, num_predict=4096)
                result = summarize_evidence("source " * 100, 400, model)
        self.assertEqual(result, "250명, 30회")
        self.assertGreater(calls[1][0], calls[0][0])
        self.assertEqual(calls[0][1], calls[1][1])

    def test_completed_chunks_survive_later_failure(self):
        text = "A" * 10000 + "B" * 1000
        with TemporaryDirectory() as folder, override_settings(MEDIA_ROOT=folder):
            model = OllamaChatModel(model="qwen3:14b", num_ctx=32768, num_predict=4096)
            with patch.object(OllamaChatModel, "invoke", side_effect=[
                AIMessage(content="first"), ConnectionError("offline")
            ]):
                with self.assertRaises(ConnectionError):
                    summarize_evidence(text, 400, model)
            with patch.object(OllamaChatModel, "invoke", return_value=AIMessage(content="second")) as invoke:
                self.assertEqual(summarize_evidence(text, 400, model), "first\n\nsecond")
                self.assertEqual(invoke.call_count, 1)

    def test_second_truncation_is_not_accepted_or_cached(self):
        with TemporaryDirectory() as folder, override_settings(MEDIA_ROOT=folder):
            model = OllamaChatModel(model="qwen3:14b", num_ctx=32768, num_predict=4096)
            with patch.object(OllamaChatModel, "invoke", side_effect=LocalOutputLimitError("partial")) as invoke:
                with self.assertRaises(LocalOutputLimitError):
                    summarize_evidence("source " * 100, 400, model)
                self.assertEqual(invoke.call_count, 2)

    def test_repeated_limit_splits_all_source_without_using_partial_output(self):
        with TemporaryDirectory() as folder, override_settings(MEDIA_ROOT=folder):
            model = OllamaChatModel(model="qwen3:14b", num_ctx=32768, num_predict=4096)
            with patch.object(OllamaChatModel, "invoke", side_effect=[
                LocalOutputLimitError("partial"), LocalOutputLimitError("partial"),
                AIMessage(content="first"), AIMessage(content="second"),
            ]) as invoke:
                result = summarize_evidence("A" * 3000 + "B" * 3000, 400, model)
                self.assertEqual(result, "first\nsecond")
                self.assertEqual(invoke.call_count, 4)
                self.assertIn("A" * 3000, invoke.call_args_list[2].args[0][-1].content)
                self.assertIn("B" * 3000, invoke.call_args_list[3].args[0][-1].content)
