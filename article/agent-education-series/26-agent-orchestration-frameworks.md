# 【AI Agent 系统教学 26】Agent 编排框架：LangGraph、CrewAI、AutoGen

> 当你需要构建一个复杂的 Agent 系统，"自己写循环"就不够了。
> 编排框架帮你管理状态、流程、多 Agent 协作。

---

## 前言：什么时候需要框架？

自己写一个 Agent 循环有多简单？

```python
while True:
    response = llm.generate(messages)
    if has_tool_call(response):
        execute_tool(response)
    else:
        break
```

不到 10 行代码。但当你需要处理以下情况时，事情就复杂了：

- 状态管理（多轮对话中的状态）
- 条件分支（不同情况走不同路径）
- 错误处理（工具调用失败怎么办）
- 多 Agent 协作（多个 Agent 之间通信）
- 持久化（Agent 状态保存和恢复）

这时候，Agent 编排框架就派上用场了。

---

## 一、LangGraph：状态机驱动的 Agent 框架

### 1.1 核心思想

LangGraph 把 Agent 的决策过程建模为**状态机（State Machine）**：

```
节点（Node）：Agent 的某个状态（如"思考"、"调用工具"、"生成回复"）
边（Edge）：状态之间的转换
条件边（Conditional Edge）：根据条件决定走哪条边
```

### 1.2 基础示例

```python
from langgraph.graph import StateGraph, END
from typing import TypedDict, List

# 定义状态
class AgentState(TypedDict):
    messages: List[dict]
    next_action: str

# 定义节点
def reason(state: AgentState):
    """推理节点"""
    response = llm.generate(state["messages"])
    state["next_action"] = "tool_call" if has_tool(response) else "respond"
    return state

def execute_tool(state: AgentState):
    """工具执行节点"""
    tool_call = extract_tool(state["messages"][-1])
    result = tools[tool_call["name"]].execute(tool_call["args"])
    state["messages"].append({"role": "tool", "content": result})
    return state

def respond(state: AgentState):
    """回复生成节点"""
    response = llm.generate(state["messages"])
    state["messages"].append({"role": "assistant", "content": response})
    return state

# 构建图
graph = StateGraph(AgentState)
graph.add_node("reason", reason)
graph.add_node("execute_tool", execute_tool)
graph.add_node("respond", respond)

# 添加边
graph.set_entry_point("reason")
graph.add_conditional_edges(
    "reason",
    lambda state: state["next_action"],
    {"tool_call": "execute_tool", "respond": "respond"},
)
graph.add_edge("execute_tool", "reason")
graph.add_edge("respond", END)
```

### 1.3 LangGraph 的优势

| 特性 | 说明 |
|------|------|
| 显式状态 | 所有状态明确，易于调试 |
| 循环控制 | 避免无限循环 |
| 可序列化 | 状态可以保存和恢复 |
| 分支 | 支持条件分支、并行分支 |
| 与 LangChain 集成 | 直接使用 LangChain 的工具和模型 |

### 1.4 适用场景

```
✅ 复杂工作流（多个步骤、条件分支）
✅ 需要状态持久化
✅ 需要精确控制流程
✅ 需要调试和监控

❌ 简单问答（杀鸡用牛刀）
❌ 快速原型
```

---

## 二、CrewAI：多 Agent 协作框架

### 2.1 核心思想

CrewAI 把 Agent 组织成"团队"（Crew），每个 Agent 有特定角色和职责：

```
Crew（团队）
├── Agent A：研究员（负责搜索、分析）
├── Agent B：写手（负责撰写）
├── Agent C：审核员（负责检查质量）
└── 任务：Agent 之间的协作通过任务定义
```

### 2.2 基础示例

```python
from crewai import Agent, Task, Crew, Process

# 定义 Agent
researcher = Agent(
    role="研究员",
    goal="搜索和分析信息",
    backstory="你是一名经验丰富的研究员，擅长从网络中找到准确信息",
    tools=[search_web, analyze_data],
    verbose=True,
)

writer = Agent(
    role="技术写手",
    goal="撰写高质量的技术文章",
    backstory="你是一名技术写手，擅长把复杂概念讲清楚",
    tools=[],
    verbose=True,
)

reviewer = Agent(
    role="审核员",
    goal="检查内容质量",
    backstory="你是一名严格的审核员，不放过任何错误",
    tools=[],
    verbose=True,
)

# 定义任务
research_task = Task(
    description="搜索并分析 {topic} 的最新信息",
    agent=researcher,
    expected_output="一份详细的研究报告",
)

write_task = Task(
    description="基于研究报告撰写一篇技术文章",
    agent=writer,
    expected_output="一篇 2000 字的技术文章",
)

review_task = Task(
    description="审核文章的质量",
    agent=reviewer,
    expected_output="审核意见和修改建议",
)

# 组建团队
crew = Crew(
    agents=[researcher, writer, reviewer],
    tasks=[research_task, write_task, review_task],
    process=Process.sequential,  # 顺序执行
    verbose=True,
)

# 执行
result = crew.kickoff(inputs={"topic": "AI Agent 的发展趋势"})
```

### 2.3 CrewAI 的特点

| 特性 | 说明 |
|------|------|
| 角色定义 | 每个 Agent 有明确的角色和职责 |
| 任务分配 | 任务自动分配给合适的 Agent |
| 流程控制 | 顺序、分层、自由等多种流程 |
| 工具隔离 | 每个 Agent 有不同的工具集 |
| 结果聚合 | 自动汇总多个 Agent 的输出 |

### 2.4 适用场景

```
✅ 多 Agent 协作任务
✅ 需要不同专业能力的任务
✅ 内容创作（研究+写作+审核）
✅ 自动化工作流

❌ 单 Agent 即可完成的任务
❌ 需要实时交互的任务
```

---

## 三、AutoGen：多 Agent 对话框架

### 3.1 核心思想

AutoGen 的核心是**多 Agent 之间的对话**——Agent 之间通过消息通信，完成任务。

```
Agent A（助手）←→ Agent B（用户代理）
     ↓
Agent C（代码执行器）←→ Agent D（代码审查员）
```

### 3.2 基础示例

```python
from autogen import AssistantAgent, UserProxyAgent, GroupChat, GroupChatManager

# 定义 Agent
assistant = AssistantAgent(
    name="Assistant",
    llm_config={"model": "gpt-4o"},
    system_message="你是一个 AI 助手，可以回答问题并调用工具",
)

user_proxy = UserProxyAgent(
    name="UserProxy",
    human_input_mode="NEVER",
    code_execution_config={"work_dir": "coding"},
)

coder = AssistantAgent(
    name="Coder",
    llm_config={"model": "gpt-4o"},
    system_message="你是一个 Python 程序员，负责编写代码",
)

reviewer = AssistantAgent(
    name="Reviewer",
    llm_config={"model": "gpt-4o"},
    system_message="你是一个代码审查员，负责检查代码质量",
)

# 群组对话
groupchat = GroupChat(
    agents=[user_proxy, assistant, coder, reviewer],
    messages=[],
    max_round=10,
)

manager = GroupChatManager(groupchat=groupchat)

# 发起对话
result = user_proxy.initiate_chat(
    manager,
    message="帮我写一个 Python 爬虫，抓取百度首页的标题",
)
```

### 3.3 AutoGen 的特点

| 特性 | 说明 |
|------|------|
| 对话驱动 | Agent 通过消息通信 |
| 灵活拓扑 | 一对一、一对多、群组 |
| 代码执行 | 内置代码执行沙箱 |
| 人类介入 | 支持人类在 loop 中 |
| 可扩展 | 自定义 Agent 类型 |

### 3.4 适用场景

```
✅ 需要多 Agent 讨论的任务
✅ 代码生成和执行
✅ 需要人类介入的任务
✅ 研究性任务

❌ 简单问答
❌ 需要严格流程控制的任务
```

---

## 四、框架对比

### 4.1 核心差异

| 维度 | LangGraph | CrewAI | AutoGen |
|------|-----------|--------|---------|
| 范式 | 状态机 | 团队协作 | 对话 |
| 核心概念 | 节点、边、状态 | Agent、任务、Crew | Agent、对话 |
| 流程控制 | 精确（图） | 明确（顺序/分层） | 灵活（自由对话） |
| 多 Agent | 支持 | 核心功能 | 核心功能 |
| 学习曲线 | 中等 | 低 | 中等 |
| 调试能力 | 优秀 | 良好 | 一般 |
| 生产就绪 | 是 | 是 | 部分 |

### 4.2 选型建议

```
你的场景：
├─ 需要精确控制流程 → LangGraph
├─ 需要多角色协作 → CrewAI
├─ 需要自由对话讨论 → AutoGen
└─ 不确定 → 从 LangGraph 开始（最通用）
```

### 4.3 框架之外的选择

不是所有场景都需要框架：

```python
# 简单场景：自己写循环就够了
class SimpleAgent:
    def run(self, task):
        while True:
            response = llm(task)
            if tool_call := extract_tool(response):
                result = execute(tool_call)
                task = inject_result(task, result)
            else:
                return response
```

---

## 五、2026 年框架趋势

### 5.1 框架收敛

2026 年，Agent 框架正在趋同：

- 都支持多 Agent
- 都支持工具调用
- 都支持状态管理
- 都支持监控和调试

### 5.2 轻量化

框架变得更轻量：

- 不再需要"全栈"框架
- 可以只选择需要的部分
- 模块化设计

### 5.3 框架与协议

MCP 协议让框架之间可以互操作：

```
LangGraph Agent → MCP 工具 → CrewAI Agent
AutoGen Agent → MCP 工具 → LangGraph Agent
```

---

## 总结

| 框架 | 核心模式 | 适合场景 |
|------|---------|---------|
| LangGraph | 状态机 | 复杂工作流，精确控制 |
| CrewAI | 团队协作 | 多角色分工，流水线 |
| AutoGen | 多 Agent 对话 | 自由讨论，协作探索 |
| 自己写循环 | - | 简单场景，快速原型 |

**框架解决的是"如何组织 Agent"的问题，不是"Agent 能做什么"的问题。**

下一篇文章，我们将深入**Agent Loop 的工程实现**——循环结构、错误处理、重试策略、超时控制。

---

**思考题**：
1. 你现在的 Agent 用了框架吗？如果没用，什么场景下你会考虑用框架？
2. LangGraph 的状态机和 AutoGen 的对话模式，你觉得哪个更接近人类的协作方式？
3. 如果 CrewAI 的"角色定义"和 LangGraph 的"状态机"结合，会是什么样子？

---

> 上一篇：[25] Function Calling 与 Tool Use
> 下一篇：[27] Agent Loop 的工程实现
> 系列目录：[README.md](./README.md)