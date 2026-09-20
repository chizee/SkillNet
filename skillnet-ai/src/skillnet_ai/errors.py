"""Actionable error summaries that do not echo provider response bodies."""
from skillnet_ai.config import redact


def error_details(exc: Exception) -> dict:
    current, seen = exc, set()
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        if getattr(current, "details", None):
            return current.details
        code = getattr(current, "code", None)
        status = getattr(current, "status_code", None)
        body = getattr(current, "body", None)
        if isinstance(body, dict):
            details = body.get("error", body)
            if isinstance(details, dict):
                code = details.get("code", code)
        if code in {"insufficient_quota", "insufficient_balance", "quota_exceeded"} or status == 402:
            return {"code": "quota_exceeded", "message": "Provider quota or balance is insufficient.",
                    "hint": "Check the selected endpoint's account or Coding Plan allowance."}
        if status in {401, 403}:
            return {"code": "authentication_or_access", "message": "The service rejected authentication or access.",
                    "hint": "Check the configured key, endpoint permissions and GitHub rate limits where applicable."}
        if status == 404:
            return {"code": "not_found", "message": "The resource, endpoint or model was not found.",
                    "hint": "Check the URL and exact model name accepted by this endpoint."}
        if status == 429:
            return {"code": "rate_limited", "message": "The service rate limit was reached.",
                    "hint": "Wait before retrying; check account limits."}
        if status in {400, 422}:
            return {"code": "request_rejected", "message": "The endpoint rejected the request parameters.",
                    "hint": "Check model capabilities and json_mode; credentials are not interchangeable between API protocols."}
        if isinstance(status, int) and status >= 500:
            return {"code": "service_unavailable", "message": "The service returned a server error.",
                    "hint": "Retry later on the same endpoint; existing outputs are preserved."}
        current = current.__cause__
    return {"code": "operation_failed", "message": redact(str(exc)),
            "hint": "Check the input and run skillnet doctor for configuration diagnostics."}
