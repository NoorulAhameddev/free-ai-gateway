"""
Unit tests for FreeAIClient and daemon supervisor
"""

from unittest.mock import MagicMock, patch
import pytest
from free_ai.client import FreeAIClient, FreeAIResponse
from free_ai.daemon import find_opencode_binary, is_daemon_alive


def test_daemon_binary_search():
    # Should either find string path or return None without crashing
    binary = find_opencode_binary()
    assert binary is None or isinstance(binary, str)


def test_free_ai_response_dataclass():
    resp = FreeAIResponse(
        content="Test content",
        reasoning="Test thought",
        model="deepseek-v4.1-flash-free",
        prompt_tokens=10,
        completion_tokens=20,
        total_tokens=30,
        latency_seconds=1.5,
        cost_usd=0.0,
    )
    assert resp.content == "Test content"
    assert resp.cost_usd == 0.0
    assert resp.total_tokens == 30


@patch("httpx.Client")
def test_client_chat_mock(mock_client_cls):
    mock_client = MagicMock()
    mock_client_cls.return_value.__enter__.return_value = mock_client

    # Mock /session response
    mock_sess_res = MagicMock()
    mock_sess_res.json.return_value = {"id": "ses_test_123"}
    mock_sess_res.status_code = 200

    # Mock /message response
    mock_msg_res = MagicMock()
    mock_msg_res.json.return_value = {
        "parts": [
            {"type": "reasoning", "text": "I should answer directly."},
            {"type": "text", "text": "Hello world!"},
        ],
        "info": {"tokens": {"input": 15, "output": 25}},
    }
    mock_msg_res.status_code = 200

    mock_client.post.side_effect = [mock_sess_res, mock_msg_res]

    client = FreeAIClient(auto_start=False)
    resp = client.chat("Hi")

    assert resp.content == "Hello world!"
    assert resp.reasoning == "I should answer directly."
    assert resp.cost_usd == 0.0
    assert resp.total_tokens == 40
