from unittest.mock import MagicMock, patch

import pytest

from app.core.llm_factory import get_llm


@pytest.fixture
def mock_settings():
    with patch("app.core.llm_factory.settings") as mock:
        mock.LLM_PROVIDER = "nvidia"
        mock.NVIDIA_API_KEY = "test-key"
        mock.NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"
        mock.NVIDIA_MODEL = "meta/llama-3.1-8b-instruct"
        mock.OLLAMA_BASE_URL = "http://localhost:11434"
        mock.OLLAMA_MODEL = "llama3.1:8b"
        yield mock


def test_get_llm_nvidia(mock_settings):
    with patch("langchain_openai.ChatOpenAI") as mock_chat:
        mock_chat.return_value = MagicMock()
        llm = get_llm(temperature=0.5)
        mock_chat.assert_called_once_with(
            model="meta/llama-3.1-8b-instruct",
            api_key="test-key",
            base_url="https://integrate.api.nvidia.com/v1",
            temperature=0.5,
        )
        assert llm is not None


def test_get_llm_ollama(mock_settings):
    mock_settings.LLM_PROVIDER = "ollama"
    with patch("app.core.llm_factory._create_ollama") as mock_ollama:
        mock_ollama.return_value = MagicMock()
        llm = get_llm(temperature=0.7)
        mock_ollama.assert_called_once_with(0.7)
        assert llm is not None


def test_get_llm_unknown_provider(mock_settings):
    mock_settings.LLM_PROVIDER = "anthropic"
    with pytest.raises(ValueError, match="Unknown LLM_PROVIDER"):
        get_llm()


def test_fallback_to_ollama(mock_settings):
    mock_settings.NVIDIA_API_KEY = ""
    with patch("app.core.llm_factory._create_ollama") as mock_ollama:
        mock_ollama.return_value = MagicMock()
        llm = get_llm(temperature=0.7)
        mock_ollama.assert_called_once_with(0.7)
        assert llm is not None
