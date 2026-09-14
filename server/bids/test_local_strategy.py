from unittest.mock import patch
from django.test import SimpleTestCase
from bids.services.rag.proposal import build_strategy_chain, LocalProposalStrategySchema, ProposalStrategySchema

class LocalStrategyTests(SimpleTestCase):
    @patch("bids.services.rag.proposal.structured_chain")
    @patch("bids.services.rag.proposal.build_proposal_model")
    @patch("bids.services.rag.proposal.model_selection", return_value=("ollama", "qwen3:14b"))
    def test_local_strategy_has_bounded_overview(self, selection, model, chain):
        build_strategy_chain()
        self.assertIs(chain.call_args.args[2], LocalProposalStrategySchema)
        schema = LocalProposalStrategySchema.model_json_schema()
        self.assertEqual(schema["properties"]["compliance_matrix"]["maxItems"], 3)
        self.assertEqual(schema["properties"]["bid_summary"]["maxLength"], 180)

    @patch("bids.services.rag.proposal.structured_chain")
    @patch("bids.services.rag.proposal.build_proposal_model")
    @patch("bids.services.rag.proposal.model_selection", return_value=("openai", "test"))
    def test_cloud_strategy_retains_existing_schema(self, selection, model, chain):
        build_strategy_chain()
        self.assertIs(chain.call_args.args[2], ProposalStrategySchema)
