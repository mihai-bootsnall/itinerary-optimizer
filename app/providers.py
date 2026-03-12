from __future__ import annotations

from abc import ABC, abstractmethod

from app.config import settings

_DEFAULT_MODELS = {
    "anthropic": "claude-sonnet-4-6",
    "openai": "gpt-4o",
    "google": "gemini-2.5-flash",
}


class BaseLLMProvider(ABC):
    @abstractmethod
    async def complete(self, system: str, user: str) -> str: ...


class AnthropicProvider(BaseLLMProvider):
    def __init__(self, api_key: str, model: str, max_tokens: int) -> None:
        import anthropic

        self._client = anthropic.AsyncAnthropic(api_key=api_key)
        self._model = model
        self._max_tokens = max_tokens

    async def complete(self, system: str, user: str) -> str:
        message = await self._client.messages.create(
            model=self._model,
            max_tokens=self._max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return message.content[0].text if message.content else ""


class OpenAIProvider(BaseLLMProvider):
    def __init__(self, api_key: str, model: str, max_tokens: int) -> None:
        import openai

        self._client = openai.AsyncOpenAI(api_key=api_key)
        self._model = model
        self._max_tokens = max_tokens

    async def complete(self, system: str, user: str) -> str:
        response = await self._client.chat.completions.create(
            model=self._model,
            max_tokens=self._max_tokens,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        choice = response.choices[0] if response.choices else None
        return choice.message.content or "" if choice else ""


class GoogleProvider(BaseLLMProvider):
    """Google Gemini via its OpenAI-compatible Chat Completions endpoint."""

    _BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"

    def __init__(self, api_key: str, model: str, max_tokens: int) -> None:
        import openai

        self._client = openai.AsyncOpenAI(api_key=api_key, base_url=self._BASE_URL)
        self._model = model
        self._max_tokens = max_tokens

    async def complete(self, system: str, user: str) -> str:
        response = await self._client.chat.completions.create(
            model=self._model,
            max_tokens=self._max_tokens,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        choice = response.choices[0] if response.choices else None
        return choice.message.content or "" if choice else ""


def _resolve_model() -> str:
    """Return the configured model, falling back to a provider-specific default."""
    if settings.ai_model:
        return settings.ai_model
    return _DEFAULT_MODELS.get(settings.ai_provider, "")


def get_provider() -> BaseLLMProvider:
    """Instantiate the LLM provider selected by ``ITINERARY_AI_PROVIDER``."""
    provider = settings.ai_provider.lower()
    model = _resolve_model()

    if provider == "anthropic":
        if not settings.anthropic_api_key:
            raise ValueError("ITINERARY_ANTHROPIC_API_KEY is required for the Anthropic provider")
        return AnthropicProvider(settings.anthropic_api_key, model, settings.ai_max_tokens)

    if provider == "openai":
        if not settings.openai_api_key:
            raise ValueError("ITINERARY_OPENAI_API_KEY is required for the OpenAI provider")
        return OpenAIProvider(settings.openai_api_key, model, settings.ai_max_tokens)

    if provider == "google":
        if not settings.google_api_key:
            raise ValueError("ITINERARY_GOOGLE_API_KEY is required for the Google provider")
        return GoogleProvider(settings.google_api_key, model, settings.ai_max_tokens)

    raise ValueError(f"Unsupported AI provider: {provider!r}. Use 'anthropic', 'openai', or 'google'.")
