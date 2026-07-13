# 【AI Agent 系统教学 25】Function Calling 与 Tool Use

> Agent 不只是一个"聊天机器人"，它是能"动手"的助手。
> 而"手"就是工具。Function Calling 就是让 Agent 知道怎么用这些"手"。

---

## 前言：Agent 的"手"

LLM 的能力上限是"说话"。但 Agent 需要"做事"——查天气、发邮件、写文件、运行代码。

这些"做事"的能力，来自工具（Tools）。

**Function Calling** 就是让 LLM 能理解工具的接口、决定何时调用、并生成正确的调用参数。

---

## 一、Function Calling 的工作原理

### 1.1 流程

```
用户：北京天气怎么样？
    ↓
API 调用（包含工具描述）：
{
  "messages": [...],
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "get_weather",
        "description": "查询天气",
        "parameters": {
          "type": "object",
          "properties": {
            "city": {"type": "string"}
          },
          "required": ["city"]
        }
      }
    }
  ]
}
    ↓
模型返回：
{
  "tool_calls": [
    {
      "type": "function",
      "function": {
        "name": "get_weather",
        "arguments": "{\"city\": \"北京\"}"
      }
    }
  ]
}
    ↓
执行工具，返回结果到模型
    ↓
模型生成最终回复
```

### 1.2 工具定义格式

标准 OpenAI 格式的工具定义：

```python
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "查询指定城市的当前天气",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "城市名，如"北京"、"上海"",
                    },
                    "unit": {
                        "type": "string",
                        "enum": ["celsius", "fahrenheit"],
                        "description": "温度单位，默认 celsius",
                    },
                },
                "required": ["city"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "send_email",
            "description": "发送邮件",
            "parameters": {
                "type": "object",
                "properties": {
                    "to": {"type": "string", "description": "收件人邮箱"},
                    "subject": {"type": "string", "description": "邮件主题"},
                    "body": {"type": "string", "description": "邮件正文"},
                },
                "required": ["to", "subject", "body"],
            },
        },
    },
]
```

---

## 二、工具设计的核心原则

### 2.1 命名清晰

```python
# ❌ 模糊
{"name": "search", "description": "搜索"}

# ✅ 清晰
{"name": "search_web", "description": "搜索网络获取最新信息，适合查询实时数据"}
```

### 2.2 描述准确

```python
# ❌ 模糊
{"description": "获取天气信息"}

# ✅ 精确
{"description": "查询指定城市的当前天气和未来7天预报，包含温度、湿度、风速"}
```

### 2.3 参数设计

```python
# ❌ 参数过多，类型模糊
{
    "name": "do_task",
    "parameters": {
        "type": "object",
        "properties": {
            "data": {"type": "object"},  # 模糊的类型
            "options": {"type": "object"},  # 模糊
        },
    },
}

# ✅ 参数明确
{
    "name": "search_products",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "搜索关键词"},
            "category": {
                "type": "string",
                "enum": ["electronics", "clothing", "books"],
                "description": "商品分类",
            },
            "max_price": {"type": "number", "description": "最高价格（元）"},
        },
        "required": ["query"],
    },
}
```

### 2.4 错误处理

```python
@tool
def get_weather(city: str) -> str:
    """
    查询天气
    """
    try:
        result = weather_api.get(city)
        return json.dumps(result, ensure_ascii=False)
    except CityNotFoundError:
        return json.dumps({"error": f"未找到城市：{city}"})
    except APIError:
        return json.dumps({"error": "天气服务暂时不可用"})
```

---

## 三、工具注册与加载

### 3.1 装饰器风格

```python
class ToolRegistry:
    def __init__(self):
        self.tools = {}
    
    def register(self, name=None, description=None):
        """装饰器注册工具"""
        def decorator(func):
            tool_name = name or func.__name__
            self.tools[tool_name] = {
                "function": func,
                "name": tool_name,
                "description": description or func.__doc__,
                "schema": self._infer_schema(func),
            }
            return func
        return decorator
    
    def get_openai_tools(self):
        """生成 OpenAI 格式的工具定义"""
        return [
            {
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t["description"],
                    "parameters": t["schema"],
                },
            }
            for t in self.tools.values()
        ]
    
    def execute(self, name, arguments):
        """执行工具调用"""
        tool = self.tools.get(name)
        if not tool:
            return json.dumps({"error": f"未知工具：{name}"})
        
        args = json.loads(arguments)
        result = tool["function"](**args)
        return result


# 使用
registry = ToolRegistry()

@registry.register()
def get_weather(city: str, unit: str = "celsius") -> str:
    """查询天气"""
    ...

@registry.register()
def search_web(query: str) -> str:
    """搜索网络"""
    ...
```

### 3.2 动态工具加载

根据任务动态加载需要的工具：

```python
class DynamicToolLoader:
    def __init__(self):
        self.all_tools = self._load_all_tools()
    
    def get_relevant_tools(self, user_input, max_tools=10):
        """根据用户输入，选择最相关的工具"""
        # 方法：用嵌入模型匹配工具描述
        input_embedding = embed(user_input)
        tool_scores = []
        
        for name, tool in self.all_tools.items():
            tool_embedding = embed(tool.description)
            score = cosine_similarity(input_embedding, tool_embedding)
            tool_scores.append((name, score))
        
        # 取 top-k
        tool_scores.sort(key=lambda x: x[1], reverse=True)
        return [self.all_tools[name] for name, _ in tool_scores[:max_tools]]
```

---

## 四、并行工具调用

### 4.1 并行调用

支持一次调用多个工具：

```python
# 用户：帮我查一下北京和上海的天气，然后搜索一下最新的 Python 教程

# 模型可能一次返回多个 tool_calls：
{
    "tool_calls": [
        {
            "type": "function",
            "function": {"name": "get_weather", "arguments": '{"city": "北京"}'},
        },
        {
            "type": "function",
            "function": {"name": "get_weather", "arguments": '{"city": "上海"}'},
        },
        {
            "type": "function",
            "function": {"name": "search_web", "arguments": '{"query": "Python 教程 2026"}'},
        },
    ]
}
```

### 4.2 并行执行

```python
async def execute_parallel_tool_calls(tool_calls, registry):
    """并行执行多个工具调用"""
    tasks = []
    for tc in tool_calls:
        name = tc.function.name
        arguments = tc.function.arguments
        task = asyncio.create_task(registry.execute_async(name, arguments))
        tasks.append(task)
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return results
```

---

## 五、工具链与组合

### 5.1 工具链

多个工具按顺序调用，前一个的输出作为后一个的输入：

```python
# 用户：帮我查一下北京今天的天气，然后根据天气推荐穿搭

# Step 1: 查天气
get_weather("北京") → {"temperature": 25, "condition": "晴"}

# Step 2: 根据天气推荐穿搭
recommend_outfit("晴", 25) → "建议穿短袖T恤和薄外套，带好防晒"
```

### 5.2 工具组合

```python
class ToolChain:
    def __init__(self, registry):
        self.registry = registry
    
    def execute_chain(self, tool_calls, max_steps=10):
        """执行工具链"""
        context = {}
        
        for step in range(max_steps):
            if not tool_calls:
                break
            
            # 执行所有并行工具
            results = self._execute_batch(tool_calls)
            
            # 更新上下文
            context.update(results)
            
            # 让模型决定下一步
            tool_calls = self._decide_next(context)
        
        return context
```

---

## 六、工具调用的常见问题

### 6.1 模型不调用工具

```
问题：模型应该调用工具，但直接用"知识"回答

原因：
- 工具描述不够清晰
- 模型没有意识到需要调用工具
- 工具定义中有歧义

解决方案：
- 在 System Prompt 中强调"优先使用工具"
- 给工具调用的示例
- 简化工具描述
```

### 6.2 模型调错工具

```
问题：模型应该调用 search_web，却调用了 get_weather

原因：
- 工具描述相似
- 参数匹配错误

解决方案：
- 工具名要有区分度
- 描述要精确
- 减少工具数量（太多工具会让模型困惑）
```

### 6.3 参数错误

```
问题：工具调用的参数格式不对

原因：
- 参数定义不够清晰
- 模型没理解参数含义

解决方案：
- 给参数提供示例值
- 使用 enum 约束枚举值
- 参数描述中加入"注意"信息
```

---

## 七、2026 年工具系统趋势

### 7.1 MCP 协议

MCP（Model Context Protocol）是 2025 年推出的**标准工具协议**，统一了工具的定义和调用方式。

```
MCP 工具定义：
{
  "name": "get_weather",
  "description": "...",
  "inputSchema": {
    "type": "object",
    "properties": {...}
  }
}
```

### 7.2 工具市场

Agent 可以从"工具市场"动态安装工具，不再需要代码预定义。

### 7.3 Agent 自建工具

Agent 可以根据任务需求，自己编写工具并注册。

---

## 总结

| 概念 | 一句话 |
|------|--------|
| Function Calling | 让 LLM 理解并调用工具的标准方式 |
| 工具定义 | 名称、描述、参数——三个都要准确 |
| 动态加载 | 根据任务只加载相关工具 |
| 并行调用 | 同时调用多个工具，提高效率 |
| 工具链 | 多个工具按顺序组合使用 |

**Agent 的能力 = 模型能力 × 工具能力。**

下一篇文章，我们将深入**Agent 编排框架**——LangGraph、CrewAI、AutoGen 的对比和使用。

---

**思考题**：
1. 你的 Agent 现在有多少个工具？其中哪些是真正常用的？
2. 如果工具超过 20 个，你会怎么管理？全部加载还是动态加载？
3. 你遇到过模型"不调用工具"的情况吗？怎么解决的？

---

> 上一篇：[24] Agent 范式巡礼：ReAct、Plan-and-Execute、Reflexion
> 下一篇：[26] Agent 编排框架：LangGraph、CrewAI、AutoGen
> 系列目录：[README.md](./README.md)