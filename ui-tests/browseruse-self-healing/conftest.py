"""
pytest configuration for self-healing tests.
- asyncio_mode = auto (pytest-asyncio)
- loads .env
- shared llm fixture
"""
import os

import pytest
import pytest_asyncio
from dotenv import load_dotenv, find_dotenv
from browser_use.llm.anthropic.chat import ChatAnthropic

# Traverse parent directories to find .env (handles running from any subdir)
load_dotenv(find_dotenv(usecwd=True))

# Tell pytest-asyncio to treat every async test/fixture as auto-mode
def pytest_configure(config):
    config.addinivalue_line(
        "markers", "asyncio: mark test as async"
    )


@pytest.fixture(scope="session")
def llm() -> ChatAnthropic:
    return ChatAnthropic(
        model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6"),
        api_key=os.getenv("ANTHROPIC_API_KEY"),
    )
