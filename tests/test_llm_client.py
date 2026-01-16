"""Unit tests for LLMClient wrapper."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.llm.client import LLMClient
from src.llm.base import LLMResponse


class TestLLMClient:
    """Tests for LLMClient backwards-compatibility wrapper."""

    @pytest.fixture
    def mock_llm_provider(self):
        """Create a mock LLM provider."""
        mock_provider = MagicMock()
        mock_provider.complete = AsyncMock()
        return mock_provider

    @pytest.fixture
    def llm_client(self, mock_llm_provider):
        """Create LLMClient instance with mocked provider."""
        with patch("src.llm.client.llm_provider", mock_llm_provider):
            client = LLMClient()
            client._mock_provider = mock_llm_provider  # Store for test access
            yield client

    def test_complete_returns_parsed_json(self, llm_client):
        """Test that complete returns parsed JSON with token count."""
        # Setup mock response
        mock_response = LLMResponse(
            content='{"classification": "PROMISE_TO_PAY", "confidence": 0.95}',
            model="gemini-3-flash-preview",
            provider="gemini",
            usage={"prompt_tokens": 50, "completion_tokens": 20, "total_tokens": 70},
        )
        llm_client._mock_provider.complete.return_value = mock_response

        result = llm_client.complete(
            system_prompt="You are a classifier",
            user_prompt="Classify this email",
        )

        assert result["classification"] == "PROMISE_TO_PAY"
        assert result["confidence"] == 0.95
        assert result["_tokens_used"] == 70

    def test_complete_handles_markdown_json(self, llm_client):
        """Test that complete strips markdown code blocks from JSON."""
        # Some LLMs wrap JSON in markdown code blocks
        mock_response = LLMResponse(
            content='```json\n{"subject": "Test", "body": "Hello"}\n```',
            model="gemini-3-flash-preview",
            provider="gemini",
            usage={"prompt_tokens": 30, "completion_tokens": 15, "total_tokens": 45},
        )
        llm_client._mock_provider.complete.return_value = mock_response

        result = llm_client.complete(
            system_prompt="Generate email",
            user_prompt="Write a test email",
        )

        assert result["subject"] == "Test"
        assert result["body"] == "Hello"
        assert result["_tokens_used"] == 45

    def test_complete_non_json_response(self, llm_client):
        """Test complete with json_response=False returns raw content."""
        mock_response = LLMResponse(
            content="This is a plain text response",
            model="gemini-3-flash-preview",
            provider="gemini",
            usage={"prompt_tokens": 20, "completion_tokens": 10, "total_tokens": 30},
        )
        llm_client._mock_provider.complete.return_value = mock_response

        result = llm_client.complete(
            system_prompt="Summarize",
            user_prompt="Summarize this text",
            json_response=False,
        )

        assert result["content"] == "This is a plain text response"
        assert result["_tokens_used"] == 30

    def test_complete_passes_parameters_to_provider(self, llm_client):
        """Test that temperature and max_tokens are passed to provider."""
        mock_response = LLMResponse(
            content='{"result": "ok"}',
            model="gemini-3-flash-preview",
            provider="gemini",
            usage={"total_tokens": 25},
        )
        llm_client._mock_provider.complete.return_value = mock_response

        llm_client.complete(
            system_prompt="Test",
            user_prompt="Test prompt",
            temperature=0.5,
            max_tokens=1000,
        )

        # Verify provider was called with correct parameters
        call_kwargs = llm_client._mock_provider.complete.call_args.kwargs
        assert call_kwargs["temperature"] == 0.5
        assert call_kwargs["max_tokens"] == 1000
        assert call_kwargs["json_mode"] is True

    def test_complete_raises_on_invalid_json(self, llm_client):
        """Test that complete raises JSONDecodeError on invalid JSON."""
        mock_response = LLMResponse(
            content="This is not valid JSON {broken",
            model="gemini-3-flash-preview",
            provider="gemini",
            usage={"total_tokens": 20},
        )
        llm_client._mock_provider.complete.return_value = mock_response

        import json
        with pytest.raises(json.JSONDecodeError):
            llm_client.complete(
                system_prompt="Test",
                user_prompt="Test prompt",
                json_response=True,
            )
