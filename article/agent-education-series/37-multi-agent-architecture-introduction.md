# 【AI Agent 系统教学 37】多 Agent 架构导论

> 一个 Agent 能力有限，但多个 Agent 协作可以完成远超单个 Agent 的任务。
> 多 Agent 不是"多个人"，是"多个专业的人组成团队"。

---

## 前言：为什么需要多 Agent？

单个 Agent 的局限：

```
1. 上下文窗口有限：无法处理超长任务
2. 工具数量有限：太多工具会让模型困惑
3. 专业知识有限：一个模型不可能精通所有领域
4. 可靠性有限：单点故障，一个错误影响全局
5. 并行能力有限：一个 Agent 只能顺序工作
```

多 Agent 解决这些问题：**分而治之，各司其职。**

---

## 一、多 Agent 架构模式

### 1.1 架构分类

```
多 Agent 架构 = 拓扑结构 + 通信模式 + 协作策略

拓扑结构：
  - 中心化：一个主 Agent 协调多个子 Agent
  - 去中心化：Agent 之间直接通信
  - 分层：多层 Agent 逐级管理

通信模式：
  - 同步：等待对方响应
  - 异步：发消息后继续工作
  - 广播：向所有 Agent 发送
  - 点对点：指定接收者

协作策略：
  - 分工：各做各的，最后汇总
  - 辩论：不同 Agent 讨论，取最优
  - 投票：多个 Agent 投票决策
  - 级联：A 的输出是 B 的输入
```

### 1.2 中心化架构

```python
class CentralizedOrchestrator:
    """中心化架构"""
    def __init__(self):
        self.orchestrator = Agent("主控", tools=["assign", "monitor", "merge"])
        self.workers = {
            "researcher": Agent("研究员", tools=["search", "analyze"]),
            "writer": Agent("写手", tools=["write", "format"]),
            "reviewer": Agent("审核员", tools=["review", "validate"]),
        }
    
    def execute(self, task):
        # 1. 主控分解任务
        subtasks = self.orchestrator.decompose(task)
        
        # 2. 分配任务
        results = {}
        for subtask, worker_name in subtasks:
            worker = self.workers[worker_name]
            results[subtask.id] = worker.execute(subtask)
        
        # 3. 主控汇总
        final = self.orchestrator.merge(results)
        return final
```

### 1.3 去中心化架构

```python
class DecentralizedSwarm:
    """去中心化架构"""
    def __init__(self):
        self.agents = {
            "agent_a": Agent("A"),
            "agent_b": Agent("B"),
            "agent_c": Agent("C"),
        }
        self.message_bus = MessageBus()
    
    def broadcast(self, sender, message):
        """广播消息"""
        for name, agent in self.agents.items():
            if name != sender:
                self.message_bus.send(sender, name, message)
    
    def converge(self, task):
        """多 Agent 协商达成一致"""
        proposals = []
        for agent in self.agents.values():
            proposal = agent.propose(task)
            proposals.append(proposal)
        
        # 各 Agent 评议
        final = self.agents["agent_a"].negotiate(proposals)
        return final
```

### 1.4 分层架构

```python
class HierarchicalArchitecture:
    """分层架构"""
    def __init__(self):
        self.top_level = ManagerAgent("高层管理者")
        self.mid_level = {
            "tech": ManagerAgent("技术主管"),
            "business": ManagerAgent("业务主管"),
        }
        self.bottom_level = {
            "coder": WorkerAgent("程序员"),
            "tester": WorkerAgent("测试员"),
            "analyst": WorkerAgent("分析师"),
            "sales": WorkerAgent("销售"),
        }
    
    def execute(self, task):
        # 高层分解任务到中层
        mid_tasks = self.top_level.decompose(task)
        
        # 中层分解任务到底层
        for mid_name, mid_task in mid_tasks.items():
            bottom_tasks = self.mid_level[mid_name].decompose(mid_task)
            for bottom_name, bottom_task in bottom_tasks.items():
                result = self.bottom_level[bottom_name].execute(bottom_task)
                self.mid_level[mid_name].collect(bottom_name, result)
        
        # 中层汇总给高层
        return self.top_level.collect(mid_tasks)
```

---

## 二、Agent 通信

### 2.1 消息总线

```python
class MessageBus:
    """Agent 消息总线"""
    def __init__(self):
        self.queues = {}
        self.history = []
    
    def register_agent(self, agent_name):
        self.queues[agent_name] = []
    
    def send(self, sender, receiver, message):
        """发送消息"""
        msg = {
            "id": str(uuid.uuid4()),
            "sender": sender,
            "receiver": receiver,
            "content": message,
            "timestamp": time.time(),
            "type": message.get("type", "text"),
        }
        if receiver in self.queues:
            self.queues[receiver].append(msg)
        self.history.append(msg)
    
    def receive(self, agent_name):
        """接收消息"""
        queue = self.queues.get(agent_name, [])
        messages = queue[:]
        queue.clear()
        return messages
    
    def broadcast(self, sender, message, exclude=None):
        """广播"""
        for name in self.queues:
            if name != sender and name != exclude:
                self.send(sender, name, message)
```

### 2.2 通信协议

```python
# 消息格式
MESSAGE_FORMAT = {
    "type": "request/response/broadcast/error",
    "sender": "agent_name",
    "receiver": "agent_name_or_all",
    "content": {
        "action": "task/query/result/feedback",
        "data": {},
    },
    "metadata": {
        "timestamp": 1234567890,
        "message_id": "uuid",
        "conversation_id": "uuid",
    },
}

# 通信模式
class CommunicationProtocol:
    REQUEST = "request"      # 请求
    RESPONSE = "response"    # 响应
    BROADCAST = "broadcast"  # 广播
    ERROR = "error"          # 错误
    
    def create_message(self, msg_type, sender, receiver, content):
        return {
            "type": msg_type,
            "sender": sender,
            "receiver": receiver,
            "content": content,
            "metadata": {
                "timestamp": time.time(),
                "message_id": str(uuid.uuid4()),
            },
        }
```

---

## 三、任务分配

### 3.1 分配策略

```python
class TaskDistributor:
    """任务分配器"""
    def __init__(self, agents):
        self.agents = agents
    
    def distribute(self, task):
        """分配任务"""
        # 策略 1：按能力匹配
        agent_scores = {}
        for name, agent in self.agents.items():
            score = self._match_score(task, agent)
            agent_scores[name] = score
        
        best_agent = max(agent_scores, key=agent_scores.get)
        return best_agent, task
    
    def distribute_batch(self, tasks):
        """批量分配"""
        # 策略 2：负载均衡
        assignments = {}
        agent_loads = {name: 0 for name in self.agents}
        
        for task in sorted(tasks, key=lambda t: t.estimated_effort, reverse=True):
            # 找当前负载最低的 Agent
            agent = min(agent_loads, key=agent_loads.get)
            assignments[agent] = assignments.get(agent, []) + [task]
            agent_loads[agent] += task.estimated_effort
        
        return assignments
    
    def _match_score(self, task, agent):
        """计算任务与 Agent 的匹配度"""
        return agent.capabilities.get(task.category, 0)
```

### 3.2 结果汇总

```python
class ResultAggregator:
    """结果汇总器"""
    def aggregate(self, results):
        """汇总多个 Agent 的结果"""
        # 1. 去重
        unique = self._deduplicate(results)
        
        # 2. 排序
        sorted_results = sorted(unique, key=lambda r: r.get("confidence", 0), reverse=True)
        
        # 3. 融合
        if len(sorted_results) == 1:
            return sorted_results[0]
        
        return self._merge(sorted_results)
    
    def _merge(self, results):
        """融合多个结果"""
        prompt = f"""
        以下是多个 Agent 的处理结果，请融合成一个完整的输出：
        {results}
        
        融合后的输出：
        """
        return llm(prompt)
```

---

## 四、多 Agent 的挑战

### 4.1 通信开销

```
问题：Agent 之间的通信成本
  - 每次通信都消耗 token
  - 通信次数随 Agent 数量平方增长
  - 过多的通信可能"淹没"有用信息

解决方案：
  - 限制通信频率
  - 使用结构化消息格式
  - 只传递必要信息
```

### 4.2 协调困难

```
问题：多个 Agent 之间的协调
  - 目标冲突（Agent A 想快，Agent B 想准确）
  - 资源竞争（都想用同一个工具）
  - 信息不一致（同一个问题，不同 Agent 回答不同）

解决方案：
  - 明确的优先级规则
  - 仲裁机制
  - 共享信息池
```

### 4.3 故障传播

```
问题：一个 Agent 出错，影响整个系统
  - 链式反应：A 出错 → B 基于错误结果 → C 继续错误

解决方案：
  - 每个 Agent 独立验证
  - 结果一致性检查
  - 自动隔离故障 Agent
```

---

## 五、适用场景

### 5.1 什么时候用多 Agent

```
需要多 Agent 的场景：
  ✅ 需要多种专业能力（研究 + 写作 + 审核）
  ✅ 需要并行处理（同时处理多个任务）
  ✅ 需要辩论和验证（多个 Agent 互相检查）
  ✅ 需要分步骤处理（流水线作业）

不需要多 Agent 的场景：
  ❌ 简单问答（一个 Agent 就够了）
  ❌ 成本敏感（多 Agent 成本倍增）
  ❌ 延迟敏感（多 Agent 通信增加延迟）
```

### 5.2 成本与收益

```
多 Agent 的成本：
  - 2 个 Agent：成本 ×2
  - 3 个 Agent：成本 ×3
  - 每增加 1 个 Agent，成本线性增加

多 Agent 的收益：
  - 质量提升：通常 10-30%
  - 覆盖面提升：可以处理更多类型任务
  - 可靠性提升：有冗余

建议：从 2 个 Agent 开始，验证收益后再增加
```

---

## 总结

| 架构 | 优点 | 缺点 | 适合场景 |
|------|------|------|---------|
| 中心化 | 易于管理、控制 | 单点瓶颈 | 有明确管理者 |
| 去中心化 | 灵活、容错 | 协调困难 | 平等协作 |
| 分层 | 可扩展、清晰 | 效率低 | 复杂组织 |

**多 Agent 不是"越多越好"，而是"刚刚好最好"。**

下一篇文章，我们将深入**Agent 通信协议**。

---

**思考题**：
1. 你的场景需要多 Agent 吗？如果需要，你会选哪种架构？
2. 中心化和去中心化架构，在"可靠性"和"效率"上各有什么优劣？
3. 如果 3 个 Agent 对同一个问题给出了 3 个不同的答案，你怎么处理？

---

> 上一篇：[36] Agent 个性化与角色定制
> 下一篇：[38] Agent 通信协议
> 系列目录：[README.md](./README.md)