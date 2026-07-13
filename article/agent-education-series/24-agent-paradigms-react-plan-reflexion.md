# 【AI Agent 系统教学 24】Agent 范式巡礼：ReAct、Plan-and-Execute、Reflexion

> 一个 Agent 怎么做决策？这不是"让 LLM 自由发挥"的问题。
> 不同的范式，决定了 Agent 能做什么、不能做什么、做得好不好。

---

## 前言：Agent 的"工作模式"

Agent 的核心是"决策循环"——感知、思考、行动、再感知。

但"思考"的方式有很多种：

- 是边想边做，还是想好了再做？
- 做错了怎么发现？怎么纠正？
- 遇到复杂任务，怎么分解？

**不同的范式，对应不同的决策模式。**

---

## 一、ReAct：边想边做

### 1.1 核心思想

ReAct（Reasoning + Acting）是 2023 年提出的 Agent 范式，也是目前最广泛使用的范式。

**核心思想**：推理和行动交织进行——想一步，做一步，观察结果，再想下一步。

```
Thought: 用户想知道北京天气，我需要查询天气工具
Action: get_weather("北京")
Observation: {"temperature": 25, "condition": "晴"}
Thought: 北京 25 度，晴天，适合户外活动
Action: 生成回复
```

### 1.2 实现

```python
class ReActAgent:
    def __init__(self, llm, tools, max_steps=10):
        self.llm = llm
        self.tools = tools
        self.max_steps = max_steps
    
    def run(self, task):
        steps = []
        for i in range(self.max_steps):
            # 1. 思考
            thought = self._think(task, steps)
            
            # 2. 行动
            action = self._decide_action(thought)
            
            if action["type"] == "finish":
                return action["output"]
            
            # 3. 观察
            observation = self._execute_action(action)
            
            steps.append({
                "thought": thought,
                "action": action,
                "observation": observation,
            })
        
        return "达到最大步数"
    
    def _think(self, task, steps):
        """生成思考"""
        prompt = f"任务：{task}\n历史步骤：{steps}\n下一步思考："
        return self.llm.generate(prompt)
    
    def _decide_action(self, thought):
        """从思考中提取行动"""
        # 解析 thought 中的 Action 部分
        return parse_action(thought)
```

### 1.3 ReAct 的优缺点

| 优点 | 缺点 |
|------|------|
| 灵活，每一步都基于当前信息 | 可能陷入局部最优 |
| 容易实现，逻辑直观 | 多步后可能偏离目标 |
| 适合交互式任务 | 缺乏全局规划 |
| 能处理不确定性 | 对复杂任务效率低 |

### 1.4 适用场景

```
ReAct 适合：
  ✅ 需要实时信息的任务（查询天气、搜索）
  ✅ 交互式任务（客服、对话）
  ✅ 不确定性高的任务
  ✅ 简单到中等复杂度的任务

ReAct 不适合：
  ❌ 需要全局规划的任务
  ❌ 需要精确多步执行的任务
  ❌ 需要长期执行的复杂任务
```

---

## 二、Plan-and-Execute：先想再做

### 2.1 核心思想

Plan-and-Execute 把"思考"和"执行"分开：

1. **规划阶段**：先制定完整的计划
2. **执行阶段**：按计划执行，监控进度

```
Phase 1: 规划
Task: 帮我研究 Python 和 JavaScript 的区别，写一篇对比报告

Plan:
1. 搜索 Python 的核心特点
2. 搜索 JavaScript 的核心特点
3. 对比两者的语法差异
4. 对比两者的性能差异
5. 对比两者的适用场景
6. 整理成对比报告

Phase 2: 执行
Step 1: search("Python 核心特点") → 完成
Step 2: search("JavaScript 核心特点") → 完成
...
Step 6: 生成报告 → 完成
```

### 2.2 实现

```python
class PlanExecuteAgent:
    def __init__(self, llm, tools):
        self.llm = llm
        self.tools = tools
    
    def run(self, task):
        # Phase 1: 规划
        plan = self._create_plan(task)
        
        # Phase 2: 执行
        results = []
        for step in plan:
            result = self._execute_step(step)
            results.append(result)
            
            # 可选：根据执行结果调整计划
            if self._needs_replan(task, plan, results):
                plan = self._replan(task, plan, results)
                results = []
        
        # 最终输出
        return self._generate_output(task, plan, results)
    
    def _create_plan(self, task):
        prompt = f"""
        任务：{task}
        
        请制定一个详细的执行计划，包括具体步骤：
        每个步骤应该：
        - 有明确的目标
        - 可独立执行
        - 指定使用的工具
        
        计划：
        """
        plan_text = self.llm.generate(prompt)
        return parse_plan(plan_text)
    
    def _execute_step(self, step):
        """执行单个步骤"""
        action = step["action"]
        tool = self.tools[action["tool"]]
        return tool.execute(action["params"])
    
    def _needs_replan(self, task, plan, results):
        """判断是否需要重新规划"""
        prompt = f"""
        任务：{task}
        计划：{plan}
        当前执行结果：{results}
        
        是否需要调整计划？回答"是"或"否"。
        """
        return self.llm.generate(prompt) == "是"
```

### 2.3 Plan-and-Execute 的优缺点

| 优点 | 缺点 |
|------|------|
| 有全局视野，不容易偏离目标 | 规划可能不切实际 |
| 执行效率高（减少无用步骤） | 缺乏灵活性（严格按照计划） |
| 易于监控进度 | 规划本身耗时长 |
| 适合复杂任务 | 意外情况处理弱 |

### 2.4 适用场景

```
Plan-and-Execute 适合：
  ✅ 复杂、多步骤的任务
  ✅ 需要全局规划的任务
  ✅ 可预测性高的任务
  ✅ 需要监控进度的任务

Plan-and-Execute 不适合：
  ❌ 需要实时互动的任务
  ❌ 不确定性高的任务
  ❌ 简单任务（杀鸡用牛刀）
```

---

## 三、Reflexion：反思与修正

### 3.1 核心思想

Reflexion 在 ReAct 的基础上增加了**反思**环节——Agent 不仅执行，还会总结经验教训，用于后续的改进。

```
Task: 实现一个二分查找函数

Attempt 1:
  Thought: 二分查找需要找到中间点
  Action: 写代码
  Observation: 代码有 bug，列表索引越界
  Reflection: 我忘记检查列表为空的情况，我需要加上边界检查

Attempt 2:
  Thought: 基于上次的反思，这次加上边界检查
  Action: 修改代码
  Observation: 代码运行正确
  Reflection: 边界检查很重要，以后写算法时优先考虑
```

### 3.2 实现

```python
class ReflexionAgent:
    def __init__(self, llm, tools, max_attempts=5):
        self.llm = llm
        self.tools = tools
        self.max_attempts = max_attempts
        self.memories = []  # 存储反思经验
    
    def run(self, task):
        for attempt in range(self.max_attempts):
            # 1. 执行
            result = self._execute(task, self.memories)
            
            # 2. 评估
            evaluation = self._evaluate(task, result)
            
            if evaluation["success"]:
                return result
            
            # 3. 反思
            reflection = self._reflect(task, result, evaluation)
            self.memories.append(reflection)
        
        return "达到最大尝试次数"
    
    def _execute(self, task, memories):
        """执行任务（使用 ReAct 范式）"""
        prompt = f"""
        任务：{task}
        
        历史经验（从之前的尝试中总结）：
        {format_memories(memories)}
        
        请执行任务：
        """
        return self.llm.generate(prompt)
    
    def _evaluate(self, task, result):
        """评估执行结果"""
        prompt = f"""
        任务：{task}
        执行结果：{result}
        
        评估：
        1. 任务是否成功完成？是/否
        2. 如果失败，原因是什么？
        3. 如何改进？
        """
        evaluation = self.llm.generate(prompt)
        return parse_evaluation(evaluation)
    
    def _reflect(self, task, result, evaluation):
        """生成反思"""
        return {
            "task": task,
            "failed_result": result,
            "reason": evaluation["reason"],
            "improvement": evaluation["improvement"],
            "lesson": f"在 {task} 中，因为 {evaluation['reason']} 失败，下次应该 {evaluation['improvement']}",
        }
```

### 3.3 Reflexion 的优缺点

| 优点 | 缺点 |
|------|------|
| 从错误中学习 | 多次尝试耗时长、成本高 |
| 不断提高准确率 | 反思可能不准确 |
| 积累了可复用的经验 | 经验可能过时 |
| 适合高难度任务 | 简单任务不需要 |

### 3.4 适用场景

```
Reflexion 适合：
  ✅ 需要高准确率的任务
  ✅ 复杂推理任务（如数学、代码）
  ✅ 有明确评估标准的任务
  ✅ 能容忍多次尝试的任务

Reflexion 不适合：
  ❌ 实时响应任务
  ❌ 成本敏感的任务
  ❌ 简单任务
```

---

## 四、三大范式对比

### 4.1 对比总结

| 维度 | ReAct | Plan-and-Execute | Reflexion |
|------|-------|-----------------|-----------|
| 思考方式 | 边想边做 | 先想再做 | 边想边做+反思 |
| 规划深度 | 浅（单步规划） | 深（全局规划） | 中（逐步迭代） |
| 灵活性 | 高 | 低 | 中 |
| 容错性 | 中 | 低 | 高 |
| 效率 | 中等 | 高 | 低 |
| 实现复杂度 | 低 | 中 | 高 |
| 适用任务 | 中等 | 复杂 | 高难度 |

### 4.2 选型建议

```
你的任务：
├─ 简单、快速 → ReAct
├─ 复杂、可规划 → Plan-and-Execute
├─ 高难度、需准确 → Reflexion
└─ 混合 → 组合使用
```

### 4.3 组合使用

```python
class HybridAgent:
    def __init__(self, llm, tools):
        self.llm = llm
        self.tools = tools
        self.react = ReActAgent(llm, tools)
        self.plan = PlanExecuteAgent(llm, tools)
        self.reflexion = ReflexionAgent(llm, tools)
    
    def run(self, task):
        # 1. 评估任务复杂度
        complexity = self._assess_complexity(task)
        
        # 2. 选择范式
        if complexity == "simple":
            return self.react.run(task)
        elif complexity == "complex":
            plan = self.plan.run(task)
            if plan["success"]:
                return plan
            # 复杂任务失败 → 切换到 Reflexion
            return self.reflexion.run(task)
        else:
            return self.reflexion.run(task)
```

---

## 五、2026 年范式演进

### 5.1 从范式到框架

2026 年，Agent 范式不再只是"实现方式"，而是被封装到框架中：

- LangGraph：ReAct + Plan-and-Execute 的混合（通过状态机）
- CrewAI：多 Agent 协作范式
- AutoGen：Agent 对话范式
- OpenClaw：工具优先范式

### 5.2 自适应范式

未来的 Agent 不再是固定范式，而是**根据任务自适应选择**：

```
Agent 启动时，自动分析任务：
- 任务类型（问答、创作、执行）
- 复杂度（简单、中等、复杂）
- 约束条件（时间、成本、质量）

然后选择最优范式。
```

### 5.3 范式与模型的关系

不同范式对模型能力的要求不同：

```
ReAct：7B 模型就能跑，但效果一般
Plan-and-Execute：需要 70B+，规划能力是关键
Reflexion：需要 70B+，反思能力是关键
```

---

## 总结

| 范式 | 一句话 | 核心优势 |
|------|--------|---------|
| ReAct | 边想边做 | 灵活，适应性强 |
| Plan-and-Execute | 先想再做 | 全局视野，效率高 |
| Reflexion | 反思改进 | 从错误中学习 |

**没有最好的范式，只有最适合你场景的范式。**

下一篇文章，我们将深入**Function Calling 与 Tool Use**——工具定义、调用机制、并行调用，以及如何让 Agent 可靠地使用工具。

---

**思考题**：
1. 你现在的 Agent 用的是什么范式？ReAct 吗？有没有尝试过 Plan-and-Execute？
2. Reflexion 的"反思"环节，可以用另一个模型来做吗？这样有什么好处？
3. 在什么场景下，你愿意为了更高的准确率，接受 Reflexion 的多倍成本？

---

> 上一篇：[23] 从 LLM 到 Agent：Agent 的定义与本质
> 下一篇：[25] Function Calling 与 Tool Use
> 系列目录：[README.md](./README.md)