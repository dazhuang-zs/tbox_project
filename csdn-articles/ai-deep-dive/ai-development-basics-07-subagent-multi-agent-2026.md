# AI 开发基础（第7篇）：Subagent 与 Multi-Agent - 分而治之，多智能体协作

> **适合读者**：已读完第6篇（Memory），想了解多Agent架构和协作模式  
> **预计阅读时间**：35分钟

---

## 前言：一个Agent能做多少事？

一个Agent装了20个工具，处理各种任务。但随着任务变复杂，单个Agent会遇到瓶颈：

1. **上下文爆炸**：工具多了，system prompt巨长，LLM容易选错工具
2. **角色冲突**：代码审查需要严格，创意写作需要放松，一个Agent没法同时"严格"又"放松"
3. **专家 vs 通才**：一个通才什么都会一点，但不如专家在特定领域做得好

**解决思路**：拆分成多个专业Agent，各司其职，协作完成。

---

## 一、Subagent：分而治之

### 1.1 什么是Subagent？

**Subagent = 主Agent的"小弟"。** 主Agent负责理解意图、分配任务，Subagent负责执行具体任务。

```
用户 → 主Agent → 判断需要搜索 → 调用搜索Subagent
                  → 判断需要写代码 → 调用代码Subagent
                  → 判断需要翻译 → 调用翻译Subagent
                  → 整合所有结果 → 回复用户
```

**和Tool Use的区别**：

| | Tool Use | Subagent |
|--|---------|----------|
| **能力** | 单个函数调用 | 完整的Agent能力（有LLM、有循环、有工具） |
| **复杂度** | 简单操作（查天气、搜POI） | 复杂任务（写代码、分析文档、多步推理） |
| **自主性** | 主Agent决定参数 | Subagent自己决定怎么做 |

### 1.2 代码实现

```python
import asyncio

class Subagent:
    """Subagent基类"""
    
    def __init__(self, name: str, system_prompt: str, tools: list = None):
        self.name = name
        self.system_prompt = system_prompt
        self.tools = tools or []
        self.tool_map = {}
    
    async def run(self, task: str, max_rounds: int = 5) -> str:
        """执行任务"""
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": task},
        ]
        
        for _ in range(max_rounds):
            response = await async_llm_call(messages, self.tools)
            choice = response.choices[0]
            
            if choice.finish_reason == "stop":
                return choice.message.content
            
            # 处理工具调用...
        
        return "任务未完成（达到最大轮次）"


class RouterAgent:
    """主Agent：负责理解意图和分配任务"""
    
    def __init__(self):
        self.subagents = {}
    
    def register(self, subagent: Subagent):
        """注册Subagent"""
        self.subagents[subagent.name] = subagent
    
    async def handle(self, user_input: str) -> str:
        """处理用户输入"""
        # 第1步：分析意图，决定交给哪个Subagent
        agent_names = list(self.subagents.keys())
        
        routing_prompt = f"""分析用户需求，选择最合适的Agent处理。
可选Agent: {agent_names}
只输出Agent名称，不要其他内容。

用户需求：{user_input}"""

        choice = await async_llm_call(
            [{"role": "user", "content": routing_prompt}]
        )
        target_agent = choice.choices[0].message.content.strip()
        
        # 第2步：如果需要多个Agent，逐个调用
        # （简化版：只选一个Agent）
        if target_agent in self.subagents:
            result = await self.subagents[target_agent].run(user_input)
            return result
        else:
            # 兜底：用默认方式处理
            return await self.subagents["general"].run(user_input)


# 注册Subagent
router = RouterAgent()
router.register(Subagent(
    name="coder",
    system_prompt="你是一个代码专家。用户给你需求，你写出高质量的Python代码。代码必须可运行。",
    tools=[search_docs_tool, run_code_tool],
))
router.register(Subagent(
    name="researcher",
    system_prompt="你是一个研究助手。用户给你问题，你搜索资料并给出详细分析。",
    tools=[search_web_tool, search_paper_tool],
))
router.register(Subagent(
    name="writer",
    system_prompt="你是一个写作专家。用户给你主题，你写出高质量的技术文章。",
    tools=[search_ref_tool, check_grammar_tool],
))
router.register(Subagent(
    name="general",
    system_prompt="你是一个通用助手。处理其他Agent不适合的任务。",
))

# 使用
result = await router.handle("帮我写一个快速排序的Python实现")
```

### 1.3 Subagent的实际效果

**对比单Agent vs Subagent**：

| 指标 | 单Agent（20个工具） | Subagent（4个专业Agent） |
|------|-------------------|----------------------|
| 工具选择准确率 | ~75% | ~95% |
| 平均完成轮次 | 4.2轮 | 2.8轮 |
| Token消耗 | 高（system prompt长） | 低（每个Agent prompt短） |
| 维护难度 | 高（改一个工具影响全局） | 低（改一个Agent不影响其他） |

---

## 二、Multi-Agent：多智能体协作

### 2.1 三种协作模式

| 模式 | 说明 | 类比 |
|------|------|------|
| **流水线式** | A做完交给B，B做完交给C | 工厂流水线 |
| **并行式** | A、B、C同时做，最后合并 | 多人同时查资料 |
| **讨论式** | A提出方案，B审查，C补充，反复讨论 | 团队会议 |

### 2.2 流水线式：写作Agent

```
用户："写一篇关于FastAPI的文章"

[研究Agent] → 收集资料、确定大纲
    ↓
[写作Agent] → 根据大纲写初稿
    ↓
[审查Agent] → 检查错误、给出评分和修改建议
    ↓
[修改Agent] → 根据审查意见修改
    ↓
输出最终文章
```

```python
async def pipeline_write(topic: str) -> str:
    """流水线式写作"""
    
    # 第1步：研究（确定大纲）
    outline = await researcher.run(f"研究'{topic}'，输出一个详细的文章大纲")
    
    # 第2步：写作（根据大纲写初稿）
    draft = await writer.run(f"根据以下大纲写一篇技术文章：\n{outline}")
    
    # 第3步：审查（代码检查、事实核查）
    review = await reviewer.run(f"审查以下文章，给出评分（1-10）和具体修改建议：\n{draft}")
    
    # 第4步：修改
    final = await writer.run(f"根据以下审查意见修改文章：\n审查意见：{review}\n原文：{draft}")
    
    return final
```

### 2.3 并行式：多维度分析

```python
async def parallel_analyze(question: str) -> str:
    """并行式分析"""
    
    tasks = [
        code_expert.run(f"从技术角度分析：{question}"),
        product_expert.run(f"从产品角度分析：{question}"),
        business_expert.run(f"从商业角度分析：{question}"),
    ]
    
    results = await asyncio.gather(*tasks)
    
    # 合并结果
    summary_prompt = f"""综合以下三个专家的分析，给出最终结论：

技术专家：{results[0]}
产品专家：{results[1]}
商业专家：{results[2]}"""
    
    final = await general_agent.run(summary_prompt)
    return final
```

### 2.4 讨论式：代码审查

```python
async def debate_review(code: str, max_rounds: int = 3) -> str:
    """讨论式代码审查"""
    
    reviewer_agent = Subagent("reviewer", "你是一个严格的代码审查员。找出所有问题。")
    developer_agent = Subagent("developer", "你是一个开发者。回应审查意见，解释或修复。")
    
    current_state = code
    
    for round_num in range(max_rounds):
        # 审查员审查
        review = await reviewer_agent.run(f"审查以下代码（第{round_num+1}轮）：\n{current_state}")
        
        # 检查是否通过
        if "通过" in review or "没有问题" in review:
            return f"审查通过（{round_num+1}轮）\n代码：{current_state}"
        
        # 开发者回应
        response = await developer_agent.run(f"审查意见：{review}\n\n请回应并修复代码：\n{current_state}")
        current_state = response
        
        print(f"第{round_num+1}轮审查完成")
    
    return f"审查未通过（{max_rounds}轮后仍有问题）\n最终代码：{current_state}"
```

---

## 三、用LangGraph实现Multi-Agent

### 3.1 状态图定义

LangGraph用"图"来定义Agent之间的协作关系。

```python
from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated
import operator


class AgentState(TypedDict):
    """共享状态"""
    messages: Annotated[list, operator.add]  # 消息累积
    task: str                                # 原始任务
    research_result: str                     # 研究结果
    draft: str                               # 初稿
    review_result: str                       # 审查结果
    final_output: str                        # 最终输出
    round_num: int                           # 当前轮次


def researcher_node(state: AgentState) -> AgentState:
    """研究节点"""
    research = llm.invoke(f"研究任务：{state['task']}，输出要点")
    return {"research_result": research.content}


def writer_node(state: AgentState) -> AgentState:
    """写作节点"""
    draft = llm.invoke(f"根据研究要点写文章：\n{state['research_result']}")
    return {"draft": draft.content}


def reviewer_node(state: AgentState) -> AgentState:
    """审查节点"""
    review = llm.invoke(f"审查文章：\n{state['draft']}\n\n给出评分和修改建议")
    return {"review_result": review.content}


def should_revise(state: AgentState) -> str:
    """条件判断：是否需要修改"""
    round_num = state.get("round_num", 0) + 1
    
    if round_num >= 3:  # 最多3轮
        return "finalize"
    
    review = state["review_result"]
    if "通过" in review or "10" in review:
        return "finalize"
    
    return "revise"


def revise_node(state: AgentState) -> AgentState:
    """修改节点"""
    revised = llm.invoke(
        f"根据审查意见修改文章：\n审查：{state['review_result']}\n原文：{state['draft']}"
    )
    return {"draft": revised.content, "round_num": state.get("round_num", 0) + 1}


# 构建图
graph = StateGraph(AgentState)

graph.add_node("research", researcher_node)
graph.add_node("write", writer_node)
graph.add_node("review", reviewer_node)
graph.add_node("revise", revise_node)
graph.add_node("finalize", lambda s: {"final_output": s["draft"]})

graph.add_edge("research", "write")
graph.add_edge("write", "review")
graph.add_conditional_edges("review", should_revise, {
    "revise": "revise",
    "finalize": "finalize",
})
graph.add_edge("revise", "review")
graph.add_edge("finalize", END)

graph.set_entry_point("research")

# 执行
app = graph.compile()
result = app.invoke({"task": "写一篇关于FastAPI性能优化的文章"})
print(result["final_output"])
```

### 3.2 图结构可视化

```
research → write → review → [条件判断]
                              ├─ 通过 → finalize → END
                              └─ 不通过 → revise → review（循环）
```

---

## 四、真实项目经验

### 4.1 CSDN文章生产流水线

我在实际项目中用Multi-Agent生产CSDN文章：

```
[选题Agent] → 分析热点，推荐选题
    ↓
[搜索Agent] → 收集资料、竞品文章
    ↓
[写作Agent] → 写初稿
    ↓
[审查Agent] → 检查代码、数据来源、原创性
    ↓
[修改Agent] → 修复问题
    ↓
输出文章
```

**踩坑**：
1. 审查Agent太严格，反复修改5-6轮才通过。后来加了max_rounds=3的硬限制
2. 写作Agent的风格和审查Agent的标准不一致（一个宽松一个严格）。后来统一了system prompt中的质量标准
3. 并行Agent之间的消息传递格式不统一。后来用TypedDict定义了标准状态

### 4.2 什么时候该用Multi-Agent？

| 场景 | 推荐 |
|------|------|
| 1-3个工具、简单逻辑 | 单Agent |
| 4-10个工具、有分工 | Subagent |
| 需要多角色协作（写+审+改） | Multi-Agent |
| 生产环境、需要可观测性 | Multi-Agent + LangGraph |
| 原型验证 | 单Agent先跑通，再拆分 |

**经验法则**：先用单Agent跑通，发现瓶颈后再拆分。过早拆分会增加复杂度。

---

## 五、本章总结

**你学到了什么**：

1. **Subagent**：主Agent分配任务，专业Subagent执行。比单Agent工具选择更准确、更省Token
2. **三种协作模式**：流水线（串行）、并行（同时）、讨论（反复迭代）
3. **LangGraph**：用状态图定义Agent之间的协作关系，支持条件分支和循环
4. **渐进式架构**：先单Agent → 发现瓶颈 → 拆Subagent → 复杂场景用Multi-Agent

**关键公式**：
```
Subagent = 主Agent(理解+分配) + 专业Agent(执行)
流水线 = A → B → C → ...
讨论式 = A → B → A → B → ... (直到收敛)
渐进式 = 单Agent → Subagent → Multi-Agent
```

**下一篇预告**：
- 第8篇：Prompt Engineering 与 Context Engineering - 与模型沟通的艺术

---

## 参考资料

1. Multi-Agent综述论文：https://arxiv.org/abs/2408.08922
2. LangGraph文档：https://langchain-ai.github.io/langgraph/
3. CrewAI文档：https://docs.crewai.com/
4. AutoGen：https://microsoft.github.io/autogen/

---

**上一篇**：第6篇 Memory  
**下一篇**：第8篇 Prompt Engineering 与 Context Engineering
