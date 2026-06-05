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
    settings,
)


def test_settings_loads_defaults():
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
    env_file = tmp_path / ".env"
    env_file.write_text(
        "APP_NAME=TestApp\n"
        "DEBUG=false\n"
        "NVIDIA_API_KEY=test-key-123\n"
        "LLM_PROVIDER=ollama\n"
    )
    with patch.dict(os.environ, {}, clear=False):
        os.environ["APP_NAME"] = "TestApp"
        os.environ["DEBUG"] = "false"
        os.environ["NVIDIA_API_KEY"] = "test-key-123"
        os.environ["LLM_PROVIDER"] = "ollama"
        s = Settings()
        assert s.APP_NAME == "TestApp"
        assert s.DEBUG is False
        assert s.NVIDIA_API_KEY == "test-key-123"
        assert s.LLM_PROVIDER == "ollama"
