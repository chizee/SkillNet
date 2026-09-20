"""Exercise installed SDK dependencies and keep the default suite offline."""
import importlib

import pytest

# The older analyzer suite supplies stubs only when these modules are not loaded.
# With a installed SDK, test the real libraries rather than collection-order stubs.
for module in ("openai", "requests", "pydantic", "json_repair", "tqdm"):
    importlib.import_module(module)


@pytest.fixture(autouse=True)
def isolated_configuration_and_network(monkeypatch, tmp_path):
    from skillnet_ai.config import ENVIRONMENT
    for env in ENVIRONMENT.values():
        monkeypatch.delenv(env, raising=False)
    monkeypatch.setenv("SKILLNET_CONFIG", str(tmp_path / "user-config.json"))

    def blocked(*args, **kwargs):
        raise AssertionError("Default tests must mock network requests.")

    monkeypatch.setattr("requests.sessions.Session.request", blocked)
    monkeypatch.setattr("httpx.HTTPTransport.handle_request", blocked)
