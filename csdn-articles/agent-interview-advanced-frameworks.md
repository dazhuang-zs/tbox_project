# 【AI Agent面试进阶篇】30道框架深入与多智能体系统高频题（双视角答案版）

> 覆盖 Agent 框架选型、规划算法、Multi-Agent 编排、A2A/MCP 协议、工具链设计等 6 大进阶模块。每道题提供「有工作经验」和「背面经」两个视角。
> 题目来源：字节跳动 Agent 平台组、阿里 Tongyi Agent、蚂蚁集团 AgentInfra、MiniMax、智谱 GLM-Agent、月之暗面等团队 2025-2026 真实面试。

---

## 目录

1. [Agent 框架深入对比（5题）](#1-agent-框架深入对比)
2. [Agent 规划与推理算法（6题）](#2-agent-规划与推理算法)
3. [工具链设计与优化（5题）](#3-工具链设计与优化)
4. [Multi-Agent 系统深入（6题）](#4-multi-agent-系统深入)
5. [A2A 与 MCP 协议深入（5题）](#5-a2a-与-mcp-协议深入)
6. [Agent 推理优化（3题）](#6-agent-推理优化)
7. [面试准备建议](#-面试准备建议)

---

## 1. Agent 框架深入对比

### Q1：LangGraph、AutoGen、CrewAI 三个框架的核心设计哲学有什么不同？各自适合什么场景？

> 🏢 高频来源：字节跳动 Agent 平台组、蚂蚁 AgentInfra、商汤

**🧠 有工作经验视角：**

我在实际项目中三种都用过，它们的设计哲学决定了各自的适用边界：

**LangGraph：状态机思维**

LangGraph 的核心是 `StateGraph`——把 Agent 的行为建模成有状态的有向图。每个节点是一个处理步骤，每条边定义了状态转移条件。这和你画流程图的感觉一样。

举个例子，做数据清洗 Pipeline：清洗节点 → 状态=clean → 校验节点 → 校验通过 → 输出节点；校验失败 → 回到清洗节点。这个循环用 LangGraph 的 `add_conditional_edges` 天然表达。

LangGraph 的强项是**精确控制执行流**。但代价是写起来代码量大——一个中等复杂度的 Agent 可能要 300+ 行图定义。

**AutoGen：对话即编排**

AutoGen（微软）的核心抽象是 `ConversableAgent`——每个 Agent 是一个能「对话」的实体。多个 Agent 通过消息传递完成协作。

它的设计哲学是「对话就是一切」。两个 Agent 之间的交互就是一轮对话。这个模型非常适合需要讨论、辩论、审查的场景——比如 Code Review Agent 给 Code Writer Agent 提修改意见。

但问题也在这里：如果需求是严格的状态流转（先查库→再调 API→再通知用户），用「对话」来建模就显得别扭，不如 LangGraph 直观。

**CrewAI：角色扮演**

CrewAI 的核心是「角色（Role）+ 任务（Task）+ 流程（Process）」。你给每个 Agent 定义一个角色描述，它自己决定怎么完成任务。

它的优势是**概念最接近人类直觉**——PM Agent、开发 Agent、测试 Agent，各干各的。非技术人员也能理解在干什么。

但它的可控性最差——Agent 在角色框架内的行为自由度太大，生产环境出问题时很难定位「为什么 Agent 做了这个决定」。

**选型决策表：**

| 场景 | 推荐框架 | 原因 |
|------|---------|------|
| 需要精确控制执行流程 | LangGraph | 状态图天然表达分支和循环 |
| 需要多 Agent 讨论和辩论 | AutoGen | 对话模型最适合协商 |
| 快速原型，非技术人员参与 | CrewAI | 角色概念直观 |
| 生产级高可靠 | LangGraph 或手写 | 可控性 > 开发效率 |
| 低代码/零代码场景 | Dify/Coze | 拖拽式，非开发人员能用 |

**📝 背面经视角：**

| 维度 | LangGraph | AutoGen | CrewAI |
|------|-----------|---------|--------|
| 核心抽象 | StateGraph（有向状态图） | ConversableAgent（对话实体） | Role + Task + Process |
| 编排方式 | 显式图定义 | 消息传递 | 角色分配 |
| 可控性 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ |
| 开发效率 | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| 生产就绪度 | 高 | 中 | 低-中 |
| 适合场景 | 复杂工作流 | 协作讨论 | 快速原型 |
| 出品方 | LangChain | 微软 | CrewAI Inc |

关键区别：LangGraph 是「你告诉 Agent 每一步怎么做」，AutoGen 是「Agent 们自己商量着办」，CrewAI 是「Agent 各司其职」。

---

### Q2：Dify 和 Coze 这类低代码 Agent 平台适合生产环境吗？你怎么看低代码 Agent 的趋势？

> 🏢 高频来源：字节跳动 Coze 团队、蚂蚁集团、百度智能云

**🧠 有工作经验视角：**

说实话，我对低代码 Agent 平台的态度比较复杂。

**它们确实解决了真问题：**
- 非技术人员（产品、运营）能自己搭 Agent，不用等工程排期
- 可视化调试——你能看到每一步的输入输出，比翻代码日志直观 10 倍
- 模板生态——别人搭好的 Agent 你改改就能用

**但在生产环境有硬伤：**
- 平台锁定：Dify 的 DSL 和 Coze 的 Bot 定义互相不兼容，迁移成本极高
- 性能天花板：复杂工作流在低代码平台跑，RT（响应时间）通常比手写慢 30-50%
- 调试地狱：当 Agent 行为不符合预期时，你只能看平台给的有限日志，不能打断点
- 成本不可控：Coze 的扣费逻辑对复杂 Agent 不透明，月账单出来才知道花了多少

**我的建议：**
- 内部工具、Demo、POC → 用低代码，快
- 面向外部用户、对延迟敏感、需要精细控制 → 手写
- 混合策略：用低代码做原型，确认可行后用代码重写生产版

**📝 背面经视角：**

Dify 和 Coze 的核心差异：

| 维度 | Dify | Coze（字节） |
|------|------|-------------|
| 定位 | 开源 LLMOps 平台 | 商业 Agent 开发平台 |
| 部署 | 私有化部署/云 | 纯云（字节生态） |
| 工作流 | 可视化拖拽 | 可视化 + Bot 模板 |
| 插件生态 | 社区驱动 | 官方精选 + 字节系 |
| 定价 | 开源免费/企业版 | 按 token + 调用次数 |
| 国内适配 | 需自行部署 | 原生国内优化 |

两者共同的局限：复杂条件分支的可视化维护性差，Agent 行为黑盒度高。

---

### Q3：从 LangChain Agent 迁移到 LangGraph，最大的思维转变是什么？

> 🏢 高频来源：蚂蚁集团、MiniMax、字节跳动

**🧠 有工作经验视角：**

我去年亲自把一个 15 个 tool 的客服 Agent 从 LangChain 的 `AgentExecutor` 迁移到了 LangGraph。最大的思维转变是：

**从「黑盒循环」到「显式流程」。**

LangChain 的 AgentExecutor 是这样的：
```python
agent = create_openai_tools_agent(llm, tools, prompt)
executor = AgentExecutor(agent=agent, tools=tools)
result = executor.invoke({"input": "帮我退款"})
# 内部发生了什么？不知道。重试了几次？不知道。哪个 tool 被调了几次？不知道。
```

整个 Think-Act-Observe 循环被 `AgentExecutor` 封装死了。出问题时你只能靠猜。

LangGraph 的等价实现：
```python
def should_continue(state):
    if state["agent_outcome"].return_values.get("tool_calls"):
        return "action"
    return "end"

workflow = StateGraph(AgentState)
workflow.add_node("agent", call_model)
workflow.add_node("action", call_tool)
workflow.add_conditional_edges("agent", should_continue, {
    "action": "action",
    "end": END
})
workflow.add_edge("action", "agent")
```

每一步都在你的控制之下。你可以：
- 在 `call_model` 和 `call_tool` 之间插入任意逻辑（认证检查、内容审核、日志记录）
- 自定义重试策略（tool 超时不一定要重新调 LLM，可以只重试 tool）
- 添加人工审批节点（`"human_approval"` 状态，等待外部信号）

迁移后最直接的收益：线上故障定位时间从 30 分钟降到了 5 分钟。因为你知道每一步在哪断了。

**📝 背面经视角：**

| LangChain AgentExecutor | LangGraph StateGraph |
|-------------------------|---------------------|
| 黑盒封装 | 显式状态机 |
| Think-Act-Observe 不可见 | 每个节点可插拔 |
| 重试逻辑不可定制 | 完全可定制 |
| 适合 Demo | 适合生产 |
| 学习曲线平 | 学习曲线陡 |

核心转变：从「相信框架的默认行为」到「承担每一步的控制责任」。

---

### Q4：轻量级 Agent 框架（如 OpenAI Swarm、Anthropic Tool Use）和重量级框架（LangGraph、AutoGen）的边界在哪？什么时候不需要用框架？

> 🏢 高频来源：MiniMax、月之暗面、智谱 AI

**🧠 有工作经验视角：**

这个问题其实是在问「你的 Agent 复杂度在哪条线上」。

我做了一个简单的判断模型：

```
Agent 需要几个 tool？
  ├─ 1-3 个 tool，单轮调用 → 不需要框架，直接用 LLM SDK 的 function calling
  ├─ 3-10 个 tool，多轮循环 → OpenAI Swarm / Anthropic SDK 够用
  └─ 10+ 个 tool，有状态流转、人工审批 → 上 LangGraph / 手写
```

去年我犯的最大错误是：一个只有 2 个 tool 的简单 Agent（搜索 + 摘要），硬上了 LangChain。引入了几百 KB 依赖，就为了实现一个——如果 LLM 返回 tool_calls 就调 tool，否则返回结果——10 行的 while 循环。

**什么时候不需要框架：**
- Tool 数量 < 5
- 没有复杂的状态流转（比如不需要「调完 tool A → 根据结果决定走 tool B 还是 tool C」）
- 不需要多 Agent 协作
- 不需要人工审批节点

这些场景下，直接用 OpenAI/Anthropic SDK 的原生 function calling + 一个简单的 while 循环，代码不超过 100 行。

**📝 背面经视角：**

框架选型决策树：

```
你的 Agent 复杂度？
├─ 简单（单轮 tool call）
│   └─ 直接用 LLM API function calling
├─ 中等（多轮循环，<10 tools）
│   ├─ OpenAI 生态 → Swarm
│   └─ Anthropic 生态 → Claude Tool Use
└─ 复杂（状态流转、多 Agent、人工审批）
    ├─ 需要精确控制 → LangGraph
    ├─ 需要 Agent 讨论 → AutoGen
    └─ 需要快速原型 → CrewAI / Dify
```

核心原则：**框架的复杂度不应该超过问题的复杂度**。

---

### Q5：你怎么评估一个新出的 Agent 框架是否值得在生产环境采用？

> 🏢 高频来源：蚂蚁 AgentInfra、字节跳动基础架构

**🧠 有工作经验视角：**

我有一套「生产就绪度检查清单」，用了两年多了：

**硬指标：**
1. **可观测性**：能不能接入 OpenTelemetry？有没有原生 tracing？没有 → -30 分
2. **错误处理可定制**：tool 超时、LLM 返回格式错误时，我能不能自己写处理逻辑？不能 → -20 分
3. **并发模型**：支持异步吗？多个 tool 能并行调吗？不支持 → -15 分
4. **流式输出**：SSE 还是 WebSocket？中间步骤能推到前端吗？不支持 → -10 分
5. **版本稳定性**：最近半年有 breaking change 吗？有 → -25 分

**软指标：**
- 社区活跃度：GitHub issue 平均多久有人回？
- 文档质量：有 troubleshooting guide 吗？还是只有 happy path？
- 抽象泄漏度：出了框架预期范围的问题时，你能绕过框架直接改吗？

这其实是从 LangChain 的坑里学来的——0.1 → 0.2 的 breaking change 迁移成本够我再写三个 Agent。

**📝 背面经视角：**

生产选型六维评估模型：

| 维度 | 关键问题 | 权重 |
|------|---------|:---:|
| 可观测性 | 有 tracing/logging/metrics 吗？ | 30% |
| 可控性 | 我能绕过框架处理异常吗？ | 25% |
| 稳定性 | 最近 breaking change 频率？ | 20% |
| 性能 | 框架本身增加多少延迟？ | 15% |
| 生态 | 社区活跃度、文档质量 | 5% |
| 学习成本 | 团队多久能上手？ | 5% |

---

## 2. Agent 规划与推理算法

### Q6：ReAct 之外还有哪些重要的 Agent 推理范式？ToT、GoT、Reflexion 各自的适用场景？

> 🏢 高频来源：智谱 GLM-Agent 团队、MiniMax、字节跳动

**🧠 有工作经验视角：**

ReAct（Reasoning + Acting）是 Agent 推理的 baseline，但它有一个致命问题：**线性思维**——想一步、做一步、看结果、再想一步。遇到需要全局规划或多种方案比较的问题就卡住了。

我实际用过的几种进阶范式：

**Tree-of-Thoughts（ToT）：多路径探索**

核心思想：在每一步推理时，生成多个候选思路，用 BFS/DFS 探索，最终选最佳路径。

适合场景：数学证明、逻辑推理、游戏策略规划（比如 24 点游戏）。不适合：需要大量 tool 调用的实时交互——BFS 意味着每个分支都要调 tool，成本指数级。

**Graph-of-Thoughts（GoT）：灵活图结构**

ToT 的泛化版本。不再是严格的树结构，允许节点之间任意连接、聚合、循环。适合「需要综合多个信息源做决策」的场景。

我在一个合同审查 Agent 中用过类似的思想：法规库搜索结果 + 相似案例检索结果 + 合同条款本身 → 三个信息源各自推理 → 聚合 → 输出审查意见。这本质上是 GoT 的聚合模式。

**Reflexion：自我反思与纠错**

核心思想：Agent 执行任务后，对自己的输出进行「反思」——哪里做得好、哪里做错了、下次怎么改进。反思结果存入长期记忆，影响后续行为。

适合场景：代码生成（写 → 跑 → 看报错 → 反思 → 改）、需要多轮试错的复杂任务。

生产环境的实际问题：Reflexion 的反思环节多调一次 LLM，成本 +50%，但代码生成的准确率提升显著（SWE-bench 上约 +15%）。

**选型速查：**

| 范式 | 核心机制 | 适合场景 | 代价 |
|------|---------|---------|------|
| ReAct | 想→做→看→循环 | 90% 日常任务 | 基准 |
| ToT | 多分支探索+BFS/DFS | 数学/逻辑推理 | LLM 调用 x N |
| GoT | 图结构+聚合+回溯 | 多源信息融合决策 | 复杂度高 |
| Reflexion | 执行→反思→记忆 | 代码生成、试错型任务 | +50% token |
| Plan-Execute | 先全局规划再逐步执行 | 多步骤复杂任务 | 延迟敏感 |

**📝 背面经视角：**

ToT（Yao et al., 2023）将推理建模为树搜索，GoT（Besta et al., 2024）泛化为图结构。Reflexion（Shinn et al., 2023）引入 verbal reinforcement learning——用自然语言做反思而非数值奖励。核心区别是推理的拓扑结构：线性（ReAct）→ 树（ToT）→ 图（GoT）。

---

### Q7：为什么大多数 Agent 框架默认用 ReAct 而不是更高级的规划算法？

> 🏢 高频来源：字节跳动、蚂蚁集团

**🧠 有工作经验视角：**

简单说：因为 90% 的实际任务不需要更复杂的规划。上了复杂算法反而更差。

ReAct 有三个工程优势：

1. **成本可控**：每步 1 次 LLM 调用。ToT 每个分支都是一次调用，一个问题可能调 20+ 次
2. **延迟可预期**：串行执行，用户可以估算「大概几秒」。ToT 的 BFS 执行时间不确定
3. **实现简单**：就是一个 while 循环 + if-else，300 行代码搞定

我在一个客户咨询 Agent 上试过 ToT——用户问「我应该买 A 还是 B」，Agent 对 A 和 B 各生成一系列分析分支，然后组合对比。效果确实好，但平均延迟从 ReAct 的 4 秒变成了 18 秒——用户在第五秒就开始焦虑了。

**📝 背面经视角：**

ReAct 是 Agent 推理的 Pareto 最优解——在效果、成本、延迟、实现复杂度四个维度上取得了最好的平衡。更高级的算法在某些 benchmarks 上效果更好，但在真实产品的约束下（延迟 SLA、成本预算、工程复杂度）往往得不偿失。

---

### Q8：Self-Refine 和 Reflexion 有什么区别？各自怎么实现？

> 🏢 高频来源：月之暗面、智谱 AI

**🧠 有工作经验视角：**

两者都做「自我改进」，但机制不同：

**Self-Refine：单轮内的即时修正**

模型先输出一个答案，然后立刻对自己的答案进行「批评」，再基于批评修改输出。这在一个 LLM 调用轮次内完成（或者 2-3 次）。

实现很简单——prompt 里加一句：「输出你的答案后，请检查是否有错误，然后输出修正后的最终答案。」

我用在代码生成 Agent 上的效果：直接输出的一次通过率约 65%，加 Self-Refine 后 78%。

**Reflexion：跨轮次的持续学习**

Reflexion 的反思不是即时的，而是持久化的——Agent 完成一个完整任务后，生成反思总结，存入长期记忆。下次执行类似任务时，先读取之前的反思。

举个例子：Agent 尝试调一个 API，超时了。Reflexion 机制会记录「这个 API 在高峰时段超时率高，下次加大超时时间或换备选 API」。下次再跑到这个 tool 时，Agent 能看到之前的教训。

**实现要点：**
- Self-Refine：改 prompt，0 工程成本，效果提升有限
- Reflexion：需要 Memory 系统支持，工程成本中等，效果提升显著（尤其是重复性任务）

**📝 背面经视角：**

| 维度 | Self-Refine | Reflexion |
|------|------------|-----------|
| 作用范围 | 单轮内 | 跨轮次 |
| 持久化 | 否 | 是（存 Memory） |
| 实现复杂度 | prompt 改动 | 需 Memory 基础设施 |
| 适用场景 | 提高单次输出质量 | 持续改进同类任务 |
| 代表论文 | Self-Refine (Madaan et al., 2023) | Reflexion (Shinn et al., 2023) |

---

### Q9：Agent 的「过度规划」问题怎么解决？什么时候应该「少想多做」？

> 🏢 高频来源：字节跳动、MiniMax

**🧠 有工作经验视角：**

过度规划是 Agent 开发里最容易被忽视的问题。典型症状：用户问「今天天气怎么样」，Agent 输出了一大段规划：「我需要先获取用户位置，然后调用天气 API，然后处理数据，然后格式化输出...」——用户只是想听一句「晴天，25度」。

**为什么会出现：** 因为你在 System Prompt 里写了「请先制定计划再执行」。LLM 忠实执行了，但它不理解「简单问题不配被规划」。

**解法：**
1. **复杂度判断节点**：在执行规划之前，加一个轻量级判断——这个问题需要规划吗？可以用一个更便宜的模型（比如 Haiku 或 Qwen-Turbo）做这个判断
2. **时间预算**：在 prompt 里明确「如果任务能在 1 步内完成，请直接执行，不要规划」
3. **用户可见规划**：如果一定要规划，至少让用户看到你在规划什么，而不是干等

**📝 背面经视角：**

过度规划是 Agent 效率杀手。典型解法是加入 `complexity_router`——简单问题走 fast path（直接 ReAct），复杂问题走 slow path（Plan-Execute）。实现上可以用一个轻量 classifier 做路由。

---

### Q10：怎么让 Agent 在规划时利用外部知识（文档、API 文档、历史经验）？

> 🏢 高频来源：蚂蚁集团、阿里 Tongyi Agent

**🧠 有工作经验视角：**

这个问题我花了两个月优化。核心挑战：LLM 规划时依赖的是「训练数据中的知识」，但生产环境要对接的 API、内部系统、业务规则在训练数据里没有。

**三层知识注入策略：**

1. **Tool Description 即文档**：每个 tool 的 description 不只是「这是干什么的」，更要写清楚「输入参数约束」「返回值格式」「常见失败模式」。一个 tool description 写得好，相当于内置了 API 文档
2. **RAG 增强规划**：在执行 Planning 阶段，先检索相关知识再规划。比如用户要处理一个订单，先把订单系统的 API 文档、常见处理流程检索出来，塞进 context 再让 LLM 规划
3. **经验库（Experience Buffer）**：每次 Agent 执行完成后，总结成功/失败经验，存入向量库。下次规划类似任务时，检索相关经验作为 context

第三点最有效但也最难维护——经验质量参差不齐，需要定期清理。

**📝 背面经视角：**

Agent 规划的知识增强方案：
- 静态知识：Tool Description、System Prompt 中的业务规则
- 动态知识：RAG 检索的相关文档，注入 Planning 阶段的 context
- 经验知识：从历史执行中提取的 Experience Buffer，用向量检索匹配当前任务

三者优先级：动态 > 经验 > 静态（越新鲜越准确）。

---

### Q11：规划失败时 Agent 怎么优雅地 fallback？

> 🏢 高频来源：字节跳动、蚂蚁集团

**🧠 有工作经验视角：**

规划失败在生产环境是常态，不是异常。常见的失败模式：

- 规划了不存在的工具（LLM 幻觉了 tool 名）
- 规划了逻辑不可行的步骤序列
- 执行到第 3 步发现前两步的假设是错的

**分级 fallback 策略：**

```
Level 1: 重新规划（同一 LLM，加错误信息）
  ↓ 失败
Level 2: 降级规划（换更强大的模型重新规划）
  ↓ 失败  
Level 3: 简化任务（把复杂任务拆成用户可直接执行的子任务，让用户做决策）
  ↓ 失败
Level 4: 人工介入（触发转人工流程，把上下文打包给人工客服）
```

关键设计原则：**不要让用户感知到「AI 失败了」，而是让用户感知到「AI 在尝试另一种方式」**。

**📝 背面经视角：**

Agent 规划 fallback 通常采用分级降级策略。每一级增加人工干预程度，最终兜底到人工。核心是在用户体验受损之前完成降级。

---

## 3. 工具链设计与优化

### Q12：怎么给 Agent 设计一个好的 Tool Schema？有哪些容易被忽视的细节？

> 🏢 高频来源：几乎所有 Agent 岗位

**🧠 有工作经验视角：**

Tool Schema 就是 Agent 的「API 文档」。写得好，LLM 能准确调用；写得不好，翻车率高得离谱。

**五个血泪教训：**

1. **Description 要比你以为的详细 3 倍**。不只是说「这个 tool 干什么」，要说「什么时候用、什么情况下不要用、输入输出格式、常见错误示例」。LLM 看 tool description 就像人类看 API 文档——越详细越不容易用错

2. **参数名用自然语言，别用缩写**。`customer_id` 而不是 `cust_id`，`order_status` 而不是 `ord_st`。LLM 对自然语言参数名的理解准确度远高于缩写

3. **给枚举值加中文说明**。Schema 里 `enum: ["pending", "shipped", "cancelled"]` 不如 `enum: ["pending(待处理)", "shipped(已发货)", "cancelled(已取消)"]`——模型选枚举值的准确率提升明显

4. **必须声明 side effect**。这个 tool 是只读（readonly）还是写操作？写操作的话 LLM 应该更谨慎。在 description 开头标 `[READONLY]` 或 `[WRITE]`

5. **给返回值 Schema**。不只告诉 LLM 怎么调，还要告诉它返回的是什么结构。有些框架（Claude Tool Use、GPT function calling）支持 output schema，一定要用

**📝 背面经视角：**

Tool Schema 设计最佳实践：
- description 包含：功能描述 + 使用场景 + 限制条件 + 示例
- 参数名用 snake_case 自然语言
- 枚举值标注语义
- 标注 side effect（readonly vs write）
- 提供 output schema

---

### Q13：Agent 的 Tool 数量膨胀后怎么管理？Tool 路由和服务发现怎么做？

> 🏢 高频来源：蚂蚁集团 AgentInfra、字节 Agent 平台

**🧠 有工作经验视角：**

当一个 Agent 挂载了 50+ 个 tool，每次 LLM 调用都要把所有 tool definition 塞进 context——token 消耗暴涨，tool 选择准确率暴跌。

**分层路由方案：**

```
用户请求 → Tool Router（轻量分类器）
  ├─ 订单相关 → 只暴露 订单域 tools（5个）
  ├─ 商品相关 → 只暴露 商品域 tools（7个）
  ├─ 用户相关 → 只暴露 用户域 tools（4个）
  └─ 通用 → 只暴露 通用 tools（3个）
```

实现方式：
- **静态路由**：基于关键词/意图分类预定义 tool 分组，最稳定
- **语义路由**：用 embedding 匹配「用户意图 → tool 域」，更灵活但偶尔误分类
- **动态路由**：LLM 先选择 tool 类别，再在类别内选择具体 tool，最灵活但多一次 LLM 调用

我在生产用的是「静态路由 + 语义回退」——关键词匹配优先，匹配不到再用 embedding。

**📝 背面经视角：**

Tool 路由的核心思想是「减少 LLM 选择空间」。从 N 个 tool 中选 1 个 → 变成先从 K 个类别中选 1 个，再从 M 个 tool 中选 1 个（K×M≈N）。两层检索 + 精准匹配。

---

### Q14：Parallel Tool Calling 的坑有哪些？怎么设计支持并行调用还能保证正确性？

> 🏢 高频来源：字节跳动、月之暗面

**🧠 有工作经验视角：**

并行 Tool Calling 看起来很美好——同时调三个 API，延迟从 3s 变 1s。但坑很多：

**坑1：数据依赖**
三个 tool 如果存在依赖关系（tool B 需要 tool A 的输出），并行调用就会出错。解法：在 tool description 中显式声明依赖 `depends_on: ["tool_a"]`，Agent 框架在调度时检查依赖图。

**坑2：竞态条件**
两个并行 tool 都试图修改同一个资源。比如 tool A 把订单状态改成「已取消」，tool B 同时尝试创建退货单——创建了但订单已取消，数据不一致。解法：乐观锁 + 事务 + 写操作串行化。

**坑3：部分失败**
三个 tool 并行，两个成功一个失败。Agent 需要决定：是回滚成功的两个，还是忽略失败的继续？这个决策 LLM 做得不好。解法：预定义「补偿事务」——每个写 tool 都要配一个 reverse tool。

**📝 背面经视角：**

并行 Tool Calling 三个核心挑战：
1. 依赖检测 → tool schema 中声明 depends_on
2. 并发控制 → 写操作加锁或串行化
3. 部分失败处理 → 补偿事务或 Saga 模式

Anthropic 的 Claude 在 2025 年支持了 native parallel tool calling，OpenAI 的 GPT-4 也支持，但调度和错误处理仍需应用层实现。

---

### Q15：Agent 怎么处理 tool 返回的超大数据量（比如一次数据库查询返回 10 万行）？

> 🏢 高频来源：蚂蚁集团、字节跳动数据平台

**🧠 有工作经验视角：**

10 万行塞进 context → token 爆炸 + LLM 注意力稀释。这个问题没有银弹，几种方案的组合：

1. **Tool 端做预处理**：Tool 不返回原始数据，返回聚合/统计/摘要。`SELECT *` 在 tool 层做 `COUNT`、`GROUP BY`、取 TOP N
2. **分页 + Agent 主动查询**：Tool 返回分页数据 + 总行数，Agent 分析第一页后决定是否需要查看更多
3. **让 Agent 写代码处理**：Tool 返回「数据太大，已存为临时文件」，Agent 生成 Python/SQL 代码去处理文件，把处理结果（而非原始数据）带回 context

方案 3 需要 Code Interpreter（沙箱执行环境），安全风险更高，但也最灵活。

**📝 背面经视角：**

大数据量 tool 返回的解决方案：预处理（tool 层聚合）> 分页（Agent 主动查询）> 代码处理（Agent 写代码在沙箱中处理数据）。选择取决于数据结构和安全要求。

---

### Q16：Tool 返回的错误信息怎么写才能让 LLM 做出正确决策？

> 🏢 高频来源：MiniMax、智谱 AI

**🧠 有工作经验视角：**

这个问题被严重低估。很多团队 tool 出错时直接返回 raw error：`HTTP 500 Internal Server Error`——LLM 看到这个只能干瞪眼。

**好的 tool 错误信息应该包含三个部分：**

```
{
  "error": true,
  "error_type": "TEMPORARY_UNAVAILABLE",    // 错误分类
  "error_message": "订单服务当前不可用，这是暂时性故障，通常 30 秒内恢复",  // 人类可读说明
  "suggested_action": "retry",               // 建议动作
  "retry_after_seconds": 5,                  // 重试等待时间
  "alternative": "也可调用 fallback_order_query 获取缓存数据"  // 替代方案
}
```

LLM 看到 `TEMPORARY_UNAVAILABLE` + `suggested_action: retry`，就知道要等一会重试。看到 `PERMISSION_DENIED` + `alternative`，就知道换条路走。

**📝 背面经视角：**

Tool 错误信息结构化：error_type（分类）+ error_message（人类可读）+ suggested_action（重试/换工具/放弃）+ alternative（备选方案）。目标是让 LLM 像人类工程师一样看完报错就能做决策。

---

## 4. Multi-Agent 系统深入

### Q17：Multi-Agent 系统中，任务怎么分配给不同的 Agent？有什么分配策略？

> 🏢 高频来源：字节 Agent 平台、蚂蚁集团、阿里 Tongyi

**🧠 有工作经验视角：**

任务分配是 Multi-Agent 系统最难的问题之一。我用过三种策略：

**策略1：静态角色分配**
每个 Agent 角色固定（PM Agent、Dev Agent、QA Agent），任务根据类型路由。简单但不够灵活——如果 QA Agent 闲着、Dev Agent 忙，QA 帮不上忙。

**策略2：语义匹配分配**
任务描述 → embedding → 匹配最合适的 Agent profile。比静态灵活，但偶尔匹配错——把性能优化任务派给了写文档的 Agent。

**策略3：竞价分配（Auction-based）**
广播任务给所有 Agent，每个 Agent 评估自己能完成的程度，出价（confidence score）。调度器选置信度最高的。最灵活但通信开销大。

我在一个客服系统中用的是「静态分配 + 人工兜底」——90% 的任务按类型路由，10% 不确定的交给用户选择「您要找哪个部门？」。

**📝 背面经视角：**

Multi-Agent 任务分配三大策略：
- 静态角色（Rule-based Routing）：预定义角色→任务类型映射
- 语义匹配（Semantic Matching）：embedding 相似度匹配
- 竞标机制（Auction）：Agent 自行评估并竞价

生产环境推荐静态 + 语义混合，竞标机制开销大、不确定性高。

---

### Q18：多个 Agent 之间出现分歧怎么办？谁来做最终决策？

> 🏢 高频来源：字节跳动、蚂蚁集团

**🧠 有工作经验视角：**

多 Agent 分歧在生产环境太常见了。我遇到过的：

- Dev Agent 说「这个 bug 是前端的问题」，Frontend Agent 说「是后端返回数据不对」
- Review Agent 说代码通过，Security Agent 说代码有注入风险

**分歧解决机制：**

1. **仲裁 Agent（Arbiter）**：一个专门的决策 Agent，听取各方意见后做最终决定。适合「争议明确、需要拍板」的场景
2. **投票机制**：多个 Agent 投票，少数服从多数。适合「决策类型有限、可以量化」的场景
3. **置信度加权**：每个 Agent 给出结论 + 置信度分数，加权平均。适合「Agent 能力不均衡」的场景
4. **升级到人类**：分歧超过阈值 → 打包上下文发给人类决策。适「高风险决策」的场景

实际使用：低风险操作 → 仲裁 Agent 拍板；高风险操作 → 必须人类确认。

**📝 背面经视角：**

多 Agent 分歧解决：Arbiter Agent（仲裁）、Majority Voting（投票）、Confidence Weighted（置信度加权）、Human Escalation（升级）。选择取决于风险等级和决策可逆性。

---

### Q19：Multi-Agent 系统中的「幻觉放大」问题怎么系统性地解决？

> 🏢 高频来源：智谱 AI、月之暗面

**🧠 有工作经验视角：**

幻觉放大是 Multi-Agent 最隐蔽的 bug。Agent A 输出了一个看起来合理但实际错误的信息 → Agent B 基于这个错误信息做决策 → Agent C 基于 B 的决策输出最终结果——每一步都增加了错误，最终结果和事实差了十万八千里。

**系统性的解法：**

1. **事实锚定（Fact Checkpoint）**：每个 Agent 的输出都要引用信息来源。如果 Agent A 说「根据 X 系统的返回值，订单金额是 299」，那 Agent B 可以追溯验证 X 系统是不是真的返回了 299
2. **交叉验证（Cross Validation）**：让两个独立的 Agent 对同一个事实做判断。两者一致 → 可信；不一致 → 标记并重新查询
3. **置信度传播（Confidence Propagation）**：每个 Agent 为输出标注置信度。低置信度输出在后续 Agent 中使用时会触发「谨慎模式」
4. **溯源链（Provenance Chain）**：类似区块链的溯源机制——最终输出可以一路追溯到原始数据源

**📝 背面经视角：**

Multi-Agent 幻觉放大是级联错误问题。解决方案包括：Fact Checkpoint（事实锚点）、Cross Validation（交叉验证）、Confidence Propagation（置信度传播）、Provenance Chain（溯源链）。核心思想：不让未经验证的信息在 Agent 之间传递。

---

### Q20：Agent 之间的上下文传递怎么做？共享 Memory、消息传递还是黑板模式？

> 🏢 高频来源：蚂蚁集团、阿里 Tongyi

**🧠 有工作经验视角：**

三种模式我都用过，各有适用场景：

**消息传递（Message Passing）**
Agent A 的输出 → 直接作为 Agent B 的输入。AutoGen 就是这种模式。

优点：简单，逻辑清晰。缺点：信息只在相邻 Agent 间传递，第三个 Agent 不知道第一个做了什么。类似「传话游戏」——传到后面变味了。

**共享 Memory（Shared Memory）**
所有 Agent 共用一个 Memory 空间，随便读写。

优点：所有 Agent 看到一致的信息。缺点：并发写入冲突、Memory 膨胀快。需要设计读写锁和淘汰策略。

**黑板模式（Blackboard）**
一个中心化的「黑板」，Agent 们在上面写发现、读别人的发现。

优点：结构化、可审计。缺点：中心化单点，黑板本身的设计决定了系统的上限。

**我的选型经验：**
- 2-3 个 Agent 简单协作 → 消息传递
- 需要全局状态一致性 → 共享 Memory
- 需要审计和可解释性 → 黑板模式
- 生产环境 → 共享 Memory + 结构化事件日志（既能实时读写，又能追溯）

**📝 背面经视角：**

Agent 通信三模式：
| 模式 | 代表 | 优点 | 缺点 |
|------|------|------|------|
| 消息传递 | AutoGen | 简单 | 信息衰减 |
| 共享 Memory | LangGraph | 一致 | 并发冲突 |
| 黑板模式 | 经典 AI | 可审计 | 单点 |

---

### Q21：怎么防止 Multi-Agent 系统中的「死亡循环」——两个 Agent 互相指使对方干活？

> 🏢 高频来源：字节跳动、蚂蚁集团

**🧠 有工作经验视角：**

我亲眼见过：Agent A 说「这个问题需要 Agent B 处理」，Agent B 收到后说「这应该由 Agent A 处理」——然后它们俩来回踢了 12 轮。

**解法：**

1. **最大跳数（Max Hops）**：消息在 Agent 间传递的次数上限。超过就强制截断，由仲裁 Agent 接手
2. **去重检测（Deduplication）**：如果发现当前任务和之前某个任务相似度 > 95%，触发循环检测 → 升级处理
3. **任务拆解而不是转交**：Agent 不能简单说「这个该你干」，必须说明「我做了 X，需要你做 Y」——把转交变成协作

**📝 背面经视角：**

Multi-Agent 死亡循环防护：Max Hops（传递次数上限）、Deduplication（任务去重检测）、强制性任务拆解（不能纯转交，必须说明已完成什么+需要对方做什么）。

---

### Q22：如果你的 Multi-Agent 系统要支撑 100 万并发用户，架构上会遇到哪些挑战？

> 🏢 高频来源：蚂蚁 AgentInfra、字节 Agent 平台

**🧠 有工作经验视角：**

百万并发对 Agent 系统的挑战比传统微服务更大，因为每个 Agent 请求是「长连接 + 多次 LLM 调用 + 可能人工等待」。

**核心挑战：**

1. **LLM 调用是瓶颈**：每个 Agent 请求可能触发 5-20 次 LLM 调用，百万并发意味着一秒可能有几十万次 LLM API 调用。API 限流、成本、延迟都是问题
2. **会话状态管理**：Agent 的上下文（几十 KB）需要跨多次 LLM 调用持久化。存 Redis 还是数据库？读写频率多高？
3. **Tool 调用放大**：Agent 调一次 tool 可能触发下游 N 个微服务调用，形成调用链放大

**架构思路：**
- LLM 层做多模型路由 + 缓存（相同/相似 query 直接返回缓存）
- 会话状态存 Redis Cluster，带 TTL 自动过期
- Tool 调用走异步队列 + 熔断降级

**📝 背面经视角：**

高并发 Agent 系统的挑战：
- LLM 调用放大效应 → 多模型路由 + 语义缓存
- 有状态会话 → 分布式会话存储 + 自动过期
- Tool 调用链级联 → 异步化 + 熔断
- 成本控制 → 路由策略（小模型预处理 → 大模型深加工）

---

## 5. A2A 与 MCP 协议深入

### Q23：除了 MCP，还有哪些 Agent 间通信协议？A2A 和 MCP 的定位有什么不同？

> 🏢 高频来源：字节跳动、Google Cloud 相关岗位

**🧠 有工作经验视角：**

MCP（Model Context Protocol）和 A2A（Agent-to-Agent）是 2024-2025 年 Agent 协议领域最重要的两个标准。

**MCP（Anthropic 主导，2024 年 11 月发布）：**
定位：Agent 与外部工具/数据源的交互协议。解决「Agent 怎么发现和调用工具」的问题。

MCP 的核心概念：Client（Agent 框架）→ Server（工具提供方）。Server 暴露 tools、resources、prompts 三种能力。Client 通过 JSON-RPC 发现并调用。

我在生产环境用 MCP 的好处：换 LLM 时不需要改 tool 集成代码——MCP Server 不变，只换 Client 端的 LLM SDK。

**A2A（Google 主导，2025 年 4 月 Google Cloud Next 发布）：**
定位：Agent 与 Agent 之间的通信协议。解决「不同团队的 Agent 怎么互相发现和协作」的问题。

A2A 的核心概念：Agent Card（Agent 的「名片」，描述能力）+ Task（异步任务）+ Message（消息传递）。支持流式通信和长任务管理。

两者的关系：**MCP 是「Agent ↔ 工具」，A2A 是「Agent ↔ Agent」**。它们互补，不是竞争关系。

**📝 背面经视角：**

| 维度 | MCP | A2A |
|------|-----|-----|
| 主导方 | Anthropic | Google |
| 发布时间 | 2024.11 | 2025.04 |
| 定位 | Agent ↔ 工具/数据 | Agent ↔ Agent |
| 核心概念 | Client-Server, Tools/Resources/Prompts | Agent Card, Task, Message |
| 通信方式 | JSON-RPC | HTTP + JSON |
| 适用场景 | 统一工具接入标准 | 跨团队 Agent 协作 |

---

### Q24：MCP Server 怎么设计才能做到「一个 Server 服务多种 LLM」？

> 🏢 高频来源：蚂蚁 AgentInfra、字节 Agent 平台

**🧠 有工作经验视角：**

MCP 的设计哲学本身就是「LLM 无关」——Server 只暴露能力，不关心调用方是谁。但实际接入多种 LLM 时有几个坑：

1. **Tool Description 格式差异**：GPT 的 function calling 和 Claude 的 tool use 对 description 的敏感点不同。GPT 对 JSON Schema 更敏感，Claude 对自然语言 description 理解更好。解法：description 同时保持结构化（给 GPT）和自然语言（给 Claude）

2. **参数传递差异**：有些 LLM 对 optional 参数的处理不一致——GPT 可能省略，Claude 可能传 null。Server 端必须兼容两种行为

3. **返回格式偏好**：GPT 偏好 JSON 结构化返回，Claude 偏好 Markdown/自然语言。MCP Server 的返回格式应该同时提供（text + structured 两种表示）

**📝 背面经视角：**

MCP 的 LLM 无关性依赖两个设计原则：（1）Tool schema 用 JSON Schema 标准，不依赖特定 LLM 的格式；（2）返回内容同时提供 text 和 structured 两种表示。实践中需要针对主流 LLM 的差异做适配测试。

---

### Q25：MCP 的安全模型是什么样的？Agent 调 MCP Tool 时怎么防止越权？

> 🏢 高频来源：蚂蚁集团、字节跳动安全团队

**🧠 有工作经验视角：**

MCP 的安全模型是我在生产落地时最关注的问题。标准 MCP 本身的安全机制比较简单——主要靠传输层（SSE/WebSocket）的 TLS + OAuth 认证。

**但真正的安全挑战不在传输层，而在授权层：**

- Agent 代表用户 A 调 MCP Tool，但 MCP Server 怎么知道 Agent 有权限操作用户 A 的数据？
- 同一个 MCP Tool 对不同用户应该有不同的数据访问范围

**我在生产环境的方案：**
- MCP Client 在调用时传递 `X-User-ID` 和 `X-User-Role` 的 metadata
- MCP Server 端做 RBAC（基于角色的访问控制）
- 敏感操作（删除、退款、改价）的 tool 在 Server 端加二次确认逻辑

**标准演进：** MCP 社区已经在讨论 OAuth 2.0 + scope 授权方案，但 2026 年初还未标准化。

**📝 背面经视角：**

MCP 安全层次：传输安全（TLS）→ 认证（OAuth/API Key）→ 授权（RBAC/Scope）→ 审计（日志）。当前标准在传输和认证层较成熟，授权和审计层仍需应用自行实现。敏感操作建议在 Server 端而非 Client 端做权限控制。

---

### Q26：如果让你设计一个新的 Agent 通信协议，MCP 和 A2A 各自有哪些可以改进的地方？

> 🏢 高频来源：蚂蚁集团、月之暗面 Infra

**🧠 有工作经验视角：**

这题考察对协议设计的系统性思考。不要求你真的设计过协议，而是看你能不能指出成熟协议的局限。

**MCP 的不足：**
- 不支持 tool 的动态注册和发现（热更新）——新增 tool 需要重启 MCP Server
- 流式返回（streaming）的支持还在早期，实际体验不够流畅
- tool 调用没有原生的重试和超时语义——这些容错机制靠应用层自己实现

**A2A 的不足：**
- 协议较重，Agent Card 的定义粒度还不够细——「能做自然语言处理」这种描述对自动发现没用
- 异步 Task 的状态机设计较复杂，实现成本高
- 目前生态较小，实际落地的案例有限

**📝 背面经视角：**

改进方向：
- MCP：热更新 tool 注册、原生的 retry/timeout 语义、更好的 streaming 支持
- A2A：更细粒度的能力描述、简化 Task 状态机、降低实现门槛

---

### Q27：Agent 协议的未来趋势是什么？会统一还是有多个标准并存？

> 🏢 高频来源：字节跳动、Google、阿里云

**🧠 有工作经验视角：**

我个人的判断：**短期内（2026-2027）多个标准并存，长期会收敛到 2-3 个主流协议**。

理由：
- MCP 在「Agent ↔ 工具」这个层面已经形成事实标准——Anthropic、OpenAI 都支持，开源社区跟进速度快
- A2A 在「Agent ↔ Agent」层面解决了 MCP 没覆盖的问题，Google 的推动力很强
- 但中国的云厂商（阿里云、华为云、腾讯云）可能推出自己的协议变体，形成区域生态

**对工程师的建议：**
- 工具接入 → 优先上 MCP，生态最大
- Agent 间通信 → 关注 A2A 的发展，但别急着在生产环境上
- 内部系统 → 别等标准成熟，先用简单的 JSON/Protobuf 协议跑起来

**📝 背面经视角：**

Agent 协议趋势：MCP（Agent-Tool）已成事实标准，A2A（Agent-Agent）在快速发展。国内可能有区域标准出现。建议：工具层用 MCP，Agent 间通信视场景选择。

---

## 6. Agent 推理优化

### Q28：怎么降低 Agent 的推理延迟？从 prompt 到 infra 有哪些优化手段？

> 🏢 高频来源：字节跳动、MiniMax、蚂蚁集团

**🧠 有工作经验视角：**

Agent 延迟是一个全链路问题，不是只在 LLM 推理那一步。

**Prompt 层优化：**
- 精简 System Prompt：实测 500 字的 System Prompt 和 2000 字的，LLM 推理延迟差 20-30%。每多 1000 token，首 token 延迟 +0.3-0.5s
- 减少 tool definition 数量：每次 LLM 调用只传需要的 tool schema，不要全量传

**模型层优化：**
- 分级模型路由：简单任务（意图识别、参数提取）用 Haiku/Flash → 延迟 0.5s；复杂推理用 Sonnet/Pro → 延迟 3s
- 投机解码（Speculative Decoding）：用草稿模型生成候选 token，大模型并行验证。延迟降低 30-50%

**Infra 层优化：**
- Tool 调用并行化：无依赖的 tool 同时调
- 预取（Prefetch）：Agent 还在思考时，根据历史数据预加载可能需要的 tool 结果
- LLM 缓存：相同 System Prompt + 相似 User Input → hit 缓存，延迟降到 50ms

**📝 背面经视角：**

Agent 延迟优化全链路：
- Prompt → 精简上下文、tool 按需加载
- Model → 分级路由、投机解码
- Infra → 并行调用、预取、语义缓存

效果排序：缓存 > 并行调用 > 分级路由 > 精简 prompt。

---

### Q29：Agent 的 Token 成本怎么控制？有没有「花小钱办大事」的策略？

> 🏢 高频来源：所有 Agent 团队（成本是老板必问的）

**🧠 有工作经验视角：**

Agent 的 token 消耗是普通 Chat 的 5-20 倍（因为多轮 tool calling + 积累的 context），不控制的话账单爆炸。

**五个具体策略（按省钱效果排序）：**

1. **上下文窗口管理（最有效）**：不要把整个对话历史一直带着。用摘要（Summarization）替代原始记录——每 5 轮对话生成一次摘要，丢掉原始 message，只保留摘要 + 最近 3 轮
2. **分级模型路由**：80% 的简单操作（tool 选择、参数提取、格式校验）用 Haiku/Flash 1.5，只有 20% 的复杂推理用 Sonnet/Pro
3. **Prompt 缓存**：Claude 和 GPT-4 都支持 prompt caching——System Prompt + tool definitions 这些不变的部分可以被缓存，token 价格降到 1/10
4. **Tool 返回裁剪**：不要让 tool 返回完整数据，在 tool 层做裁剪和摘要后再返回给 LLM
5. **批处理**：非实时请求（如离线分析 Agent）合批处理，摊薄 System Prompt 成本

**📝 背面经视角：**

Token 成本控制金字塔：
```
      批处理（> 10x）
    上下文管理（3-5x）
  分级路由（2-3x）
 Prompt Caching（5-10x 不变部分）
Tool 返回裁剪（1.5-2x）
```

组合使用效果叠加。优先级：Prompt Caching + 分级路由 + 上下文管理。

---

### Q30：流式 Agent（Streaming Agent）和普通 Agent 的架构有什么不同？中间结果怎么推给前端？

> 🏢 高频来源：字节跳动、月之暗面、MiniMax（所有做 Chat 类产品的）

**🧠 有工作经验视角：**

普通 Agent：用户发消息 → 等 15 秒 → 看到最终结果。用户在第 5 秒开始焦虑「是不是卡了？」。

流式 Agent：用户发消息 → 立即看到「正在思考...」→ 「正在查询订单...」→ 「找到 3 笔订单...」→ 「正在计算退款...」→ 最终结果。每一步都可见。

**架构差异：**

普通 Agent：
```
Client → [Agent Loop（think→act→observe）× N] → Final Output → Client
```

流式 Agent：
```
Client ←SSE→ [Agent Loop]
  ← event: thinking  "正在分析您的退款请求..."
  ← event: tool_call "正在查询订单#8823..."
  ← event: tool_result "找到订单，金额299元..."
  ← event: thinking  "根据退货政策，您符合退款条件..."
  ← event: tool_call "正在创建退货单..."
  ← event: final  "退货单已创建，明天下午上门取件"
```

**实现要点：**
- 用 SSE（Server-Sent Events）而非 WebSocket——Agent 场景是「服务端推客户端」为主，SSE 够用且更简单
- 每个 Agent Loop 的步骤发一个 event，携带 `{type: "thinking"|"tool_call"|"tool_result"|"final", content: "...", step: 3, total_steps: 5}`
- 前端状态机：根据 event type 展示不同的 UI（loading spinner / tool 卡片 / 最终结果）

**📝 背面经视角：**

流式 Agent 通过 SSE 将 Agent Loop 的中间步骤实时推送前端。每个步骤封装为 typed event，前端根据 type 渲染对应的 UI 组件。核心挑战：中间步骤的不确定性（Agent 可能在第 3 步改变主意），前端要做好状态回滚。

---

## 📌 面试准备建议

### 面试官的关注点

Agent 进阶岗面试，面试官通常在看三件事：

1. **你有没有在生产环境踩过坑** — 理论谁都会背，真正区分水平的是「你做的 Agent 线上出过什么问题、怎么解决的」
2. **你的技术判断力** — 框架选型、协议选择、架构决策，能不能说出「为什么选 A 不选 B」
3. **你对 Agent 边界的认知** — 知道 Agent 擅长什么、不擅长什么、什么情况下 Agent 不是正确的方案

### 刷题优先级

| 优先级 | 模块 | 原因 |
|:---:|------|------|
| 🔥🔥🔥 | 框架对比（Q1-Q5） | 必考，无例外 |
| 🔥🔥🔥 | 规划算法（Q6-Q11） | 大厂 Agent 核心岗高频 |
| 🔥🔥 | 工具链设计（Q12-Q16） | 考察工程能力 |
| 🔥🔥 | Multi-Agent（Q17-Q22） | 系统设计题标配 |
| 🔥 | 协议（Q23-Q27） | 前沿方向，加分项 |
| 🔥 | 推理优化（Q28-Q30） | 性能和成本是落地关键 |

---

> 如果本文对你有帮助，欢迎收藏备用。下一篇：《AI Agent 工程落地与实战篇》——覆盖评估体系、可观测性、安全护栏、生产部署、成本优化等 30 道题。
> 
> 面试中遇到本文没覆盖的 Agent 题？评论区告诉我，我补充进下一篇。
