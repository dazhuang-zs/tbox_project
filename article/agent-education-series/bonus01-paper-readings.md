# 【AI Agent 系统教学】番外篇 01：Agent 领域经典论文精读

> 技术的源头在论文里。读懂了这几篇，你就理解了 Agent 技术的来龙去脉。

---

## 前言：为什么读论文

Agent 开发者在日常工作中，更多是写代码、调 API、修 bug。但当你遇到瓶颈时——比如模型不调用工具、Agent 在长对话中失效、多 Agent 协作不稳定——论文里往往有答案。

这个番外篇精读 5 篇 Agent 领域最具影响力的论文，每篇只讲核心思想和实践启示。

---

## 一、ReAct：Reasoning + Acting（2023）

> **论文**：Synergizing Reasoning and Acting in Language Models
> **作者**：Shunyu Yao 等（Princeton）
> **时间**：2023 年 3 月

### 核心思想

让 LLM 的"推理"和"行动"交织进行，而不是分离的。

```
传统做法：先推理，再行动（Plan → Execute）
ReAct：推理 → 行动 → 观察 → 再推理 → 再行动 ...
```

### 关键发现

1. 推理和行动交织比分离效果好
2. ReAct 比单纯的 CoT 或单纯的工具调用都好
3. 在问答、事实验证、交互式决策任务上效果显著

### 对 Agent 开发者的启示

**你现在用的所有 Agent 框架（LangGraph、CrewAI、OpenClaw）的底层逻辑都是 ReAct。** 理解 ReAct，就理解了 Agent 循环的本质。

---

## 二、Toolformer：教模型使用工具（2023）

> **论文**：Toolformer: Language Models Can Teach Themselves to Use Tools
> **作者**：Timo Schick 等（Meta AI）
> **时间**：2023 年 2 月

### 核心思想

让模型自己学会什么时候调用工具，而不是手动定义规则。

> 模型通过自监督学习，学会在合适的位置插入 API 调用。

### 关键发现

1. 模型可以自学使用工具，不需要人工标注
2. 工具调用可以像生成文本一样自然
3. 但 Toolformer 的调用是"离散的"（每个 API 一个 token），不如后来的 Function Calling 灵活

### 实践启示

**工具定义的质量直接影响 Agent 的效果。** 工具名称、描述、参数的精确度，决定了模型是否会在正确的时机调用正确的工具。

---

## 三、AgentBench：Agent 基准测试（2023）

> **论文**：AgentBench: Evaluating LLMs as Agents
> **作者**：Xiao Liu 等（清华大学）
> **时间**：2023 年 8 月

### 核心思想

为 Agent 设计专门的评估基准，而不是用 MMLU 等通用基准。

### 8 个任务

1. **操作系统**：在 Linux 终端中执行命令
2. **SQL 数据库**：查询数据库
3. **Web 浏览**：在网页中导航
4. **数字购物**：在模拟购物网站中操作
5. **知识图谱**：查询知识图谱
6. **家用电器**：控制智能设备
7. **横向思维**：解决谜题
8. **排序**：对输入进行排序

### 关键发现

**当时只有 GPT-4 能在 Agent 任务上达到可用水平。** 7B 模型在 Agent 任务上的表现远低于对话任务。

### 实践启示

**不要在通用基准上选 Agent 模型。** 用 AgentBench 或 BFCL 的工具调用基准来评估，比 MMLU 更有参考价值。

---

## 四、Reflexion：自我反思的 Agent（2023）

> **论文**：Reflexion: Language Agents with Verbal Reinforcement Learning
> **作者**：Noah Shinn 等（Northeastern University）
> **时间**：2023 年 3 月

### 核心思想

Agent 不仅执行任务，还会从失败中总结经验，用于后续改进。

```
尝试 → 失败 → 反思 → 记住教训 → 重新尝试 → 成功
```

### 关键发现

1. 反思机制让 Agent 在编程任务上准确率提升 20%+
2. 反思可以存储在"记忆"中，跨任务复用
3. 反思比单纯的"重试"更有效

### 实践启示

**在 Agent 的关键决策点加入反思机制，比简单增加重试次数更有效。** 把你的 Agent 的错误日志转化为"经验提示"，在后续任务中注入。

---

## 五、GraphRAG：知识图谱增强的 RAG（2024）

> **论文**：From Local to Global: A GraphRAG Approach to Query-Focused Summarization
> **作者**：Darren Edge 等（Microsoft Research）
> **时间**：2024 年 4 月

### 核心思想

用知识图谱替代简单向量检索，先构建实体关系图，再在图上做社区检测和摘要。

### 关键发现

1. GraphRAG 在需要"全局理解"的问题上，远超向量 RAG
2. 构建成本高，但在复杂查询上收益显著
3. 社区检测 + 分层摘要 = 从局部到全局的理解

### 实践启示

**如果你的 Agent 需要回答"整体性问题"（如"这个报告的主要结论是什么"），GraphRAG 比简单 RAG 效果好得多。** 但如果是"具体事实"（如"张三的邮箱是多少"），向量 RAG 就够了。

---

## 六、补充阅读清单

| 论文 | 主题 | 为什么重要 |
|------|------|----------|
| "Attention Is All You Need" (2017) | Transformer | Agent 一切能力的底层基础 |
| "Scaling Laws for Neural Language Models" (2020) | 扩展定律 | 理解模型能力与规模的关系 |
| "Training Language Models to Follow Instructions" (2022) | InstructGPT | 对齐技术的起源 |
| "Chain-of-Thought Prompting" (2022) | 思维链 | Agent 推理的基石 |
| "Tree of Thoughts" (2023) | 思维树 | Agent 规划能力的进阶 |
| "Self-RAG" (2023) | 自反思 RAG | RAG 的进阶方案 |
| "SWE-bench" (2024) | 代码 Agent 基准 | 代码 Agent 评估标准 |

---

## 总结

读论文不是为了背公式，而是为了理解**为什么**。

- 为什么 Agent 需要 ReAct？因为推理和行动交织比分离好。
- 为什么工具定义要精确？因为 Toolformer 证明了模型能自学工具，但依赖定义质量。
- 为什么小模型做 Agent 不行？因为 AgentBench 测试证明 Agent 任务是"涌现能力"。
- 为什么加入反思有效？因为 Reflexion 证明从失败中学习比简单重试更好。
- 为什么 GraphRAG 适合复杂查询？因为微软证明了全局理解需要知识图谱。

**论文是"道"，框架是"术"。道不变，术常新。**

---

> 下一篇：[番外02] 主流 Agent 框架深度横评
> 系列目录：[README.md](./README.md)