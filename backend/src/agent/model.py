"""BYOK model factory — returns a chat model that supports .bind_tools().

Both providers (ollama, openrouter) are first-class everywhere (agent / eval / sweep / judge).
API keys are set ONCE per provider in the environment (OLLAMA_API_KEY, OPENROUTER_API_KEY); each
checkpoint chooses a provider + model and `provider_api_key()` resolves the matching key.
"""

import os

from langchain_openrouter import ChatOpenRouter
from langchain_openai import ChatOpenAI

# Cap output length so a single reading can't run to ~90s / a huge bill. Model-agnostic
# latency + output-cost guard (see eval EV04). Generous enough for a full kundli reading.
_MAX_OUTPUT_TOKENS = 1024

# Auto-retry transient provider failures (429 rate-limit / 5xx) with backoff before surfacing
# an error — recommended by the LangChain/OpenRouter docs and applied to both providers.
_MAX_RETRIES = 2

# Provider → the single env var holding that provider's API key (set once each).
_PROVIDER_KEY_ENV = {
    "openrouter": "OPENROUTER_API_KEY",
    "ollama": "OLLAMA_API_KEY",
}


def provider_api_key(provider: str) -> str:
    """Resolve the API key for a provider from the environment (read at call time).

    Returns "" if the provider is unknown or its key is unset. Lets any checkpoint use either
    provider with keys defined once. Casing/whitespace tolerant ('OpenRouter' / ' ollama ').
    """
    env_name = _PROVIDER_KEY_ENV.get((provider or "").strip().lower())
    return os.environ.get(env_name, "") if env_name else ""


def make_model(
    provider: str,
    model: str,
    api_key: str | None = None,
    streaming: bool = True,
    max_tokens: int | None = _MAX_OUTPUT_TOKENS,
    max_retries: int = _MAX_RETRIES,
):
    """Return a LangChain chat model for the given provider.

    Supports 'openrouter' and 'ollama'. Raises ValueError for unknown providers or when
    a required API key is missing (clearer than a deferred HTTP 401 deep in the LLM call).

    streaming: token-by-token output for the UI (FR-C4). The eval sets streaming=False so the
        provider returns usage_metadata (token counts), which the streamed path omits.
    max_tokens: hard output cap (bounds latency/cost); None to leave the provider default.
    max_retries: auto-retry transient 429/5xx failures with backoff before surfacing an error.
    """
    if not api_key or not str(api_key).strip():
        raise ValueError(
            f"Missing API key for provider {provider!r}. "
            f"Enter it in the model selector or set the matching key in backend/.env."
        )
    if provider == "openrouter":
        # ChatOpenRouter is the dedicated, recommended client (sets base_url itself). No app-
        # attribution headers (HTTP-Referer/X-Title) — by request, the app stays off the dashboard.
        return ChatOpenRouter(
            model=model, api_key=api_key, temperature=0.3,
            streaming=streaming, max_tokens=max_tokens, max_retries=max_retries,
        )
    if provider == "ollama":
        # Ollama via its OpenAI-compatible compat endpoint so api_key works cleanly.
        # stream_usage asks the endpoint to include token usage even while streaming
        # (best-effort; the eval disables streaming for reliable accounting).
        return ChatOpenAI(
            model=model,
            api_key=api_key,
            base_url="https://ollama.com/v1",
            temperature=0.3,
            streaming=streaming,
            stream_usage=True,
            max_tokens=max_tokens,
            max_retries=max_retries,
        )
    raise ValueError(f"Unknown provider: {provider!r}. Choose 'openrouter' or 'ollama'.")
