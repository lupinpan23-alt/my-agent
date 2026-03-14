"""Agent initialization and invocation."""

from __future__ import annotations

import os
from typing import Any

import yaml
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openrouter import ChatOpenRouter


def load_config(config_path: str = "config.yaml") -> dict[str, Any]:
    with open(config_path) as f:
        return yaml.safe_load(f)


class Agent:
    def __init__(self, name: str, model: str, system_prompt: str) -> None:
        self.name = name
        self.system_prompt = system_prompt
        self.model_name = model
        self.llm = ChatOpenRouter(
            model=self.model_name,
            api_key=os.getenv("OPENROUTER_API_KEY"),
        )
        # 会话历史：{session_id: [messages]}
        self._sessions: dict[str, list] = {}

    def chat(self, message: str) -> str:
        """单轮对话，无历史记忆。"""
        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=message),
        ]
        response = self.llm.invoke(messages)
        return response.content

    def chat_with_session(self, session_id: str, message: str) -> str:
        """多轮对话，按 session_id 保持历史。"""
        if session_id not in self._sessions:
            self._sessions[session_id] = [SystemMessage(content=self.system_prompt)]

        history = self._sessions[session_id]
        history.append(HumanMessage(content=message))

        response = self.llm.invoke(history)
        history.append(response)

        return response.content

    def clear_session(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)
