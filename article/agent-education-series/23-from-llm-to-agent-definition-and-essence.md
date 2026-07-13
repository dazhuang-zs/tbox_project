# 【AI Agent 系统教学 23】从 LLM 到 Agent：Agent 的定义与本质

> 有了 LLM 就够了吗？不够。
> LLM 是大脑，Agent 是完整的个体——有大脑、有感官、有手、有记忆。

---

## 前言：为什么 LLM 不是 Agent？

2023 年，有人把 GPT-4 包装成一个"Agent"，然后发现它：

- 能做简单任务，但多步就不行了
- 能调用工具，但一个接一个调用就乱了
- 能记住上下文，但超过 10 轮对话就忘了
- 能推理，但需要规划时就不行了

**LLM 不是 Agent。LLM 是 Agent 的大脑，但不是全部。**

就像人类有大脑、眼睛、耳朵、手、脚、记忆——Agent 也需要这些组件，LLM 只是其中的"大脑"。

---

## 一、Agent 的定义

### 1.1 经典定义

Agent 是能够**感知环境、做出决策、执行行动**的实体。

从 AI 角度，一个 Agent 包含以下核心要素：

```
Agent = LLM（大脑） + 感知（输入） + 行动（工具） + 记忆（上下文） + 规划（推理）
```

### 1.2 Agent 的三要素

学术界通常用"三要素"来定义 Agent：

```
1. 感知（Perception）：接收环境信息
2. 决策（Decision）：基于信息做出判断
3. 行动（Action）：执行具体操作

LLM Agent 的对应关系：
  感知 → 用户输入、工具返回结果、上下文
  决策 → LLM 推理、规划、选择
  行动 → 工具调用、回复生成
```

### 1.3 LLM Agent 的特殊性

传统 Agent（如强化学习 Agent）和 LLM Agent 有本质区别：

| 维度 | 传统 Agent | LLM Agent |
|------|-----------|-----------|
| 知识来源 | 从零学习 | 预训练知识 |
| 决策方式 | 策略网络 | 语言推理 |
| 行动空间 | 预定义 | 动态扩展（工具） |
| 记忆 | 神经网络状态 | 上下文窗口 |
| 泛化能力 | 弱 | 强（通过语言泛化） |

**LLM Agent 的最大优势**：不需要从零训练，继承了 LLM 的泛化能力。

---

## 二、Agent 的核心组件

### 2.1 架构图

```
                    ┌──────────────┐
                    │   用户输入    │
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │   感知模块    │ ← 理解输入、提取意图
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │   推理模块    │ ← 推理、规划、决策
                    └──────┬───────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
        ┌─────▼────┐ ┌────▼─────┐ ┌────▼─────┐
        │ 工具调用  │ │ 记忆管理  │ │ 回复生成  │
        └─────┬────┘ └────┬─────┘ └────┬─────┘
              │            │            │
              └────────────┼────────────┘
                           │
                    ┌──────▼───────┐
                    │   输出模块    │
                    └──────────────┘
```

### 2.2 各组件职责

| 组件 | 职责 | 实现方式 |
|------|------|---------|
| 感知模块 | 理解用户输入、提取意图 | LLM + 意图分类 |
| 推理模块 | 规划、推理、决策 | LLM + CoT/ToT |
| 工具模块 | 调用外部工具、获取信息 | Function Calling |
| 记忆模块 | 管理上下文、长期记忆 | 上下文窗口 + 外部存储 |
| 回复模块 | 生成最终输出 | LLM + 格式约束 |

### 2.3 最小 Agent 实现

```python
class MinimalAgent:
    def __init__(self, llm, tools):
        self.llm = llm
        self.tools = {t.name: t for t in tools}
        self.memory = []
    
    def respond(self, user_input):
        # 1. 感知
        self.memory.append({"role": "user", "content": user_input})
        
        # 2. 推理 + 决策
        response = self.llm.generate(
            system_prompt=self._build_system_prompt(),
            messages=self.memory,
        )
        
        # 3. 行动（如果有工具调用）
        while self._has_tool_call(response):
            tool_result = self._execute_tool(response)
            self.memory.append({"role": "tool", "content": tool_result})
            response = self.llm.generate(messages=self.memory)
        
        # 4. 输出
        self.memory.append({"role": "assistant", "content": response})
        return response
```

---

## 三、LLM 到 Agent 的演化路径

### 3.1 三个阶段

```
阶段一：Chat Model（2022-2023）
  LLM 只是对话接口
  输入 → 输出
  能力：问答、对话

阶段二：Function Calling（2023-2024）
  LLM 可以调用工具
  输入 → 调用工具 → 输出
  能力：获取实时信息、执行操作

阶段三：Agent（2024-2026）
  LLM 自主规划、推理、执行
  输入 → 推理 → 规划 → 多次工具调用 → 输出
  能力：复杂任务、多步推理、自我纠错
```

### 3.2 关键跨越

**从 Function Calling 到 Agent 的跨越**：
- 单步工具调用 → 多步工具链
- 被动响应 → 主动规划
- 无记忆 → 有记忆
- 一次性 → 持续循环

```python
# Function Calling（单步）
def function_calling(user_input):
    intent = classify(user_input)
    tool = select_tool(intent)
    result = tool.execute(user_input)
    return result

# Agent（多步循环）
def agent_loop(user_input):
    state = {"input": user_input, "history": [], "result": None}
    while not done:
        plan = llm.plan(state)
        for step in plan:
            result = execute_step(step)
            state["history"].append(result)
            if check_done(state):
                done = True
                break
    return state["result"]
```

---

## 四、Agent 的分类

### 4.1 按自主性

```
简单反射 Agent：根据输入直接反应（如"天气查询"）
    ↓
基于模型的 Agent：使用内部模型推理（如"代码助手"）
    ↓
目标导向 Agent：根据目标规划行动（如"研究助手"）
    ↓
效用导向 Agent：最大化某个效用函数（如"交易 Agent"）
    ↓
学习 Agent：从经验中学习改进（如"个性化助手"）
```

### 4.2 按能力

| 类型 | 能力 | 代表 | 复杂度 |
|------|------|------|-------|
| 单步 Agent | 一次工具调用 | 简单客服 | 低 |
| 多步 Agent | 多次工具调用 | 研究助手 | 中 |
| 规划 Agent | 先规划再执行 | 项目管理 Agent | 高 |
| 反思 Agent | 自我评估和修正 | 代码 Agent | 高 |
| 协作 Agent | 多 Agent 协作 | 软件开发 Agent | 极高 |

### 4.3 按应用场景

```python
agent_types = {
    "客服Agent": {
        "tools": ["search_kb", "check_order", "update_ticket"],
        "memory": "short_term",
        "autonomy": "low",
    },
    "代码Agent": {
        "tools": ["read_file", "write_file", "run_code", "search_web"],
        "memory": "long_term",
        "autonomy": "high",
    },
    "研究Agent": {
        "tools": ["search_web", "search_papers", "analyze_data"],
        "memory": "session",
        "autonomy": "medium",
    },
    "交易Agent": {
        "tools": ["get_price", "execute_trade", "check_balance"],
        "memory": "long_term",
        "autonomy": "high",
    },
}
```

---

## 五、Agent 的核心能力

### 5.1 能力图谱

```
       ┌───────────┐
       │  推理能力  │
       └─────┬─────┘
             │
┌────────────┼────────────┐
│            │            │
▼            ▼            ▼
工具使用    记忆管理    规划能力
│            │            │
│            │            │
▼            ▼            ▼
安全控制    错误处理    学习适应
```

### 5.2 能力评估

```python
def assess_agent_capabilities(agent):
    """评估 Agent 的核心能力"""
    assessments = {
        "reasoning": test_reasoning(agent, [
            "如果 A > B, B > C, 那么 A 和 C 的关系是什么？",
            "帮我规划一个项目计划",
        ]),
        "tool_use": test_tool_use(agent, [
            "查询今天的天气",
            "搜索 Python 教程，然后写一个 hello world",
        ]),
        "memory": test_memory(agent, [
            "记住我的名字是张三",
            "我叫什么名字？",
        ]),
        "planning": test_planning(agent, [
            "帮我写一个研究计划",
            "如何从零开始学习 Python？",
        ]),
    }
    return assessments
```

---

## 六、Agent 的局限性

### 6.1 当前 Agent 的瓶颈

| 瓶颈 | 表现 | 根因 |
|------|------|------|
| 上下文限制 | 长对话效能下降 | Transformer 的 O(n²) 复杂度 |
| 工具可靠性 | 多步工具调用出错 | 模型对工具编排的理解不深 |
| 规划能力 | 规划不切实际 | 模型缺乏"执行成本"的认知 |
| 自我纠错 | 不会发现自己的错误 | 缺乏"反思"的训练 |
| 学习能力 | 不会从错误中学习 | 无持久化学习机制 |

### 6.2 Agent 不是万能的

```
Agent 擅长：
  - 有明确目标的任务
  - 步骤可拆解的任务
  - 有工具支持的任务
  - 中等复杂度的任务

Agent 不擅长：
  - 需要长期持续学习的任务
  - 需要创造性突破的任务
  - 需要极高可靠性的任务
  - 需要理解人类情感细微处
```

---

## 七、2026 年 Agent 生态

### 7.1 主流框架对比

| 框架 | 语言 | 特点 | 适合场景 |
|------|------|------|---------|
| LangGraph | Python | 状态机，灵活 | 复杂 Agent 流程 |
| CrewAI | Python | 多 Agent 协作 | 团队协作 |
| AutoGen | Python | 多 Agent 对话 | 研究实验 |
| OpenClaw | TypeScript | 生产级，微信集成 | 个人助手 |
| OpenAI Agents SDK | Python | 官方，简洁 | 快速原型 |

### 7.2 Agent 开发的核心原则

1. **从简单开始**：先做出能用的最小 Agent，再增加复杂度
2. **工具优先**：Agent 的能力取决于它能用什么工具
3. **可观测性**：让 Agent 的决策过程可见
4. **容错设计**：假设 Agent 会出错，设计错误恢复
5. **渐进式**：给 Agent 的能力越多，越需要控制

---

## 总结

| 概念 | 一句话 |
|------|--------|
| Agent | 能感知、决策、行动的 AI 实体 |
| LLM Agent | 以 LLM 为大脑的 Agent |
| 三要素 | 感知、决策、行动 |
| 核心组件 | 感知、推理、工具、记忆、输出 |
| 局限性 | 上下文、工具、规划、学习 |

**Agent 不是 LLM 的"升级版"，而是 LLM 的"完整包装"。** LLM 提供了大脑，Agent 框架提供了感知、行动、记忆等所有组件。

下一篇文章，我们将深入**Agent 的三大范式**——ReAct、Plan-and-Execute、Reflexion，以及它们各自的适用场景。

---

**思考题**：
1. 你现在的 Agent 系统，实现了 Agent 三要素（感知、决策、行动）中的哪些？
2. 从 Chat Model 到 Agent，最难跨越的瓶颈是什么？
3. 如果你只能给 Agent 装 3 个工具，你会选哪 3 个？为什么？

---

> 上一篇：[22] RAG 在 Agent 中的角色
> 下一篇：[24] Agent 范式巡礼：ReAct、Plan-and-Execute、Reflexion
> 系列目录：[README.md](./README.md)