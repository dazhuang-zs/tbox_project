# 【AI Agent 系统教学 40】Agent 编排器与 Subagent

> 编排器不是"另一个 Agent"，而是"管理 Agent 的 Agent"。
> Subagent 不是"小 Agent"，而是"专注做一件事的 Agent"。

---

## 前言：编排器 vs Subagent

在单 Agent 系统中，所有逻辑都在一个 Agent 的循环中。

在多 Agent 系统中，需要：
- **编排器（Orchestrator）**：负责规划、分配、监督、汇总
- **Subagent（子 Agent）**：负责执行具体任务

编排器是"经理"，Subagent 是"员工"。

---

## 一、编排器设计

### 1.1 编排器的职责

```python
class Orchestrator:
    """Agent 编排器"""
    def __init__(self, llm, agent_registry):
        self.llm = llm
        self.registry = agent_registry
        self.task_queue = TaskQueue()
        self.result_store = ResultStore()
    
    def execute(self, task):
        # 1. 分析任务，制定计划
        plan = self._analyze(task)
        
        # 2. 分配任务
        assignments = self._assign(plan)
        
        # 3. 执行并监控
        results = self._monitor(assignments)
        
        # 4. 汇总结果
        return self._aggregate(results)
    
    def _analyze(self, task):
        """分析任务，制定计划"""
        prompt = f"""
        任务：{task}
        可用 Agent：{list(self.registry.agents.keys())}
        
        请制定执行计划：
        1. 需要哪些 Agent
        2. 每个 Agent 做什么
        3. 执行顺序
        4. 依赖关系
        """
        return self.llm.generate(prompt)
    
    def _assign(self, plan):
        """分配任务"""
        assignments = []
        for step in plan["steps"]:
            agent = self.registry.get(step["agent"])
            if agent:
                task = self.task_queue.enqueue(step)
                assignments.append((agent, task))
        return assignments
    
    def _monitor(self, assignments):
        """监控执行"""
        results = {}
        for agent, task in assignments:
            # 启动 Subagent
            future = agent.execute_async(task)
            
            # 监控进度
            while not future.done():
                progress = agent.get_progress(task.id)
                if progress["status"] == "stuck":
                    self._intervene(agent, task)
                time.sleep(0.1)
            
            results[task.id] = future.result()
        
        return results
```

### 1.2 动态编排

```python
class DynamicOrchestrator:
    """动态编排器"""
    def __init__(self):
        self.agents = []
        self.current_plan = None
    
    def execute_dynamic(self, task):
        """动态编排：边执行边调整"""
        plan = self._create_initial_plan(task)
        
        while not self._is_complete(plan):
            # 1. 获取可执行的步骤
            ready_steps = self._get_ready_steps(plan)
            
            # 2. 执行
            for step in ready_steps:
                agent = self._select_agent(step)
                result = agent.execute(step)
                plan.update(step.id, result)
            
            # 3. 检查是否需要调整计划
            if self._needs_adjustment(plan):
                plan = self._adjust_plan(plan)
        
        return plan.final_result()
```

---

## 二、Subagent 设计

### 2.1 Subagent 的生命周期

```python
class Subagent:
    """Subagent（子 Agent）"""
    def __init__(self, name, system_prompt, tools):
        self.name = name
        self.system_prompt = system_prompt
        self.tools = tools
        self.state = "idle"  # idle, running, paused, error, done
        self.current_task = None
        self.result = None
    
    def execute(self, task):
        """执行任务"""
        self.state = "running"
        self.current_task = task
        
        try:
            result = self._run_loop(task)
            self.result = result
            self.state = "done"
            return result
        except Exception as e:
            self.state = "error"
            raise
    
    def _run_loop(self, task):
        """Subagent 的执行循环"""
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": task},
        ]
        
        for step in range(10):
            response = llm.generate(messages)
            
            if has_tool_call(response):
                for tool_call in response.tool_calls:
                    result = self._execute_tool(tool_call)
                    messages.append({"role": "tool", "content": result})
            else:
                return response.content
        
        return "达到最大步数"
    
    def get_status(self):
        """获取状态"""
        return {
            "name": self.name,
            "state": self.state,
            "current_task": self.current_task,
            "progress": self._calculate_progress(),
        }
```

### 2.2 Subagent 池

```python
class SubagentPool:
    """Subagent 池"""
    def __init__(self, max_concurrent=5):
        self.pool = []
        self.max_concurrent = max_concurrent
        self.available = []
        self.busy = []
    
    def acquire(self, agent_type):
        """获取一个可用的 Subagent"""
        for agent in self.available:
            if agent.type == agent_type:
                self.available.remove(agent)
                self.busy.append(agent)
                return agent
        
        # 如果没有可用，创建新的
        if len(self.pool) < self.max_concurrent:
            agent = self._create_agent(agent_type)
            self.pool.append(agent)
            self.busy.append(agent)
            return agent
        
        return None  # 没有可用资源
    
    def release(self, agent):
        """释放 Subagent"""
        if agent in self.busy:
            self.busy.remove(agent)
            self.available.append(agent)
            agent.state = "idle"
```

---

## 三、任务分配策略

### 3.1 分配策略

```python
class TaskAssigner:
    """任务分配器"""
    def assign(self, task, agents):
        strategies = {
            "round_robin": self._round_robin,
            "capability": self._capability_based,
            "load_balance": self._load_balance,
            "priority": self._priority_based,
        }
        strategy = strategies.get(task.strategy, self._round_robin)
        return strategy(task, agents)
    
    def _round_robin(self, task, agents):
        """轮询分配"""
        idx = hash(task.id) % len(agents)
        return agents[idx]
    
    def _capability_based(self, task, agents):
        """基于能力匹配"""
        scores = [(a, self._match_score(task, a)) for a in agents]
        return max(scores, key=lambda x: x[1])[0]
    
    def _load_balance(self, task, agents):
        """负载均衡"""
        return min(agents, key=lambda a: a.current_load)
```

---

## 四、结果合并

### 4.1 合并策略

```python
class ResultMerger:
    """结果合并器"""
    def merge(self, results, strategy="concatenate"):
        if strategy == "concatenate":
            return self._concatenate(results)
        elif strategy == "summarize":
            return self._summarize(results)
        elif strategy == "best_of":
            return self._best_of(results)
        elif strategy == "composite":
            return self._composite(results)
    
    def _concatenate(self, results):
        """直接拼接"""
        return "\n\n".join(results)
    
    def _summarize(self, results):
        """让 LLM 总结"""
        prompt = f"请总结以下多个 Agent 的输出：\n{results}"
        return llm.generate(prompt)
    
    def _best_of(self, results):
        """选择最佳"""
        prompt = f"以下哪个回答最好？\n{results}"
        return llm.generate(prompt)
    
    def _composite(self, results):
        """组合各部分的优点"""
        prompt = f"请从以下结果中取各部分的优点，组合成一个完整输出：\n{results}"
        return llm.generate(prompt)
```

---

## 五、编排器 vs Subagent 的边界

### 5.1 职责划分

```
编排器负责：
  - 理解任务全局
  - 制定计划
  - 分配任务
  - 监控进度
  - 处理异常
  - 合并结果

Subagent 负责：
  - 执行具体任务
  - 使用特定工具
  - 报告进度
  - 返回结果
```

### 5.2 编排器不做什么

```
编排器不做：
  - 执行 Subagent 的具体任务（避免越俎代庖）
  - 替 Subagent 做决策（保持 Subagent 的自主性）
  - 做 Subagent 的工作（分工明确）
```

---

## 六、最佳实践

### 6.1 编排器设计原则

```
1. 编排器知道"做什么"，Subagent 知道"怎么做"
2. 编排器不干预 Subagent 的执行细节
3. 编排器管异常，不管正常流程
4. Subagent 独立，不依赖其他 Subagent
5. 结果统一格式，便于合并
```

### 6.2 常见模式

```python
class SubagentOrchestrationPattern:
    """常见编排模式"""
    
    def fan_out(self, task, subagents):
        """扇出：一个任务，多个 Subagent 独立处理"""
        results = []
        for agent in subagents:
            result = agent.execute(task)
            results.append(result)
        return self.merger.merge(results)
    
    def chain(self, task, subagents):
        """链式：A → B → C"""
        current = task
        for agent in subagents:
            current = agent.execute(current)
        return current
    
    def dag(self, task, subagents, dependencies):
        """DAG：有向无环图"""
        executor = DAGExecutor(subagents, dependencies)
        return executor.execute(task)
```

---

## 总结

| 角色 | 职责 | 能力 |
|------|------|------|
| 编排器 | 规划、分配、监督 | 宏观视角、协调能力 |
| Subagent | 执行具体任务 | 专业能力、工具使用 |
| 编排器 | 处理异常 | 决策能力 |
| Subagent | 报告结果 | 输出能力 |

**好的编排器让 Subagent 发挥最大价值，好的 Subagent 让编排器不必事必躬亲。**

下一篇文章，我们将深入**多 Agent 系统的涌现行为**。

---

**思考题**：
1. 编排器本身也是一个 Agent，它会不会也出错？谁来监督编排器？
2. Subagent 的"粒度"怎么把握？太粗或太细各有什么问题？
3. 如果编排器分配给 Subagent 的任务，Subagent 做不了，怎么办？

---

> 上一篇：[39] 多 Agent 协作模式
> 下一篇：[41] 多 Agent 系统的涌现行为
> 系列目录：[README.md](./README.md)