"""
OpenAI-Compatible Proxy Gateway
FastAPI server exposing standard OpenAI v1 REST endpoints backed by the free OpenCode daemon.
"""

from __future__ import annotations
import asyncio
import json
import time
import uuid
from typing import AsyncGenerator
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

from free_ai.client import FreeAIClient
from free_ai.daemon import DEFAULT_DAEMON_URL, ensure_daemon_running
from free_ai.models import (
    ChatCompletionChoice,
    ChatCompletionChoiceMessage,
    ChatCompletionChunk,
    ChatCompletionChunkChoice,
    ChatCompletionRequest,
    ChatCompletionResponse,
    DeltaMessage,
    ModelCard,
    ModelListResponse,
    UsageInfo,
)

app = FastAPI(
    title="Free AI Gateway (OpenAI Compatible)",
    description="Drop-in $0.00 OpenAI-compatible gateway powered by local OpenCode daemon.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_client = FreeAIClient(auto_start=True)

AVAILABLE_MODELS = [
    ModelCard(id="deepseek-v4.1-flash-free"),
    ModelCard(id="nemotron-3.5-super-vl-free"),
    ModelCard(id="opencode/free"),
    ModelCard(id="gpt-4o"),  # Alias for third-party libraries hardcoding gpt-4o
]


@app.get("/health")
async def health_check():
    alive = ensure_daemon_running()
    return {"status": "ok" if alive else "daemon_offline", "backend": DEFAULT_DAEMON_URL}


@app.get("/v1/models")
async def list_models():
    return ModelListResponse(data=AVAILABLE_MODELS)


@app.post("/v1/chat/completions")
async def create_chat_completion(req: ChatCompletionRequest):
    req_id = f"chatcmpl-{uuid.uuid4().hex[:12]}"

    # Map model aliases
    target_model = req.model
    if target_model in ("gpt-4o", "opencode/free", "default"):
        target_model = "deepseek-v4.1-flash-free"

    # Convert OpenAI messages to free_ai format
    formatted_messages = []
    for m in req.messages:
        content_str = ""
        if isinstance(m.content, str):
            content_str = m.content
        elif isinstance(m.content, list):
            # Extract text parts
            texts = [p.text for p in m.content if p.type == "text" and p.text]
            content_str = " ".join(texts)
        formatted_messages.append({"role": m.role, "content": content_str})

    # Non-streaming response
    if not req.stream:
        try:
            loop = asyncio.get_running_loop()
            resp = await loop.run_in_executor(
                None,
                lambda: _client.chat(prompt=formatted_messages, model=target_model),
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"OpenCode inference failure: {e}")

        choice = ChatCompletionChoice(
            index=0,
            message=ChatCompletionChoiceMessage(
                role="assistant",
                content=resp.content,
                reasoning_content=resp.reasoning or None,
            ),
            finish_reason="stop",
        )

        return ChatCompletionResponse(
            id=req_id,
            model=req.model,
            choices=[choice],
            usage=UsageInfo(
                prompt_tokens=resp.prompt_tokens,
                completion_tokens=resp.completion_tokens,
                total_tokens=resp.total_tokens,
            ),
        )

    # Streaming response (SSE)
    async def sse_generator() -> AsyncGenerator[str, None]:
        loop = asyncio.get_running_loop()
        try:
            resp = await loop.run_in_executor(
                None,
                lambda: _client.chat(prompt=formatted_messages, model=target_model),
            )
        except Exception as e:
            err_chunk = f"data: {json.dumps({'error': str(e)})}\n\n"
            yield err_chunk
            yield "data: [DONE]\n\n"
            return

        # First send role
        first_chunk = ChatCompletionChunk(
            id=req_id,
            model=req.model,
            choices=[ChatCompletionChunkChoice(index=0, delta=DeltaMessage(role="assistant"))],
        )
        yield f"data: {first_chunk.model_dump_json()}\n\n"

        # Stream reasoning (if present)
        if resp.reasoning:
            r_chunk = ChatCompletionChunk(
                id=req_id,
                model=req.model,
                choices=[ChatCompletionChunkChoice(index=0, delta=DeltaMessage(reasoning_content=resp.reasoning))],
            )
            yield f"data: {r_chunk.model_dump_json()}\n\n"

        # Stream content tokens in chunks
        text = resp.content
        chunk_size = 20
        for i in range(0, len(text), chunk_size):
            segment = text[i : i + chunk_size]
            chunk = ChatCompletionChunk(
                id=req_id,
                model=req.model,
                choices=[ChatCompletionChunkChoice(index=0, delta=DeltaMessage(content=segment))],
            )
            yield f"data: {chunk.model_dump_json()}\n\n"
            await asyncio.sleep(0.015)

        # Final stop chunk
        stop_chunk = ChatCompletionChunk(
            id=req_id,
            model=req.model,
            choices=[ChatCompletionChunkChoice(index=0, delta=DeltaMessage(), finish_reason="stop")],
        )
        yield f"data: {stop_chunk.model_dump_json()}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(sse_generator(), media_type="text/event-stream")
