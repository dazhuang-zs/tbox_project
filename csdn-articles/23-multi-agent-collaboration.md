# 【AI Agent 内核】23 · 多智能体协作：三种架构模式的工程实践与选择指南

> **标签**：`#AI Agent` `#Multi-Agent` `#LangGraph` `#CrewAI` `#架构设计`

> 单 Agent 的瓶颈是明显的：上下文窗口有限，单一角色无法处理复杂场景，一个 Agent 的推理偏差会导致全局崩溃。多智能体协作不是"多调几个 Agent"那么简单——架构选错了，3 个 Agent 的产出可能还不如 1 个。本文从三种协作拓扑的工程实现出发，给你选择标准和避坑指南。

---

## 一、什么时候单 Agent 不够用了？

三个信号告诉你该考虑多 Agent 了：

| 信号 | 症状 | 为什么单 Agent 不行 |
|------|------|-------------------|
| 上下文爆炸 | 对话超过 50 轮后 Agent 开始"忘事" | 单上下文窗口有限，职责混合导致注意分散 |
| 角色冲突 | 一个任务需要"规划者"和"执行者"两种思维 | LLM 在"先想大框架"和"立刻写代码"之间摇摆 |
| 工具爆炸 | Agent 需要调用 20+ 个工具 | 工具选择准确率从 95% 降到 70% |

**关键洞察**（来自 Lanham 书中的实验数据）：当工具数量超过 15 个，单 Agent 的工具选择准确率断崖式下降。分拆成 3 个专业 Agent（每个 5 个工具），准确率回升到 93%。

---

## 二、拓扑 A：顺序流水线（Sequential Pipeline）

```
┌──────────┐     ┌──────────┐     ┌──────────┐
│ Agent A  │ ──→ │ Agent B  │ ──→ │ Agent C  │ ──→ 结果
│ 规划     │     │ 执行     │     │ 审查     │
└──────────┘     └──────────┘     └──────────┘
```

### 适用场景
- 任务步骤之间**有明确的前后依赖**
- 每个阶段有**清晰的输入/输出 Schema**
- 需要质量把关（最后一步是审查 Agent）

### 工程实现（基于 LangGraph）

```python
from typing import TypedDict, List
from langgraph.graph import StateGraph, END

# 1. 定义状态（Agent 间的"消息格式"）
class PipelineState(TypedDict):
    task: str                    # 原始任务
    plan: List[str]              # 规划 Agent 的输出
    code: str                    # 编码 Agent 的输出
    review_comments: List[str]   # 审查 Agent 的输出
    final_result: str            # 最终结果
    stage: str                   # 当前阶段：planning/coding/reviewing/done

# 2. 定义三个 Agent
class PlanningAgent:
    """架构师 Agent — 只负责规划"""
    
    def __call__(self, state: PipelineState) -> PipelineState:
        plan = self._generate_plan(state["task"])
        return {
            **state,
            "plan": plan,
            "stage": "planning_done"
        }
    
    def _generate_plan(self, task: str) -> List[str]:
        # 实际调用 LLM，返回结构化的步骤列表
        return [
            "Step 1: 分析需求，确定技术方案",
            "Step 2: 设计数据模型",
            "Step 3: 实现核心逻辑",
            "Step 4: 编写测试"
        ]

class CodingAgent:
    """工程师 Agent — 只负责写代码"""
    
    def __call__(self, state: PipelineState) -> PipelineState:
        code = self._implement_plan(state["plan"])
        return {
            **state,
            "code": code,
            "stage": "coding_done"
        }
    
    def _implement_plan(self, plan: List[str]) -> str:
        # 按照 planner 的步骤逐条实现
        # 注意：这里不会"推翻重来"，只执行
        return "def solution():\n    # implementation\n    pass"

class ReviewerAgent:
    """审查 Agent — 只负责检查质量"""
    
    def __call__(self, state: PipelineState) -> PipelineState:
        comments = self._review_code(state["code"], state["plan"])
        
        if self._has_blocking_issues(comments):
            # 有严重问题，退回 Coding Agent
            return {
                **state,
                "review_comments": comments,
                "stage": "needs_fix"  # 触发回退
            }
        else:
            return {
                **state,
                "review_comments": comments,
                "final_result": state["code"],
                "stage": "done"
            }
    
    def _review_code(self, code: str, plan: List[str]) -> List[str]:
        return ["✅ 代码结构清晰", "⚠️ 缺少异常处理", "✅ 符合 plan 的步骤要求"]

# 3. 构建流水线
def build_sequential_pipeline():
    graph = StateGraph(PipelineState)
    
    graph.add_node("planner", PlanningAgent())
    graph.add_node("coder", CodingAgent())
    graph.add_node("reviewer", ReviewerAgent())
    
    # 定义流向
    graph.set_entry_point("planner")
    graph.add_edge("planner", "coder")
    graph.add_edge("coder", "reviewer")
    
    # 条件路由：审查不通过 → 退回 coder
    graph.add_conditional_edges(
        "reviewer",
        lambda state: "coder" if state["stage"] == "needs_fix" else END
    )
    
    return graph.compile()
```

### 流水线模式的优缺点

| ✅ 优点 | ❌ 缺点 |
|---------|---------|
| 结构清晰，容易调试 | 上游错误会传导到下游 |
| 每个 Agent 职责单一，工具集小 | 不灵活，不能动态调整流程 |
| 审查 Agent 提供质量保证 | 一个 Agent 慢了，整条线阻塞 |

### 一个真实的坑

```
Planner 生成的 step 顺序错了 → Coder 忠实地按错误顺序写 → 
Reviewer 发现了问题 → 退回 Coder → Coder 重写 →

但如果 Planner 的 plan 有根本性错误（比如技术选型不对），
Coder 和 Reviewer 可能在"错误的方向上反复重试"。
```

**解法**：Planner 出错时，退回的不是 Coder 而是 Planner 本身。

---

## 三、拓扑 B：层级调度（Hierarchical Orchestration）

```
                ┌──────────────┐
                │ Orchestrator │  ← 分析任务 + 分派 + 汇总
                └──┬───────┬───┘
                   │       │
          ┌────────▼──┐ ┌──▼────────┐
          │ Agent A   │ │ Agent B   │  ← 领域专家
          │ 前端专家  │ │ 后端专家  │
          └───────────┘ └───────────┘
```

### 适用场景
- 任务可以**分解成独立子任务**
- 不同子任务需要**不同领域的专业能力**
- 需要一个"总指挥"来**协调和汇总**

### 工程实现

```python
from typing import List, Dict
from langgraph.graph import StateGraph
import asyncio

class OrchestratorAgent:
    """调度器 — 整个系统的"大脑""""
    
    def __call__(self, state: dict) -> dict:
        # 1. 分析任务
        task = state["task"]
        subtasks = self._decompose(task)
        # subtasks = [
        #     {"id": "1", "domain": "frontend", "desc": "设计页面布局"},
        #     {"id": "2", "domain": "backend", "desc": "设计API接口"},
        #     {"id": "3", "domain": "database", "desc": "设计数据表"}
        # ]
        
        # 2. 并行分派给领域专家
        results = asyncio.run(self._dispatch_parallel(subtasks))
        
        # 3. 检查结果质量
        failed = [r for r in results if r["quality_score"] < 0.7]
        if failed:
            # 质量不够，重试（最多 2 次）
            retry_results = asyncio.run(
                self._dispatch_parallel(failed, retry_count=1)
            )
            results.extend(retry_results)
        
        # 4. 汇总
        return {
            **state,
            "sub_results": results,
            "final_output": self._synthesize(results)
        }
    
    def _decompose(self, task: str) -> List[Dict]:
        """关键能力：把大任务拆成小任务"""
        # 调用 LLM 进行任务分解
        # 输出格式：[{domain, desc, expected_output_format}]
        pass
    
    async def _dispatch_parallel(self, subtasks: List[Dict], 
                                  retry_count: int = 0) -> List[Dict]:
        """并行分发——不是顺序执行"""
        tasks = []
        for subtask in subtasks:
            agent = self._select_agent(subtask["domain"])
            tasks.append(agent.execute(subtask, retry_count))
        
        return await asyncio.gather(*tasks)
    
    def _select_agent(self, domain: str):
        """基于能力描述选择 Agent"""
        agents = {
            "frontend": FrontendAgent(),
            "backend": BackendAgent(),
            "database": DatabaseAgent(),
            "devops": DevOpsAgent()
        }
        return agents.get(domain, GeneralAgent())
    
    def _synthesize(self, results: List[Dict]) -> str:
        """汇总多个 Agent 的结果为一个整体输出"""
        # 处理跨子任务的依赖关系
        # 例如：前端 Agent 需要后端 Agent 的 API 定义
        pass

class FrontendAgent:
    """前端专家 — 只要知道输入/输出就行，不关心其他 Agent 做了什么"""
    
    def execute(self, subtask: Dict, retry_count: int) -> Dict:
        result = self._do_work(subtask)
        # 自评质量
        quality = self._self_evaluate(result)
        return {
            "subtask_id": subtask["id"],
            "domain": subtask["domain"],
            "output": result,
            "quality_score": quality
        }
```

### 层级调度的关键设计决策

| 决策点 | 错误做法 | 正确做法 |
|--------|---------|---------|
| 任务分解 | 让 Orchestrator 拍脑袋 | 先让 Orchestrator 提出计划 → 再让各领域 Agent 确认可行性 |
| 并行 vs 串行 | 全部并行（忽略依赖） | 识别依赖关系，有依赖的串行，无依赖的并行 |
| 结果汇总 | 简单拼接 | 检查跨子任务的一致性（前端需要的 API 是否和后端产出的匹配） |
| 失败处理 | 整体回滚 | 只重试失败的子任务，不影响已成功的 |

### Orchestrator 是单点——怎么防？

```python
class ResilientOrchestrator:
    """带熔断和降级的调度器"""
    
    def execute_with_safety(self, task: str):
        try:
            # 正常执行
            return self.orchestrator(task)
        except AgentTimeoutException:
            # 超时 → 降级为简单模式
            return self._fallback_simple_execution(task)
        except AgentLoopException:
            # Agent 陷入循环 → 人工介入
            return self._request_human_intervention(task)
    
    def _fallback_simple_execution(self, task: str):
        """降级方案：跳过 Orchestrator，直接用单 Agent 处理"""
        return SingleAgent().execute(task)
```

---

## 四、拓扑 C：对等协作（Peer-to-Peer Debate）

```
    Agent A ←→ Agent B
       ↕         ↕
    Agent C ←→ Agent D

没有"领导"，互相辩论，达成共识
```

### 适用场景
- 需要**多视角分析**的决策型任务
- 没有"正确答案"的开放性问题
- 需要消除单 Agent 偏见的场景

### 工程实现：辩论协议

```python
class DebateProtocol:
    """多 Agent 辩论协议"""
    
    def __init__(self, agents: List[str], max_rounds: int = 3):
        self.agents = agents  # ["分析师A", "分析师B", "分析师C"]
        self.max_rounds = max_rounds
        self.round_history = []
    
    def debate(self, question: str) -> Dict:
        """
        辩论流程：
        Round 1: 各 Agent 独立发表观点
        Round 2: 各 Agent 评价他人观点 + 修正自己观点
        Round 3: 投票 + 合成最终共识
        """
        
        # Round 1: 独立观点
        initial_opinions = {}
        for agent in self.agents:
            opinion = self._ask_agent(agent, question)
            initial_opinions[agent] = opinion
        
        self.round_history.append({
            "round": 1,
            "type": "initial",
            "opinions": initial_opinions
        })
        
        # Round 2-N: 互评 + 修正
        current_opinions = initial_opinions
        for round_num in range(2, self.max_rounds + 1):
            updated_opinions = {}
            for agent in self.agents:
                # 让每个 Agent 看到其他人的观点
                others = {a: o for a, o in current_opinions.items() if a != agent}
                
                critique_and_revise = self._ask_agent(
                    agent,
                    f"""原始问题：{question}
                    
                    你的上一轮观点：{current_opinions[agent]}
                    
                    其他Agent的观点：
                    {self._format_others(others)}
                    
                    请：1. 评价其他人的观点（哪些同意、哪些不同意、为什么）
                        2. 根据讨论修正你的观点
                    
                    输出JSON格式：{{"critique": "...", "revised_opinion": "..."}}"""
                )
                
                updated_opinions[agent] = critique_and_revise
            
            current_opinions = updated_opinions
            self.round_history.append({
                "round": round_num,
                "type": "revision",
                "opinions": current_opinions
            })
        
        # Final: 投票 + 共识合成
        return self._synthesize_consensus(question, self.round_history)
    
    def _synthesize_consensus(self, question: str, history: List) -> Dict:
        """从辩论历史中提取共识"""
        # 识别所有 Agent 一致同意的点
        # 标记有分歧的点
        # 对于分歧，采用多数投票或交由人工决策
        
        consensus_points = self._find_consensus(history)
        disagreements = self._find_disagreements(history)
        
        return {
            "consensus": consensus_points,       # 一致意见
            "disagreements": disagreements,       # 分歧点（需要人工决策）
            "confidence": self._calc_confidence(consensus_points, disagreements),
            "debate_summary": self._summarize_debate(history)
        }
```

### 辩论模式的致命弱点

**不是所有问题都适合辩论。** 以下是判断标准：

| 适合辩论 | 不适合辩论 |
|----------|-----------|
| 技术选型（React vs Vue） | 事实性问题（"1+1=?"） |
| 架构设计（微服务 vs 单体） | 有明确标准的任务 |
| 风险评估（这个方案的风险） | 需要快速决策的场景（时间成本太高） |
| 需要消除偏见的决策 | Agent 之间能力相同（辩论无意义） |

---

## 五、三种拓扑的选择决策树

```
你的任务是不是有明显的前后步骤？
    ├── 是 → 每个步骤的输出是否可清晰定义？
    │       ├── 是 → 用「顺序流水线」
    │       └── 否 → 往下看
    └── 否 → 任务能不能拆成独立子任务？
            ├── 是 → 子任务需要不同领域专长？
            │       ├── 是 → 用「层级调度」
            │       └── 否 → 用一个 Agent 就够了
            └── 否 → 任务是不是开放性决策？
                    ├── 是 → 你对时间敏感吗？
                    │       ├── 是 → 用单 Agent + 多次采样
                    │       └── 否 → 用「对等协作辩论」
                    └── 否 → 用一个 Agent 就够了
```

---

## 六、多 Agent 系统的通用陷阱

### 陷阱 1：过度工程化

```
初学者："我用 6 个 Agent 搭建了一个博客生成器！"
老手："这个任务一个 Agent 就够了，你那 5 个 Agent 在互相传话浪费时间。"

数据：CrewAI 官方文档建议 Agent 数量≤5。
     超过 5 个 Agent，协调开销指数级增长。
```

### 陷阱 2：Agent 之间的"传话游戏"

```
Agent A → "请生成一个蓝色按钮"
Agent B → 收到后转给 Agent C → "请生成一个按钮"
Agent C → 收到后转给 Agent D → "请生成"

信息在传递中逐级丢失。3 次传递后，原始指令只剩 40%。
```

**解法**：关键信息放在共享 State 里，不通过 Agent 之间传话。

### 陷阱 3：虚假共识

```
辩论模式下，3 个 Agent 用同一个 LLM（比如都是 GPT-4）
→ 它们的"观点"可能高度一致（因为训练数据相同）
→ 看起来达成了共识，实际上只是同源偏见
```

**解法**：辩论模式中混用不同模型（GPT-4 + Claude + Gemini）。

---

## 七、总结

| 拓扑 | 一句话 | 最佳场景 |
|------|--------|---------|
| 顺序流水线 | 流水线作业，一次只做一件事 | 有明确步骤的代码生成 |
| 层级调度 | 一个大脑，多个手脚 | 复杂项目的多领域协作 |
| 对等辩论 | 三个诸葛亮顶个臭皮匠 | 技术决策、风险评估 |

**核心原则**：能用一个 Agent 解决的，不要用多个。Agent 数量增加 = 系统复杂度指数增加。

---

*你的多 Agent 系统用了哪种拓扑？踩过"过度工程化"的坑吗？👇*
