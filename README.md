# My Agent

基于 LangChain + OpenRouter 的智能体 HTTP API 服务，支持动态创建和管理多个 Agent。

**线上地址：** `https://my-agent-be0o.onrender.com`

交互式 API 文档：`https://my-agent-be0o.onrender.com/docs`

---

## 快速开始（本地开发）

```bash
cd my-agent

# 1. 安装依赖
pip install -e .

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env，填入以下变量：
#   OPENROUTER_API_KEY=sk-or-...
#   DATABASE_URL=postgresql://user:password@host/dbname

# 3. 启动服务
uvicorn main:app --reload
```

---

## API 文档

### Agent 管理

#### GET /agents — 列出所有 Agent

```bash
curl https://my-agent-be0o.onrender.com/agents
```

响应：

```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "写作助手",
    "model": "google/gemini-3-flash-preview",
    "system_prompt": "你是一个写作助手",
    "created_at": "2026-03-14T02:00:00+00:00"
  }
]
```

#### POST /agents — 创建 Agent

```bash
curl -X POST https://my-agent-be0o.onrender.com/agents \
  -H "Content-Type: application/json" \
  -d '{
    "name": "写作助手",
    "model": "google/gemini-3-flash-preview",
    "system_prompt": "你是一个写作助手，擅长各种文体创作"
  }'
```

响应（201）：

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "写作助手",
  "model": "google/gemini-3-flash-preview",
  "system_prompt": "你是一个写作助手，擅长各种文体创作",
  "created_at": "2026-03-14T02:00:00+00:00"
}
```

#### GET /agents/{agent_id} — 获取 Agent 详情

```bash
curl https://my-agent-be0o.onrender.com/agents/550e8400-e29b-41d4-a716-446655440000
```

#### PUT /agents/{agent_id} — 更新 Agent

```bash
curl -X PUT https://my-agent-be0o.onrender.com/agents/550e8400-e29b-41d4-a716-446655440000 \
  -H "Content-Type: application/json" \
  -d '{
    "name": "写作助手 v2",
    "model": "anthropic/claude-sonnet-4-5",
    "system_prompt": "你是一个专业写作助手"
  }'
```

#### DELETE /agents/{agent_id} — 删除 Agent

```bash
curl -X DELETE https://my-agent-be0o.onrender.com/agents/550e8400-e29b-41d4-a716-446655440000
```

响应：`{"status": "ok"}`

---

### 对话（绑定具体 Agent）

#### POST /agents/{agent_id}/chat — 单轮对话

```bash
curl -X POST https://my-agent-be0o.onrender.com/agents/550e8400-e29b-41d4-a716-446655440000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "帮我写一首关于春天的诗"}'
```

响应：

```json
{"reply": "春风轻抚柳丝长..."}
```

#### POST /agents/{agent_id}/chat/session — 多轮对话（带历史）

用 `session_id` 标识一个对话会话，同一 `session_id` 的请求共享历史上下文。

```bash
# 第一轮
curl -X POST https://my-agent-be0o.onrender.com/agents/550e8400-e29b-41d4-a716-446655440000/chat/session \
  -H "Content-Type: application/json" \
  -d '{"session_id": "user-1", "message": "我想写一篇关于环保的文章"}'

# 第二轮（携带上文记忆）
curl -X POST https://my-agent-be0o.onrender.com/agents/550e8400-e29b-41d4-a716-446655440000/chat/session \
  -H "Content-Type: application/json" \
  -d '{"session_id": "user-1", "message": "帮我列出三个论点"}'
```

#### DELETE /agents/{agent_id}/chat/session/{session_id} — 清除会话历史

```bash
curl -X DELETE https://my-agent-be0o.onrender.com/agents/550e8400-e29b-41d4-a716-446655440000/chat/session/user-1
```

---

### 兼容接口（使用默认 Agent）

以下接口使用 `config.yaml` 中配置的默认 Agent，保留用于向后兼容。

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/chat` | 单轮对话 |
| `POST` | `/chat/session` | 多轮对话 |
| `DELETE` | `/chat/session/{session_id}` | 清除会话 |

---

### GET /health — 健康检查

```bash
curl https://my-agent-be0o.onrender.com/health
# {"status": "ok"}
```

---

## 模型参考

`model` 字段填写 OpenRouter 支持的模型名，例如：

| 模型 | model 值 |
|------|----------|
| Gemini 2.0 Flash | `google/gemini-3-flash-preview` |
| Claude Sonnet | `anthropic/claude-sonnet-4-5` |
| GPT-4o | `openai/gpt-4o` |

完整列表见 [openrouter.ai/models](https://openrouter.ai/models)。
