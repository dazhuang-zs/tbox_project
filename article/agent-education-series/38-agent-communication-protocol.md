# 【AI Agent 系统教学 38】Agent 通信协议

> 多 Agent 系统的核心不是"Agent 有多少"，而是"Agent 之间怎么说话"。
> 通信协议决定了 Agent 是"团队"还是"乌合之众"。

---

## 前言：Agent 之间的"语言"

单 Agent 和 LLM 通信：通过自然语言或 API。

多 Agent 系统需要 Agent 之间通信：通过**协议**。

```
Agent A 对 Agent B 说：
  "帮我查一下这个数据"
  
这不是简单的"说话"，而是：
  1. 谁（Agent A）
  2. 对谁（Agent B）
  3. 说什么（请求数据）
  4. 怎么回（数据格式）
  5. 什么时候回（同步/异步）
  6. 如果出错怎么办（错误处理）
```

---

## 一、通信模式

### 1.1 同步通信

```python
class SyncCommunication:
    """同步通信：A 等待 B 响应"""
    async def request(self, sender, receiver, message):
        # 发送请求
        msg_id = self.message_bus.send(sender, receiver, message)
        
        # 等待响应（阻塞）
        response = await self.message_bus.wait_for_response(msg_id, timeout=10)
        
        return response
```

### 1.2 异步通信

```python
class AsyncCommunication:
    """异步通信：A 发消息后继续工作，B 完成后通知"""
    def __init__(self):
        self.callbacks = {}
        self.message_bus = MessageBus()
    
    async def request_async(self, sender, receiver, message, callback=None):
        msg_id = self.message_bus.send(sender, receiver, message)
        
        if callback:
            self.callbacks[msg_id] = callback
        
        # 不等待，立即返回
        return msg_id
    
    async def handle_response(self, msg_id, response):
        """处理响应"""
        if msg_id in self.callbacks:
            await self.callbacks[msg_id](response)
```

### 1.3 黑板模式

```python
class BlackboardPattern:
    """黑板模式：共享信息空间"""
    def __init__(self):
        self.blackboard = {}  # 共享信息
        self.subscribers = {}  # 订阅者
    
    def write(self, agent, key, value):
        """写入黑板"""
        self.blackboard[key] = {
            "value": value,
            "writer": agent,
            "timestamp": time.time(),
        }
        self._notify(key)
    
    def read(self, key):
        """读取黑板"""
        return self.blackboard.get(key)
    
    def subscribe(self, agent, key_pattern, callback):
        """订阅特定模式的信息"""
        if key_pattern not in self.subscribers:
            self.subscribers[key_pattern] = []
        self.subscribers[key_pattern].append((agent, callback))
    
    def _notify(self, key):
        """通知订阅者"""
        for pattern, subscribers in self.subscribers.items():
            if self._match_pattern(key, pattern):
                for agent, callback in subscribers:
                    callback(agent, key, self.blackboard[key])
```

---

## 二、消息格式

### 2.1 标准消息

```python
class AgentMessage:
    """标准 Agent 消息"""
    def __init__(self):
        self.version = "1.0"
        self.message_id = str(uuid.uuid4())
        self.conversation_id = str(uuid.uuid4())
        
        # 路由
        self.sender = None
        self.receiver = None
        self.reply_to = None
        
        # 内容
        self.type = None  # request, response, broadcast, error
        self.action = None  # task, query, result, feedback
        self.payload = None
        
        # 控制
        self.priority = 0
        self.ttl = 60  # Time To Live
        self.requires_ack = False
        
        # 元数据
        self.timestamp = time.time()
        self.token_cost = 0
    
    def to_dict(self):
        return {
            "version": self.version,
            "message_id": self.message_id,
            "conversation_id": self.conversation_id,
            "sender": self.sender,
            "receiver": self.receiver,
            "type": self.type,
            "action": self.action,
            "payload": self.payload,
            "priority": self.priority,
            "ttl": self.ttl,
            "timestamp": self.timestamp,
        }
```

### 2.2 消息类型

```python
class MessageTypes:
    """消息类型"""
    # 任务相关
    TASK_ASSIGN = "task_assign"      # 分配任务
    TASK_RESULT = "task_result"      # 返回结果
    TASK_PROGRESS = "task_progress"  # 进度更新
    TASK_CANCEL = "task_cancel"      # 取消任务
    
    # 查询相关
    QUERY = "query"                  # 查询信息
    QUERY_RESPONSE = "query_response"  # 查询响应
    
    # 协调相关
    LOCK = "lock"                    # 请求锁
    RELEASE = "release"              # 释放锁
    SYNC = "sync"                    # 同步请求
    
    # 错误相关
    ERROR = "error"                  # 错误
    RETRY = "retry"                  # 重试请求
    FALLBACK = "fallback"            # 降级请求
```

---

## 三、协商协议

### 3.1 合同网协议

```python
class ContractNetProtocol:
    """合同网协议：任务招标"""
    def __init__(self, agents):
        self.agents = agents
        self.bids = {}
    
    def announce_task(self, task):
        """招标：向所有 Agent 发布任务"""
        self.current_task = task
        self.bids = {}
        
        for agent in self.agents:
            message = AgentMessage()
            message.type = "task_announcement"
            message.payload = {
                "task": task,
                "deadline": time.time() + 10,
            }
            agent.receive(message)
    
    def receive_bid(self, agent_name, bid):
        """接收投标"""
        self.bids[agent_name] = bid
    
    def award_contract(self):
        """评标：选择最优投标"""
        if not self.bids:
            return None
        
        best_agent = max(
            self.bids.items(),
            key=lambda x: x[1]["score"],
        )
        
        # 通知中标
        self._notify_winner(best_agent[0])
        
        # 通知未中标
        for agent in self.bids:
            if agent != best_agent[0]:
                self._notify_loser(agent)
        
        return best_agent
```

### 3.2 投票协议

```python
class VotingProtocol:
    """投票协议"""
    def __init__(self, agents):
        self.agents = agents
    
    def vote(self, question, options):
        """发起投票"""
        votes = {}
        for agent in self.agents:
            vote = agent.cast_vote(question, options)
            votes[agent.name] = vote
        
        return self._tally(votes)
    
    def _tally(self, votes):
        """计票"""
        counts = {}
        for agent, vote in votes.items():
            option = vote["choice"]
            confidence = vote.get("confidence", 1.0)
            counts[option] = counts.get(option, 0) + confidence
        
        winner = max(counts, key=counts.get)
        return {
            "winner": winner,
            "counts": counts,
            "total_votes": len(votes),
        }
```

---

## 四、协调机制

### 4.1 锁机制

```python
class DistributedLock:
    """分布式锁，避免资源冲突"""
    def __init__(self):
        self.locks = {}
    
    def acquire(self, resource, agent, timeout=5):
        """获取锁"""
        if resource in self.locks:
            lock = self.locks[resource]
            if time.time() - lock["timestamp"] > timeout:
                # 锁超时，强制释放
                del self.locks[resource]
            else:
                return False
        
        self.locks[resource] = {
            "agent": agent,
            "timestamp": time.time(),
        }
        return True
    
    def release(self, resource, agent):
        """释放锁"""
        if resource in self.locks:
            if self.locks[resource]["agent"] == agent:
                del self.locks[resource]
```

### 4.2 共识协议

```python
class ConsensusProtocol:
    """共识协议：多方达成一致"""
    def achieve_consensus(self, agents, proposal, max_rounds=5):
        """达成共识"""
        current_proposal = proposal
        
        for round in range(max_rounds):
            responses = []
            for agent in agents:
                response = agent.evaluate(current_proposal)
                responses.append(response)
            
            if all(r["approved"] for r in responses):
                return {"status": "consensus", "proposal": current_proposal}
            
            # 收集反馈，修改提案
            feedbacks = [r.get("feedback", "") for r in responses if not r["approved"]]
            current_proposal = self._revise(proposal, feedbacks)
        
        return {"status": "failed", "reason": "无法达成共识"}
```

---

## 五、通信优化

### 5.1 消息压缩

```python
class MessageCompressor:
    """消息压缩"""
    def compress(self, message):
        """压缩消息，减少 token 消耗"""
        # 1. 移除冗余字段
        compressed = {k: v for k, v in message.items() 
                      if v is not None and v != ""}
        
        # 2. 缩短字段名
        field_mapping = {
            "message_id": "id",
            "conversation_id": "cid",
            "timestamp": "ts",
            "payload": "p",
        }
        for old, new in field_mapping.items():
            if old in compressed:
                compressed[new] = compressed.pop(old)
        
        return compressed
```

### 5.2 消息聚合

```python
class MessageAggregator:
    """消息聚合"""
    def aggregate(self, messages, max_batch_size=10):
        """聚合多条消息为一条"""
        if len(messages) <= 1:
            return messages
        
        batches = []
        for i in range(0, len(messages), max_batch_size):
            batch = messages[i:i+max_batch_size]
            aggregated = {
                "type": "batch",
                "count": len(batch),
                "messages": batch,
            }
            batches.append(aggregated)
        
        return batches
```

---

## 六、2026 年通信协议趋势

### 6.1 A2A 协议

Google 在 2026 年提出的 **Agent-to-Agent（A2A）** 协议，类似 MCP 但针对 Agent 间通信：

```
MCP：Agent ↔ 工具
A2A：Agent ↔ Agent
```

### 6.2 自然语言通信

Agent 之间的通信从"结构化数据"回归"自然语言"：

```
A2A 之前：
  {"type": "request", "action": "search", "params": {"query": "..."}}

A2A 之后（自然语言）：
  "请帮我查一下这个数据，我等着用"
```

### 6.3 语义通信

Agent 不再传输"数据"，而是传输"语义"：

```
传统：传输完整文档
语义：传输"文档的核心观点是...，包含三个要点..."
```

---

## 总结

| 通信模式 | 特点 | 适用场景 |
|---------|------|---------|
| 同步 | 简单、直接 | 需要立即响应 |
| 异步 | 灵活、高效 | 耗时任务 |
| 黑板 | 共享、解耦 | 多对多通信 |
| 合同网 | 招标式 | 任务分配 |
| 投票 | 民主式 | 决策 |

**好的通信协议，让多 Agent 系统从"混乱"变为"有序"。**

下一篇文章，我们将深入**多 Agent 协作模式**。

---

**思考题**：
1. 异步通信和同步通信，在 Agent 场景中各有什么利弊？
2. 黑板模式在什么场景下特别有用？有什么缺点？
3. 如果你需要 10 个 Agent 协作完成一个任务，你会怎么设计通信协议？

---

> 上一篇：[37] 多 Agent 架构导论
> 下一篇：[39] 多 Agent 协作模式
> 系列目录：[README.md](./README.md)