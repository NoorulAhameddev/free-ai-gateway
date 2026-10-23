"""
Free AI Package
Drop-in zero-cost AI model inference via local OpenCode daemon.
"""

from __future__ import annotations
from typing import Dict, List, Optional, Union
from free_ai.client import FreeAIClient, FreeAIResponse
from free_ai.daemon import ensure_daemon_running, is_daemon_alive

__all__ = [
    "FreeAIClient",
    "FreeAIResponse",
    "ensure_daemon_running",
    "is_daemon_alive",
    "chat",
    "stream",
]

_shared_client: Optional[FreeAIClient] = None


def _get_shared_client() -> FreeAIClient:
    global _shared_client
    if _shared_client is None:
        _shared_client = FreeAIClient()
    return _shared_client


def chat(
    prompt: Union[str, List[Dict[str, str]]],
    model: Optional[str] = None,
    system_prompt: Optional[str] = None,
) -> FreeAIResponse:
    """Convenience helper: chat with free model without manual client instantiation."""
    client = _get_shared_client()
    return client.chat(prompt=prompt, model=model, system_prompt=system_prompt)


def stream(
    prompt: Union[str, List[Dict[str, str]]],
    model: Optional[str] = None,
    system_prompt: Optional[str] = None,
):
    """Convenience helper: stream tokens from free model."""
    client = _get_shared_client()
    return client.stream_chat(prompt=prompt, model=model, system_prompt=system_prompt)
