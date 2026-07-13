# 【AI Agent 系统教学 33】Agent 规划与推理

> 工具是 Agent 的"手"，记忆是 Agent 的"存储"，规划是 Agent 的"大脑"。
> 没有规划能力的 Agent，只能做"应激反应"。

---

## 前言：为什么 Agent 需要规划

没有规划的 Agent：

```
用户：帮我写一个数据分析报告
Agent 直接开始写，写到一半发现需要数据
→ 搜索数据
→ 发现有数据，但格式不对
→ 重新处理
→ 效率极低
```

有规划的 Agent：

```
用户：帮我写一个数据分析报告
Agent 先规划：
1. 明确数据源和格式
2. 获取数据
3. 数据清洗
4. 数据分析
5. 生成报告
→ 按顺序执行，效率高，出错少
```

**规划 = 把复杂任务拆解成可管理的子任务。**

---

## 一、任务分解

### 1.1 任务分解方法

```python
class TaskDecomposer:
    """任务分解"""
    def decompose(self, task, max_subtasks=5):
        prompt = f"""
        任务：{task}
        
        请将这个任务分解成 {max_subtasks} 个以内的子任务。
        每个子任务应该：
        - 可独立执行
        - 有明确的输入和输出
        - 有明确的完成标准
        
        输出格式（JSON）：
        [
            {{
                "id": 1,
                "name": "子任务名称",
                "description": "子任务描述",
                "dependencies": [],  # 依赖的子任务 ID
                "tools_needed": [],   # 需要的工具
                "success_criteria": "完成标准"
            }}
        ]
        """
        return llm(prompt)
```

### 1.2 任务依赖图

```python
class TaskDAG:
    """任务依赖图（DAG）"""
    def __init__(self, tasks):
        self.tasks = tasks
        self.dag = self._build_dag(tasks)
    
    def _build_dag(self, tasks):
        """构建有向无环图"""
        dag = {t["id"]: {"task": t, "deps": t.get("dependencies", [])} for t in tasks}
        return dag
    
    def get_execution_order(self):
        """拓扑排序，获取执行顺序"""
        visited = set()
        order = []
        
        def dfs(task_id):
            if task_id in visited:
                return
            visited.add(task_id)
            for dep in self.dag[task_id]["deps"]:
                dfs(dep)
            order.append(task_id)
        
        for task_id in self.dag:
            dfs(task_id)
        
        return [self.dag[tid]["task"] for tid in order]
    
    def get_parallel_tasks(self):
        """获取可以并行执行的任务"""
        order = self.get_execution_order()
        batches = []
        current_batch = []
        completed = set()
        
        for task in order:
            deps = set(task.get("dependencies", []))
            if deps.issubset(completed):
                current_batch.append(task)
            else:
                if current_batch:
                    batches.append(current_batch)
                    completed.update(t["id"] for t in current_batch)
                current_batch = [task]
        
        if current_batch:
            batches.append(current_batch)
        
        return batches
```

---

## 二、计划生成与执行

### 2.1 计划生成

```python
class Planner:
    """Agent 规划器"""
    def __init__(self, llm, tools):
        self.llm = llm
        self.tools = tools
    
    def plan(self, task, context=None):
        """生成执行计划"""
        prompt = f"""
        任务：{task}
        可用工具：{list(self.tools.keys())}
        上下文：{context}
        
        请生成一个详细的执行计划：
        1. 任务分解成多个步骤
        2. 每个步骤指定使用的工具
        3. 步骤之间的依赖关系
        4. 预期输出
        
        计划：
        """
        plan_text = self.llm.generate(prompt)
        return self._parse_plan(plan_text)
    
    def validate_plan(self, plan):
        """验证计划的可行性"""
        for step in plan:
            tool = step.get("tool")
            if tool and tool not in self.tools:
                return False, f"步骤 {step['id']} 需要工具 {tool}，但不可用"
        return True, "计划可行"
```

### 2.2 计划执行

```python
class PlanExecutor:
    """计划执行器"""
    def __init__(self, planner, tools, max_retries=2):
        self.planner = planner
        self.tools = tools
        self.max_retries = max_retries
    
    def execute(self, task):
        # 1. 生成计划
        plan = self.planner.plan(task)
        
        # 2. 验证计划
        valid, message = self.planner.validate_plan(plan)
        if not valid:
            return {"status": "error", "message": message}
        
        # 3. 获取执行顺序
        dag = TaskDAG(plan)
        batches = dag.get_parallel_tasks()
        
        # 4. 按批次执行
        results = {}
        for batch in batches:
            batch_results = self._execute_batch(batch, results)
            results.update(batch_results)
            
            # 5. 动态调整
            if self._needs_replan(task, plan, results):
                plan = self.planner.plan(task, context=results)
                batches = dag.get_parallel_tasks()
        
        # 6. 汇总结果
        return self._summarize_results(task, results)
    
    def _execute_batch(self, batch, previous_results):
        """执行一批并行任务"""
        batch_results = {}
        
        for step in batch:
            # 准备参数
            params = self._prepare_params(step, previous_results)
            
            # 执行
            for attempt in range(self.max_retries):
                try:
                    result = self.tools[step["tool"]](**params)
                    batch_results[step["id"]] = result
                    break
                except Exception as e:
                    if attempt == self.max_retries - 1:
                        batch_results[step["id"]] = {"error": str(e)}
        
        return batch_results
```

---

## 三、动态重规划

### 3.1 什么时候需要重规划

```python
class ReplanDetector:
    """重规划检测"""
    def check(self, task, plan, results):
        triggers = []
        
        # 1. 工具调用失败
        for step_id, result in results.items():
            if "error" in result:
                triggers.append(f"步骤 {step_id} 失败")
        
        # 2. 结果不符合预期
        for step_id, result in results.items():
            if not self._check_expectation(plan, step_id, result):
                triggers.append(f"步骤 {step_id} 结果不符合预期")
        
        # 3. 环境变化
        if self._environment_changed():
            triggers.append("环境发生变化")
        
        # 4. 用户干预
        if self._user_intervened():
            triggers.append("用户干预")
        
        return triggers
```

### 3.2 动态调整

```python
def dynamic_replan(task, plan, results, triggers):
    """
    根据触发条件动态调整计划
    """
    # 1. 分析失败原因
    analysis = analyze_failures(triggers, results)
    
    # 2. 生成修正方案
    revised = llm.generate(f"""
    原始任务：{task}
    原始计划：{plan}
    执行结果：{results}
    失败原因：{analysis}
    
    请提供修正方案：
    1. 哪些步骤需要重做？
    2. 哪些步骤可以跳过？
    3. 需要新增哪些步骤？
    """)
    
    return revised
```

---

## 四、推理与规划的结合

### 4.1 推理驱动的规划

```python
class ReasoningPlanner:
    """基于推理的规划"""
    def plan_with_reasoning(self, task):
        # 1. 推理任务本质
        reasoning = self.llm.generate(f"""
        任务：{task}
        
        分析：
        1. 这个任务的本质是什么？
        2. 成功的关键是什么？
        3. 可能遇到的困难是什么？
        4. 已知信息有哪些？
        5. 需要获取什么信息？
        """)
        
        # 2. 基于推理生成计划
        plan = self.llm.generate(f"""
        基于以上分析，请生成执行计划：
        推理：{reasoning}
        """)
        
        return plan
```

### 4.2 规划中的推理检查点

```python
def plan_with_checkpoints(task):
    """在规划中设置推理检查点"""
    plan = planner.plan(task)
    
    for step in plan:
        # 在执行前，先推理
        reasoning = llm.generate(f"""
        当前步骤：{step}
        上下文：{context}
        
        推理：
        1. 这个步骤的目标是什么？
        2. 预期输出是什么？
        3. 如果出错，备选方案是什么？
        """)
        
        # 执行
        result = execute(step)
        
        # 执行后验证
        verification = llm.generate(f"""
        推理：{reasoning}
        实际结果：{result}
        
        验证：
        1. 结果是否符合预期？
        2. 如果不符合，原因是什么？
        """)
        
        if verification["status"] == "unexpected":
            plan = dynamic_replan(plan, step, result)
```

---

## 五、规划的局限性

### 5.1 过度规划

```
问题：花太多时间规划，实际执行很少
表现：生成了 20 步计划，但只执行了 3 步

解决方案：
- 限制规划步数（最多 5-10 步）
- 采用"渐进式规划"（先规划前几步，后面边做边规划）
- 设置规划超时
```

### 5.2 不切实际的规划

```
问题：规划了无法执行的步骤
表现：假设了不存在的工具、不可用的数据

解决方案：
- 规划前验证工具的可用性
- 规划时考虑实际情况（数据可用性、时间限制）
- 执行时验证每一步的可行性
```

### 5.3 规划与执行脱节

```
问题：计划很好，但执行时发现现实不一样
表现：搜索不到预期的数据、工具返回错误

解决方案：
- 动态重规划机制
- 执行结果反馈到规划
- 允许人工干预
```

---

## 六、2026 年规划技术趋势

### 6.1 分层规划

高层规划（抽象）→ 中层规划（具体）→ 底层规划（执行）

```
高层：写一个数据分析报告
中层：获取数据 → 分析数据 → 生成报告
底层：search_web → extract_data → analyze → format
```

### 6.2 学习型规划

Agent 从历史规划中学习：

```
完成 100 个任务后，Agent 学会：
- 类似的任务通常需要哪些步骤
- 哪些步骤容易失败
- 哪些工具组合最有效
```

### 6.3 规划即代码

规划不再是"自然语言"，而是"代码"：

```
plan = {
    "type": "sequential",
    "steps": [
        {"tool": "search", "params": {...}},
        {"tool": "analyze", "params": {...}},
    ],
    "fallback": {"tool": "ask_user", "params": {...}},
}
```

---

## 总结

| 能力 | 说明 | 实现方式 |
|------|------|---------|
| 任务分解 | 把复杂任务拆成子任务 | LLM 分解 + DAG |
| 计划生成 | 生成执行步骤 | LLM 规划 |
| 计划执行 | 按顺序/并行执行 | 执行器 |
| 动态重规划 | 根据执行结果调整 | 触发条件检测 |
| 推理增强 | 在规划中融入推理 | 推理检查点 |

**规划让 Agent 从"应激反应"进化到"主动思考"。**

下一篇文章，我们将深入**Agent 安全与治理**。

---

**思考题**：
1. 你的 Agent 现在有"规划"能力吗？如果没有，什么场景下最需要规划？
2. 动态重规划在什么场景下特别重要？什么场景下不需要？
3. 如果规划步骤超过 10 步，你会怎么处理？

---

> 上一篇：[32] 工具系统与 MCP 协议
> 下一篇：[34] Agent 安全与治理
> 系列目录：[README.md](./README.md)