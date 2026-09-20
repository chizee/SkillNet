"""Shared, runtime configuration for the SDK and CLI."""
import json
import os
import re
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from urllib.parse import urlsplit

DEFAULT_MODEL = "gpt-4o"
DEFAULT_BASE_URL = "https://api.openai.com/v1"
DEFAULT_SEARCH_URL = "http://api-skillnet.openkg.cn"
ENVIRONMENT = {
    "api_key": "API_KEY", "base_url": "BASE_URL", "model": "SKILLNET_MODEL",
    "github_token": "GITHUB_TOKEN", "github_mirror": "GITHUB_MIRROR",
    "skillnet_api_url": "SKILLNET_API_URL", "json_mode": "SKILLNET_JSON_MODE",
}
DEFAULTS = {"base_url": DEFAULT_BASE_URL, "model": DEFAULT_MODEL,
            "skillnet_api_url": DEFAULT_SEARCH_URL, "json_mode": "auto"}
SECRETS = {"api_key", "github_token"}


def config_path() -> Path:
    return Path(os.environ.get("SKILLNET_CONFIG") or "~/.skillnet/config.json").expanduser()


def _validate(values: dict) -> None:
    if not isinstance(values, dict) or set(values) - set(ENVIRONMENT):
        raise ValueError("Config must be a JSON object with documented SkillNet settings.")
    for key, value in values.items():
        if not isinstance(value, str):
            raise ValueError(f"Config field {key} must be a string.")
        if key in {"base_url", "skillnet_api_url", "github_mirror"} and value:
            parsed = urlsplit(value)
            if (parsed.scheme not in {"http", "https"} or not parsed.hostname
                    or parsed.username or parsed.password or parsed.query or parsed.fragment):
                raise ValueError(f"{key} must be an HTTP(S) base URL without credentials, query or fragment.")
        if key == "json_mode" and value not in {"auto", "on", "off"}:
            raise ValueError("json_mode must be auto, on or off.")


def read_config() -> dict:
    path = config_path()
    try:
        values = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except (OSError, ValueError) as exc:
        raise ValueError(f"Cannot read SkillNet config at {path}; repair it or set SKILLNET_CONFIG.") from exc
    _validate(values)
    return values


def save_config(updates: dict) -> Path:
    """Merge explicit updates and atomically save in the user's chosen location."""
    _validate(updates)
    values = {**read_config(), **updates}
    path = config_path()
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".config-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(values, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return path


@dataclass
class Settings:
    api_key: Optional[str] = field(default=None, repr=False)
    base_url: str = DEFAULT_BASE_URL
    model: str = DEFAULT_MODEL
    github_token: Optional[str] = field(default=None, repr=False)
    github_mirror: Optional[str] = None
    skillnet_api_url: str = DEFAULT_SEARCH_URL
    json_mode: str = "auto"
    sources: dict = field(default_factory=dict)

    def public(self) -> dict:
        return {key: {"value": bool(getattr(self, key)) if key in SECRETS else getattr(self, key),
                      "source": self.sources[key]}
                for key in ENVIRONMENT}


def resolve_settings(**overrides) -> Settings:
    stored = read_config()
    values, sources = {}, {}
    for key, env in ENVIRONMENT.items():
        if overrides.get(key) is not None:
            values[key], sources[key] = overrides[key], "argument"
        elif os.environ.get(env):
            values[key], sources[key] = os.environ[env], env
        elif stored.get(key):
            values[key], sources[key] = stored[key], "config"
        else:
            values[key], sources[key] = DEFAULTS.get(key), "default"
    _validate({key: value for key, value in values.items() if value is not None})
    return Settings(**values, sources=sources)


def redact(text: str, *secrets: Optional[str]) -> str:
    """Redact known credentials and common Authorization/key renderings."""
    known = list(secrets) + [os.environ.get(ENVIRONMENT[key]) for key in SECRETS]
    try:
        stored = read_config()
        known.extend(stored.get(key) for key in SECRETS)
    except ValueError:
        pass
    for value in sorted((v for v in known if v), key=len, reverse=True):
        text = text.replace(value, "[REDACTED]")
    text = re.sub(r"(?i)(Bearer|token)\s+[\w.\-]+", r"\1 [REDACTED]", text)
    return re.sub(r"(?i)(api[_-]?key[\s\"':=]+)[^\s\"',}]+", r"\1[REDACTED]", text)
