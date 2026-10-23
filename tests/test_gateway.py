"""
Integration tests for OpenAI-compatible gateway endpoints
"""

from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
import pytest
from free_ai.client import FreeAIResponse
from free_ai.gateway import app

client = TestClient(app)


def test_health_endpoint():
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert "status" in data
    assert "backend" in data


def test_list_models_endpoint():
    res = client.get("/v1/models")
    assert res.status_code == 200
    data = res.json()
    assert data["object"] == "list"
    ids = [m["id"] for m in data["data"]]
    assert "deepseek-v4.1-flash-free" in ids
    assert "nemotron-3.5-super-vl-free" in ids


@patch("free_ai.gateway._client.chat")
def test_chat_completions_non_streaming(mock_chat):
    mock_chat.return_value = FreeAIResponse(
        content="This is the answer.",
        reasoning="Thinking carefully...",
        model="deepseek-v4.1-flash-free",
        prompt_tokens=12,
        completion_tokens=8,
        total_tokens=20,
        latency_seconds=0.8,
        cost_usd=0.0,
    )

    payload = {
        "model": "deepseek-v4.1-flash-free",
        "messages": [
            {"role": "user", "content": "What is 2+2?"}
        ],
        "stream": False,
    }

    res = client.post("/v1/chat/completions", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["object"] == "chat.completion"
    assert data["choices"][0]["message"]["content"] == "This is the answer."
    assert data["choices"][0]["message"]["reasoning_content"] == "Thinking carefully..."
    assert data["usage"]["total_tokens"] == 20


@patch("free_ai.gateway._client.chat")
def test_chat_completions_streaming(mock_chat):
    mock_chat.return_value = FreeAIResponse(
        content="Streaming test response.",
        reasoning="Deep thought",
        model="deepseek-v4.1-flash-free",
    )

    payload = {
        "model": "deepseek-v4.1-flash-free",
        "messages": [
            {"role": "user", "content": "Stream me a poem"}
        ],
        "stream": True,
    }

    res = client.post("/v1/chat/completions", json=payload)
    assert res.status_code == 200
    assert "text/event-stream" in res.headers["content-type"]
    text = res.text
    assert "data: " in text
    assert "[DONE]" in text
