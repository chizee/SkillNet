"""Bounded Chat Completions compatibility, without provider switching."""
import logging

logger = logging.getLogger(__name__)


def _unsupported(exc, parameter: str) -> bool:
    if getattr(exc, "status_code", None) not in {400, 422}:
        return False
    body = getattr(exc, "body", None)
    error = body.get("error", body) if isinstance(body, dict) else {}
    message = str(error.get("message", "")) if isinstance(error, dict) else ""
    # Some OpenAI-compatible providers put the explanation only in the message.
    message = (message or str(exc)).lower()
    named = parameter in message or (isinstance(error, dict) and error.get("param") == parameter)
    unsupported_code = isinstance(error, dict) and error.get("code") == "unsupported_parameter"
    return named and (unsupported_code or any(term in message for term in (
        "not support", "unsupported", "not allowed", "not permitted", "only the default",
    )))


def chat_completion(client, *, model: str, messages: list, json_mode: str = "off",
                    temperature=None):
    if json_mode not in {"auto", "on", "off"}:
        raise ValueError("json_mode must be auto, on or off.")
    kwargs = {"model": model, "messages": messages}
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
            del kwargs[parameter]
            logger.warning("Endpoint rejected optional %s; retrying without it.", parameter)
