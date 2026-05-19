# Agent 设计模式：ReAct 与 Plan-Execute 讲透

> Function Calling 让 Agent 会用工具，但真正让 Agent「聪明」的，是它的思考模式。这就像给你一本字典不意味着你会写文章——你需要方法论。ReAct 和 Plan-Execute 就是 Agent 的两种核心方法论。

---

## 一、什么是 Agent 的「思考模式」

看一个例子：

```
用户：写一个 Python 脚本，从 CSV 读取销售数据，计算月度汇总，生成图表

普通 LLM：直接写一堆代码（可能缺少依赖、路径写死、图表类型不合适）

有思考的 Agent：
  思考：我需要分几步做这件事
  步骤1：先看看 CSV 长什么样（调 read_file）
  步骤2：用 pandas 读取和计算（写代码）
  步骤3：用 matplotlib 生成图表（写代码）
  步骤4：跑一遍验证（执行）
  结果：完整、可运行的方案
```

这就是 Agent 的核心价值——**不是一步到位，而是分步执行、观察结果、修正方向。**

---

## 二、ReAct：边想边做

**ReAct = Reasoning + Acting**，是 2023 年 Google 提出的范式，至今仍是 Agent 设计的基础。

### ReAct 循环

```
         ┌──────────────┐
         │  观察环境     │←─────────────┐
         └──────┬───────┘              │
                ▼                       │
         ┌──────────────┐              │
         │  推理思考     │              │
         └──────┬───────┘              │
                ▼                       │
         ┌──────────────┐              │
         │  执行动作     │──────────────┘
         └──────────────┘      （循环直到完成）
```

### 手写 ReAct Agent

```python
import json
from openai import OpenAI

client = OpenAI(api_key="your-key", base_url="https://api.deepseek.com/v1")

# ── 工具定义 ──
tools = [...]  # 同上一篇的天气和计算工具

# ── ReAct System Prompt ──
REACT_PROMPT = """你是一个 ReAct Agent。按以下格式思考和行动：

Thought: 分析当前情况，决定下一步做什么
Action: 调用的工具名称
Action Input: 工具参数（JSON 格式）
Observation: 工具返回的结果
...（重复 Thought/Action/Action Input/Observation）
Thought: 我已经有足够的信息回答用户了
Final Answer: 最终回答

可用工具：
- get_weather(city: str): 查询城市天气
- calculate(expression: str): 执行数学计算

开始！"""


def react_agent(user_input: str, max_steps: int = 5) -> str:
    messages = [
        {"role": "system", "content": REACT_PROMPT},
        {"role": "user", "content": user_input}
    ]

    for step in range(max_steps):
        print(f"\n--- Step {step + 1} ---")

        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            tools=tools,
            tool_choice="auto"
        )

        msg = response.choices[0].message
        content = msg.content or ""
        print(content[:200])

        # 如果 LLM 输出 Final Answer，结束
        if "Final Answer:" in content:
            return content.split("Final Answer:")[-1].strip()

        # 如果有工具调用，执行
        if msg.tool_calls:
            for tool_call in msg.tool_calls:
                func_name = tool_call.function.name
                func_args = json.loads(tool_call.function.arguments)
                print(f"🔧 调用：{func_name}({func_args})")

                # 执行工具
                result = execute_tool(func_name, func_args)
                print(f"📊 结果：{result}")

                # 追加入对话
                messages.append(msg)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result
                })

    return "未能完成（超过最大步骤数）"


# ── 复杂任务测试 ──
result = react_agent(
    "北京今天什么天气？如果温度超过 20 度，帮我把 100 + 200 算一下"
)
print(f"\n✅ 最终答案：{result}")
```

**执行过程**：

```
--- Step 1 ---
Thought: 用户问了两个问题。先查北京天气。
Action: get_weather
🔧 调用：get_weather({'city': '北京'})
📊 结果：北京：晴，25°C

--- Step 2 ---
Thought: 温度超过 20 度，需要计算 100 + 200
Action: calculate
🔧 调用：calculate({'expression': '100 + 200'})
📊 结果：300

--- Step 3 ---
Thought: 两个问题都有了结果
Final Answer: 北京今天晴天，温度 25°C。由于超过 20 度，100 + 200 = 300。
```

---

## 三、Plan-Execute：先规划后执行

ReAct 是「走一步看一步」，Plan-Execute 是「谋定而后动」。

```
Plan-Execute 流程：

① Planner（规划器）：
   分析任务 → 生成步骤清单

② Executor（执行器）：
   逐步执行计划中的每一步

③ Monitor（监控器）：
   检查执行结果，必要时让 Planner 重新规划
```

### Plan-Execute 代码框架

```python
PLANNER_PROMPT = """你是任务规划器。请将用户需求分解为可执行的步骤清单。
每步应该是单一的、可独立完成的动作。

输出格式：
{
  "steps": [
    {"step": 1, "action": "描述动作", "tool": "工具名", "args": {}},
    {"step": 2, ...}
  ]
}"""

EXECUTOR_PROMPT = """你是任务执行器。执行给定的步骤，报告结果。"""


async def plan_execute_agent(user_input: str):
    # 1. 规划
    plan_response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": PLANNER_PROMPT},
            {"role": "user", "content": user_input}
        ],
        response_format={"type": "json_object"}
    )

    plan = json.loads(plan_response.choices[0].message.content)
    print(f"📋 规划了 {len(plan['steps'])} 个步骤：")

    # 2. 逐步执行
    results = []
    for s in plan["steps"]:
        print(f"  执行步骤 {s['step']}: {s['action']}")
        result = execute_tool(s["tool"], s["args"])
        results.append(result)

    # 3. 汇总
    summary_prompt = f"根据以下执行结果，生成最终回复：\n{json.dumps(results)}"
    final = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": summary_prompt}]
    )

    return final.choices[0].message.content
```

---

## 四、ReAct vs Plan-Execute

| 维度 | ReAct | Plan-Execute |
|------|-------|-------------|
| 决策方式 | 每步看结果再决定下一步 | 一次性规划，逐步执行 |
| 灵活性 | 高——能应对意外 | 低——按计划走 |
| 效率 | 步骤可能多 | 步骤少，不反复 |
| 适用场景 | 需要试错、探索性任务 | 步骤明确、流程化任务 |
| 风险 | 可能「迷路」（无限循环） | 第一步规划错就全错 |

> **实战建议**：简单任务用 ReAct，流程明确的任务用 Plan-Execute。复杂任务可以混合——先用 Plan-Execute 规划大框架，每个子任务内部用 ReAct。

---

## 五、进阶：Reflection（反思）模式

在 ReAct 基础上加一层「回头看」：

```
ReAct 循环
    ↓
暂停 → 自我检查：
  "我做对了吗？有没有遗漏？有没有更简单的做法？"
    ↓
有问题 → 修正 → 继续
没问题 → 输出最终答案
```

```python
REFLECTION_PROMPT = """
请检查你刚才的推理和行动：
1. 是否遗漏了用户需求？
2. 工具调用结果是否正确理解？
3. 最终回答是否完整？
如果发现问题，请修正后重新输出。
"""
```

---

## 六、实战：用 ReAct 做一个代码助手 Agent

```python
# 工具集
tools = [
    {"name": "read_file", "description": "读取文件内容"},
    {"name": "write_file", "description": "写入文件"},
    {"name": "run_tests", "description": "运行测试"},
    {"name": "search_docs", "description": "搜索技术文档"},
]

# 场景：修 bug
task = """
用户报告：app.py 第 42 行的 login 函数，当用户名为空时没有返回错误。
请修复这个 bug，并确保所有测试通过。
"""

# Agent 的执行过程：
# Thought: 先看看 app.py 长什么样
# Action: read_file("app.py")
# Observation: [文件内容]
# Thought: 第 42 行确实没有处理空用户名。需要加校验。
# Action: write_file("app.py", "[修改后的内容]")
# Observation: 写入成功
# Thought: 跑测试确认
# Action: run_tests()
# Observation: 全部通过 ✅
# Final Answer: 已在 login 函数开头添加了空用户名校验，测试全部通过。
```

---

## 七、总结

1. **ReAct 是 Agent 的基础循环**：思考→行动→观察→再思考
2. **Plan-Execute 适合确定性任务**：先列计划，逐步执行
3. **Reflection 提升准确率**：执行后自我检查
4. **生产环境通常混合使用**：外层 Plan-Execute，子任务 ReAct
5. **设置 max_steps**：防止 Agent 无限循环

---

## 八、生产实战：Agent 上线后才知道的事

### 8.1 Agent 无限循环——每月至少遇到一次

ReAct Agent 最常见的 bug：LLM 反复调用同一个工具，永远到不了 Final Answer。

一个代码审查 Agent 因为 LLM 对修复不满意，连续调了 14 次 read_file + write_file，烧了 $2 Token，什么都没改好：

```python
MAX_STEPS = 5
STAGNATION_LIMIT = 3  # 连续同一动作超过 3 次 → 强制终止

def detect_loop(action_history: list) -> bool:
    if len(action_history) < STAGNATION_LIMIT:
        return False
    recent = action_history[-STAGNATION_LIMIT:]
    # 检查最近 3 次是否都在做一模一样的事
    return len(set((a['tool'], str(a['args'])) for a in recent)) == 1

# 在主循环中检测
if detect_loop(action_history):
    messages.append({"role": "system", "content": "你陷入了循环。直接输出 Final Answer，说明无法完成的原因。"})
```

### 8.2 成本失控——Agent 偷偷帮你花钱

```
电商客服 Agent，日均 200 次对话
每次对话：3250 Token
月消耗：2000 万 Token

Claude Opus:  $300/月
Claude Sonnet: $60/月
DeepSeek V3:  ¥20/月
```

> **经验**：Agent 开发阶段用便宜模型。上线后对任务分级——简单意图识别用 DeepSeek，复杂推理才切 Claude。定时拉 API 账单，发现异常立即排查。

### 8.3 Human-in-the-Loop：不该让 Agent 自己做决定的事

```python
DANGEROUS_ACTIONS = ["delete_file", "drop_table", "send_email_to_all", "publish_article"]

def requires_approval(action: dict) -> bool:
    if action["tool"] in DANGEROUS_ACTIONS:
        return True
    if estimate_cost(action) > 0.5:  # 预估成本 > $0.5
        return True
    return False
```

> 一个真实事件：Agent 在测试环境自动 DROP 了一张表，因为 LLM 把「清理测试数据」理解成了 DROP TABLE。从那以后所有 DROP/TRUNCATE 操作都加了人工确认。

### 8.4 Agent 输出质量的评估

Agent 不像传统代码那么容易测：

| 评估维度 | 问题 | 怎么测 |
|---------|------|------|
| 任务完成率 | 用户需求被满足了吗？ | 人工标注 100 个 case |
| 工具选择 | 选的工具对吗？有没有多调/漏调？ | 对比最优调用路径 |
| 效率 | 步骤数合理吗？有没有绕弯路？ | 统计平均步骤数 |
| 安全 | 有没有危险操作？ | 敏感操作审计日志 |
| 成本 | Token 消耗合理吗？ | 监控 API 账单 |

---

> 下一篇：**《LangGraph 入门：用状态图构建 Agent》**——告别手写循环，用声明式的方式定义 Agent 的行为逻辑。

*系列文章：00-总纲 → ①-LLM 原理 → ②-Prompt 工程 → ③-Function Calling → ④-RAG → ⑤-Agent 模式 → ⑥-LangGraph → ⑦-MCP → ⑧-Multi-Agent*
