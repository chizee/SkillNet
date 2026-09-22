"""Shared model requests and error reporting, without provider switching."""

import json
import logging
from typing import Any, TypeVar

from openai import OpenAI
from openai.types.chat import ChatCompletion, ChatCompletionMessageParam
from openai.types.chat.completion_create_params import CompletionCreateParamsNonStreaming
from pydantic import BaseModel

from skillnet_ai.core.config import redact
from skillnet_ai.core.models import AnalysisOptions, Endpoint

logger = logging.getLogger(__name__)
ResultModel = TypeVar("ResultModel", bound=BaseModel)


def _unsupported(exc: Exception, parameter: str) -> bool:
    """Recognize explicit parameter rejections for existing create/evaluate behavior."""
    if getattr(exc, "status_code", None) not in {400, 422}:
        return False
    body = getattr(exc, "body", None)
    error = body.get("error", body) if isinstance(body, dict) else {}
    message = str(error.get("message", "")) if isinstance(error, dict) else ""
    # Some OpenAI-compatible providers put the explanation only in the message.
    message = (message or str(exc)).lower()
    named = parameter in message or (isinstance(error, dict) and error.get("param") == parameter)
    unsupported_code = isinstance(error, dict) and error.get("code") == "unsupported_parameter"
    return named and (
        unsupported_code
        or any(
            term in message
            for term in (
                "not support",
                "unsupported",
                "not allowed",
                "not permitted",
                "only the default",
            )
        )
    )


def chat_completion(
    client: OpenAI,
    *,
    model: str,
    messages: list[ChatCompletionMessageParam],
    json_mode: str = "off",
    temperature: float | None = None,
) -> ChatCompletion:
    """Preserve create/evaluate's bounded optional-parameter compatibility."""
    if json_mode not in {"auto", "on", "off"}:
        raise ValueError("json_mode must be auto, on or off.")
    kwargs: CompletionCreateParamsNonStreaming = {"model": model, "messages": messages}
    if json_mode != "off":
        kwargs["response_format"] = {"type": "json_object"}
    if temperature is not None:
        kwargs["temperature"] = temperature
    # Each optional parameter can be removed once. No endpoint or model changes.
    while True:
        try:
            return client.chat.completions.create(**kwargs)
        except Exception as exc:
            removable = ["temperature"]
            if json_mode == "auto":
                removable.append("response_format")
            parameter = next((p for p in removable if p in kwargs and _unsupported(exc, p)), None)
            if parameter is None:
                raise
            if parameter == "temperature":
                del kwargs["temperature"]
            else:
                del kwargs["response_format"]
            logger.warning("Endpoint rejected optional %s; retrying without it.", parameter)


def structured_call(
    endpoint: Endpoint,
    options: AnalysisOptions,
    system: str,
    payload: object,
    model: type[ResultModel],
    *,
    output_schema: dict[str, Any] | None = None,
) -> ResultModel:
    """Make one schema-directed call; rejected protocols and malformed JSON propagate."""

    schema_object = output_schema if output_schema is not None else model.model_json_schema()
    schema = json.dumps(schema_object, ensure_ascii=False)
    with OpenAI(
        api_key=endpoint.api_key.get_secret_value(),
        base_url=endpoint.base_url,
        timeout=options.timeout,
        max_retries=options.request_retries,
    ) as client:
        request: CompletionCreateParamsNonStreaming = {
            "model": endpoint.model,
            "messages": [
                {"role": "system", "content": system + "\nJSON schema:\n" + schema},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
            ],
        }
        if options.json_mode == "on":
            request["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": model.__name__,
                    "strict": True,
                    "schema": schema_object,
                },
            }
        if options.reasoning_effort is not None:
            request["reasoning_effort"] = options.reasoning_effort
        response = client.chat.completions.create(**request)
    if not response.choices or response.choices[0].finish_reason != "stop":
        raise ValueError("Model did not finish a complete structured response.")
    content = response.choices[0].message.content
    if not content:
        raise ValueError("Model returned no structured content.")
    return model.model_validate_json(content)


def embed(
    endpoint: Endpoint, texts: list[str], *, timeout: float = 120, retries: int = 0
) -> list[list[float]]:
    """Embed one batch on the configured endpoint; never change models or providers."""

    with OpenAI(
        api_key=endpoint.api_key.get_secret_value(),
        base_url=endpoint.base_url,
        timeout=timeout,
        max_retries=retries,
    ) as client:
        result = client.embeddings.create(model=endpoint.model, input=texts)
        rows = sorted(result.data, key=lambda row: row.index)
        if [r.index for r in rows] != list(range(len(texts))):
            raise ValueError("Embedding response does not match the requested batch.")
        return [row.embedding for row in rows]


def error_details(exc: Exception) -> dict[str, Any]:
    """Describe the original failure without exposing provider bodies or retrying."""
    current: BaseException | None = exc
    seen: set[int] = set()
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        recorded = getattr(current, "details", None)
        if recorded:
            return recorded
        code = getattr(current, "code", None)
        status = getattr(current, "status_code", None)
        body = getattr(current, "body", None)
        if isinstance(body, dict):
            details = body.get("error", body)
            if isinstance(details, dict):
                code = details.get("code", code)
        if (
            code in {"insufficient_quota", "insufficient_balance", "quota_exceeded"}
            or status == 402
        ):
            return {
                "code": "quota_exceeded",
                "message": "Provider quota or balance is insufficient.",
                "hint": "Check the selected endpoint's account or Coding Plan allowance.",
            }
        if status in {401, 403}:
            return {
                "code": "authentication_or_access",
                "message": "The service rejected authentication or access.",
                "hint": "Check the configured key, endpoint permissions and GitHub rate limits where applicable.",
            }
        if status == 404:
            return {
                "code": "not_found",
                "message": "The resource, endpoint or model was not found.",
                "hint": "Check the URL and exact model name accepted by this endpoint.",
            }
        if status == 429:
            return {
                "code": "rate_limited",
                "message": "The service rate limit was reached.",
                "hint": "Wait before retrying; check account limits.",
            }
        if status in {400, 422}:
            return {
                "code": "request_rejected",
                "message": "The endpoint rejected the request parameters.",
                "hint": "Check model capabilities and json_mode; credentials are not interchangeable between API protocols.",
            }
        if isinstance(status, int) and status >= 500:
            return {
                "code": "service_unavailable",
                "message": "The service returned a server error.",
                "hint": "Retry later on the same endpoint; existing outputs are preserved.",
            }
        current = current.__cause__
    return {
        "code": "operation_failed",
        "message": redact(str(exc)),
        "hint": "Check the input and run skillnet doctor for configuration diagnostics.",
    }
