"""FastAPI entry point."""

from __future__ import annotations

from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from agent import Agent

load_dotenv()

_agent: Agent | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _agent
    _agent = Agent()
    yield


app = FastAPI(title="My Agent", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str


class SessionChatRequest(BaseModel):
    session_id: str
    message: str


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """单轮对话，无历史记忆。"""
    if _agent is None:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    reply = _agent.chat(request.message)
    return ChatResponse(reply=reply)


@app.post("/chat/session", response_model=ChatResponse)
async def chat_with_session(request: SessionChatRequest) -> ChatResponse:
    """多轮对话，按 session_id 保持历史。"""
    if _agent is None:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    reply = _agent.chat_with_session(request.session_id, request.message)
    return ChatResponse(reply=reply)


@app.delete("/chat/session/{session_id}")
async def clear_session(session_id: str) -> dict:
    """清除指定会话的历史。"""
    if _agent is None:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    _agent.clear_session(session_id)
    return {"status": "ok"}


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
