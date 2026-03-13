# My Agent

基于 LangChain + OpenRouter 的智能体 HTTP API 服务。

## 快速开始

```bash
cd my-agent

# 1. 安装依赖
pip install -e .

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env，填入 OPENROUTER_API_KEY

# 3. 启动服务
uvicorn main:app --reload
```

服务默认运行在 `http://localhost:8000`，可访问 `http://localhost:8000/docs` 查看交互式 API 文档。

## 配置

编辑 `config.yaml`：

```yaml
model: "anthropic/claude-sonnet-4-5"   # OpenRouter 模型名，参考 https://openrouter.ai/models
system_prompt: "You are a helpful assistant."
```

## API

### POST /chat — 单轮对话

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "你好"}'
```

### POST /chat/session — 多轮对话（带历史）

```bash
curl -X POST http://localhost:8000/chat/session \
  -H "Content-Type: application/json" \
  -d '{"session_id": "user-1", "message": "我叫小明"}'

curl -X POST http://localhost:8000/chat/session \
  -H "Content-Type: application/json" \
  -d '{"session_id": "user-1", "message": "我叫什么名字？"}'
```

### DELETE /chat/session/{session_id} — 清除会话历史

```bash
curl -X DELETE http://localhost:8000/chat/session/user-1
```

### GET /health — 健康检查

```bash
curl http://localhost:8000/health
```
