# 强烈推荐收藏！AI Agent 进化史：从1960年代规则引擎到2026年GPT-5 Agent——一篇讲透起源、原理、机制、应用

> 1966年，MIT的ELIZA用一个150行的脚本让人类第一次觉得「机器在听我说话」。2026年，GPT-5 Agent能自己读需求、建仓库、修Bug、提交PR。60年间，Agent发生了什么？ReAct模式为什么成为主流？LLM怎么「决定」调用哪个工具？这篇文章从底层原理开讲，每段都带核心代码。

---

## 一、起源：Agent 不是 GPT 发明的

### 1.1 1960s：第一个 Agent —— ELIZA

1966年，MIT 的 Joseph Weizenbaum 写了 ELIZA，一个模仿心理治疗师的对话程序。

```python
# ELIZA 的核心逻辑，只有 150 行代码
def respond(text):
    text = text.lower()
    if "伤心" in text:
        return "为什么你会感到伤心？"
    elif "讨厌" in text:
        return "说说你讨厌什么"
    else:
        return "请继续说下去"
```

ELIZA 没有任何智能——它只是模式匹配 + 关键词触发。但它证明了一件事：**只要反馈足够自然，人类会赋予机器「智能感」**。这至今仍是 Agent 设计的核心原则——用户不关心 Agent 内部多复杂，只关心「它听不听得懂我」。

### 1.2 1980s-2000s：专家系统 → BDI 模型

| 阶段 | 代表 | 核心思路 | 局限 |
|------|------|------|------|
| 专家系统 (1980s) | MYCIN、XCON | 把人类专家知识写成 if-then 规则 | 规则爆炸，维护不了 |
| BDI 模型 (1990s) | PRS、JASON | Belief（信念）+ Desire（愿望）+ Intention（意图） | 需要手动建模，无法泛化 |
| 强化学习 Agent (2010s) | AlphaGo、DQN | 与环境交互，通过奖励信号学习 | 每个任务从头训练，不通用 |

### 1.3 2022-2023：LLM 改变一切

GPT-3.5 的出现让 Agent 研究出现了一个范式转移：

```
传统 Agent：手工设计规则 → 手工建模环境 → 针对性训练
LLM Agent：给一个自然语言 Prompt → 它自己理解 → 自己规划 → 自己执行
```

这个转变的核心是什么？**LLM 解决了 Agent 最难的「常识推理」问题。** 过去需要手工建模的「如果用户说饿了，他想要食物而不是文件」——LLM 天生就知道。

---

## 二、原理：Agent 的四件套

### 2.1 核心架构

```
                    Agent
                      │
     ┌────────────────┼────────────────┐
     ▼                ▼                ▼
  感知模块          规划模块          执行模块
  (Perception)     (Planning)       (Execution)
     │                │                │
 理解用户输入      拆解任务步骤      调用工具/API
 理解环境反馈      选择策略路径      生成最终输出
     │                │                │
     └────────────────┼────────────────┘
                      ▼
                  记忆模块
                  (Memory)
                      │
              短期：当前对话上下文
              长期：向量库 + 结构化存储
```

### 2.2 为什么 Agent 和普通 LLM 调用完全不同

```python
# 普通 LLM 调用：一问一答，一锤子买卖
response = llm.chat("用 Python 写一个排序函数")
# → 返回代码，结束

# Agent 调用：多步循环，边走边看
for step in range(max_steps):
    thought = llm.think(context)        # 思考下一步
    action = decide_action(thought)     # 决定做什么
    result = execute(action)            # 真正去做
    observation = observe(result)       # 观察结果
    context = update(context, observation)  # 更新上下文
    if done(observation):
        break
```

> 关键区别：Agent 有一个**闭环**。LLM 不只是输出结果，而是在自己的输出和外部反馈之间不断循环。

### 2.3 ReAct 的底层逻辑（图解）

ReAct（Reasoning + Acting）是 Google 2023 年提出的范式，至今仍是 Agent 设计的黄金标准。

```
         ┌──────────────────┐
         │    观察环境        │←────────────────┐
         │  Observation      │                  │
         └────────┬─────────┘                  │
                  ▼                             │
         ┌──────────────────┐                  │
         │    推理思考        │                  │
         │  Thought          │                  │
         └────────┬─────────┘                  │
                  ▼                             │
         ┌──────────────────┐                  │
         │    执行动作        │──────────────────┘
         │  Action           │    循环直到任务完成
         └──────────────────┘       或超时
```

**为什么 ReAct 比「直接回答」准确率高 30-50%？**

因为 LLM 在直接回答时，所有推理都是隐式的——在参数内部完成的。而 ReAct 把推理显式化——每一步 Thought 都是一个向外输出的中间结果。这种「外部化推理」让 LLM 能检查自己的思路，也让开发者能 Debug Agent 的「思考过程」。

---

## 三、机制：LLM 怎么「决定」调用哪个工具

### 3.1 Function Calling 的 Token 级原理

```python
# 你把工具定义发送给 LLM（以 OpenAI 格式为例）
tools = [{
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "获取指定城市的天气",
        "parameters": {
            "type": "object",
            "properties": {
                "city": {"type": "string", "description": "城市名"}
            },
            "required": ["city"]
        }
    }
}]

# LLM 返回的是一段特殊格式的 Token 序列
# 不是普通文本，而是结构化的 tool_call 对象：
{
    "id": "call_abc123",
    "type": "function",
    "function": {
        "name": "get_weather",
        "arguments": '{"city": "北京"}'
    }
}
```

> **关键**：LLM 不是「执行」工具，而是「说」应该调哪个。拿到 `tool_call` 后，是你的代码去真正调用 `get_weather("北京")`。LLM 完全不知道 `get_weather` 的实现——它只知道你描述给它的函数签名。

### 3.2 工具路由：LLM 内部是怎么选的

```python
# tool_choice 的三个模式
# 1. "auto": LLM 自己判断要不要用工具（默认）
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[...],
    tools=tools,
    tool_choice="auto"  # 让 LLM 自主决定
)

# 2. "required": 强制 LLM 必须调用一个工具
#    场景：你知道这个问题一定需要工具
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[...],
    tools=tools,
    tool_choice="required"
)

# 3. 指定工具名：强制 LLM 调用特定工具
#    场景：你已经在外层做了意图识别，指定工具
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[...],
    tools=tools,
    tool_choice={"type": "function", "function": {"name": "get_weather"}}
)
```

**LLM 的决策链路**：

```
用户输入："北京今天什么天气？"
    ↓
LLM 内部推理：
  - 用户想知道天气 → 需要实时信息
  - 我的训练数据可能没有今天的天气
  - 有一个 get_weather 工具可以用
  - get_weather 需要 city 参数 = "北京"
    ↓
输出：{"function": "get_weather", "arguments": {"city": "北京"}}
```

### 3.3 一个完整的 Agent 执行循环

```python
import json
from openai import OpenAI

client = OpenAI()

SYSTEM_PROMPT = """你是一个智能助手，可以使用工具来完成任务。
每次思考后决定下一步行动。"""


def agent_loop(user_input: str, tools: list, max_steps: int = 5):
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_input}
    ]

    for step in range(max_steps):
        print(f"\n{'='*40}\nStep {step+1}")

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            tools=tools,
            tool_choice="auto"
        )

        msg = response.choices[0].message

        # 检查是否需要工具
        if msg.tool_calls:
            for tool_call in msg.tool_calls:
                func_name = tool_call.function.name
                func_args = json.loads(tool_call.function.arguments)
                print(f"🔧 {func_name}({func_args})")

                # 执行工具
                result = execute_tool(func_name, func_args)
                print(f"📊 {result}")

                # 把调用和结果都追加到对话
                messages.append({
                    "role": "assistant",
                    "tool_calls": [tool_call]
                })
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result
                })
        else:
            # 没有工具调用 → 最终回复
            return msg.content

        # 防循环
        if (
            msg.tool_calls
            and all(c.function.name == messages[-3].get("tool_calls", [{}])[0].get("function", {}).get("name")
                    for c in msg.tool_calls if messages[-3].get("role") == "assistant")
        ):
            messages.append({
                "role": "system",
                "content": "你重复了上一步的操作。请尝试不同的方法或给出最终结论。"
            })

    return "任务超过最大步骤数，请检查 Agent 逻辑"


def execute_tool(name: str, args: dict) -> str:
    tools_map = {
        "get_weather": lambda city: f"{city}：晴，25°C",
        "search": lambda query: f"关于'{query}'的搜索结果：..."
    }
    return tools_map.get(name, lambda **k: "未知工具")(**args)
```

---

## 四、应用：三种 Agent 架构的生产决策

### 4.1 单 Agent：简单任务的最佳选择

```
用户 → Agent → 工具 → 回复
```

**适用**：单一领域问答、简单工具调用、意图明确的任务。
**优点**：简单、成本低、调试容易。
**缺点**：复杂多领域任务会超出 Context Window。

### 4.2 Multi-Agent：术业有专攻

```
          PM Agent
         （拆任务）
             │
    ┌────────┼────────┐
    ▼        ▼        ▼
 前端Agent 后端Agent 测试Agent
    │        │        │
    └────────┼────────┘
             ▼
        整合Agent
```

**适用**：跨领域复杂项目、需要不同技术栈协作。
**优点**：每个 Agent 专精，质量更高。
**缺点**：成本 ×N，错误级联，串行延迟高。

### 4.3 Hierarchical Agent：有领导的团队

```
         Manager Agent
        （分配 + 审核）
             │
    ┌────────┼────────┐
    ▼        ▼        ▼
 Worker 1  Worker 2  Worker 3
```

**适用**：任务需要动态分派和结果审核。
**优点**：灵活，Manager 可以调整策略。
**缺点**：Manager 本身的决策质量决定整体成败。

### 4.4 选型决策树

```
任务复杂度？
│
├─ 单一领域，步骤 ≤ 5  →  单 Agent
│
├─ 跨领域，步骤 ≤ 10  →  Multi-Agent（顺序模式）
│
└─ 需要动态决策       →  Hierarchical Agent
```

---

## 五、Agent 的幻觉问题——最被低估的风险

Agent 比普通 LLM 更容易产生幻觉，因为它不仅要「说对」，还要「做对」。

### 5.1 Tool Calling 的幻觉

```
LLM 说：调用 send_email(to="boss@company.com", body="辞职信...")
问题：send_email 工具不存在，LLM 自己编的
结果：什么都没发生，但 Agent 以为邮件已发送
```

```python
# 防御：工具调用后必须验证
def safe_execute(name, args):
    if name not in registered_tools:
        return f"错误：工具 {name} 不存在。请使用可用工具。"
    return registered_tools[name](**args)
```

### 5.2 循环幻觉

```
Agent 反复执行同一个操作，始终到不了终点。
原因：LLM 对当前结果不满意 → 重试 → 还是不满意 → 重试 → ...
```

这在你 Agent 系列文章里讲过——用 `detect_loop` 检测 + 强制终止。

---

## 六、总结

| 时间段 | Agent 形态 | 关键突破 |
|--------|----------|------|
| 1966 | ELIZA | 证明规则匹配可以模拟对话 |
| 1980s | 专家系统 | 知识可以编码为规则 |
| 1990s | BDI Agent | 信念-愿望-意图形式化 |
| 2010s | 强化学习 Agent | 与环境交互学习 |
| 2023 | LLM Agent | 自然语言驱动的通用智能体 |
| 2026 | Multi-Agent + MCP | 多 Agent 协作 + 标准化工具接入 |

> Agent 不是新概念，但 LLM 让它从「能跑」变成了「能用」。理解 Agent 的底层循环，是 AI 开发工程师和 Agent 使用者的分水岭。

---

> 🔖 系列下一篇：**《MCP 协议深度解析：AI 工具的 USB-C 是怎么设计的》**

*标签：#AI #Agent #LLM #ReAct #FunctionCalling #程序员必读*