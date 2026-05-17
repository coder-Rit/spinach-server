import logging
import threading
from enum import StrEnum
from typing import Optional

from langchain_openai import ChatOpenAI

from app.core.config import settings
from app.helpers.log_helper import get_llm_callbacks

logger = logging.getLogger(__name__)


class LLMProvider(StrEnum):
    OPENAI = "openai"
    OPENROUTER = "openrouter"
    GEMINI = "gemini"
    NVIDIA = "nvidia"


class _GeminiKeyRotator:
    """Thread-safe round-robin over configured Gemini API keys."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._index = 0

    def next_key(self) -> str:
        keys = settings.gemini_api_keys
        if not keys:
            raise ValueError(
                "No Gemini API keys configured. Set GEMINI_API_KEY_1 … GEMINI_API_KEY_5 in .env"
            )
        with self._lock:
            key = keys[self._index % len(keys)]
            slot = self._index % len(keys) + 1
            self._index += 1
        logger.debug("Using Gemini API key slot %s/%s", slot, len(keys))
        return key


_gemini_key_rotator = _GeminiKeyRotator()


class AiClient:
    @staticmethod
    def get_llm(
        provider: LLMProvider | str = LLMProvider.OPENAI,
        model: Optional[str] = None,
        temperature: float = 0.9,
        api_key: Optional[str] = None,
    ) -> ChatOpenAI:
        provider = LLMProvider(provider)

        common_kwargs = {
            "temperature": temperature,
            "callbacks": get_llm_callbacks(),
        }

        if provider == LLMProvider.GEMINI:
            resolved_key = api_key or (
                settings.gemini_api_keys[0] if settings.gemini_api_keys else ""
            )
            if not resolved_key:
                raise ValueError(
                    "No Gemini API keys configured. Set GEMINI_API_KEY_1 … GEMINI_API_KEY_5 in .env"
                )
            return ChatOpenAI(
                model=model or settings.GEMINI_MODEL,
                api_key=resolved_key,
                base_url="https://generativelanguage.googleapis.com/v1beta/openai",
                **common_kwargs,
            )

        raise ValueError(f"Unsupported provider: {provider}")

    @staticmethod
    def get_chat_llm(
        model: Optional[str] = None,
        temperature: float = 0.9,
    ) -> ChatOpenAI:
        """LLM for /llm chat: picks the next Gemini key (round-robin per request)."""
        api_key = _gemini_key_rotator.next_key()
        return AiClient.get_llm(
            LLMProvider.GEMINI,
            model=model,
            temperature=temperature,
            api_key=api_key,
        )

    @staticmethod
    def get_default_llm() -> ChatOpenAI:
        """Default LLM (first configured Gemini key). Prefer get_chat_llm for /llm."""
        return AiClient.get_llm(LLMProvider.GEMINI)
