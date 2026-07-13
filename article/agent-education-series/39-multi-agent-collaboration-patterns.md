# 【AI Agent 系统教学 39】多 Agent 协作模式

> 单 Agent 是"单打独斗"，多 Agent 是"团队作战"。
> 不同的协作模式，适合不同的任务。

---

## 前言：多 Agent 协作的本质

多 Agent 协作 = 多个 Agent 通过通信和协调，共同完成单个 Agent 无法完成的任务。

不同的协作模式，对应不同的"团队合作方式"：

```
辩论模式：不同观点碰撞，找到最优解
投票模式：多个 Agent 独立判断，取多数意见
分工模式：各司其职，最后汇总
流水线模式：A → B → C，逐级处理
经理-员工模式：一个管理者，多个执行者
```

---

## 一、辩论模式

### 1.1 核心思想

多个 Agent 扮演不同角色，对同一个问题进行辩论，通过讨论逼近最优解。

```python
class DebateTeam:
    """辩论团队"""
    def __init__(self, llm):
        self.agents = {
            "optimist": Agent("乐观派", "关注积极面"),
            "pessimist": Agent("悲观派", "关注风险"),
            "analyst": Agent("分析师", "关注数据"),
            "moderator": Agent("主持人", "控制节奏"),
        }
    
    def debate(self, question, max_rounds=3):
        """多轮辩论"""
        transcript = []
        
        for round in range(max_rounds):
            round_opinions = {}
            
            for name, agent in self.agents.items():
                if name == "moderator":
                    continue
                
                opinion = agent.argue(question, transcript)
                round_opinions[name] = opinion
            
            # 主持人总结
            summary = self.agents["moderator"].summarize(round_opinions)
            transcript.append({
                "round": round,
                "opinions": round_opinions,
                "summary": summary,
            })
        
        # 最终结论
        conclusion = self.agents["moderator"].conclude(transcript)
        return conclusion
```

### 1.2 适用场景

```
辩论模式适合：
  ✅ 有多个可行方案的决策
  ✅ 需要权衡利弊的问题
  ✅ 需要批判性思考的任务
  ✅ 风险较高的决策

辩论模式不适合：
  ❌ 需要快速响应的任务
  ❌ 事实性问题（有标准答案）
  ❌ 简单任务
```

---

## 二、投票模式

### 2.1 核心思想

多个 Agent 独立处理同一个问题，然后投票选出最佳答案。

```python
class VotingSystem:
    """投票系统"""
    def __init__(self, agents, voting_strategy="majority"):
        self.agents = agents
        self.strategy = voting_strategy
    
    def solve(self, task):
        # 1. 每个 Agent 独立处理
        results = []
        for agent in self.agents:
            result = agent.solve(task)
            results.append(result)
        
        # 2. 投票
        if self.strategy == "majority":
            return self._majority_vote(results)
        elif self.strategy == "weighted":
            return self._weighted_vote(results)
        elif self.strategy == "consensus":
            return self._consensus_vote(results)
    
    def _majority_vote(self, results):
        """多数投票"""
        from collections import Counter
        answers = [r["answer"] for r in results]
        most_common = Counter(answers).most_common(1)
        return most_common[0][0] if most_common else None
    
    def _weighted_vote(self, results):
        """加权投票（按 Agent 的历史准确率加权）"""
        weighted = {}
        for r in results:
            answer = r["answer"]
            weight = r.get("confidence", 1.0) * self.agents[0].accuracy
            weighted[answer] = weighted.get(answer, 0) + weight
        return max(weighted, key=weighted.get)
```

### 2.2 适用场景

```
投票模式适合：
  ✅ 有标准答案的问题（数学、事实）
  ✅ 需要高准确率的任务
  ✅ 可以容忍多次执行成本

投票模式不适合：
  ❌ 创造性任务（没有标准答案）
  ❌ 成本敏感的场景
  ❌ 需要解释的任务
```

---

## 三、分工模式

### 3.1 核心思想

把任务分解成多个子任务，每个 Agent 负责自己擅长的部分。

```python
class DivisionOfWork:
    """分工协作"""
    def __init__(self):
        self.agents = {
            "researcher": Agent("研究员", ["search", "analyze"]),
            "writer": Agent("写手", ["write", "format"]),
            "designer": Agent("设计师", ["design", "layout"]),
            "reviewer": Agent("审核员", ["review", "validate"]),
        }
    
    def execute(self, task):
        # 1. 分解任务
        subtasks = {
            "research": "研究主题，收集资料",
            "write": "撰写内容",
            "design": "设计排版",
            "review": "审核质量",
        }
        
        # 2. 并行执行
        with ThreadPoolExecutor() as executor:
            futures = {
                executor.submit(self.agents["researcher"].execute, subtasks["research"]): "research",
                executor.submit(self.agents["writer"].execute, subtasks["write"]): "write",
                executor.submit(self.agents["designer"].execute, subtasks["design"]): "design",
            }
            
            results = {}
            for future in as_completed(futures):
                name = futures[future]
                results[name] = future.result()
        
        # 3. 审核
        review_result = self.agents["reviewer"].execute(
            f"审核以下内容：{results}"
        )
        
        # 4. 汇总
        return self._merge(results, review_result)
```

### 3.2 适用场景

```
分工模式适合：
  ✅ 复杂的大型任务
  ✅ 需要多种专业能力的任务
  ✅ 可以并行处理的子任务

分工模式不适合：
  ❌ 简单任务（杀鸡用牛刀）
  ❌ 子任务之间强依赖
  ❌ Agent 能力重复
```

---

## 四、流水线模式

### 4.1 核心思想

Agent 按顺序处理，前一个的输出是后一个的输入。

```python
class PipelineMode:
    """流水线协作"""
    def __init__(self):
        self.stages = [
            Stage("分析师", "分析需求"),
            Stage("规划师", "制定方案"),
            Stage("执行者", "执行方案"),
            Stage("验证者", "验证结果"),
        ]
    
    def execute(self, task):
        current = task
        
        for stage in self.stages:
            # 每个阶段处理
            result = stage.agent.process(current)
            
            # 质量检查
            if not stage.validate(result):
                # 回退到上一阶段
                return self._rollback(stage, current)
            
            current = result
        
        return current
```

### 4.2 适用场景

```
流水线模式适合：
  ✅ 步骤明确的流程
  ✅ 每个步骤有明确输入输出
  ✅ 需要质量控制的场景

流水线模式不适合：
  ❌ 需要灵活调整的任务
  ❌ 步骤间需要大量交互
  ❌ 并行任务
```

---

## 五、经理-员工模式

### 5.1 核心思想

一个经理 Agent 负责规划、分配、监督，多个员工 Agent 负责执行。

```python
class ManagerWorkerMode:
    """经理-员工模式"""
    def __init__(self):
        self.manager = Agent("经理", ["规划", "分配", "监督"])
        self.workers = [
            Agent("员工1", ["执行", "报告"]),
            Agent("员工2", ["执行", "报告"]),
            Agent("员工3", ["执行", "报告"]),
        ]
    
    def execute(self, task):
        # 1. 经理规划
        plan = self.manager.plan(task)
        
        # 2. 经理分配任务
        assignments = self.manager.assign(plan, self.workers)
        
        # 3. 员工执行
        results = {}
        for worker, subtasks in assignments.items():
            for subtask in subtasks:
                results[subtask.id] = worker.execute(subtask)
        
        # 4. 经理监督和汇总
        report = self.manager.review(results)
        return report
```

---

## 六、协作模式选型

### 6.1 选型决策树

```
你的任务：
├─ 有标准答案 → 投票模式
├─ 需要创造性 → 辩论模式
├─ 复杂、多步骤 → 分工模式
├─ 步骤明确、流水线 → 流水线模式
├─ 需要管理监督 → 经理-员工模式
└─ 混合型 → 组合使用
```

### 6.2 协作模式对比

| 模式 | 质量 | 速度 | 成本 | 复杂度 |
|------|------|------|------|--------|
| 辩论 | 高 | 慢 | 高 | 高 |
| 投票 | 很高 | 慢 | 高 | 中 |
| 分工 | 中 | 快 | 中 | 中 |
| 流水线 | 中 | 中 | 中 | 低 |
| 经理-员工 | 高 | 中 | 高 | 高 |

---

## 总结

| 模式 | 一句话 | 核心优势 |
|------|--------|---------|
| 辩论 | 碰撞出真理 | 多角度思考 |
| 投票 | 多数人是对的 | 高准确率 |
| 分工 | 各司其职 | 并行效率 |
| 流水线 | 逐级处理 | 流程清晰 |
| 经理-员工 | 统一指挥 | 管控有力 |

**选择协作模式的核心原则：匹配任务特性。**

下一篇文章，我们将深入**Agent 编排器与 Subagent**。

---

**思考题**：
1. 辩论模式中，如果 Agent 的观点一致，还有辩论的价值吗？
2. 投票模式中，如果多数 Agent 都错了，怎么办？
3. 你会在什么场景下使用"经理-员工"模式？什么场景下不会？

---

> 上一篇：[38] Agent 通信协议
> 下一篇：[40] Agent 编排器与 Subagent
> 系列目录：[README.md](./README.md)