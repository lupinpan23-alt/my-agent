"""
测试多 Agent 场景：
1. 创建两个 Agent（不同模型 + 不同提示词）
2. 验证每个 Agent 的模型和提示词正确存储
3. 分别与两个 Agent 进行多轮对话，验证上下文保持
4. 验证两个 Agent 之间互不干扰
5. 清理测试数据
"""

from __future__ import annotations

import sys
import uuid
import requests

BASE_URL = "https://my-agent-be0o.onrender.com"

# 用于存储测试创建的 agent ID，方便最后清理
created_agent_ids: list[str] = []


def log(msg: str) -> None:
    print(f"\n{'='*60}\n{msg}\n{'='*60}")


def check_health() -> None:
    log("0. 检查服务健康状态")
    resp = requests.get(f"{BASE_URL}/health")
    print(f"  Status: {resp.status_code}")
    print(f"  Body: {resp.json()}")
    assert resp.status_code == 200, f"Health check failed: {resp.status_code}"
    print("  ✅ 服务正常")


def create_agent(name: str, model: str, system_prompt: str) -> str:
    """创建 Agent 并返回 agent_id"""
    resp = requests.post(
        f"{BASE_URL}/agents",
        json={"name": name, "model": model, "system_prompt": system_prompt},
    )
    print(f"  Create '{name}' → Status: {resp.status_code}")
    data = resp.json()
    print(f"  Response: {data}")
    assert resp.status_code == 201, f"Create failed: {resp.status_code} {resp.text}"
    agent_id = data["id"]
    created_agent_ids.append(agent_id)
    return agent_id


def get_agent(agent_id: str) -> dict:
    """获取 Agent 详情"""
    resp = requests.get(f"{BASE_URL}/agents/{agent_id}")
    assert resp.status_code == 200, f"Get agent failed: {resp.status_code} {resp.text}"
    return resp.json()


def chat_with_session(agent_id: str, session_id: str, message: str) -> str:
    """多轮对话"""
    resp = requests.post(
        f"{BASE_URL}/agents/{agent_id}/chat/session",
        json={"session_id": session_id, "message": message},
    )
    print(f"  User: {message}")
    if resp.status_code != 200:
        print(f"  ❌ Chat failed: {resp.status_code} {resp.text}")
        return f"ERROR: {resp.status_code}"
    data = resp.json()
    reply = data["reply"]
    # 截取前 200 字符显示
    display = reply[:200] + ("..." if len(reply) > 200 else "")
    print(f"  Agent: {display}")
    return reply


def delete_agent(agent_id: str) -> None:
    """删除 Agent"""
    resp = requests.delete(f"{BASE_URL}/agents/{agent_id}")
    print(f"  Delete {agent_id[:8]}... → Status: {resp.status_code}")


def test_create_two_agents() -> tuple[str, str]:
    """测试 1: 创建两个不同模型+提示词的 Agent"""
    log("1. 创建两个 Agent（不同模型 + 不同提示词）")

    # Agent A: 使用 deepseek，扮演"猫娘"
    agent_a_id = create_agent(
        name="猫娘小助手",
        model="deepseek/deepseek-chat",
        system_prompt="你是一只可爱的猫娘，每句话结尾都要加上「喵~」。你非常热情友好。如果用户问你是谁，你要说你叫小花。记住用户告诉你的任何信息。",
    )
    print(f"  ✅ Agent A 创建成功: {agent_a_id[:8]}...")

    # Agent B: 使用 google gemini，扮演"冷酷程序员"
    agent_b_id = create_agent(
        name="程序员老王",
        model="google/gemini-2.0-flash-001",
        system_prompt="你是一个严肃的高级程序员，名叫老王。你说话简洁直接，喜欢用技术术语。如果用户问你是谁，你要说你是老王。记住用户告诉你的任何信息。不需要太客气，保持简洁。",
    )
    print(f"  ✅ Agent B 创建成功: {agent_b_id[:8]}...")

    return agent_a_id, agent_b_id


def test_verify_agent_configs(agent_a_id: str, agent_b_id: str) -> None:
    """测试 2: 验证 Agent 配置正确存储"""
    log("2. 验证 Agent 配置（模型+提示词）")

    agent_a = get_agent(agent_a_id)
    print(f"  Agent A: model={agent_a['model']}, prompt starts with='{agent_a['system_prompt'][:30]}...'")
    assert agent_a["model"] == "deepseek/deepseek-chat", f"Agent A model wrong: {agent_a['model']}"
    assert "猫娘" in agent_a["system_prompt"], "Agent A prompt missing keyword"
    print("  ✅ Agent A 配置正确")

    agent_b = get_agent(agent_b_id)
    print(f"  Agent B: model={agent_b['model']}, prompt starts with='{agent_b['system_prompt'][:30]}...'")
    assert agent_b["model"] == "google/gemini-2.0-flash-001", f"Agent B model wrong: {agent_b['model']}"
    assert "老王" in agent_b["system_prompt"], "Agent B prompt missing keyword"
    print("  ✅ Agent B 配置正确")


def test_multi_turn_agent_a(agent_a_id: str) -> None:
    """测试 3: Agent A 多轮对话，验证上下文保持"""
    log("3. Agent A（猫娘）多轮对话 - 验证上下文保持")

    session_id = str(uuid.uuid4())
    print(f"  Session ID: {session_id[:8]}...")

    # 第 1 轮：自我介绍
    reply1 = chat_with_session(agent_a_id, session_id, "你好，你是谁？")
    # 检查猫娘特征
    has_cat = "喵" in reply1 or "小花" in reply1
    print(f"  → 含猫娘特征: {'✅' if has_cat else '⚠️ 未检测到（可能需要几轮才显现）'}")

    # 第 2 轮：告诉它一个信息
    reply2 = chat_with_session(agent_a_id, session_id, "我叫小明，我今年25岁。记住了吗？")

    # 第 3 轮：验证它记住了
    reply3 = chat_with_session(agent_a_id, session_id, "我叫什么名字？我几岁？")
    has_context = "小明" in reply3 or "25" in reply3
    print(f"  → 记住上下文: {'✅' if has_context else '❌ 未记住'}")
    if not has_context:
        print(f"  ⚠️ 完整回复: {reply3}")


def test_multi_turn_agent_b(agent_b_id: str) -> None:
    """测试 4: Agent B 多轮对话，验证上下文保持"""
    log("4. Agent B（程序员老王）多轮对话 - 验证上下文保持")

    session_id = str(uuid.uuid4())
    print(f"  Session ID: {session_id[:8]}...")

    # 第 1 轮
    reply1 = chat_with_session(agent_b_id, session_id, "你好，你是谁？")
    has_lw = "老王" in reply1
    print(f"  → 含'老王'特征: {'✅' if has_lw else '⚠️ 未检测到'}")

    # 第 2 轮
    reply2 = chat_with_session(agent_b_id, session_id, "我正在学Python，遇到了一个问题：列表推导式和生成器表达式有什么区别？")

    # 第 3 轮：验证上下文
    reply3 = chat_with_session(agent_b_id, session_id, "那你刚才说的，哪个更省内存？")
    # 应该能基于上下文回答（生成器更省内存）
    has_context = "生成器" in reply3 or "generator" in reply3.lower() or "内存" in reply3
    print(f"  → 记住上下文: {'✅' if has_context else '⚠️ 未明确引用上文'}")


def test_isolation(agent_a_id: str, agent_b_id: str) -> None:
    """测试 5: 验证两个 Agent 互不干扰"""
    log("5. 验证 Agent 之间互不干扰")

    session_a = str(uuid.uuid4())
    session_b = str(uuid.uuid4())

    # Agent A 说
    chat_with_session(agent_a_id, session_a, "我的密码是 cat123，帮我记住")

    # Agent B 说
    chat_with_session(agent_b_id, session_b, "我的密码是 dog456，帮我记住")

    # 验证 Agent A 不知道 Agent B 的信息
    reply_a = chat_with_session(agent_a_id, session_a, "我的密码是什么？")
    a_knows_own = "cat123" in reply_a
    a_knows_b = "dog456" in reply_a
    print(f"  → Agent A 记住自己的密码: {'✅' if a_knows_own else '❌'}")
    print(f"  → Agent A 不知道 B 的密码: {'✅' if not a_knows_b else '❌ 隔离失败！'}")

    # 验证 Agent B 不知道 Agent A 的信息
    reply_b = chat_with_session(agent_b_id, session_b, "我的密码是什么？")
    b_knows_own = "dog456" in reply_b
    b_knows_a = "cat123" in reply_b
    print(f"  → Agent B 记住自己的密码: {'✅' if b_knows_own else '❌'}")
    print(f"  → Agent B 不知道 A 的密码: {'✅' if not b_knows_a else '❌ 隔离失败！'}")


def test_session_isolation_same_agent(agent_a_id: str) -> None:
    """测试 6: 同一 Agent 不同 session 互不干扰"""
    log("6. 同一 Agent 不同 Session 互不干扰")

    session_1 = str(uuid.uuid4())
    session_2 = str(uuid.uuid4())

    # Session 1 告诉信息
    chat_with_session(agent_a_id, session_1, "我是张三")

    # Session 2 告诉不同信息
    chat_with_session(agent_a_id, session_2, "我是李四")

    # Session 1 验证
    reply_1 = chat_with_session(agent_a_id, session_1, "我是谁？")
    s1_correct = "张三" in reply_1
    s1_leaked = "李四" in reply_1
    print(f"  → Session 1 记住'张三': {'✅' if s1_correct else '❌'}")
    print(f"  → Session 1 不知道'李四': {'✅' if not s1_leaked else '❌ Session 隔离失败！'}")

    # Session 2 验证
    reply_2 = chat_with_session(agent_a_id, session_2, "我是谁？")
    s2_correct = "李四" in reply_2
    s2_leaked = "张三" in reply_2
    print(f"  → Session 2 记住'李四': {'✅' if s2_correct else '❌'}")
    print(f"  → Session 2 不知道'张三': {'✅' if not s2_leaked else '❌ Session 隔离失败！'}")


def cleanup() -> None:
    """清理测试创建的 Agent"""
    log("7. 清理测试数据")
    for agent_id in created_agent_ids:
        try:
            delete_agent(agent_id)
        except Exception as e:
            print(f"  ⚠️ 清理失败 {agent_id[:8]}...: {e}")
    print("  ✅ 清理完成")


def main() -> None:
    print("\n" + "🚀" * 30)
    print("   MyAgent 多 Agent 测试套件")
    print("🚀" * 30)

    try:
        # 0. 健康检查
        check_health()

        # 1. 创建两个 Agent
        agent_a_id, agent_b_id = test_create_two_agents()

        # 2. 验证配置
        test_verify_agent_configs(agent_a_id, agent_b_id)

        # 3. Agent A 多轮对话
        test_multi_turn_agent_a(agent_a_id)

        # 4. Agent B 多轮对话
        test_multi_turn_agent_b(agent_b_id)

        # 5. 跨 Agent 隔离
        test_isolation(agent_a_id, agent_b_id)

        # 6. 同 Agent 跨 Session 隔离
        test_session_isolation_same_agent(agent_a_id)

        log("🎉 所有测试完成！")

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # 总是清理
        cleanup()


if __name__ == "__main__":
    main()
