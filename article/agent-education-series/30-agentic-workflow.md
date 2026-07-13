# 【AI Agent 系统教学 30】从 Agent 到 Agentic Workflow

> 纯 Agent 自主决策太不可控，纯确定性流程太死板。
> Agentic Workflow 是两者的结合——让 Agent 在框架内自由。

---

## 前言：Agent 的"自由"需要边界

纯粹的 Agent 自主决策（Full Autonomy）有个问题：

```
Agent 自主决策：
  ✅ 灵活，适应性强
  ❌ 不可预测，可能走偏
  ❌ 难以调试，依赖模型能力

确定性流程（Hardcoded Flow）：
  ✅ 可控，可预测
  ✅ 容易调试，不依赖模型
  ❌ 死板，无法处理意外情况
```

**Agentic Workflow 就是两者的结合：在确定的流程框架中，让 Agent 在关键节点自主决策。**

---

## 一、什么是 Agentic Workflow

### 1.1 定义

Agentic Workflow = 确定性流程 + Agent 自主决策节点

```
流程框架是确定的（先做什么，再做什么）
每个节点内，Agent 可以自主决策（怎么实现）
```

### 1.2 对比

| 模式 | 流程控制 | 决策方式 | 灵活性 | 可靠性 |
|------|---------|---------|-------|-------|
| 纯 Agent | Agent 自主 | Agent 全权 | 高 | 低 |
| 确定性流程 | 代码硬编码 | 固定规则 | 低 | 高 |
| Agentic Workflow | 代码定义 | Agent 在节点内决策 | 中 | 高 |

---

## 二、Agentic Workflow 的核心模式

### 2.1 模式一：Pandas 模式

```
对于每个输入，执行相同的流程
```

```python
def pandas_workflow(items):
    """
    批量处理：对每个输入执行相同的流程
    """
    results = []
    for item in items:
        # 节点 1：分类
        category = classify(item)
        
        # 节点 2：处理（Agent 自主决策）
        processed = agent_handle(item, category)
        
        # 节点 3：验证
        valid = validate(processed)
        
        # 节点 4：输出
        if valid:
            results.append(format_output(processed))
        else:
            results.append(handle_error(processed))
    
    return results
```

### 2.2 模式二：门卫模式

```
先通过确定性规则筛选，复杂情况交给 Agent
```

```python
def gatekeeper_workflow(user_input):
    # 节点 1：规则引擎（快速、确定性）
    if is_simple_query(user_input):
        return rule_based_response(user_input)
    
    if is_known_pattern(user_input):
        return template_response(user_input)
    
    # 节点 2：Agent（复杂、灵活）
    if is_complex_query(user_input):
        return agent_handle(user_input)
    
    # 节点 3：兜底
    return fallback_response(user_input)
```

### 2.3 模式三：并行模式

```
多个任务并行处理，最后汇总
```

```python
def parallel_workflow(task):
    # 节点 1：规划
    subtasks = decompose(task)
    
    # 节点 2：并行执行（每个子任务由 Agent 自主处理）
    with ThreadPoolExecutor() as executor:
        futures = [
            executor.submit(agent_handle, subtask)
            for subtask in subtasks
        ]
        results = [f.result() for f in futures]
    
    # 节点 3：汇总
    final = merge_results(results)
    
    # 节点 4：验证
    return validate_and_output(final)
```

### 2.4 模式四：循环模式

```
迭代执行，直到满足条件
```

```python
def iterative_workflow(task, max_iterations=5):
    state = {"task": task, "attempts": 0, "result": None}
    
    while state["attempts"] < max_iterations:
        # 节点 1：Agent 处理
        state["result"] = agent_handle(state)
        
        # 节点 2：验证
        validation = validate(state["result"], task)
        
        if validation["passed"]:
            return state["result"]
        
        # 节点 3：反思
        feedback = validation["feedback"]
        state["result"] = agent_refine(state["result"], feedback)
        state["attempts"] += 1
    
    return state["result"]
```

---

## 三、设计 Agentic Workflow

### 3.1 设计原则

```
1. 确定部分用代码，不确定部分用 Agent
2. 每个节点只做一件事
3. 节点间用明确的数据接口
4. 每个节点都有失败处理
5. 可观测性内置
```

### 3.2 实战：客服 Agent 的 Workflow

```python
class CustomerServiceWorkflow:
    """客服 Agent 的工作流"""
    def handle(self, request):
        # 1. 路由（确定性）
        intent = self._route_intent(request)
        
        # 2. 根据意图走不同流程
        handlers = {
            "refund": self._handle_refund,
            "complaint": self._handle_complaint,
            "inquiry": self._handle_inquiry,
            "technical": self._handle_technical,
        }
        
        handler = handlers.get(intent, self._handle_unknown)
        return handler(request)
    
    def _handle_refund(self, request):
        """退款流程"""
        # 步骤 1：验证身份（确定性）
        if not self._verify_identity(request.user_id):
            return "请先验证身份"
        
        # 步骤 2：查询订单（确定性）
        order = self._query_order(request.order_id)
        if not order:
            return "未找到订单"
        
        # 步骤 3：Agent 处理退款（Agent 自主决策）
        result = self._agent_process_refund(request, order)
        
        # 步骤 4：通知用户（确定性）
        self._send_notification(request.user_id, result)
        
        return result
    
    def _handle_technical(self, request):
        """技术支持流程"""
        # 步骤 1：检查常见问题（确定性）
        solution = self._check_faq(request.issue)
        if solution:
            return solution
        
        # 步骤 2：Agent 诊断（Agent 自主决策）
        diagnosis = self._agent_diagnose(request.issue)
        
        # 步骤 3：根据诊断结果走不同路径
        if diagnosis["severity"] == "high":
            # 高优先级：转人工（确定性）
            return self._escalate_to_human(request)
        else:
            # 低优先级：Agent 解决（Agent 自主决策）
            return self._agent_resolve(request, diagnosis)
```

### 3.3 状态机形式

```python
from enum import Enum

class WorkflowState(Enum):
    START = "start"
    ROUTE = "route"
    PROCESS = "process"
    VERIFY = "verify"
    HANDLE_ERROR = "handle_error"
    FINISH = "finish"

class WorkflowEngine:
    def __init__(self):
        self.state = WorkflowState.START
        self.handlers = {
            WorkflowState.START: self._handle_start,
            WorkflowState.ROUTE: self._handle_route,
            WorkflowState.PROCESS: self._handle_process,
            WorkflowState.VERIFY: self._handle_verify,
            WorkflowState.HANDLE_ERROR: self._handle_error,
            WorkflowState.FINISH: self._handle_finish,
        }
    
    def run(self, input_data):
        while self.state != WorkflowState.FINISH:
            handler = self.handlers[self.state]
            self.state = handler(input_data)
        return input_data
```

---

## 四、何时用 Agent，何时用规则

### 4.1 决策树

```
这个任务的判断标准是什么？
├─ 有明确的规则 → 用规则（确定性）
│   例：密码长度验证、格式检查、权限判断
│
├─ 需要理解语义 → 用 Agent
│   例：意图识别、情感分析、内容生成
│
└─ 混合型 → 规则 + Agent 组合
    例：先用规则过滤，再用 Agent 处理复杂情况
```

### 4.2 成本与收益

```python
def decide_approach(task):
    """
    判断用规则还是 Agent
    """
    # 规则的成本
    rule_cost = estimate_rule_development_cost(task)
    rule_accuracy = estimate_rule_accuracy(task)
    
    # Agent 的成本
    agent_cost = token_cost(task) * num_requests
    agent_accuracy = estimate_agent_accuracy(task)
    
    # 规则开发成本低 + 准确率高 → 用规则
    if rule_cost < 100 and rule_accuracy > 0.95:
        return "rule"
    
    # Agent 成本低 + 准确率高 → 用 Agent
    if agent_cost < 0.01 and agent_accuracy > 0.9:
        return "agent"
    
    # 混合
    return "hybrid"
```

---

## 五、向 Agentic System 演进

### 5.1 演进路径

```
阶段 1：纯规则
  所有逻辑用代码硬编码
  优点：可控、可预测
  缺点：死板

阶段 2：规则 + Agent 单点
  在关键节点用 Agent 替代规则
  优点：更灵活
  缺点：集成复杂

阶段 3：Agentic Workflow
  流程框架确定，节点内 Agent 自主
  优点：灵活 + 可控
  缺点：需要设计良好的接口

阶段 4：Agentic System
  多个 Agentic Workflow 协同
  优点：处理复杂业务
  缺点：系统复杂度高
```

### 5.2 从 Agent 到 Agentic System

```
Agent：单个 Agent 完成一个任务
Agentic Workflow：确定性流程 + Agent 节点
Agentic System：多个 Workflow 协同，处理全流程
```

---

## 总结

| 模式 | 流程控制 | 决策方式 | 典型场景 |
|------|---------|---------|---------|
| 纯 Agent | 无 | 全自主 | 探索性任务 |
| 确定性流程 | 代码 | 规则 | 简单、重复任务 |
| Agentic Workflow | 代码框架 | 节点内自主 | 复杂业务 |
| Pandas 模式 | 循环 | 批量处理 | 批量任务 |
| 门卫模式 | 规则优先 | 分级处理 | 客服系统 |
| 并行模式 | 并行 | 分布式处理 | 大规模任务 |
| 循环模式 | 迭代 | 逐步优化 | 质量敏感任务 |

**Agentic Workflow 是"确定性"和"自主性"的最佳平衡点。**

**模块四总结**：8 篇文章，从 Agent 的定义、三大范式、Function Calling、编排框架、工程实现、状态管理、持久化到 Agentic Workflow，覆盖了 Agent 范式与架构的完整体系。

**下一篇**：进入模块五——**Agent 核心能力系统**，从记忆系统开始。

---

**思考题**：
1. 你现在的 Agent 系统，是纯 Agent 模式还是 Agentic Workflow？各有什么优缺点？
2. 如果让你设计一个客服 Agent 的 Workflow，你会把哪些部分用规则，哪些用 Agent？
3. Agentic Workflow 的"节点"粒度怎么把握？太粗或太细各有什么问题？

---

> 上一篇：[29] Agent 持久化与数据库
> 下一篇：[31] Agent 记忆系统深度解析
> 系列目录：[README.md](./README.md)