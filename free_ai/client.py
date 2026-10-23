"""
Free AI Python Client
Direct programmatic interface to the zero-cost OpenCode local bridge.
"""

from __future__ import annotations
from dataclasses import dataclass, field
import json
import time
from typing import Any, Dict, Generator, List, Optional, Union
import httpx

from free_ai.daemon import DEFAULT_DAEMON_URL, ensure_daemon_running


@dataclass
class FreeAIResponse:
    content: str
    reasoning: str = ""
    model: str = "deepseek-v4.1-flash-free"
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    latency_seconds: float = 0.0
    cost_usd: float = 0.0  # Always $0.00!


class FreeAIClient:
    """
    High-level Python client for OpenCode free models.
    """

    def __init__(
        self,
        base_url: str = DEFAULT_DAEMON_URL,
        default_model: str = "deepseek-v4.1-flash-free",
        auto_start: bool = True,
        timeout: float = 120.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.default_model = default_model
        self.auto_start = auto_start
        self.timeout = timeout
        self.session_id: Optional[str] = None

        if self.auto_start:
            ensure_daemon_running(self.base_url)

    def _get_or_create_session(self) -> str:
        if self.session_id:
            return self.session_id

        if self.auto_start:
            ensure_daemon_running(self.base_url)

        with httpx.Client(base_url=self.base_url, timeout=15.0) as client:
            res = client.post("/session", json={"directory": "."})
            res.raise_for_status()
            self.session_id = res.json()["id"]
            return self.session_id

    def chat(
        self,
        prompt: Union[str, List[Dict[str, str]]],
        model: Optional[str] = None,
        system_prompt: Optional[str] = None,
    ) -> FreeAIResponse:
        """
        Sends a prompt and returns the completed text response with reasoning.
        """
        sid = self._get_or_create_session()
        chosen_model = model or self.default_model

        # Normalize prompt
        conversation_blocks: List[str] = []
        if system_prompt:
            conversation_blocks.append(f"System Instructions:\n{system_prompt}")

        if isinstance(prompt, str):
            conversation_blocks.append(prompt)
        elif isinstance(prompt, list):
            for msg in prompt:
                role = msg.get("role", "user").capitalize()
                content = msg.get("content", "")
                conversation_blocks.append(f"{role}:\n{content}")

        full_text = "\n\n".join(conversation_blocks)

        payload = {
            "model": {
                "providerID": "opencode",
                "modelID": chosen_model,
            },
            "parts": [
                {
                    "type": "text",
                    "text": full_text,
                }
            ],
        }

        t0 = time.perf_counter()
        with httpx.Client(base_url=self.base_url, timeout=self.timeout) as client:
            res = client.post(f"/session/{sid}/message", json=payload)
            res.raise_for_status()
            data = res.json()
        latency = time.perf_counter() - t0

        reasoning_parts: List[str] = []
        text_parts: List[str] = []

        for part in data.get("parts", []):
            ptype = part.get("type")
            if ptype == "reasoning":
                reasoning_parts.append(part.get("text", ""))
            elif ptype == "text":
                text_parts.append(part.get("text", ""))

        tokens = data.get("info", {}).get("tokens", {})
        inp_tok = tokens.get("input", 0)
        out_tok = tokens.get("output", 0)

        return FreeAIResponse(
            content="\n".join(text_parts).strip(),
            reasoning="\n".join(reasoning_parts).strip(),
            model=chosen_model,
            prompt_tokens=inp_tok,
            completion_tokens=out_tok,
            total_tokens=inp_tok + out_tok,
            latency_seconds=latency,
            cost_usd=0.0,
        )

    def stream_chat(
        self,
        prompt: Union[str, List[Dict[str, str]]],
        model: Optional[str] = None,
        system_prompt: Optional[str] = None,
        chunk_size: int = 15,
    ) -> Generator[str, None, None]:
        """
        Yields text chunks. Generates smooth streaming output for UIs and terminals.
        """
        resp = self.chat(prompt=prompt, model=model, system_prompt=system_prompt)
        text = resp.content
        for i in range(0, len(text), chunk_size):
            yield text[i : i + chunk_size]
            time.sleep(0.01)
