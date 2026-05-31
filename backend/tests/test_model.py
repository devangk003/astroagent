"""make_model fails fast and clearly on bad config (vs. a deferred HTTP 401)."""
import pytest

from agent.model import make_model


def test_missing_api_key_raises_clear_error():
    with pytest.raises(ValueError) as exc:
        make_model("ollama", "qwen3.5:397b", "")
    assert "API key" in str(exc.value)


def test_none_api_key_raises():
    with pytest.raises(ValueError):
        make_model("openrouter", "some-model", None)


def test_unknown_provider_raises():
    with pytest.raises(ValueError) as exc:
        make_model("not-a-provider", "m", "key-present")
    assert "provider" in str(exc.value).lower()
