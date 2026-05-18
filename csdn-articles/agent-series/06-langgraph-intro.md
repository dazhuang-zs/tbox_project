# LangGraph 入门：用状态图构建 Agent

> 手写 ReAct 循环容易写出 bug。LangGraph 用「状态图」的方式定义 Agent，把每一步定义为一个节点，跳转逻辑定义为边——清晰、可测试、可扩展。

---

## 一、为什么需要 LangGraph

手写 Agent 循环的痛点：

```python
# 手写版：容易出 bug，难扩展
while step < max_steps:
    response = llm.chat(messages)
    if "Final Answer" in response:
        break
    elif tool_call:
        result = execute(tool_call)
        messages.append(result)
    elif need_retry:
        # 嗯...重试逻辑写哪？
    # 越写越乱
```

LangGraph 换了个思路：**Agent 就是一个状态图（State Graph）**。每个「做什么」是一个节点，每个「下一步去哪」是一条边。

---

## 二、核心概念

```
┌──────────────────────────────────────┐
│             LangGraph 四要素           │
├──────────────────────────────────────┤
│  State（状态）  Agent 当前记住的所有信息 │
│  Node（节点）   做什么（调用 LLM、执行工具）│
│  Edge（边）     做完之后去哪            │
│  Graph（图）    节点 + 边的集合          │
└──────────────────────────────────────┘
```

---

## 三、第一个 LangGraph Agent

```python
# pip install langgraph langchain-openai

from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI

# ── 1. 定义状态 ──
class AgentState(TypedDict):
    messages: list[dict]  # 对话历史
    next_step: str        # 下一步去哪

# ── 2. 初始化 LLM ──
llm = ChatOpenAI(
    model="deepseek-chat",
    api_key="your-key",
    base_url="https://api.deepseek.com/v1"
)

# ── 3. 定义节点函数 ──
def chatbot(state: AgentState) -> AgentState:
    """LLM 节点：调用大模型"""
    response = llm.invoke(state["messages"])
    state["messages"].append(response)
    state["next_step"] = "check_tools"  # 下一步去检查是否需要工具
    return state


def check_tools(state: AgentState) -> AgentState:
    """工具路由：判断是否需要调工具"""
    last_msg = state["messages"][-1]
    if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
        state["next_step"] = "execute_tools"
    else:
        state["next_step"] = "end"
    return state


def execute_tools(state: AgentState) -> AgentState:
    """工具执行节点"""
    # 简化的工具执行逻辑
    last_msg = state["messages"][-1]
    for tool_call in last_msg.tool_calls:
        result = f"工具 {tool_call['name']} 执行结果"
        state["messages"].append({"role": "tool", "content": result})
    state["next_step"] = "chatbot"  # 回到 LLM 继续
    return state


# ── 4. 构建图 ──
def build_graph():
    graph = StateGraph(AgentState)

    # 添加节点
    graph.add_node("chatbot", chatbot)
    graph.add_node("check_tools", check_tools)
    graph.add_node("execute_tools", execute_tools)

    # 添加边
    graph.add_edge("chatbot", "check_tools")

    # 条件边：根据 next_step 决定去向
    graph.add_conditional_edges(
        "check_tools",
        lambda state: state["next_step"],
        {
            "execute_tools": "execute_tools",
            "end": END
        }
    )

    graph.add_edge("execute_tools", "chatbot")  # 返回 LLM
    graph.set_entry_point("chatbot")  # 入口

    return graph.compile()


# ── 5. 运行 ──
agent = build_graph()
result = agent.invoke({
    "messages": [{"role": "user", "content": "你好"}],
    "next_step": "chatbot"
})
print(result["messages"][-1].content)
```

**执行流程可视化**：

```
       ┌──────────┐
       │ chatbot  │ ← 入口：调用 LLM
       └────┬─────┘
            │
       ┌────▼─────┐
       │check_tools│ ← 判断：需要工具吗？
       └────┬─────┘
        ┌───┴───┐
        ▼       ▼
    execute    END
    _tools      │
        │       │
        └───→───┘
        （回到 chatbot）
```

---

## 四、完整实战：代码审查 Agent

```python
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

class CodeReviewState(TypedDict):
    code: str
    review_result: str
    fixed_code: str
    test_result: str
    step: str

def review_code(state: CodeReviewState) -> CodeReviewState:
    """节点 1：审查代码"""
    prompt = f"审查以下代码，指出问题和改进建议：\n```\n{state['code']}\n```"
    response = llm.invoke([{"role": "user", "content": prompt}])
    state["review_result"] = response.content
    state["step"] = "fix" if "问题" in response.content else "pass"
    return state

def fix_code(state: CodeReviewState) -> CodeReviewState:
    """节点 2：修复问题"""
    prompt = f"""
    原始代码：
    ```
    {state['code']}
    ```
    审查意见：
    {state['review_result']}
    
    请修复所有问题，只输出修复后的代码。
    """
    response = llm.invoke([{"role": "user", "content": prompt}])
    state["fixed_code"] = response.content
    state["step"] = "test"
    return state

def run_tests(state: CodeReviewState) -> CodeReviewState:
    """节点 3：运行测试验证"""
    # 实际项目中会真的执行测试
    prompt = f"检查以下代码是否有明显的语法或逻辑错误：\n```\n{state['fixed_code']}\n```"
    response = llm.invoke([{"role": "user", "content": prompt}])
    state["test_result"] = response.content
    state["step"] = "done"
    return state

# 构建审查工作流
def build_review_graph():
    graph = StateGraph(CodeReviewState)

    graph.add_node("review", review_code)
    graph.add_node("fix", fix_code)
    graph.add_node("test", run_tests)

    graph.set_entry_point("review")

    # 条件路由
    graph.add_conditional_edges(
        "review",
        lambda s: s["step"],
        {"fix": "fix", "pass": END}
    )

    graph.add_edge("fix", "test")
    graph.add_edge("test", END)

    return graph.compile()

# 运行
review_agent = build_review_graph()
result = review_agent.invoke({
    "code": "def add(a,b):\n return a+b\n\nprint(add('1','2'))",
    "review_result": "",
    "fixed_code": "",
    "test_result": "",
    "step": "review"
})

print(f"审查结果：{result['review_result']}")
print(f"修复代码：\n{result['fixed_code']}")
```

---

## 五、LangGraph vs 手写循环

| 维度 | 手写 while 循环 | LangGraph |
|------|:--:|:--:|
| 逻辑清晰度 | ❌ 嵌套深了容易乱 | ✅ 状态图一目了然 |
| 可测试性 | ❌ 整个循环是一个函数 | ✅ 每个节点独立测试 |
| 可扩展性 | ❌ 加新逻辑要改主循环 | ✅ 加新节点 + 新边 |
| 调试 | ❌ print 大法 | ✅ 每个节点状态可见 |
| 持久化 | ❌ 自己实现 | ✅ MemorySaver 开箱即用 |
| 学习成本 | ✅ 不需要学框架 | ❌ 需要学新概念 |

---

## 六、总结

1. **LangGraph 是构建 Agent 的工业级方案**——告别手写循环
2. **核心是「状态图」**——节点 = 做什么，边 = 去哪
3. **条件边实现路由**——根据不同状态走不同分支
4. **每个节点独立可测试**——符合软件工程最佳实践

---

> 下一篇：**《MCP 协议实战：给 AI 接上外部世界》**——写一个 MCP Server，让 Claude Desktop、Cursor 都能调用你的工具。

*系列文章：00-总纲 → ①-LLM 原理 → ②-Prompt 工程 → ③-Function Calling → ④-RAG → ⑤-Agent 模式 → ⑥-LangGraph → ⑦-MCP → ⑧-Multi-Agent*
