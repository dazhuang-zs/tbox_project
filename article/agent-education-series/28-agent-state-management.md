# 【AI Agent 系统教学 28】Agent 状态管理

> Agent 不是"一次性"的——它需要记住对话历史、当前状态、中间结果。
> 管理好状态，Agent 才能"持续工作"。

---

## 前言：无状态 Agent 的局限

最简单的 Agent 实现是无状态的——每次请求都是独立的。

但实际场景中，Agent 需要：

- 记住用户说过的信息
- 知道当前执行到哪一步了
- 能从中断的地方继续
- 跨会话保持用户偏好

**没有状态管理，Agent 就是一个"每次都要重新认识"的助手。**

---

## 一、Agent 的状态模型

### 1.1 状态的三层结构

```
┌─────────────────────────────────────┐
│ 第一层：会话状态（Session）           │
│ 当前对话的上下文、临时变量             │
│ 生命周期：一次会话                    │
├─────────────────────────────────────┤
│ 第二层：用户状态（User）              │
│ 用户偏好、历史交互、设置              │
│ 生命周期：长期                        │
├─────────────────────────────────────┤
│ 第三层：全局状态（Global）            │
│ 工具注册、模型配置、系统设置           │
│ 生命周期：永久                        │
└─────────────────────────────────────┘
```

### 1.2 状态定义

```python
from typing import TypedDict, List, Optional
from datetime import datetime

class AgentState(TypedDict):
    """Agent 的完整状态"""
    # 会话状态
    session_id: str
    messages: List[dict]          # 对话历史
    step_count: int               # 当前步数
    current_task: Optional[str]   # 当前任务
    pending_tool_calls: List      # 待执行的工具调用
    tool_results: List            # 工具执行结果
    
    # 用户状态
    user_id: str
    user_preferences: dict        # 用户偏好
    user_context: dict            # 用户上下文（如姓名、邮箱等）
    
    # 执行状态
    status: str                   # idle, running, paused, error, done
    error: Optional[str]          # 错误信息
    created_at: datetime
    updated_at: datetime
```

---

## 二、状态管理实现

### 2.1 内存状态管理

```python
class InMemoryStateManager:
    """内存状态管理（适合单实例、不持久化）"""
    def __init__(self):
        self.states = {}
    
    def get_state(self, session_id: str) -> AgentState:
        if session_id not in self.states:
            self.states[session_id] = self._create_state(session_id)
        return self.states[session_id]
    
    def update_state(self, session_id: str, updates: dict):
        state = self.get_state(session_id)
        state.update(updates)
        state["updated_at"] = datetime.now()
    
    def clear_state(self, session_id: str):
        self.states.pop(session_id, None)
    
    def _create_state(self, session_id: str) -> AgentState:
        return {
            "session_id": session_id,
            "messages": [],
            "step_count": 0,
            "current_task": None,
            "pending_tool_calls": [],
            "tool_results": [],
            "user_id": "anonymous",
            "user_preferences": {},
            "user_context": {},
            "status": "idle",
            "error": None,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }
```

### 2.2 持久化状态管理

```python
import json
import sqlite3

class PersistentStateManager:
    """持久化状态管理（使用 SQLite）"""
    def __init__(self, db_path="agent_state.db"):
        self.conn = sqlite3.connect(db_path)
        self._init_db()
    
    def _init_db(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS agent_states (
                session_id TEXT PRIMARY KEY,
                user_id TEXT,
                state_json TEXT,
                created_at TIMESTAMP,
                updated_at TIMESTAMP
            )
        """)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS user_preferences (
                user_id TEXT PRIMARY KEY,
                preferences_json TEXT
            )
        """)
        self.conn.commit()
    
    def save_state(self, session_id: str, state: dict):
        self.conn.execute("""
            INSERT OR REPLACE INTO agent_states
            (session_id, user_id, state_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
        """, (
            session_id,
            state.get("user_id", "anonymous"),
            json.dumps(state, default=str),
            state.get("created_at", datetime.now()),
            datetime.now(),
        ))
        self.conn.commit()
    
    def load_state(self, session_id: str) -> Optional[dict]:
        cursor = self.conn.execute(
            "SELECT state_json FROM agent_states WHERE session_id = ?",
            (session_id,),
        )
        row = cursor.fetchone()
        if row:
            return json.loads(row[0])
        return None
    
    def save_user_preferences(self, user_id: str, preferences: dict):
        self.conn.execute("""
            INSERT OR REPLACE INTO user_preferences
            (user_id, preferences_json)
            VALUES (?, ?)
        """, (user_id, json.dumps(preferences)))
        self.conn.commit()
    
    def load_user_preferences(self, user_id: str) -> dict:
        cursor = self.conn.execute(
            "SELECT preferences_json FROM user_preferences WHERE user_id = ?",
            (user_id,),
        )
        row = cursor.fetchone()
        if row:
            return json.loads(row[0])
        return {}
```

---

## 三、中断与恢复

### 3.1 中断点

```python
class InterruptibleAgent:
    """支持中断和恢复的 Agent"""
    def __init__(self, state_manager):
        self.state_manager = state_manager
    
    def run(self, session_id: str, user_input: str):
        # 1. 加载状态
        state = self.state_manager.load_state(session_id)
        if not state:
            state = self._create_new_state(session_id)
        
        # 2. 检查是否有未完成的任务
        if state["status"] == "paused":
            return self._resume(state)
        
        # 3. 开始新任务
        state["status"] = "running"
        state["current_task"] = user_input
        state["messages"].append({"role": "user", "content": user_input})
        
        # 4. 执行 Agent 循环
        result = self._execute_loop(state)
        
        # 5. 保存状态
        state["status"] = "done" if result["success"] else "error"
        state["error"] = result.get("error")
        self.state_manager.save_state(session_id, state)
        
        return result
    
    def _execute_loop(self, state):
        """执行 Agent 循环，支持中断"""
        for step in range(10):
            # 检查外部中断信号
            if self._check_interrupt(state["session_id"]):
                state["status"] = "paused"
                self.state_manager.save_state(state["session_id"], state)
                return {"status": "paused", "message": "已暂停"}
            
            response = self.llm.generate(state["messages"])
            
            if not self._has_tool_call(response):
                return {"status": "done", "response": response}
            
            results = self._execute_tools(response)
            for r in results:
                state["messages"].append(r)
                state["tool_results"].append(r)
            
            state["step_count"] = step + 1
            # 每步保存状态
            self.state_manager.save_state(state["session_id"], state)
        
        return {"status": "max_steps", "response": "达到最大步数"}
    
    def _resume(self, state):
        """从暂停点恢复"""
        state["status"] = "running"
        return self._execute_loop(state)
```

### 3.2 断点续传

```python
class CheckpointManager:
    """检查点管理，支持更细粒度的中断恢复"""
    def __init__(self, storage_path="checkpoints/"):
        self.path = storage_path
        os.makedirs(storage_path, exist_ok=True)
    
    def save_checkpoint(self, session_id, step, state):
        filename = f"{self.path}/{session_id}_step_{step}.json"
        with open(filename, "w") as f:
            json.dump(state, f, default=str)
    
    def load_checkpoint(self, session_id, step):
        filename = f"{self.path}/{session_id}_step_{step}.json"
        if os.path.exists(filename):
            with open(filename) as f:
                return json.load(f)
        return None
    
    def get_last_checkpoint(self, session_id):
        """获取最近的检查点"""
        import glob
        pattern = f"{self.path}/{session_id}_step_*.json"
        files = glob.glob(pattern)
        if not files:
            return None
        latest = max(files, key=os.path.getctime)
        with open(latest) as f:
            return json.load(f)
```

---

## 四、状态一致性

### 4.1 乐观锁

```python
class OptimisticLock:
    """乐观锁，防止并发修改状态"""
    def __init__(self, state_manager):
        self.state_manager = state_manager
    
    def update_state(self, session_id, update_fn):
        max_retries = 3
        for attempt in range(max_retries):
            state = self.state_manager.load_state(session_id)
            version = state.get("version", 0)
            
            # 执行更新
            new_state = update_fn(state)
            new_state["version"] = version + 1
            
            # 检查版本冲突
            current = self.state_manager.load_state(session_id)
            if current.get("version", 0) == version:
                self.state_manager.save_state(session_id, new_state)
                return new_state
            else:
                if attempt == max_retries - 1:
                    raise ConflictError("状态版本冲突")
                time.sleep(0.1)
```

### 4.2 事务

```python
class StateTransaction:
    """状态事务，保证原子性"""
    def __init__(self, state_manager):
        self.state_manager = state_manager
        self.backup = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            # 异常时回滚
            if self.backup:
                self.state_manager.restore(self.backup)
            return False
        return True
    
    def begin(self, session_id):
        self.backup = self.state_manager.load_state(session_id)
```

---

## 五、状态模式设计

### 5.1 Agent 状态机

```python
from enum import Enum

class AgentStatus(Enum):
    IDLE = "idle"           # 空闲
    RUNNING = "running"     # 运行中
    WAITING = "waiting"     # 等待工具结果
    PAUSED = "paused"       # 已暂停
    ERROR = "error"         # 错误
    DONE = "done"           # 完成

class AgentStateMachine:
    """Agent 状态机"""
    TRANSITIONS = {
        AgentStatus.IDLE: [AgentStatus.RUNNING],
        AgentStatus.RUNNING: [AgentStatus.WAITING, AgentStatus.DONE, AgentStatus.ERROR, AgentStatus.PAUSED],
        AgentStatus.WAITING: [AgentStatus.RUNNING, AgentStatus.ERROR],
        AgentStatus.PAUSED: [AgentStatus.RUNNING, AgentStatus.IDLE],
        AgentStatus.ERROR: [AgentStatus.IDLE, AgentStatus.RUNNING],
        AgentStatus.DONE: [AgentStatus.IDLE],
    }
    
    def __init__(self):
        self.current = AgentStatus.IDLE
    
    def transition(self, new_status):
        if new_status in self.TRANSITIONS[self.current]:
            self.current = new_status
            return True
        raise InvalidTransition(f"不能从 {self.current} 转换到 {new_status}")
```

---

## 六、实践建议

### 6.1 状态管理原则

1. **最小状态原则**：只保存必要的信息，不要保存所有内容
2. **可序列化**：所有状态必须可序列化（JSON 兼容）
3. **版本控制**：状态格式变化时，需要迁移策略
4. **清理策略**：定期清理过期状态
5. **安全**：敏感信息不能保存在状态中

### 6.2 状态大小控制

```python
class StateSizeController:
    """控制状态大小"""
    MAX_STATE_SIZE = 1024 * 1024  # 1MB
    
    def check_size(self, state):
        size = len(json.dumps(state, default=str))
        if size > self.MAX_STATE_SIZE:
            # 压缩：压缩历史对话
            state["messages"] = self._compress_messages(state["messages"])
            # 压缩：只保留最近的工具结果
            state["tool_results"] = state["tool_results"][-10:]
        return state
```

---

## 总结

| 状态类型 | 存储 | 生命周期 | 示例 |
|---------|------|---------|------|
| 会话状态 | 内存/Redis | 一次会话 | 对话历史、当前步骤 |
| 用户状态 | 数据库 | 长期 | 偏好、设置 |
| 全局状态 | 配置文件 | 永久 | 工具注册、模型配置 |
| 检查点 | 文件/数据库 | 直到恢复 | 中断点、迁移点 |

**好的状态管理，让 Agent 从"每次重新开始"变成"持续工作"。**

下一篇文章，我们将深入**Agent 持久化与数据库**——如何设计 Agent 的数据层。

---

**思考题**：
1. 你的 Agent 现在的状态管理是怎么做的？有没有持久化？
2. 如果 Agent 在执行过程中断了，你希望它怎么恢复？
3. 状态中的"用户偏好"和"对话历史"，你觉得哪个更重要？为什么？

---

> 上一篇：[27] Agent Loop 的工程实现
> 下一篇：[29] Agent 持久化与数据库
> 系列目录：[README.md](./README.md)