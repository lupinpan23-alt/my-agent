"""FastAPI entry point."""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from typing import Any

import yaml
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import database
from agent import Agent

load_dotenv()

# 全局单例（向后兼容）
_agent: Agent | None = None

# 多 Agent 内存缓存：{agent_id: Agent}
_agent_cache: dict[str, Agent] = {}


def _load_default_agent() -> Agent | None:
    """从 config.yaml 加载默认 Agent（向后兼容）。"""
    try:
        with open("config.yaml") as f:
            cfg = yaml.safe_load(f)
        return Agent(
            name="default",
            model=cfg["model"],
            system_prompt=cfg["system_prompt"],
        )
    except FileNotFoundError:
        return None


def _get_agent_instance(agent_id: str) -> Agent:
    """按 agent_id 获取 Agent 实例，优先从缓存取，否则从数据库加载。"""
    if agent_id not in _agent_cache:
        row = database.get_agent(agent_id)
        if row is None:
            raise HTTPException(status_code=404, detail=f"Agent {agent_id!r} not found")
        _agent_cache[agent_id] = Agent(
            name=row["name"],
            model=row["model"],
            system_prompt=row["system_prompt"],
        )
    return _agent_cache[agent_id]


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _agent
    database.init_db()
    _agent = _load_default_agent()
    yield


app = FastAPI(title="My Agent", version="0.2.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Pydantic models ───────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str


class SessionChatRequest(BaseModel):
    session_id: str
    message: str


class AgentCreateRequest(BaseModel):
    name: str
    model: str
    system_prompt: str


class AgentUpdateRequest(BaseModel):
    name: str
    model: str
    system_prompt: str


# ── 向后兼容路由 ──────────────────────────────────────────────────────────────

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


# ── Agent CRUD ────────────────────────────────────────────────────────────────

@app.get("/agents")
async def list_agents() -> list[dict]:
    """列出所有 Agent。"""
    return database.list_agents()


@app.post("/agents", status_code=201)
async def create_agent(request: AgentCreateRequest) -> dict:
    """创建新 Agent。"""
    agent_id = str(uuid.uuid4())
    return database.create_agent(
        agent_id=agent_id,
        name=request.name,
        model=request.model,
        system_prompt=request.system_prompt,
    )


@app.get("/agents/{agent_id}")
async def get_agent(agent_id: str) -> dict:
    """获取单个 Agent 详情。"""
    row = database.get_agent(agent_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id!r} not found")
    return row


@app.put("/agents/{agent_id}")
async def update_agent(agent_id: str, request: AgentUpdateRequest) -> dict:
    """更新 Agent 配置。"""
    row = database.update_agent(
        agent_id=agent_id,
        name=request.name,
        model=request.model,
        system_prompt=request.system_prompt,
    )
    if row is None:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id!r} not found")
    # 使缓存失效，下次请求时重新加载
    _agent_cache.pop(agent_id, None)
    return row


@app.delete("/agents/{agent_id}")
async def delete_agent(agent_id: str) -> dict:
    """删除 Agent。"""
    deleted = database.delete_agent(agent_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id!r} not found")
    _agent_cache.pop(agent_id, None)
    return {"status": "ok"}


# ── 绑定 agent_id 的对话路由 ──────────────────────────────────────────────────

@app.post("/agents/{agent_id}/chat", response_model=ChatResponse)
async def agent_chat(agent_id: str, request: ChatRequest) -> ChatResponse:
    """单轮对话（绑定到具体 Agent）。"""
    agent = _get_agent_instance(agent_id)
    reply = agent.chat(request.message)
    return ChatResponse(reply=reply)


@app.post("/agents/{agent_id}/chat/session", response_model=ChatResponse)
async def agent_chat_with_session(agent_id: str, request: SessionChatRequest) -> ChatResponse:
    """多轮对话（绑定到具体 Agent，带 session_id）。"""
    agent = _get_agent_instance(agent_id)
    reply = agent.chat_with_session(request.session_id, request.message)
    return ChatResponse(reply=reply)


@app.delete("/agents/{agent_id}/chat/session/{session_id}")
async def agent_clear_session(agent_id: str, session_id: str) -> dict:
    """清除指定 Agent 的会话历史。"""
    agent = _get_agent_instance(agent_id)
    agent.clear_session(session_id)
    return {"status": "ok"}


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health() -> dict:
    info: dict[str, Any] = {"status": "ok"}
    if _agent is not None:
        info["default_agent"] = {
            "name": _agent.name,
            "model": _agent.model_name,
        }
    info["cached_agents"] = len(_agent_cache)
    return info
