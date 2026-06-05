import os
from pathlib import Path
from unittest.mock import patch

import pytest

from app.core.config import (
    BASE_DIR,
    CHROMA_DIR,
    DATA_DIR,
    JOBS_DIR,
    PROMPTS_DIR,
    RESUMES_DIR,
    Settings,
)


def test_settings_loads_defaults():
    env = {
        "NVIDIA_API_KEY": "",
        "NVIDIA_BASE_URL": "https://integrate.api.nvidia.com/v1",
        "NVIDIA_MODEL": "meta/llama-3.1-8b-instruct",
        "OLLAMA_BASE_URL": "http://localhost:11434",
        "OLLAMA_MODEL": "llama3.1:8b",
        "LLM_PROVIDER": "nvidia",
    }
    with patch.dict(os.environ, env, clear=False):
        s = Settings()
        assert s.APP_NAME == "AI Career Agent"
        assert s.APP_VERSION == "0.1.0"
        assert s.DEBUG is True
        assert s.NVIDIA_API_KEY == ""
        assert s.NVIDIA_BASE_URL == "https://integrate.api.nvidia.com/v1"
        assert s.NVIDIA_MODEL == "meta/llama-3.1-8b-instruct"
        assert s.OLLAMA_BASE_URL == "http://localhost:11434"
        assert s.OLLAMA_MODEL == "llama3.1:8b"
        assert s.LLM_PROVIDER == "nvidia"
        assert s.EMBEDDING_MODEL == "all-MiniLM-L6-v2"
        assert s.TOP_K_RETRIEVAL == 5
        assert s.MATCH_SCORE_THRESHOLD == 60.0


def test_data_directories_created():
    assert DATA_DIR.exists()
    assert CHROMA_DIR.exists()
    assert RESUMES_DIR.exists()
    assert JOBS_DIR.exists()


def test_env_file_loading(tmp_path):
    env = {
        "APP_NAME": "TestApp",
        "DEBUG": "false",
        "NVIDIA_API_KEY": "test-key-123",
        "LLM_PROVIDER": "ollama",
    }
    with patch.dict(os.environ, env, clear=False):
        s = Settings()
        assert s.APP_NAME == "TestApp"
        assert s.DEBUG is False
        assert s.NVIDIA_API_KEY == "test-key-123"
        assert s.LLM_PROVIDER == "ollama"
