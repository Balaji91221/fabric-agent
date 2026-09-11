"""OpenAI-compatible HTTP surface for the Fabric semantic model agent.

Any OpenAI client works against this — set base_url to http://localhost:8000/v1
and use the demo key. The agent name is the model name.
"""

from __future__ import annotations

import json
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Literal

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from .agent import Agent
from .config import get_settings
from .fabric import DaxRejected, FabricClient, FabricError

settings = get_settings()
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"


# --------------------------------------------------------------------- #
# Request / response models (OpenAI shapes)
# --------------------------------------------------------------------- #


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant", "tool"]
    content: Any = None
    name: str | None = None
    tool_call_id: str | None = None


class ChatCompletionRequest(BaseModel):
    model: str = Field(default=settings.agent_model_id)
    messages: list[ChatMessage]
    stream: bool = False
    temperature: float | None = None
    max_tokens: int | None = None
    user: str | None = None


class DaxRequest(BaseModel):
    dax: str


# --------------------------------------------------------------------- #
# App
# --------------------------------------------------------------------- #


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.fabric = FabricClient(settings)
    app.state.agent = Agent(settings, app.state.fabric)
    banner = [
        "",
        "  Fabric semantic model agent",
        f"  mode            {settings.mode}"
        + ("  (set FABRIC_* env vars to hit a real model)" if settings.mode == "demo" else ""),
        f"  agent / model   {settings.agent_model_id}",
        f"  reasoning LLM   {settings.llm_model if settings.llm_configured else 'none — using built-in planner'}",
        f"  demo key        {settings.demo_key}",
        f"  base_url        http://localhost:{settings.port}/v1",
        "",
    ]
    print("\n".join(banner), flush=True)
    yield
    await app.state.agent.aclose()
    await app.state.fabric.aclose()


app = FastAPI(title="Fabric Semantic Model Agent", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def require_key(authorization: str = Header(default="")) -> str:
    token = authorization.removeprefix("Bearer ").strip()
    if not token or token not in settings.api_keys:
        raise HTTPException(
            status_code=401,
            detail={
                "error": {
                    "message": "Missing or invalid API key. Send it as `Authorization: Bearer <key>`.",
                    "type": "invalid_request_error",
                    "code": "invalid_api_key",
                }
            },
        )
    return token


# --------------------------------------------------------------------- #
# OpenAI-compatible routes
# --------------------------------------------------------------------- #


@app.get("/v1/models")
async def list_models(_: str = Depends(require_key)) -> dict[str, Any]:
    return {
        "object": "list",
        "data": [
            {
                "id": settings.agent_model_id,
                "object": "model",
                "created": 1_700_000_000,
                "owned_by": "fabric-agent",
                "description": settings.agent_display_name,
            }
        ],
    }


@app.get("/v1/models/{model_id}")
async def retrieve_model(model_id: str, _: str = Depends(require_key)) -> dict[str, Any]:
    if model_id != settings.agent_model_id:
        raise HTTPException(404, detail={"error": {"message": f"Model '{model_id}' not found."}})
    return {
        "id": model_id,
        "object": "model",
        "created": 1_700_000_000,
        "owned_by": "fabric-agent",
    }


@app.post("/v1/chat/completions")
async def chat_completions(
    body: ChatCompletionRequest, request: Request, _: str = Depends(require_key)
):
    agent: Agent = request.app.state.agent
    messages = [m.model_dump(exclude_none=True) for m in body.messages]
    completion_id = f"chatcmpl-{uuid.uuid4().hex[:24]}"
    created = int(time.time())

    if body.stream:
        return StreamingResponse(
            _stream(agent, messages, completion_id, created, body.model),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    text_parts: list[str] = []
    steps: list[dict[str, Any]] = []
    try:
        async for ev in agent.run(messages):
            if ev.kind == "text":
                text_parts.append(ev.text)
            elif ev.kind == "step" and ev.data:
                steps.append(ev.data)
    except FabricError as exc:
        raise HTTPException(502, detail={"error": {"message": str(exc), "type": "upstream_error"}})

    content = "\n".join(p for p in text_parts if p).strip()
    prompt_chars = sum(len(str(m.get("content") or "")) for m in messages)
    return {
        "id": completion_id,
        "object": "chat.completion",
        "created": created,
        "model": body.model or settings.agent_model_id,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": prompt_chars // 4,
            "completion_tokens": len(content) // 4,
            "total_tokens": (prompt_chars + len(content)) // 4,
        },
        # Non-standard, additive: what the agent did to get here.
        "fabric_agent": {"steps": steps, "mode": settings.mode},
    }


async def _stream(agent: Agent, messages, completion_id: str, created: int, model: str):
    def chunk(
        delta: dict[str, Any],
        finish: str | None = None,
        step: dict[str, Any] | None = None,
    ) -> str:
        payload: dict[str, Any] = {
            "id": completion_id,
            "object": "chat.completion.chunk",
            "created": created,
            "model": model or settings.agent_model_id,
            "choices": [{"index": 0, "delta": delta, "finish_reason": finish}],
        }
        if step is not None:
            # Extra top-level key on an otherwise valid chunk. The official
            # OpenAI SDKs ignore unknown fields, so strict clients still work
            # while our own UI can show the tool activity.
            payload["fabric_agent"] = step
        return f"data: {json.dumps(payload, default=str)}\n\n"

    yield chunk({"role": "assistant", "content": ""})
    try:
        async for ev in agent.run(messages):
            if ev.kind == "text" and ev.text:
                for piece in _pieces(ev.text):
                    yield chunk({"content": piece})
            elif ev.kind == "step" and ev.data:
                yield chunk({}, step=ev.data)
    except FabricError as exc:
        yield chunk({"content": f"\n\n_Upstream error: {exc}_"})
    yield chunk({}, finish="stop")
    yield "data: [DONE]\n\n"


def _pieces(text: str, size: int = 24):
    for i in range(0, len(text), size):
        yield text[i : i + size]


# --------------------------------------------------------------------- #
# Agent-specific routes (used by the frontend)
# --------------------------------------------------------------------- #


@app.get("/v1/agent/info")
async def agent_info(_: str = Depends(require_key)) -> dict[str, Any]:
    return {
        "id": settings.agent_model_id,
        "name": settings.agent_display_name,
        "mode": settings.mode,
        "reasoning_model": settings.llm_model if settings.llm_configured else "built-in planner",
        "dataset_id": settings.dataset_id or "demo",
        "workspace_id": settings.workspace_id or "demo",
    }


@app.get("/v1/agent/schema")
async def agent_schema(request: Request, refresh: bool = False, _: str = Depends(require_key)):
    return await request.app.state.fabric.get_schema(refresh=refresh)


@app.post("/v1/agent/dax")
async def agent_dax(body: DaxRequest, request: Request, _: str = Depends(require_key)):
    try:
        return await request.app.state.fabric.run_dax(body.dax)
    except DaxRejected as exc:
        raise HTTPException(400, detail={"error": {"message": str(exc), "type": "invalid_dax"}})
    except FabricError as exc:
        raise HTTPException(502, detail={"error": {"message": str(exc), "type": "upstream_error"}})


@app.get("/healthz")
async def healthz() -> dict[str, Any]:
    return {"status": "ok", "mode": settings.mode, "model": settings.agent_model_id}


@app.get("/demo/key")
async def demo_key() -> JSONResponse:
    """Hands the browser demo its key. Turn off with EXPOSE_DEMO_KEY=false."""
    if not settings.expose_demo_key:
        raise HTTPException(404, detail={"error": {"message": "Demo key endpoint is disabled."}})
    return JSONResponse(
        {
            "api_key": settings.demo_key,
            "base_url": "/v1",
            "model": settings.agent_model_id,
            "note": "Demo key. Set EXPOSE_DEMO_KEY=false and use API_KEYS before deploying.",
        }
    )


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")
