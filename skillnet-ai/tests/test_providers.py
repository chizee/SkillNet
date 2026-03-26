"""Unit tests for the providers module."""

import os
import unittest
from unittest.mock import patch

from skillnet_ai.providers import (
    PROVIDER_PRESETS,
    SUPPORTED_PROVIDERS,
    ProviderPreset,
    get_provider_preset,
    detect_provider,
    clamp_temperature,
    strip_think_tags,
    postprocess_response,
    resolve_provider_config,
)


class TestProviderPresets(unittest.TestCase):
    """Verify that built-in provider presets are complete and consistent."""

    def test_openai_preset_exists(self):
        preset = PROVIDER_PRESETS["openai"]
        self.assertEqual(preset.name, "openai")
        self.assertEqual(preset.base_url, "https://api.openai.com/v1")
        self.assertEqual(preset.default_model, "gpt-4o")
        self.assertEqual(preset.api_key_env, "API_KEY")

    def test_minimax_preset_exists(self):
        preset = PROVIDER_PRESETS["minimax"]
        self.assertEqual(preset.name, "minimax")
        self.assertEqual(preset.base_url, "https://api.minimax.io/v1")
        self.assertEqual(preset.default_model, "MiniMax-M2.7")
        self.assertEqual(preset.api_key_env, "MINIMAX_API_KEY")

    def test_minimax_temperature_range(self):
        preset = PROVIDER_PRESETS["minimax"]
        self.assertGreater(preset.min_temperature, 0.0)
        self.assertLessEqual(preset.max_temperature, 1.0)

    def test_minimax_strip_think_tags_enabled(self):
        preset = PROVIDER_PRESETS["minimax"]
        self.assertTrue(preset.strip_think_tags)

    def test_openai_strip_think_tags_disabled(self):
        preset = PROVIDER_PRESETS["openai"]
        self.assertFalse(preset.strip_think_tags)

    def test_supported_providers_list(self):
        self.assertIn("openai", SUPPORTED_PROVIDERS)
        self.assertIn("minimax", SUPPORTED_PROVIDERS)

    def test_preset_is_frozen(self):
        preset = PROVIDER_PRESETS["minimax"]
        with self.assertRaises(AttributeError):
            preset.name = "changed"


class TestGetProviderPreset(unittest.TestCase):
    """Tests for get_provider_preset()."""

    def test_valid_provider(self):
        preset = get_provider_preset("minimax")
        self.assertIsInstance(preset, ProviderPreset)
        self.assertEqual(preset.name, "minimax")

    def test_case_insensitive(self):
        preset = get_provider_preset("MiniMax")
        self.assertEqual(preset.name, "minimax")

    def test_unknown_provider_raises(self):
        with self.assertRaises(ValueError) as ctx:
            get_provider_preset("unknown_provider")
        self.assertIn("Unknown provider", str(ctx.exception))

    def test_openai_preset(self):
        preset = get_provider_preset("openai")
        self.assertEqual(preset.name, "openai")


class TestDetectProvider(unittest.TestCase):
    """Tests for detect_provider()."""

    def test_url_based_minimax(self):
        result = detect_provider(base_url="https://api.minimax.io/v1")
        self.assertEqual(result, "minimax")

    def test_url_based_openai(self):
        result = detect_provider(base_url="https://api.openai.com/v1")
        self.assertEqual(result, "openai")

    @patch.dict(os.environ, {"MINIMAX_API_KEY": "test-key"}, clear=False)
    def test_env_based_minimax(self):
        # Clear API_KEY to trigger MINIMAX_API_KEY detection
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("API_KEY", None)
            result = detect_provider()
            self.assertEqual(result, "minimax")

    def test_no_detection_returns_none(self):
        with patch.dict(os.environ, {}, clear=True):
            result = detect_provider()
            self.assertIsNone(result)

    def test_url_takes_precedence(self):
        result = detect_provider(
            base_url="https://api.minimax.io/v1",
            api_key="sk-something",
        )
        self.assertEqual(result, "minimax")


class TestClampTemperature(unittest.TestCase):
    """Tests for clamp_temperature()."""

    def setUp(self):
        self.minimax = PROVIDER_PRESETS["minimax"]
        self.openai = PROVIDER_PRESETS["openai"]

    def test_minimax_clamp_zero(self):
        result = clamp_temperature(0.0, self.minimax)
        self.assertEqual(result, self.minimax.min_temperature)

    def test_minimax_clamp_high(self):
        result = clamp_temperature(2.0, self.minimax)
        self.assertEqual(result, 1.0)

    def test_minimax_passthrough(self):
        result = clamp_temperature(0.5, self.minimax)
        self.assertEqual(result, 0.5)

    def test_openai_no_clamp(self):
        result = clamp_temperature(1.5, self.openai)
        self.assertEqual(result, 1.5)

    def test_negative_clamped_to_min(self):
        result = clamp_temperature(-1.0, self.minimax)
        self.assertEqual(result, self.minimax.min_temperature)


class TestStripThinkTags(unittest.TestCase):
    """Tests for strip_think_tags()."""

    def test_removes_single_think_block(self):
        text = "<think>internal reasoning</think>Hello world"
        result = strip_think_tags(text)
        self.assertEqual(result, "Hello world")

    def test_removes_multiline_think_block(self):
        text = "<think>\nline1\nline2\n</think>\nAnswer: 42"
        result = strip_think_tags(text)
        self.assertEqual(result, "Answer: 42")

    def test_removes_multiple_think_blocks(self):
        text = "<think>a</think>foo<think>b</think>bar"
        result = strip_think_tags(text)
        self.assertEqual(result, "foobar")

    def test_no_think_tags_passthrough(self):
        text = "Just plain text"
        result = strip_think_tags(text)
        self.assertEqual(result, "Just plain text")

    def test_empty_string(self):
        result = strip_think_tags("")
        self.assertEqual(result, "")

    def test_think_tag_with_json_content(self):
        text = '<think>Let me analyze...</think>{"safety": {"level": "Good"}}'
        result = strip_think_tags(text)
        self.assertEqual(result, '{"safety": {"level": "Good"}}')


class TestPostprocessResponse(unittest.TestCase):
    """Tests for postprocess_response()."""

    def test_minimax_strips_think_tags(self):
        preset = PROVIDER_PRESETS["minimax"]
        text = "<think>reasoning</think>answer"
        result = postprocess_response(text, preset)
        self.assertEqual(result, "answer")

    def test_openai_no_stripping(self):
        preset = PROVIDER_PRESETS["openai"]
        text = "<think>reasoning</think>answer"
        result = postprocess_response(text, preset)
        self.assertEqual(result, "<think>reasoning</think>answer")


class TestResolveProviderConfig(unittest.TestCase):
    """Tests for resolve_provider_config()."""

    @patch.dict(os.environ, {}, clear=True)
    def test_explicit_minimax_provider(self):
        cfg = resolve_provider_config(
            provider="minimax", api_key="test-key"
        )
        self.assertEqual(cfg["api_key"], "test-key")
        self.assertEqual(cfg["base_url"], "https://api.minimax.io/v1")
        self.assertEqual(cfg["model"], "MiniMax-M2.7")
        self.assertIsNotNone(cfg["preset"])
        self.assertEqual(cfg["preset"].name, "minimax")

    @patch.dict(os.environ, {}, clear=True)
    def test_explicit_openai_provider(self):
        cfg = resolve_provider_config(
            provider="openai", api_key="sk-test"
        )
        self.assertEqual(cfg["base_url"], "https://api.openai.com/v1")
        self.assertEqual(cfg["model"], "gpt-4o")

    @patch.dict(os.environ, {"MINIMAX_API_KEY": "mm-key"}, clear=True)
    def test_auto_detect_minimax_from_env(self):
        cfg = resolve_provider_config()
        self.assertEqual(cfg["api_key"], "mm-key")
        self.assertEqual(cfg["base_url"], "https://api.minimax.io/v1")
        self.assertEqual(cfg["model"], "MiniMax-M2.7")

    @patch.dict(os.environ, {}, clear=True)
    def test_explicit_values_override_preset(self):
        cfg = resolve_provider_config(
            provider="minimax",
            api_key="custom-key",
            base_url="https://custom.example.com/v1",
            model="custom-model",
        )
        self.assertEqual(cfg["api_key"], "custom-key")
        self.assertEqual(cfg["base_url"], "https://custom.example.com/v1")
        self.assertEqual(cfg["model"], "custom-model")
        self.assertIsNotNone(cfg["preset"])

    @patch.dict(os.environ, {}, clear=True)
    def test_no_provider_falls_back_to_openai_defaults(self):
        cfg = resolve_provider_config(api_key="sk-test")
        self.assertEqual(cfg["base_url"], "https://api.openai.com/v1")
        self.assertEqual(cfg["model"], "gpt-4o")
        self.assertIsNone(cfg["preset"])

    @patch.dict(os.environ, {"SKILLNET_MODEL": "custom-env-model"}, clear=False)
    def test_env_model_override(self):
        with patch.dict(os.environ, {}, clear=False):
            cfg = resolve_provider_config(provider="minimax", api_key="test")
            self.assertEqual(cfg["model"], "custom-env-model")

    @patch.dict(os.environ, {"API_KEY": "from-env"}, clear=True)
    def test_minimax_falls_back_to_api_key_env(self):
        cfg = resolve_provider_config(provider="minimax")
        self.assertEqual(cfg["api_key"], "from-env")


class TestProviderPresetMiniMaxModels(unittest.TestCase):
    """Verify MiniMax model defaults."""

    def test_default_model_is_m27(self):
        preset = PROVIDER_PRESETS["minimax"]
        self.assertEqual(preset.default_model, "MiniMax-M2.7")

    def test_json_mode_supported(self):
        preset = PROVIDER_PRESETS["minimax"]
        self.assertTrue(preset.supports_json_mode)


if __name__ == "__main__":
    unittest.main()
