# Multi-Agent 协作：CrewAI 实战

> 一个 Agent 是员工，多个 Agent 是团队。本文用 CrewAI 搭建一个「产品经理 + 开发 + 测试」三人开发小组，看他们怎么协作完成一个真实需求。

---

## 一、为什么需要 Multi-Agent

单 Agent 的瓶颈：

```
用户：帮我做一个待办事项 App，需要前端后端和数据库

单 Agent 的困境：
- 前端要 React，后端要 FastAPI，数据库要 PostgreSQL
- 一个 Agent 得同时掌握三种技术栈
- 上下文很快被占满
- 生成的代码风格不统一
```

Multi-Agent 的解法：

```
              用户需求
                 │
         ┌───────▼───────┐
         │   PM Agent    │ 分析需求，拆解任务
         └───────┬───────┘
                 │
     ┌───────────┼───────────┐
     ▼           ▼           ▼
前端 Agent   后端 Agent   测试 Agent
(React)      (FastAPI)    (Pytest)
     │           │           │
     └───────────┼───────────┘
                 ▼
           整合 + 交付
```

---

## 二、CrewAI 核心概念

| 概念 | 含义 | 示例 |
|------|------|------|
| **Agent** | 一个 AI 角色 | PM、前端开发、QA |
| **Task** | 分配给 Agent 的具体任务 | "设计 API 接口" |
| **Crew** | Agent 团队 | "开发小组" |
| **Process** | 协作模式 | sequential（顺序）/ hierarchical（层级） |

---

## 三、搭建三人开发团队

```python
# pip install crewai langchain-openai

from crewai import Agent, Task, Crew, Process
from langchain_openai import ChatOpenAI

# ── 共用 LLM ──
llm = ChatOpenAI(
    model="deepseek-chat",
    api_key="your-key",
    base_url="https://api.deepseek.com/v1"
)

# ── 1. 定义三个 Agent ──

pm_agent = Agent(
    role="产品经理",
    goal="分析用户需求，输出清晰的技术需求文档",
    backstory="你有 5 年 SaaS 产品经验，擅长把模糊需求转化为可执行的技术方案",
    llm=llm,
    verbose=True
)

frontend_agent = Agent(
    role="前端开发工程师",
    goal="根据技术需求，用 React + TypeScript 实现前端界面",
    backstory="你是一个 React 专家，擅长组件化开发和状态管理",
    llm=llm,
    verbose=True
)

backend_agent = Agent(
    role="后端开发工程师",
    goal="根据技术需求，用 FastAPI + SQLAlchemy 实现后端 API",
    backstory="你是一个 Python 后端专家，擅长 RESTful API 设计和数据库建模",
    llm=llm,
    verbose=True
)

qa_agent = Agent(
    role="测试工程师",
    goal="验证前后端代码的功能完整性和质量",
    backstory="你有 3 年自动化测试经验，擅长单元测试、集成测试和边界条件测试",
    llm=llm,
    verbose=True
)
```

### Agent 设计的核心要素

**Role（角色）**：越具体越好。「前端开发」不如「React 前端工程师，擅长 TypeScript 和 Tailwind CSS」。

**Goal（目标）**：单一、明确。「写代码」不如「根据 PRD 用 React + TypeScript 实现前端界面，包含 Loading/空数据/错误三种状态」。

**Backstory（背景）**：给 Agent 一段「故事」，让它的回答更有风格。不是闲聊，而是影响它如何做决策。

---

## 四、定义任务

```python
# ── 2. 定义任务链 ──

task_prd = Task(
    description="""
    用户需求：做一个个人记账 Web 应用。
    功能要求：
    1. 记录收入/支出（金额、分类、备注、日期）
    2. 查看月度收支汇总
    3. 分类统计饼图
    
    请输出一份技术需求文档，包含：
    - 数据模型设计
    - API 接口定义
    - 前端页面结构
    - 技术栈选型
    """,
    expected_output="一份 Markdown 格式的技术需求文档",
    agent=pm_agent
)

task_backend = Task(
    description="""
    根据 PM 的技术需求文档，实现后端 API。
    
    要求：
    - FastAPI + SQLAlchemy + SQLite
    - 完整的 CRUD 接口
    - 月度汇总接口
    - 添加请求参数校验和错误处理
    """,
    expected_output="完整的 Python 后端代码，包含所有 API 接口",
    agent=backend_agent
)

task_frontend = Task(
    description="""
    根据 PM 的技术需求文档和后端 API，实现前端界面。
    
    要求：
    - React + TypeScript
    - 记账表单（金额、分类下拉、备注、日期选择）
    - 交易列表（分页、筛选）
    - 月度汇总卡片
    - 分类饼图（用 recharts）
    """,
    expected_output="完整的前端代码，包含所有页面和组件",
    agent=frontend_agent
)

task_qa = Task(
    description="""
    审查前后端代码，检查：
    1. 前端是否处理了 Loading/空数据/错误三种状态
    2. 后端 API 是否有输入校验
    3. 前后端数据格式是否一致
    
    输出测试报告和改进建议。
    """,
    expected_output="测试报告，列出发现的问题和建议",
    agent=qa_agent
)
```

---

## 五、组建 Crew 并运行

```python
# ── 3. 组建团队 ──

dev_team = Crew(
    agents=[pm_agent, frontend_agent, backend_agent, qa_agent],
    tasks=[task_prd, task_backend, task_frontend, task_qa],
    process=Process.sequential,  # 顺序执行：PM → 后端 → 前端 → 测试
    verbose=True
)

# ── 4. 启动！ ──
result = dev_team.kickoff()
print(result)
```

**执行过程**：

```
🚀 Crew 启动
  ├── PM Agent 正在写 PRD...
  │   ✅ PRD 完成（技术栈：React + FastAPI + SQLite）
  ├── 后端 Agent 正在写代码...
  │   ✅ 5 个 API 接口完成
  ├── 前端 Agent 正在写代码...
  │   ✅ 4 个页面组件完成
  └── 测试 Agent 正在审查...
      ✅ 发现 3 个问题，建议 2 处改进

📦 交付物：
  - 技术需求文档 × 1
  - 后端代码 × 5 文件
  - 前端代码 × 6 文件
  - 测试报告 × 1
```

---

## 六、两种协作模式

### Sequential（顺序模式）

```
Task 1 → Task 2 → Task 3 → Task 4
 (PM)    (后端)    (前端)    (QA)
```

每个任务的输出自动作为下一个任务的上下文。适合**有明确前后依赖**的任务。

### Hierarchical（层级模式）

```
           ┌─────────┐
           │ Manager  │  ← 分配任务、审核结果
           │  Agent   │
           └────┬─────┘
    ┌───────────┼───────────┐
    ▼           ▼           ▼
Agent 1     Agent 2     Agent 3
```

Manager Agent 负责拆任务、分派、汇总。适合**复杂、需要动态决策**的场景。

```python
# 层级模式示例
manager = Agent(
    role="技术总监",
    goal="协调开发团队，确保项目按时高质量交付",
    backstory="你是技术总监，10 年经验，擅长资源调配和项目管控",
    llm=llm,
    allow_delegation=True  # 允许委派任务
)

hierarchical_crew = Crew(
    agents=[manager, frontend_agent, backend_agent, qa_agent],
    tasks=[task_prd, task_backend, task_frontend, task_qa],
    process=Process.hierarchical,
    manager_agent=manager
)
```

---

## 七、Multi-Agent 实战要点

### 7.1 Agent 角色要互补而非重叠

```
❌ 两个 Agent 都会写 React → 代码冲突
✅ 前端 Agent 写 UI，UI 设计 Agent 出设计稿
```

### 7.2 任务描述要能被下游消费

```python
# ❌ 太模糊
Task(description="写后端代码", ...)

# ✅ 下游 Agent 能直接用
Task(
    description="根据 PRD 实现 API。输出格式：Python 代码，每个文件用 === FILE: xxx.py === 分隔",
    expected_output="格式化的 Python 代码",
    ...
)
```

### 7.3 设置重试和超时

```python
Task(
    ...,
    max_retries=2,      # 失败重试 2 次
    max_execution_time=300  # 最多 5 分钟
)
```

---

## 八、CrewAI vs AutoGen vs LangGraph

| 维度 | CrewAI | AutoGen | LangGraph |
|------|:--:|:--:|:--:|
| 学习曲线 | ⭐⭐ 简单 | ⭐⭐⭐ 中等 | ⭐⭐⭐⭐ 较陡 |
| 角色定义 | Role + Goal + Backstory | Agent + System Message | Node 函数 |
| 协作模式 | 顺序 / 层级 | 对话式 | 状态图 |
| 适合场景 | 固定流程 | 动态对话 | 精细控制 |
| 中文支持 | ✅ 好 | 🟡 一般 | ✅ 好 |

> **建议**：先用 CrewAI 入门，理解 Multi-Agent 的逻辑后再学 LangGraph 做精细控制。

---

## 九、总结

1. **Multi-Agent 解决单 Agent 的复杂度瓶颈**——术业有专攻
2. **CrewAI 用角色+目标+背景定义 Agent**——像招人一样招 AI
3. **顺序模式适合固定流程，层级模式适合动态决策**
4. **Agent 角色要互补、任务描述要明确、输出格式要规范**

---

> 🎉 系列完结。从 LLM 原理到 Multi-Agent 协作，8 篇文章覆盖 Agent 开发全路径。接下来就是动手做项目——把学到的每一块拼成你自己的 Agent 产品。

*系列文章：00-总纲 → ①-LLM 原理 → ②-Prompt 工程 → ③-Function Calling → ④-RAG → ⑤-Agent 模式 → ⑥-LangGraph → ⑦-MCP → ⑧-Multi-Agent*
