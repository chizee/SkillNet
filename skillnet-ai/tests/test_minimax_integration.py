"""Integration tests for MiniMax provider with SkillNet components.

These tests verify that the provider plumbing works end-to-end without
actually calling external APIs — the OpenAI client is mocked.
"""

import json
import os
import unittest
from unittest.mock import MagicMock, patch

from skillnet_ai.client import SkillNetClient
from skillnet_ai.creator import SkillCreator
from skillnet_ai.evaluator import EvaluatorConfig, LLMClient
from skillnet_ai.analyzer import SkillRelationshipAnalyzer
from skillnet_ai.providers import PROVIDER_PRESETS


def _mock_chat_response(content: str):
    """Build a mock OpenAI ChatCompletion response."""
    choice = MagicMock()
    choice.message.content = content
    response = MagicMock()
    response.choices = [choice]
    return response


class TestSkillNetClientMiniMax(unittest.TestCase):
    """SkillNetClient initialises correctly with provider='minimax'."""

    @patch.dict(os.environ, {"MINIMAX_API_KEY": "test-mm-key"}, clear=True)
    def test_minimax_provider_sets_defaults(self):
        client = SkillNetClient(provider="minimax")
        self.assertEqual(client.api_key, "test-mm-key")
        self.assertEqual(client.base_url, "https://api.minimax.io/v1")
        self.assertEqual(client.provider, "minimax")
        self.assertIsNotNone(client._provider_preset)
        self.assertEqual(client._provider_preset.name, "minimax")

    @patch.dict(os.environ, {"MINIMAX_API_KEY": "auto-key"}, clear=True)
    def test_auto_detect_minimax(self):
        client = SkillNetClient()
        self.assertEqual(client.api_key, "auto-key")
        self.assertEqual(client.base_url, "https://api.minimax.io/v1")

    @patch.dict(os.environ, {}, clear=True)
    def test_explicit_key_overrides_env(self):
        client = SkillNetClient(
            provider="minimax", api_key="explicit-key"
        )
        self.assertEqual(client.api_key, "explicit-key")


class TestSkillCreatorMiniMax(unittest.TestCase):
    """SkillCreator handles MiniMax think-tag stripping."""

    @patch("skillnet_ai.creator.OpenAI")
    @patch.dict(os.environ, {}, clear=True)
    def test_think_tag_stripped_from_response(self, MockOpenAI):
        mock_client = MagicMock()
        MockOpenAI.return_value = mock_client

        raw = '<think>Let me reason about this...</think>[{"name": "test_skill", "description": "A test"}]'
        mock_client.chat.completions.create.return_value = _mock_chat_response(raw)

        creator = SkillCreator(
            api_key="test-key", provider="minimax"
        )
        result = creator._get_llm_response([{"role": "user", "content": "test"}])
        self.assertNotIn("<think>", result)
        self.assertIn("test_skill", result)

    @patch("skillnet_ai.creator.OpenAI")
    @patch.dict(os.environ, {}, clear=True)
    def test_minimax_base_url_used(self, MockOpenAI):
        SkillCreator(api_key="test-key", provider="minimax")
        MockOpenAI.assert_called_once_with(
            api_key="test-key",
            base_url="https://api.minimax.io/v1",
        )

    @patch("skillnet_ai.creator.OpenAI")
    @patch.dict(os.environ, {}, clear=True)
    def test_minimax_default_model(self, MockOpenAI):
        mock_client = MagicMock()
        MockOpenAI.return_value = mock_client
        mock_client.chat.completions.create.return_value = _mock_chat_response("test")

        creator = SkillCreator(api_key="test-key", provider="minimax")
        self.assertEqual(creator.model, "MiniMax-M2.7")


class TestLLMClientMiniMax(unittest.TestCase):
    """LLMClient (evaluator) handles MiniMax temperature and think-tags."""

    @patch("skillnet_ai.evaluator.OpenAI")
    @patch.dict(os.environ, {}, clear=True)
    def test_temperature_clamped(self, MockOpenAI):
        mock_client = MagicMock()
        MockOpenAI.return_value = mock_client

        config = EvaluatorConfig(
            api_key="test-key",
            base_url="https://api.minimax.io/v1",
            model="MiniMax-M2.7",
            temperature=0.0,
            provider="minimax",
        )
        llm_client = LLMClient(config)
        # Temperature 0.0 should be clamped to min (0.01)
        minimax_preset = PROVIDER_PRESETS["minimax"]
        self.assertEqual(llm_client.temperature, minimax_preset.min_temperature)

    @patch("skillnet_ai.evaluator.OpenAI")
    @patch.dict(os.environ, {}, clear=True)
    def test_think_tags_stripped_from_json(self, MockOpenAI):
        mock_client = MagicMock()
        MockOpenAI.return_value = mock_client

        raw_json = '<think>analyzing...</think>{"safety": {"level": "Good", "reason": "Safe"}}'
        mock_client.chat.completions.create.return_value = _mock_chat_response(raw_json)

        config = EvaluatorConfig(
            api_key="test-key",
            base_url="https://api.minimax.io/v1",
            model="MiniMax-M2.7",
            provider="minimax",
        )
        llm_client = LLMClient(config)
        result = llm_client.evaluate("test prompt")
        self.assertEqual(result["safety"]["level"], "Good")

    @patch("skillnet_ai.evaluator.OpenAI")
    @patch.dict(os.environ, {}, clear=True)
    def test_temperature_within_range_unchanged(self, MockOpenAI):
        MockOpenAI.return_value = MagicMock()

        config = EvaluatorConfig(
            api_key="test-key",
            base_url="https://api.minimax.io/v1",
            model="MiniMax-M2.7",
            temperature=0.5,
            provider="minimax",
        )
        llm_client = LLMClient(config)
        self.assertEqual(llm_client.temperature, 0.5)


class TestAnalyzerMiniMax(unittest.TestCase):
    """SkillRelationshipAnalyzer works with MiniMax provider."""

    @patch("skillnet_ai.analyzer.OpenAI")
    @patch.dict(os.environ, {}, clear=True)
    def test_minimax_provider_initialises(self, MockOpenAI):
        MockOpenAI.return_value = MagicMock()

        analyzer = SkillRelationshipAnalyzer(
            api_key="test-key", provider="minimax"
        )
        self.assertEqual(analyzer.model, "MiniMax-M2.7")
        self.assertEqual(analyzer.base_url, "https://api.minimax.io/v1")
        MockOpenAI.assert_called_once_with(
            api_key="test-key",
            base_url="https://api.minimax.io/v1",
        )

    @patch("skillnet_ai.analyzer.OpenAI")
    @patch.dict(os.environ, {}, clear=True)
    def test_think_tags_stripped_from_analysis(self, MockOpenAI):
        mock_client = MagicMock()
        MockOpenAI.return_value = mock_client

        raw = (
            '<think>reasoning about relationships</think>'
            '<Skill_Relationships>'
            '[{"source": "A", "target": "B", "type": "similar_to", "reason": "both do X"}]'
            '</Skill_Relationships>'
        )
        mock_client.chat.completions.create.return_value = _mock_chat_response(raw)

        analyzer = SkillRelationshipAnalyzer(
            api_key="test-key", provider="minimax"
        )
        # Mock internal methods to avoid filesystem access
        analyzer._load_skills_metadata = MagicMock(return_value=[
            {"name": "A", "description": "Skill A"},
            {"name": "B", "description": "Skill B"},
        ])
        with patch("os.path.exists", return_value=True):
            results = analyzer.analyze_local_skills("/fake/dir", save_to_file=False)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["source"], "A")
        self.assertEqual(results[0]["type"], "similar_to")


if __name__ == "__main__":
    unittest.main()
