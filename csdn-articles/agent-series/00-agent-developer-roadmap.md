# 2 个月转型 AI Agent 开发工程师：从程序员到智能体构建者

> 150 篇 CSDN 文章、HarmonyOS 开发经验、Claude Code 重度用户——如果你已经会写代码、会用 AI 工具，两个月足够完成从「AI 使用者」到「Agent 构建者」的转型。这篇文章是一张完整地图。

---

## 一、AI Agent 开发工程师是什么

先破除一个误区：**Agent 开发 ≠ 调 API**。

| 角色 | 做什么 | 用什么 |
|------|------|------|
| AI 使用者 | 用 Claude Code/Cursor 写代码 | 聊天界面 |
| **Agent 开发工程师** | 造一个「自己能干活的人」 | 框架 + 协议 + 工具 |

Agent 工程师的核心能力是让 LLM 能：

1. **用工具**：调用 API、读写文件、操作数据库（Function Calling / MCP）
2. **分步思考**：把复杂任务拆成多步执行（ReAct / Plan-Execute）
3. **协作**：多个 Agent 分工配合（Multi-Agent）
4. **记忆**：记住上下文、用户偏好、历史决策（向量库 + 结构化存储）
5. **自治**：在限定范围内自己做判断和行动

> **一句话**：Agent 开发工程师造的是「能自动完成任务的系统」，不是「会聊天的机器人」。

---

## 二、你不必手写所有代码

2026 年，AI Coding 时代的学习方式已经变了：

| 传统学法 | AI 时代学法 |
|---------|-----------|
| 看视频教程 3 小时 | 让 Claude Code 搭 demo，跑起来改 |
| 手敲样板代码 | 描述需求 → AI 生成 → 你审架构 |
| 背 API 文档 | 让 AI 帮你查、帮你写、帮你解释 |
| 调试靠自己 | AI 读报错 → 修复 → 跑测试，你验证 |

**但核心不变**：你必须理解原理，才能判断 AI 写的代码对不对。

> 衡量标准：你能不能用大白话给同事讲清楚「ReAct 是什么」「MCP 解决什么问题」？讲不清楚，就是没真懂。

---

## 三、2 个月学习路线图

### 知识体系全景

```
                     Agent 开发工程师
                           │
          ┌────────────────┼────────────────┐
          ▼                ▼                 ▼
      LLM 基础          Agent 框架         工程能力
          │                │                 │
    ┌─────┼─────┐    ┌────┼────┐      ┌────┼────┐
    ▼     ▼     ▼    ▼    ▼    ▼      ▼    ▼    ▼
 Prompt  Func  RAG  ReAct Lang MCP  部署  记忆  安全
 Engineer Call      Plan-  Graph       评估
                  Execute
```

### 第 1 个月：理解 + 手写核心模块

| 周 | 主题 | 目标 | 对应文章 |
|:--:|------|------|:--:|
| 1 | LLM 原理 + Prompt 工程 | 理解 Token/Transformer/Temperature；会写 System Prompt | ① ② |
| 2 | Function Calling + RAG | 让 LLM 能调工具、能查知识库 | ③ ④ |
| 3 | Agent 设计模式 | 掌握 ReAct 和 Plan-Execute 两种经典模式 | ⑤ |
| 4 | LangGraph + MCP | 用框架搭 Agent；给 Agent 接外部工具 | ⑥ ⑦ |

### 第 2 个月：项目 + 纵深

| 周 | 做什么 | 输出 |
|:--:|------|------|
| 5 | Multi-Agent 协作 | ⑧ |
| 6 | Agent 记忆系统 + 评估 | 项目代码 |
| 7 | 综合项目：HarmonyOS 开发 Agent v2.0 | GitHub 项目 |
| 8 | 部署上线 + 面试准备 | 简历 + 作品集 |

---

## 四、每篇的核心知识

### ① LLM 底层原理速成

> **关键词**：Token · Tokenization · Transformer · Context Window · Temperature · Top-p

**Token（令牌）**：LLM 不认字，只认 Token。英文约 4 个字符 = 1 Token，中文约 1.5 字 = 1 Token。

> 「今天天气真好」→ 约 4-5 Token

**Context Window（上下文窗口）**：一次对话 LLM 能「看到」的最大 Token 数。Claude 200K，GPT-4 128K，DeepSeek 128K。超出就「失忆」。

**为什么这两个概念重要？** 因为你设计 Agent 时必须管理上下文：
- 对话历史太长 → 裁剪或摘要
- RAG 检索的文档太大 → 分块（Chunking）
- 工具返回的结果太多 → 截断

**Temperature（温度）**：控制输出的「随机性」。0 = 每次都一样（适合代码生成），1 = 放飞自我（适合创意写作）。

---

### ② Prompt Engineering 实战

> **关键词**：System Prompt · Few-shot · Chain-of-Thought · 角色设定

**System Prompt（系统提示）**：给 LLM 设定「人设」和规则。Agent 开发中这是最重要的部分。

```
# 好的 System Prompt
你是一个 HarmonyOS 开发专家，精通 ArkTS 和 ArkUI。
回答时：
1. 给出完整可运行的代码
2. 标注 API 版本要求
3. 如果涉及权限，列出需要的权限声明
不要输出解释性废话，直接给代码。
```

**Chain-of-Thought（思维链，CoT）**：让 LLM「一步步想」而不是直接给答案。

```
# 不加 CoT
问：23 × 47 = ?
答：1081  ← 可能对可能错

# 加 CoT
问：23 × 47 = ? 请一步步计算。
答：23 × 47 = 23 × (50 - 3) = 1150 - 69 = 1081  ← 正确率高得多
```

---

### ③ Function Calling：让 AI 学会用工具

> **关键词**：Tool Use · JSON Schema · Function Calling

这是 Agent 的「手脚」。LLM 不直接执行函数，而是**输出一个结构化的调用请求**，由你的代码去执行，结果再传回 LLM。

```python
# LLM 输出的是这个（不是真的去调 API）
{
  "name": "get_weather",
  "arguments": {"city": "北京"}
}

# 你的代码拿到这个，真的去调天气 API
# 结果返回给 LLM：
{
  "city": "北京",
  "temperature": 25,
  "condition": "晴"
}

# LLM 用自然语言回复用户：
"北京今天晴天，温度 25°C"
```

---

### ④ RAG：给 LLM 装上知识库

> **关键词**：Embedding · 向量检索 · Chunking · 混合检索

**RAG（Retrieval-Augmented Generation，检索增强生成）**：LLM 的知识截止到训练日期，RAG 让它能「查资料」回答。

```
用户问题 → Embedding模型 → 向量 → 向量数据库检索 → Top-K文本 → LLM生成答案
```

**Embedding（嵌入）**：把文本变成一组数字（向量）。语义相近的文本，向量也相近。

**Chunking（分块）**：把长文档切成小段。512 Token 是最常用的块大小。

> 你 HarmonyOS 项目里已经实现了完整的 RAG：BGE-Large-ZH + Milvus + 混合检索。这是你的优势。

---

### ⑤ Agent 设计模式：ReAct 与 Plan-Execute

> **关键词**：ReAct · Plan-Execute · 反思 · 工具调用循环

**ReAct（Reasoning + Acting）**：Agent 的核心循环——

```
思考 → 行动 → 观察 → 思考 → 行动 → 观察 → ... → 完成
```

```
用户：帮我查一下北京今天天气，如果下雨就提醒我带伞

Agent 思考：我需要先查天气
Agent 行动：调用 get_weather("北京")
Agent 观察：返回 {"condition": "雨", "temperature": 18}
Agent 思考：下雨了，应该提醒
Agent 回复：北京今天有雨，18°C，记得带伞！
```

**Plan-Execute（先规划后执行）**：复杂任务先列步骤，再逐步执行。

---

### ⑥ LangGraph：用状态图构建 Agent

> **关键词**：状态图 · 节点 · 边 · 条件路由

**LangGraph** 是 LangChain 的 Agent 编排框架。核心思想：把 Agent 的每一步定义为「节点」，节点之间的跳转逻辑定义为「边」。

```
      [开始]
        │
        ▼
    [分析意图]
        │
   ┌────┴────┐
   ▼         ▼
[查天气]  [做计算]
   │         │
   └────┬────┘
        ▼
    [生成回复]
        │
        ▼
      [结束]
```

---

### ⑦ MCP 协议：给 AI 接上外部世界

> **关键词**：Model Context Protocol · JSON-RPC · MCP Server · stdio/HTTP

**MCP（模型上下文协议）**是 Anthropic 在 2024 年底发布的开放协议，被称为「AI 的 USB-C」。

**解决的问题**：以前要给 Claude + GPT + DeepSeek 分别写工具适配代码，MCP 让你写一个 Server，所有支持 MCP 的应用都能用。

```
MCP Server（你写的）
    ├── 读本地文件
    ├── 查数据库
    └── 发 Slack 消息
         ↑
    ┌────┼────┐
    ▼    ▼    ▼
Claude  GPT DeepSeek
```

---

### ⑧ Multi-Agent：让多个 AI 协作

> **关键词**：角色分工 · 任务委派 · Agent 间通信

一个 Agent 做不了的事，让多个 Agent 分工：

```
PM Agent → 拆需求、分任务
   │
   ├──→ 前端 Agent → 写 React 组件
   ├──→ 后端 Agent → 写 FastAPI 接口
   └──→ 测试 Agent → 写测试用例、跑验证
```

---

## 五、8 篇文章的阅读顺序

```
① LLM 原理速成          ← 奠基
    ↓
② Prompt Engineering     ← 最常用
    ↓
③ Function Calling       ← Agent 的"手脚"
    ↓
④ RAG 实战              ← 你已有经验，快速过
    ↓
⑤ Agent 设计模式         ← 核心理论
    ↓
⑥ LangGraph 入门         ← 框架实战
    ↓
⑦ MCP 协议实战          ← 2026 年标配
    ↓
⑧ Multi-Agent 协作       ← 进阶收尾
```

---

## 六、学习原则

1. **每篇必须跑代码**——只看不跑等于没学
2. **不懂就问 Claude Code**——「这段代码为什么这么写？」
3. **学了立刻写文章**——教别人是最好的学习
4. **2 个月后做一个完整项目**——面试时能展示的东西

---

## 七、你的差异化优势

面试时说这段话：

> 「我有 150 篇技术文章的输出习惯，从 HarmonyOS 开发者转型 Agent 开发。
> 我用 Claude Code 搭建了一个完整的 RAG + Agent 系统（展示 GitHub），
> 熟悉 MCP 协议和多 Agent 协作，能独立从 0 搭建 Agent 产品。」

这比「我学过 LangChain」有说服力 10 倍。

---

> 下一篇：**《LLM 底层原理速成：Token、Transformer、Context Window 一次性讲透》**——没有数学公式，只有看得懂的图解和代码。

*系列文章持续更新中，关注获取完整 Agent 开发学习路径。*
