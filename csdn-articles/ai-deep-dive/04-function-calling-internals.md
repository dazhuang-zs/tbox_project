# 强烈推荐收藏！Function Calling 内部原理：LLM 怎么「学会」用工具——从Token注入到并行调用的完整链路

> 你把工具定义发给 LLM，它就能「自动选择」——这个魔法背后是什么？Function Calling 不是 API 的一个简单参数，而是一整套 Token 注入、结构化输出和路由决策机制。本文从 Special Token 讲到并行调用，每个环节带真实代码。

---

## 一、起源：从 GPT-3 的「猜」到 GPT-4 的「结构化调用」

### 1.1 GPT-3 时代（2020-2022）：靠 Prompt 硬来

```python
# 没有 Function Calling，只能这样「骗」LLM
prompt = """
你只能回复 JSON，不要回复其他内容。

工具列表：
- get_weather(city): 查询天气

用户问：北京天气怎么样？
请回复：{"tool": "get_weather", "city": "北京"}
"""

response = llm.chat(prompt)
# → '{"tool": "get_weather", "city": "北京"}'
# 然后手动 json.loads()，再手动调函数
```

问题：LLM 可能输出 `{"tool": "get_wether", "city": "Beijing"}`——拼写错误，JSON 解析失败，整个流程断裂。

### 1.2 GPT-4 Function Calling（2023.6）：范式转移

```python
# 现在：LLM 直接返回结构化的 tool_calls 对象
tools = [{
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "获取指定城市的天气",
        "parameters": {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "城市名，如 北京、上海"
                }
            },
            "required": ["city"]
        }
    }
}]

response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "北京天气怎么样？"}],
    tools=tools
)

# response.choices[0].message.tool_calls 是一个结构化的列表
# [{"id": "call_xxx", "function": {"name": "get_weather", "arguments": '{"city": "北京"}'}}]
```

---

## 二、原理：Token 层看 Function Calling

### 2.1 Special Token 注入

当你把 `tools` 参数传给 API，OpenAI 底层做了三件事：

```
1. 把 tools JSON Schema 序列化为 Token 序列
2. 在消息序列中插入特殊的 Special Token（如 <|tool_call|>）
3. 模型被微调为「当需要工具时，输出 Special Token + 工具名 + 参数 JSON」
```

```python
# API 背后的 Token 流（简化示意）
[
    # 系统消息
    <|im_start|>system
    你可以使用以下工具：get_weather(city: str) - 获取天气
    <|im_end|>

    # 用户消息
    <|im_start|>user
    北京天气怎么样？
    <|im_end|>

    # LLM 输出
    <|im_start|>assistant
    <|tool_call|>get_weather
    {"city": "北京"}
    <|im_end|>
]
```

> 这就是为什么 Function Calling 比「手写 JSON Prompt」稳定得多——模型在训练时见过几百万次这种格式。

### 2.2 JSON Schema 声明 = 给模型的「装箱单」

```python
# ❌ 参数不限制类型，模型可能传空、传错
{"name": "send_email", "parameters": {"to": {"type": "string"}}}

# ✅ 类型、枚举、约束全写上
{
    "name": "send_email",
    "description": "发送邮件。只发送到内部邮箱。",
    "parameters": {
        "type": "object",
        "properties": {
            "to": {
                "type": "string",
                "format": "email",
                "description": "收件人邮箱，必须为 @company.com"
            },
            "priority": {
                "type": "string",
                "enum": ["low", "normal", "high"],
                "default": "normal"
            }
        },
        "required": ["to"]
    }
}
```

**效果对比**：
- 没有 `format: email` → LLM 可能传 `{"to": "张三"}`
- 加了 `format: email` → LLM 至少会传 `{"to": "zhang@company.com"}`

---

## 三、机制：Tool Choice 的三种模式

```python
# 1. "auto" — 让 LLM 自己决定
#    适用：不确定是否需要工具，让模型自己选
response = client.chat.completions.create(
    model="gpt-4o", messages=[...], tools=tools, tool_choice="auto"
)
# → 可能返回 text content（不需要工具）
# → 也可能返回 tool_calls（需要工具）

# 2. "required" — 强制调工具
#    适用：你已经知道这个请求一定需要工具
response = client.chat.completions.create(
    model="gpt-4o", messages=[...], tools=tools, tool_choice="required"
)
# → 一定返回 tool_calls，不会返回普通文本

# 3. 指定工具名 — 强制调特定工具
#    适用：外层已做意图识别，直接路由
response = client.chat.completions.create(
    model="gpt-4o", messages=[...], tools=tools,
    tool_choice={"type": "function", "function": {"name": "get_weather"}}
)
# → 一定返回 get_weather 的调用
```

### Tool Choice 决策树

```
你的场景是？
│
├─ 不确定是否需要工具   → "auto"
│   例：用户可能只是聊天
│
├─ 确定需要工具，但不确定哪个 → "required"
│   例：用户一定在问需要实时数据的事
│
└─ 外层已识别具体意图     → 指定工具名
    例：NLP 分类器已判断为「天气查询」
```

---

## 四、进阶：并行调用 + 流式输出

### 4.1 并行调用

```python
# 用户："北京和上海今天天气怎么样？"
# LLM 一次返回两个 tool_call：

response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "北京和上海天气怎么样？"}],
    tools=[weather_tool]
)

tool_calls = response.choices[0].message.tool_calls
# [
#   {"id": "call_1", "function": {"name": "get_weather", "arguments": '{"city": "北京"}'}},
#   {"id": "call_2", "function": {"name": "get_weather", "arguments": '{"city": "上海"}'}}
# ]

# 并行执行（不需要等北京结果就可以查上海）
import asyncio
results = await asyncio.gather(
    get_weather("北京"),
    get_weather("上海")
)
```

### 4.2 流式输出 + 工具调用

Agent 对话中不能让用户干等，每一步都发状态更新：

```python
async def agent_stream(user_input: str):
    yield {"type": "status", "text": "正在分析...\n"}

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": user_input}],
        tools=tools,
        tool_choice="auto"
    )

    msg = response.choices[0].message
    if msg.tool_calls:
        for tc in msg.tool_calls:
            yield {"type": "status",
                   "text": f"🔧 调用 {tc.function.name}...\n"}

            result = execute(tc.function.name,
                           json.loads(tc.function.arguments))

            yield {"type": "status",
                   "text": f"✓ {result[:80]}...\n"}

        # 最终回复流式输出
        final_response = client.chat.completions.create(
            model="gpt-4o",
            messages=updated_messages,
            stream=True
        )
        async for chunk in final_response:
            if chunk.choices[0].delta.content:
                yield {"type": "chunk",
                       "text": chunk.choices[0].delta.content}
```

---

## 五、工具描述的工程实践

### 5.1 描述要同时给「模型」和「维护者」看

```python
# ❌ 描述只写了用途，没写不适用场景
{"name": "search", "description": "搜索东西"}

# ✅ 描述写了四个 W
{
    "name": "search_harmonyos_docs",
    "description": (
        "搜索华为 HarmonyOS 官方开发文档。"
        "适用场景：用户问 API 用法、组件属性、开发指南。"
        "不适用场景：CSDN 博客搜索或通用技术问题。"
        "返回：匹配的文档片段和官方链接。"
    ),
    "parameters": {
        "query": {
            "type": "string",
            "description": "中文搜索关键词。例：'状态管理'、'页面路由'"
        }
    }
}
```

> 加上「不适用场景」可以让 LLM 减少 30% 以上的错误工具选择。

### 5.2 工具数量：少比多好

```
工具数    决策准确率
1-3       > 90%
4-10      70-90%
10-20     40-70%
20+       < 40%
```

> 经验：每个 Agent 不超过 8 个工具。多了就让 LLM 困惑——它会随机选一个。

---

## 六、总结

| 层级 | 做什么 | 关键 |
|------|------|------|
| Token 层 | 注入 Special Token + 工具 Schema | 这是 FC 为什么比手写 JSON 稳定的原因 |
| 推理层 | LLM 内部决策是否调工具 | `tool_choice` 控制行为 |
| 执行层 | 代码真正执行工具 | LLM 不知道工具实现 |
| 体验层 | 流式 + 状态更新 | 不能干等 |

> Function Calling 的本质：**LLM 输出一个结构化意图，你的代码去执行，结果再喂回 LLM。**"调用"二字有误导性——LLM 从不真正调用任何东西，它只是说「应该调这个」。

---

> 🔖 下一篇：**《RAG 深度原理：从向量数学到混合检索》**——Embedding 的数学直觉 + 索引算法演进 + 评估指标。

*标签：#FunctionCalling #ToolUse #Agent #LLM #并行调用 #程序员必读*