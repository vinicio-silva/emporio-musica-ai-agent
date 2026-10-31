"""FastAPI asynchronous REST server and SSE streaming bridge for Empório da Música.

Provides /health diagnostics, /api/chat with Server-Sent Events (SSE) streaming,
/api/products catalog feed, and serves the static storefront.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, AsyncIterator, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from src.agent import get_agent, memory
from src.database import DEFAULT_DB_PATH, get_connection, list_all_products
from src.llm import get_llm_client
from src.rag import get_rag_engine

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(
    title="Empório da Música — AI Customer Service Agent API",
    description="Production-grade AI customer service agent for Empório da Música (Campo Grande/MS).",
    version="1.0.0",
)

# Enable CORS for web storefront
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==========================================
# Pydantic Request / Response Models
# ==========================================

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="Customer message text in Portuguese.")
    session_id: str = Field(default="default", description="Unique session identifier for sliding memory.")
    stream: bool = Field(default=False, description="Whether to stream response tokens via SSE.")


class ChatResponse(BaseModel):
    response: str
    session_id: str
    intent: str


class SessionResetRequest(BaseModel):
    session_id: str


# ==========================================
# API Endpoints
# ==========================================

@app.get("/health", summary="Health check endpoint for database, RAG and LLM")
async def health_check() -> Dict[str, Any]:
    """Inspect availability of SQLite database, Policy RAG engine, and LLM connector."""
    db_ok = False
    prod_count = 0
    try:
        if DEFAULT_DB_PATH.exists():
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM products WHERE status = 'active';")
            prod_count = cur.fetchone()[0]
            conn.close()
            db_ok = True
    except Exception as exc:
        db_err = str(exc)

    rag_ok = False
    chunk_count = 0
    try:
        rag = get_rag_engine()
        chunk_count = len(rag.chunks)
        rag_ok = chunk_count > 0
    except Exception as exc:
        rag_err = str(exc)

    llm = get_llm_client()
    llm_provider = llm.__class__.__name__

    is_healthy = db_ok and rag_ok

    return {
        "status": "healthy" if is_healthy else "degraded",
        "database": {
            "status": "up" if db_ok else "down",
            "active_products": prod_count,
        },
        "rag": {
            "status": "up" if rag_ok else "down",
            "indexed_policy_chunks": chunk_count,
        },
        "llm": {
            "status": "up",
            "provider": llm_provider,
        },
    }


@app.get("/api/products", summary="Public catalog instrument feed for storefront")
async def get_products(category_id: Optional[int] = Query(None, description="Optional category filter ID")) -> List[Dict[str, Any]]:
    """Retrieve catalog products with calculated PIX discount and installment terms."""
    try:
        return list_all_products(category_id=category_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/chat", summary="Customer service chat interaction")
async def chat_endpoint(req: ChatRequest):
    """Process customer message with hierarchical routing, guardrails, and sliding-window memory."""
    agent = get_agent()
    intent = agent.classify_intent(req.message)

    if req.stream:
        async def event_generator() -> AsyncIterator[str]:
            for token in agent.chat_stream(req.message, session_id=req.session_id):
                yield json.dumps({"chunk": token, "done": False}, ensure_ascii=False)
            yield json.dumps({"chunk": "", "done": True, "intent": intent}, ensure_ascii=False)

        return EventSourceResponse(event_generator())

    response_text = agent.chat(req.message, session_id=req.session_id)
    return ChatResponse(
        response=response_text,
        session_id=req.session_id,
        intent=intent,
    )


@app.post("/api/session/reset", summary="Reset conversation session memory")
async def reset_session(req: SessionResetRequest) -> Dict[str, str]:
    """Clear memory for the specified session_id."""
    memory.clear(req.session_id)
    return {"status": "cleared", "session_id": req.session_id}


# Mount static storefront files if directory exists
if STATIC_DIR.exists():
    app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")
