"""
SkillNet AI SDK
~~~~~~~~~~~~~~~

A client library for searching, downloading, creating and evaluating AI Agent Skills.
"""

from skillnet_ai.client import SkillNetClient
from skillnet_ai.creator import SkillCreator
from skillnet_ai.downloader import SkillDownloader
from skillnet_ai.evaluator import SkillEvaluator, EvaluatorConfig
from skillnet_ai.searcher import SkillNetSearcher
from skillnet_ai.analyzer import SkillRelationshipAnalyzer
from skillnet_ai.providers import (
    PROVIDER_PRESETS,
    SUPPORTED_PROVIDERS,
    get_provider_preset,
    detect_provider,
)

__all__ = [
    "SkillNetClient",
    "SkillCreator",
    "SkillDownloader",
    "SkillEvaluator",
    "EvaluatorConfig",
    "SkillNetSearcher",
    "SkillRelationshipAnalyzer",
    "PROVIDER_PRESETS",
    "SUPPORTED_PROVIDERS",
    "get_provider_preset",
    "detect_provider",
]