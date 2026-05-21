# AI 开发基础（第3篇）：Agent Loop 与 Tool Use - 让模型从"回答"变成"执行"

> **适合读者**：已读完第1-2篇（LLM API、KV Cache），想理解Agent的核心机制  
> **预计阅读时间**：35分钟  
> **代码示例**：全部可运行（Python 3.10+）  
> **前置知识**：LLM API调用、Function Calling（第1篇）

---

## 前言：什么是Agent？

前两篇，我们学的是"LLM作为工具"。你问一个问题，它回答一个答案。**你控制节奏，它被动响应。**

Agent改变了这个关系。

**Agent = LLM + 循环 + 工具**

LLM不再只是"回答问题"，而是：
1. 理解你的意图
2. 决定要不要用工具
3. 调用工具，拿到结果
4. 根据结果，决定下一步做什么
5. 重复2-4，直到任务完成

**这个过程就是 Agent Loop（智能体循环）。**

---

## 一、从"问答"到"执行"：一个例子

### 1.1 普通问答（没有Agent）

```
用户：北京明天天气怎么样？吃火锅配什么好？
LLM：根据我的知识...
```

问题：LLM没有实时数据，只能"编"或者告诉你"我不知道"。

### 1.2 Agent执行（有Agent）

```
用户：北京明天天气怎么样？吃火锅配什么好？

Agent（第1轮思考）：
  → 用户问了天气，我需要调用天气API
  → 调用 get_weather(city="北京", date="明天")

Agent（收到结果：北京明天 晴 15-28°C）：
  → 天气晴朗，适合户外活动
  → 用户还问吃火锅配什么，这不需要工具，我直接回答

Agent（最终回复）：
  → 北京明天晴天，15-28°C，适合出门。
  → 火锅配毛肚、鹅肠、黄喉、冻豆腐...
```

**区别**：Agent会"自己决定"调什么工具，"自己判断"任务完没完成。

---

## 二、Agent Loop 的核心结构

### 2.1 伪代码

```python
while True:
    # 1. 发送消息给LLM（包含历史对话）
    response = llm.chat(messages)
    
    # 2. 检查LLM是否要调用工具
    if response.has_tool_calls:
        # 3. 执行工具
        for tool_call in response.tool_calls:
            result = execute_tool(tool_call.name, tool_call.arguments)
            
            # 4. 把工具结果加回对话历史
            messages.append({
                "role": "tool",
                "content": result,
                "tool_call_id": tool_call.id
            })
        
        # 5. 继续循环，让LLM看到工具结果后继续思考
        continue
    
    else:
        # 6. LLM决定不调用工具了，输出最终回复
        print(response.content)
        break
```

**就这么简单。** 整个Agent的核心就是一个 `while True` 循环。

### 2.2 用Python实现一个最小Agent

```python
import json
from openai import OpenAI

client = OpenAI(api_key="your-api-key", base_url="https://api.deepseek.com")

# 定义工具
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "获取指定城市的天气信息",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "城市名称"},
                    "date": {"type": "string", "description": "日期，如'今天'、'明天'"}
                },
                "required": ["city"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_poi",
            "description": "搜索附近的兴趣点（餐厅、景点等）",
            "parameters": {
                "type": "object",
                "properties": {
                    "keyword": {"type": "string", "description": "搜索关键词"},
                    "city": {"type": "string", "description": "城市"},
                    "radius": {"type": "number", "description": "搜索半径（米）"}
                },
                "required": ["keyword", "city"]
            }
        }
    }
]

# 实现工具函数
def get_weather(city: str, date: str = "今天") -> str:
    """模拟天气API"""
    weather_db = {
        "北京": {"今天": "晴 18-30°C", "明天": "多云 15-28°C"},
        "上海": {"今天": "阴 22-28°C", "明天": "小雨 20-25°C"},
    }
    result = weather_db.get(city, {}).get(date, f"{city}{date}：暂无数据")
    return json.dumps({"city": city, "date": date, "weather": result}, ensure_ascii=False)


def search_poi(keyword: str, city: str, radius: int = 3000) -> str:
    """模拟POI搜索API"""
    poi_db = {
        ("火锅", "北京"): [
            {"name": "海底捞(望京店)", "rating": 4.5, "distance": "800m"},
            {"name": "呷哺呷哺(朝阳大悦城)", "rating": 4.2, "distance": "1.2km"},
        ],
        ("火锅", "上海"): [
            {"name": "海底捞(南京东路店)", "rating": 4.6, "distance": "500m"},
        ],
    }
    results = poi_db.get((keyword, city), [])
    return json.dumps({"keyword": keyword, "city": city, "results": results}, ensure_ascii=False)


# 工具路由
tool_map = {
    "get_weather": get_weather,
    "search_poi": search_poi,
}

# Agent Loop
def run_agent(user_input: str, max_rounds: int = 10):
    """运行Agent"""
    messages = [
        {"role": "system", "content": "你是一个智能助手，可以查询天气和搜索地点。用中文回答。"},
        {"role": "user", "content": user_input},
    ]
    
    for round_num in range(max_rounds):
        print(f"\n--- Agent 第 {round_num + 1} 轮 ---")
        
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            tools=tools,
            tool_choice="auto",
        )
        
        choice = response.choices[0]
        
        # 检查是否要调用工具
        if choice.finish_reason == "tool_calls":
            for tool_call in choice.message.tool_calls:
                func_name = tool_call.function.name
                func_args = json.loads(tool_call.function.arguments)
                
                print(f"  调用工具: {func_name}({func_args})")
                
                # 执行工具
                result = tool_map[func_name](**func_args)
                print(f"  工具结果: {result}")
                
                # 工具结果加入对话
                messages.append(choice.message.model_dump())
                messages.append({
                    "role": "tool",
                    "content": result,
                    "tool_call_id": tool_call.id,
                })
        else:
            # LLM输出最终回复
            print(f"\n最终回复: {choice.message.content}")
            messages.append({"role": "assistant", "content": choice.message.content})
            return messages
    
    print("⚠️ 达到最大轮次限制，强制停止")
    return messages


# 测试
if __name__ == "__main__":
    run_agent("北京明天天气怎么样？帮我找附近评分高的火锅店")
```

**输出**：
```
--- Agent 第 1 轮 ---
  调用工具: get_weather({'city': '北京', 'date': '明天'})
  工具结果: {"city": "北京", "date": "明天", "weather": "多云 15-28°C"}

--- Agent 第 2 轮 ---
  调用工具: search_poi({'keyword': '火锅', 'city': '北京'})
  工具结果: {"keyword": "火锅", "city": "北京", "results": [...]}

最终回复: 北京明天多云，气温15-28°C，挺适合出门的。

附近评分高的火锅店推荐：
1. 海底捞(望京店) - 评分4.5，距离800米
2. 呷哺呷哺(朝阳大悦城) - 评分4.2，距离1.2公里
```

### 2.3 关键理解

| 概念 | 说明 |
|------|------|
| **finish_reason** | `"tool_calls"` = LLM要调用工具；`"stop"` = LLM直接回复 |
| **tool_choice** | `"auto"` = LLM自己决定；`"required"` = 强制调工具 |
| **max_rounds** | 防止无限循环（必须有上限） |
| **tool_call_id** | 把工具结果和对应的调用请求关联起来 |

---

## 三、Tool Use 的深入理解

### 3.1 工具调用的本质

**Tool Use（工具调用）不是什么魔法，它就是一个结构化的函数调用协议。**

流程：
```
1. 你告诉LLM："你有这些工具可以用"（tools参数）
2. LLM看到用户问题后，判断："我需要调用XXX工具，参数是YYY"
3. LLM输出的不是自然语言，而是一个结构化的JSON：{"name": "xxx", "arguments": {...}}
4. 你的代码解析这个JSON，执行真正的函数
5. 把函数的返回值告诉LLM
6. LLM根据返回值，生成自然语言回复
```

**核心**：LLM本身不执行任何函数。它只负责"决定调什么"和"解读结果"。真正的执行在你的代码里。

### 3.2 工具定义的技巧

工具定义的好坏，直接决定了Agent的表现。

**❌ 差的工具定义**：
```python
{
    "name": "api",
    "description": "调用API",
    "parameters": {
        "type": "object",
        "properties": {
            "url": {"type": "string"},
            "method": {"type": "string"},
            "body": {"type": "string"}
        }
    }
}
```

问题：太宽泛，LLM不知道该传什么URL和body，容易乱调。

**✅ 好的工具定义**：
```python
{
    "name": "search_restaurant",
    "description": "根据菜系、位置、评分搜索餐厅。返回餐厅名称、评分、地址、营业时间。",
    "parameters": {
        "type": "object",
        "properties": {
            "cuisine": {
                "type": "string",
                "description": "菜系类型，如'火锅'、'日料'、'川菜'"
            },
            "city": {
                "type": "string",
                "description": "城市名称"
            },
            "min_rating": {
                "type": "number",
                "description": "最低评分（1-5），默认4.0"
            }
        },
        "required": ["cuisine", "city"]
    }
}
```

**关键原则**：

| 原则 | 说明 |
|------|------|
| **语义清晰** | description要让人一看就懂这个工具干什么 |
| **参数具体** | 用有意义的字段名，不要用`param1`、`data` |
| **描述必填** | 每个参数都要有description，帮助LLM理解 |
| **范围明确** | 枚举值、默认值、单位都写清楚 |
| **返回值透明** | description里说清楚返回什么数据 |

**真实踩坑**：
- 我一开始给工具定义写了`"description": "搜索"`，三个字。结果LLM什么搜索都调这个工具，包括搜索代码、搜索文档。后来改成`"搜索餐厅（仅限餐饮类POI）"`，误调用减少了80%。

### 3.3 并行工具调用

**LLM可以同时调用多个工具**（如果它们之间没有依赖关系）。

```
用户：北京天气怎么样？上海呢？

Agent 第1轮：
  → 同时调用 get_weather(city="北京") 和 get_weather(city="上海")
  → 不需要等第一个结果回来再调第二个

Agent 第2轮：
  → 两个结果都拿到了，一次性回复
```

**代码**：
```python
# 处理并行工具调用
if choice.finish_reason == "tool_calls":
    tool_calls = choice.message.tool_calls
    
    # 所有工具调用一起加入对话
    messages.append(choice.message.model_dump())
    
    for tool_call in tool_calls:
        func_name = tool_call.function.name
        func_args = json.loads(tool_call.function.arguments)
        result = tool_map[func_name](**func_args)
        
        messages.append({
            "role": "tool",
            "content": result,
            "tool_call_id": tool_call.id,
        })
```

**注意**：并行调用只在 `tool_calls` 列表里有多个元素时才发生。如果LLM只想调一个工具，列表就只有一个元素。

---

## 四、Agent Loop 的进阶控制

### 4.1 循环终止条件

最基础的终止条件是 `finish_reason == "stop"`。但实际项目中，你需要更多保护：

```python
def run_agent(user_input: str, max_rounds: int = 10, max_tokens: int = 50000):
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_input},
    ]
    
    total_tokens_used = 0
    
    for round_num in range(max_rounds):
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            tools=tools,
        )
        
        # 累计Token使用量
        total_tokens_used += response.usage.total_tokens
        
        choice = response.choices[0]
        
        # 条件1：LLM决定不调工具了
        if choice.finish_reason == "stop":
            return choice.message.content
        
        # 条件2：Token预算用完
        if total_tokens_used > max_tokens:
            return f"（Token预算用完，共消耗{total_tokens_used}tokens。已生成部分结果：{choice.message.content}）"
        
        # 条件3：工具调用失败
        if choice.finish_reason == "tool_calls":
            for tool_call in choice.message.tool_calls:
                func_name = tool_call.function.name
                if func_name not in tool_map:
                    # 工具不存在，告诉LLM
                    messages.append(choice.message.model_dump())
                    messages.append({
                        "role": "tool",
                        "content": json.dumps({"error": f"工具 {func_name} 不存在"}),
                        "tool_call_id": tool_call.id,
                    })
                    continue
                
                # 正常执行...
    
    return f"（达到最大轮次 {max_rounds}，任务可能未完成）"
```

### 4.2 为什么Agent会死循环？

| 原因 | 表现 | 解决方案 |
|------|------|---------|
| 工具返回错误，LLM反复重试 | 同一工具连续调5次 | 加重试次数限制 |
| LLM不知道该停 | finish_reason一直是tool_calls | 在system prompt中明确说"完成任务后直接回复" |
| 工具之间互相触发 | A调B，B调A | 检测循环调用模式 |
| LLM幻觉出不存在的工具 | 调用了一个你没定义的工具 | 工具名不匹配时返回错误信息 |

**system prompt 技巧**：
```
你是一个任务执行助手。规则：
1. 仔细分析用户需求，用最少的工具调用完成任务
2. 如果工具返回了足够的信息，直接给出最终回复，不要继续调用工具
3. 如果工具调用失败，尝试替代方案，不要反复调用同一个工具
4. 完成任务后，给出清晰、完整的回复
```

### 4.3 工具调用的错误处理

```python
import time
from functools import wraps

def retry_tool(max_retries=2, delay=1):
    """工具调用重试装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt < max_retries:
                        time.sleep(delay * (attempt + 1))
                        continue
                    return json.dumps({
                        "error": str(e),
                        "tool": func.__name__,
                        "suggestion": "工具调用失败，请尝试其他方式"
                    }, ensure_ascii=False)
        return wrapper
    return decorator


@retry_tool(max_retries=2)
def get_weather(city: str, date: str = "今天") -> str:
    """天气API（带重试）"""
    # 真实项目中这里调外部API
    # 可能网络超时、服务不可用等
    weather_db = {"北京": {"今天": "晴 18-30°C"}}
    result = weather_db.get(city, {}).get(date, f"{city}{date}：暂无数据")
    return json.dumps({"city": city, "date": date, "weather": result}, ensure_ascii=False)
```

**真实项目经验**：
- 在智能行程规划项目中，高德API偶尔超时。用retry_tool包装后，成功率从95%提升到99.5%
- 但重试不是万能的。如果API本身就挂了，重试3次也白搭。所以还需要降级策略（备用API、缓存等）

---

## 五、真实项目：智能行程规划Agent

### 5.1 项目背景

用户说："帮我规划一个北京3天行程"，Agent需要：
1. 搜索景点
2. 查天气
3. 搜索餐厅
4. 根据地理位置规划路线
5. 输出完整行程单

**5个工具，多轮调用，有依赖关系。**

### 5.2 工具设计

```python
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "获取城市天气预报，用于决定室内/室外活动",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "城市名"},
                    "date": {"type": "string", "description": "日期"}
                },
                "required": ["city"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_attractions",
            "description": "搜索景点，返回名称、评分、地址、开放时间、建议游玩时长",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string"},
                    "category": {"type": "string", "description": "类型：历史、自然、主题乐园等"},
                    "top_n": {"type": "integer", "description": "返回数量，默认5"}
                },
                "required": ["city"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_restaurant",
            "description": "搜索餐厅，返回名称、菜系、评分、人均价格、地址",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string"},
                    "cuisine": {"type": "string", "description": "菜系"},
                    "near": {"type": "string", "description": "靠近哪个地点"}
                },
                "required": ["city"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_route",
            "description": "获取两个地点之间的交通路线和时间（驾车/公交/步行）",
            "parameters": {
                "type": "object",
                "properties": {
                    "origin": {"type": "string"},
                    "destination": {"type": "string"},
                    "mode": {"type": "string", "enum": ["driving", "transit", "walking"]}
                },
                "required": ["origin", "destination"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_route_batch",
            "description": "批量获取多个地点之间的路线时间，用于规划一日行程顺序",
            "parameters": {
                "type": "object",
                "properties": {
                    "locations": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "地点列表，按顺序计算相邻两个地点的路线"
                    },
                    "mode": {"type": "string", "enum": ["driving", "transit", "walking"]}
                },
                "required": ["locations"]
            }
        }
    }
]
```

### 5.3 Agent执行过程

```
用户：帮我规划北京3天行程

Agent 第1轮：
  → get_weather(city="北京")  # 先看天气

Agent 第2轮（收到天气：3天都晴）：
  → search_attractions(city="北京", top_n=10)  # 搜索景点

Agent 第3轮（收到10个景点）：
  → search_restaurant(city="北京", near="故宫")  # 搜景点附近餐厅

Agent 第4轮：
  → get_route_batch(locations=["酒店", "故宫", "南锣鼓巷", "什刹海"])  # 规划Day1路线

Agent 第5轮：
  → get_route_batch(locations=["酒店", "颐和园", "圆明园", "北大"])  # 规划Day2路线

Agent 第6轮：
  → 生成完整的3天行程单
```

**实际踩坑**：
1. **LLM选了太多景点**：一次搜了10个，排不下。后来在system prompt里加了"每天最多安排3-4个景点"
2. **路线规划不合理**：LLM把故宫和长城排在同一天。后来加了"相邻景点才排同一天"的提示
3. **餐厅搜索太泛**：LLM搜"好吃的餐厅"，结果五花八门。后来改为必须指定cuisine和near参数

---

## 六、从裸写Agent到使用框架

### 6.1 什么时候需要框架？

上面我们用纯Python实现了Agent Loop。这在简单场景够用，但复杂场景会遇到问题：

| 问题 | 裸写Agent | 用框架 |
|------|----------|--------|
| 状态管理 | 手动维护messages列表 | 框架自动管理 |
| 条件分支 | 一堆if-else | 用图/状态机表达 |
| 多Agent协作 | 手动编排 | 框架提供通信机制 |
| 可观测性 | 手动打日志 | 内置trace/debug |
| 持久化/恢复 | 自己实现 | 框架支持checkpoint |

**判断标准**：
- 1-3个工具、简单逻辑 → 裸写够用
- 4个以上工具、有条件分支 → 用框架（LangGraph推荐）
- 多Agent协作 → 必须用框架

### 6.2 主流框架对比

| 框架 | 特点 | 适合场景 |
|------|------|---------|
| **LangGraph** | 图编排、状态机、支持循环/分支/并行 | 复杂Agent、多Agent |
| **CrewAI** | 多Agent角色扮演 | 团队协作型Agent |
| **AutoGen** | 微软出品，多Agent对话 | 研究/原型 |
| **OpenAI Agents SDK** | 官方出品，Handoff机制 | OpenAI生态 |

**我的选择**：LangGraph。原因：
1. 图编排表达力强，复杂流程可控
2. 内置checkpoint（断点恢复）
3. 社区活跃，文档好
4. 和LangChain生态无缝集成

### 6.3 LangGraph版Agent Loop

```python
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI

# 定义LLM
llm = ChatOpenAI(
    model="deepseek-chat",
    base_url="https://api.deepseek.com",
    api_key="your-api-key",
)

# 创建Agent（一行代码）
agent = create_react_agent(
    model=llm,
    tools=[get_weather_tool, search_poi_tool],
    prompt="你是一个智能助手，可以查询天气和搜索地点。",
)

# 运行
result = agent.invoke({
    "messages": [{"role": "user", "content": "北京明天天气怎么样？"}]
})

print(result["messages"][-1].content)
```

**LangGraph的create_react_agent帮你做了什么**：
1. 自动管理Agent Loop（不再手动写while循环）
2. 自动处理tool_calls和tool response
3. 内置max_rounds保护
4. 支持checkpoint（中断/恢复）

---

## 七、本章总结

**你学到了什么**：

1. **Agent的核心**：LLM + while循环 + 工具调用，就这么简单
2. **Agent Loop结构**：发送→检查tool_calls→执行→结果回传→继续循环，直到stop
3. **Tool Use本质**：LLM输出结构化的函数调用请求，你的代码负责执行
4. **工具定义技巧**：语义清晰、参数具体、描述必填、返回值透明
5. **循环控制**：max_rounds保护、Token预算、错误处理、重试+降级
6. **框架选择**：简单场景裸写，复杂场景用LangGraph

**关键公式**：
```
Agent = LLM + Loop + Tools
Agent Loop = while(not done) { response = llm(messages); if tool_calls: execute; else: break }
```

**下一篇预告**：
- 第4篇：Reasoning 与 Planning - 让模型"想清楚再动手"
- 你会学到：Chain-of-Thought、ReAct、Plan-and-Execute等推理模式

---

## 参考资料

1. OpenAI Function Calling文档：https://platform.openai.com/docs/guides/function-calling
2. LangGraph官方文档：https://langchain-ai.github.io/langgraph/
3. ReAct论文：https://arxiv.org/abs/2210.03629
4. Toolformer论文：https://arxiv.org/abs/2302.04761

---

**上一篇**：第2篇 KV Cache - 理解推理性能的关键  
**下一篇**：第4篇 Reasoning 与 Planning - 让模型"想清楚再动手"
