"""
LLM provider presets and utilities for SkillNet.

Supports multiple LLM providers with auto-detection and provider-specific
parameter handling (e.g., temperature clamping, response post-processing).
"""

import os
import re
from dataclasses import dataclass
from typing import Optional, Dict, Any


@dataclass(frozen=True)
class ProviderPreset:
    """Immutable configuration preset for an LLM provider."""
    name: str
    base_url: str
    default_model: str
    api_key_env: str
    min_temperature: float = 0.0
    max_temperature: float = 2.0
    supports_json_mode: bool = True
    strip_think_tags: bool = False


# ---------------------------------------------------------------------------
# Provider registry
# ---------------------------------------------------------------------------

PROVIDER_PRESETS: Dict[str, ProviderPreset] = {
    "openai": ProviderPreset(
        name="openai",
        base_url="https://api.openai.com/v1",
        default_model="gpt-4o",
        api_key_env="API_KEY",
    ),
    "minimax": ProviderPreset(
        name="minimax",
        base_url="https://api.minimax.io/v1",
        default_model="MiniMax-M2.7",
        api_key_env="MINIMAX_API_KEY",
        min_temperature=0.01,
        max_temperature=1.0,
        supports_json_mode=True,
        strip_think_tags=True,
    ),
}

SUPPORTED_PROVIDERS = list(PROVIDER_PRESETS.keys())


def get_provider_preset(provider: str) -> ProviderPreset:
    """Look up a provider preset by name (case-insensitive).

    Raises ``ValueError`` if the provider is not recognised.
    """
    key = provider.lower()
    if key not in PROVIDER_PRESETS:
        raise ValueError(
            f"Unknown provider '{provider}'. "
            f"Supported providers: {', '.join(SUPPORTED_PROVIDERS)}"
        )
    return PROVIDER_PRESETS[key]


# ---------------------------------------------------------------------------
# Provider auto-detection
# ---------------------------------------------------------------------------

def detect_provider(
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
) -> Optional[str]:
    """Best-effort detection of the LLM provider from env / arguments.

    Detection order:
    1. If *base_url* contains a known provider domain, use that.
    2. If ``MINIMAX_API_KEY`` is set (and no OpenAI key), default to minimax.
    3. Fall back to ``None`` (caller should use OpenAI defaults).
    """
    # 1. URL-based detection
    if base_url:
        url_lower = base_url.lower()
        if "minimax" in url_lower:
            return "minimax"
        if "openai" in url_lower:
            return "openai"

    # 2. API-key-based detection
    if not api_key and not os.getenv("API_KEY"):
        if os.getenv("MINIMAX_API_KEY"):
            return "minimax"

    return None


# ---------------------------------------------------------------------------
# Provider-specific parameter helpers
# ---------------------------------------------------------------------------

def clamp_temperature(temperature: float, preset: ProviderPreset) -> float:
    """Clamp *temperature* to the provider's accepted range."""
    return max(preset.min_temperature, min(temperature, preset.max_temperature))


_THINK_TAG_RE = re.compile(r"<think>.*?</think>\s*", re.DOTALL)


def strip_think_tags(text: str) -> str:
    """Remove ``<think>…</think>`` blocks that some models emit."""
    return _THINK_TAG_RE.sub("", text).strip()


def postprocess_response(text: str, preset: ProviderPreset) -> str:
    """Apply provider-specific post-processing to a raw LLM response."""
    if preset.strip_think_tags:
        text = strip_think_tags(text)
    return text


# ---------------------------------------------------------------------------
# Resolve helpers (used by client / creator / evaluator / analyzer)
# ---------------------------------------------------------------------------

def resolve_provider_config(
    provider: Optional[str] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    model: Optional[str] = None,
) -> Dict[str, Any]:
    """Resolve the final ``(api_key, base_url, model, preset)`` tuple.

    When *provider* is given explicitly the corresponding preset supplies
    defaults.  Otherwise the function falls back to auto-detection or plain
    OpenAI defaults.

    Returns a dict with keys ``api_key``, ``base_url``, ``model``, ``preset``.
    """
    # Determine provider
    effective_provider = provider
    if not effective_provider:
        effective_provider = detect_provider(api_key=api_key, base_url=base_url)

    preset: Optional[ProviderPreset] = None
    if effective_provider:
        preset = get_provider_preset(effective_provider)

    if preset:
        resolved_api_key = api_key or os.getenv(preset.api_key_env) or os.getenv("API_KEY")
        resolved_base_url = base_url or os.getenv("BASE_URL") or preset.base_url
        resolved_model = model or os.getenv("SKILLNET_MODEL") or preset.default_model
    else:
        resolved_api_key = api_key or os.getenv("API_KEY")
        resolved_base_url = base_url or os.getenv("BASE_URL") or "https://api.openai.com/v1"
        resolved_model = model or os.getenv("SKILLNET_MODEL") or "gpt-4o"

    return {
        "api_key": resolved_api_key,
        "base_url": resolved_base_url,
        "model": resolved_model,
        "preset": preset,
    }
