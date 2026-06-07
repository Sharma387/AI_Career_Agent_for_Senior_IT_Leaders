import logging
from langchain_core.language_models import BaseChatModel

from app.core.config import settings

logger = logging.getLogger(__name__)


def get_llm(temperature: float = 0.7) -> BaseChatModel:
    if settings.LLM_PROVIDER == "anthropic":
        if not settings.ANTHROPIC_API_KEY:
            logger.warning("ANTHROPIC_API_KEY not set, falling back to Ollama")
            return _create_ollama(temperature)
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(
            model=settings.ANTHROPIC_MODEL,
            api_key=settings.ANTHROPIC_API_KEY,
            temperature=temperature,
        )

    if settings.LLM_PROVIDER == "nvidia":
        if not settings.NVIDIA_API_KEY:
            logger.warning("NVIDIA_API_KEY not set, falling back to Ollama")
            return _create_ollama(temperature)
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=settings.NVIDIA_MODEL,
            api_key=settings.NVIDIA_API_KEY,
            base_url=settings.NVIDIA_BASE_URL,
            temperature=temperature,
        )

    if settings.LLM_PROVIDER == "ollama":
        return _create_ollama(temperature)

    raise ValueError(f"Unknown LLM_PROVIDER: {settings.LLM_PROVIDER}")


def _create_ollama(temperature: float) -> BaseChatModel:
    try:
        from langchain_ollama import ChatOllama

        return ChatOllama(
            model=settings.OLLAMA_MODEL,
            base_url=settings.OLLAMA_BASE_URL,
            temperature=temperature,
        )
    except Exception as e:
        raise ConnectionError(
            f"Ollama not reachable at {settings.OLLAMA_BASE_URL}. "
            f"Start it with: ollama serve\nError: {e}"
        )
