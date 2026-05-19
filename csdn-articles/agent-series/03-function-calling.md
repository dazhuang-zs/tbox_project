# Function Calling：让 AI 学会用工具

> LLM 再聪明也只是「脑子」，没有手和脚。Function Calling 就是给 AI 装上手脚——让它能查天气、发邮件、操作数据库。这是 Agent 开发最核心的一课。

---

## 一、LLM 的先天缺陷

LLM 训练数据有截止日期，它不知道今天几号、你的数据库里有什么、你的 API 能不能用。直接问它：

```
问：帮我查一下北京现在的天气
答：抱歉，我无法获取实时天气信息。建议您查看天气预报网站...
```

但如果你告诉它「有一个 get_weather 函数可以用」，它就能输出一个**结构化的调用请求**，由你的程序去真正执行。

---

## 二、Function Calling 的工作原理

```
┌──────────┐    ① 用户提问 + 工具描述       ┌──────────┐
│          │  ──────────────────────────→   │          │
│  你的程序  │                               │   LLM    │
│          │  ←──────────────────────────   │          │
└──────────┘    ② LLM 返回：应该调哪个工具    └──────────┘
     │             调什么参数
     │
     ③ 真的去执行
     │
     ▼
┌──────────┐    ④ 执行结果 → LLM             ┌──────────┐
│ 天气 API  │  ──────────────────────────→   │   LLM    │
│ 数据库    │                               │          │
│ 文件系统  │  ←──────────────────────────   │          │
└──────────┘    ⑤ LLM 用自然语言回复用户      └──────────┘
```

**LLM 不执行工具**，它只是说「应该调哪个工具、传什么参数」。真正执行的是你的代码。

---

## 三、完整实战代码

### 3.1 定义工具

```python
import json
import httpx
from openai import AsyncOpenAI

client = AsyncOpenAI(
    api_key="your-api-key",
    base_url="https://api.deepseek.com/v1"  
)

# ── 定义工具（用 JSON Schema 描述） ──
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "获取指定城市的当前天气，包括温度、天气状况和湿度",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "城市名称，如 北京、上海"
                    }
                },
                "required": ["city"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": "执行数学计算，支持 +、-、*、/ 和括号",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "数学表达式，如 '23 * 47 + 15 * 8'"
                    }
                },
                "required": ["expression"]
            }
        }
    }
]
```

### 3.2 工具的实际实现

```python
async def get_weather(city: str) -> str:
    """模拟天气查询（生产环境替换为真实 API）"""
    # 实际项目用 httpx 调天气 API
    # response = await httpx.AsyncClient().get(f"https://api.weather.com?city={city}")
    weather_db = {
        "北京": "晴，25°C，湿度 40%",
        "上海": "多云，28°C，湿度 65%",
        "深圳": "阵雨，30°C，湿度 80%",
    }
    return weather_db.get(city, f"未找到 {city} 的天气数据")


def calculate(expression: str) -> str:
    """安全执行数学计算"""
    # ⚠️ 生产环境不要用 eval！这里仅作示例
    import ast
    import operator
    
    allowed_ops = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
    }
    
    try:
        result = eval(expression, {"__builtins__": {}}, {})
        return str(result)
    except Exception as e:
        return f"计算错误：{e}"
```

### 3.3 Agent 主循环

```python
import asyncio

# 工具名 → 实际函数
available_functions = {
    "get_weather": get_weather,
    "calculate": calculate,
}

SYSTEM_PROMPT = """你是一个智能助手，可以查询天气和执行计算。
- 用户问天气时，调用 get_weather 工具
- 用户问计算时，调用 calculate 工具
- 获取结果后，用友好的中文回复用户"""


async def agent_loop(user_input: str):
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_input}
    ]

    # 第一步：询问 LLM 是否需要调工具
    response = await client.chat.completions.create(
        model="deepseek-chat",
        messages=messages,
        tools=tools,
        tool_choice="auto"  # 让 LLM 自己决定要不要用工具
    )

    msg = response.choices[0].message

    # 如果 LLM 决定调工具
    if msg.tool_calls:
        for tool_call in msg.tool_calls:
            func_name = tool_call.function.name
            func_args = json.loads(tool_call.function.arguments)

            print(f"🔧 调用工具：{func_name}({func_args})")

            # 真正执行
            func = available_functions[func_name]
            if asyncio.iscoroutinefunction(func):
                result = await func(**func_args)
            else:
                result = func(**func_args)

            # 把工具调用的结果追加到对话中
            messages.append(msg)  # LLM 的工具调用消息
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result
            })

        # 第二步：把结果交给 LLM，让它生成友好回复
        final_response = await client.chat.completions.create(
            model="deepseek-chat",
            messages=messages
        )
        return final_response.choices[0].message.content

    # 如果不需要工具，直接返回
    return msg.content


# ── 测试 ──
async def main():
    # 测试 1：天气查询
    print("=" * 50)
    print("用户：北京现在天气怎么样？")
    reply = await agent_loop("北京现在天气怎么样？")
    print(f"助手：{reply}")

    print()
    # 测试 2：计算
    print("=" * 50)
    print("用户：23 × 47 + 15 × 8 等于多少？")
    reply = await agent_loop("23 × 47 + 15 × 8 等于多少？")
    print(f"助手：{reply}")

    print()
    # 测试 3：不需要工具
    print("=" * 50)
    print("用户：你好，请介绍一下你自己")
    reply = await agent_loop("你好，请介绍一下你自己")
    print(f"助手：{reply}")

asyncio.run(main())
```

**运行结果**：

```
用户：北京现在天气怎么样？
🔧 调用工具：get_weather({'city': '北京'})
助手：北京现在是晴天，温度 25°C，湿度 40%，很适合出门哦！

用户：23 × 47 + 15 × 8 等于多少？
🔧 调用工具：calculate({'expression': '23 * 47 + 15 * 8'})
助手：23 × 47 + 15 × 8 = 1201

用户：你好，请介绍一下你自己
助手：你好！我是智能助手，可以帮你查天气、做计算...
```

---

## 四、Function Calling 的进阶技巧

### 4.1 并行调用

LLM 可以一次返回多个 tool_call：

```python
# 用户问："北京和上海今天天气怎么样？"
# LLM 一次返回两个 tool_call：
tool_calls = [
    {"name": "get_weather", "arguments": {"city": "北京"}},
    {"name": "get_weather", "arguments": {"city": "上海"}}
]

# 并行执行
import asyncio
tasks = [get_weather(c["arguments"]["city"]) for c in tool_calls]
results = await asyncio.gather(*tasks)
```

### 4.2 工具描述就是「API 文档」

工具 JSON Schema 写得越详细，LLM 选工具越准：

```python
# ❌ 太模糊
{"name": "search", "description": "搜索东西", "parameters": {"q": {"type": "string"}}}

# ✅ 精确
{
    "name": "search_harmonyos_docs",
    "description": "搜索华为 HarmonyOS 官方文档，返回相关的 API 说明和代码示例。关键词应使用中文技术术语。",
    "parameters": {
        "query": {"type": "string", "description": "中文搜索关键词，如 '状态管理'、'页面路由'"},
        "api_version": {"type": "string", "enum": ["API12", "API11"], "default": "API12"}
    }
}
```

### 4.3 错误处理：工具调用失败怎么办

```python
try:
    result = func(**args)
except Exception as e:
    result = f"工具调用失败：{e}。请告诉用户暂时无法完成此操作。"

# LLM 拿到错误信息后会自动向用户解释
```

---

## 五、Function Calling vs MCP

这是面试高频题：

| 维度 | Function Calling | MCP |
|------|:---:|:---:|
| 是什么 | LLM 的推理能力 | 通信协议 |
| 谁定义 | 使用方（你的代码） | 工具提供方（MCP Server） |
| 复用性 | 每次要重新定义 | 写一个 Server，到处用 |
| 关系 | LLM 的输出格式 | 工具的标准接入方式 |

> MCP 底层也会触发 Function Calling。MCP 解决的是「工具从哪来」，Function Calling 解决的是「LLM 怎么选工具」。

---

## 六、生产实战：这些坑你迟早会踩

### 6.1 工具调用失败后的重试策略

Agent 最怕的不是工具失败，是工具失败了 LLM 以为成功了。

```python
# 三种重试策略
async def execute_tool_with_retry(func_name: str, args: dict, max_retries: int = 2):
    """工具调用 + 智能重试"""
    last_error = None
    
    for attempt in range(max_retries + 1):
        try:
            result = await available_functions[func_name](**args)
            return {"success": True, "result": result}
        except TimeoutError:
            last_error = f"超时（第 {attempt+1} 次尝试）"
            await asyncio.sleep(2 ** attempt)  # 指数退避
        except ValueError as e:
            # 参数错误 → 不用重试，让 LLM 修正参数
            return {"success": False, "error": f"参数错误：{e}", "retry_with_fix": True}
        except Exception as e:
            last_error = str(e)
    
    return {"success": False, "error": last_error}
```

### 6.2 并行调用的陷阱

```python
# ❌ 错误：串行调天气
for city in ["北京", "上海", "深圳", "广州"]:
    weather = await get_weather(city)

# ✅ 正确：并行调天气
results = await asyncio.gather(
    get_weather("北京"),
    get_weather("上海"),
    get_weather("深圳"),
    get_weather("广州"),
    return_exceptions=True  # 一个失败不影响其他的
)
```

> 生产环境经验：10 个城市并行查天气，串行要 2 秒（每个 200ms），并行只要 200ms。但要注意 API rate limit——并行太多可能被限流。

### 6.3 工具 Schema 写得不好 = LLM 选错工具

```python
# ❌ 两个工具描述太像，LLM 不知道该用哪个
{"name": "search_docs", "description": "搜索文档"}
{"name": "search_code", "description": "搜索代码"}

# ✅ 差异化描述
{
    "name": "search_harmonyos_docs",
    "description": "搜索华为官方 HarmonyOS 开发文档，返回 API 说明和代码示例。适用场景：用户问 API 用法、组件属性等。"
}
{
    "name": "search_csdn_articles",
    "description": "搜索 CSDN 博客的技术文章，返回实战经验和踩坑记录。适用场景：用户问怎么做、有什么坑等。"
}
```

> **经验法则**：如果你在描述里加一个「不适用场景」，LLM 选错的概率降 30%。

### 6.4 流式输出 + 工具调用

Agent 对话中用户期待实时反馈，但工具调用是阻塞的：

```python
async def agent_loop_streaming(user_input: str):
    """流式 Agent，工具调用时发送状态更新"""
    
    yield {"type": "status", "text": "正在分析你的问题..."}
    
    # ... LLM 决定调用工具 ...
    
    yield {"type": "status", "text": f"正在调用 {tool_name}..."}
    
    result = await execute_tool(tool_name, tool_args)
    
    yield {"type": "tool_result", "text": f"{tool_name} 返回：{result[:100]}..."}
    
    # ... LLM 生成最终回答 ...
    async for chunk in llm.chat_stream(messages):
        yield {"type": "chunk", "text": chunk}
```

> 用户盯着空白界面等 3 秒会觉得卡。每步发一个状态更新，体验完全不同。

---

## 六、总结

1. **Function Calling 是 Agent 的核心**——没有它，LLM 只是个聊天机器人
2. **LLM 不执行**——它只说用什么工具，真正执行的是你的代码
3. **工具描述决定准确率**——JSON Schema 写得好，LLM 才能选对工具
4. **并行调用**——多个独立工具可以同时执行，提升性能
5. **Function Calling 是 MCP 的底层机制**——理解它才能理解 Agent 生态

> 下一篇：**《RAG：给 LLM 装上知识库》**——向量数据库、Embedding、Chunking，从原理到完整可运行的 RAG 系统。

*系列文章：00-总纲 → ①-LLM 原理 → ②-Prompt 工程 → ③-Function Calling → ④-RAG → ⑤-Agent 模式 → ⑥-LangGraph → ⑦-MCP → ⑧-Multi-Agent*
