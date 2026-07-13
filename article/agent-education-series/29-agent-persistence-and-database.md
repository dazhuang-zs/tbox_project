# 【AI Agent 系统教学 29】Agent 持久化与数据库

> Agent 的状态不能只活在内存里——它会崩溃、会重启、需要迁移。
> 持久化，就是让 Agent 拥有"永久的记忆"。

---

## 前言：Agent 的数据层

Agent 需要存储的数据类型：

```
对话历史 → 文本、消息列表
用户偏好 → 键值对
知识库 → 文档、向量
工具状态 → 结构化数据
执行日志 → 时序数据
```

每种数据类型，需要不同的存储方案。

---

## 一、Agent 的数据模型

### 1.1 数据分类

```python
class AgentDataTypes:
    """Agent 的数据类型"""
    CONVERSATION = "conversation"   # 对话历史
    KNOWLEDGE = "knowledge"         # 知识库
    PREFERENCE = "preference"       # 用户偏好
    STATE = "state"                 # Agent 状态
    LOG = "log"                     # 执行日志
    MEMORY = "memory"               # 长期记忆
    
    # 各数据类型的特点
    DATA_CHARACTERISTICS = {
        CONVERSATION: {"type": "text", "size": "medium", "access": "sequential"},
        KNOWLEDGE: {"type": "vector+text", "size": "large", "access": "semantic"},
        PREFERENCE: {"type": "kv", "size": "small", "access": "key"},
        STATE: {"type": "json", "size": "small", "access": "key"},
        LOG: {"type": "text", "size": "large", "access": "time"},
        MEMORY: {"type": "json", "size": "small", "access": "semantic"},
    }
```

### 1.2 存储方案选择

| 数据类型 | 推荐存储 | 原因 |
|---------|---------|------|
| 对话历史 | SQLite / PostgreSQL | 结构化，需要查询 |
| 知识库 | 向量数据库 | 语义检索 |
| 用户偏好 | Redis / KV 存储 | 简单键值，高频访问 |
| Agent 状态 | SQLite / Redis | 小数据量，需要事务 |
| 执行日志 | 文件 / ELK | 时序数据，不常查询 |
| 长期记忆 | 向量数据库 + SQL | 需要语义检索 + 结构化查询 |

---

## 二、SQLite：轻量级持久化

### 2.1 对话历史

```python
class ConversationStore:
    """对话历史存储"""
    def __init__(self, db_path="conversations.db"):
        self.conn = sqlite3.connect(db_path)
        self._init_tables()
    
    def _init_tables(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                session_id TEXT,
                user_id TEXT,
                created_at TIMESTAMP,
                updated_at TIMESTAMP
            )
        """)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT,
                role TEXT,
                content TEXT,
                tool_calls TEXT,
                timestamp TIMESTAMP,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id)
            )
        """)
        self.conn.commit()
    
    def save_message(self, conversation_id, role, content, tool_calls=None):
        self.conn.execute("""
            INSERT INTO messages (conversation_id, role, content, tool_calls, timestamp)
            VALUES (?, ?, ?, ?, ?)
        """, (conversation_id, role, content, 
              json.dumps(tool_calls) if tool_calls else None,
              datetime.now()))
        self.conn.commit()
    
    def get_conversation(self, conversation_id):
        cursor = self.conn.execute("""
            SELECT role, content, tool_calls FROM messages
            WHERE conversation_id = ?
            ORDER BY timestamp
        """, (conversation_id,))
        return [
            {"role": row[0], "content": row[1],
             "tool_calls": json.loads(row[2]) if row[2] else None}
            for row in cursor.fetchall()
        ]
```

### 2.2 Agent 状态

```python
class AgentStateStore:
    """Agent 状态持久化"""
    def __init__(self, db_path="agent_state.db"):
        self.conn = sqlite3.connect(db_path)
        self._init_tables()
    
    def save_checkpoint(self, session_id, state, step):
        self.conn.execute("""
            INSERT OR REPLACE INTO checkpoints
            (session_id, step, state_json, created_at)
            VALUES (?, ?, ?, ?)
        """, (session_id, step, json.dumps(state), datetime.now()))
        self.conn.commit()
    
    def resume_from_checkpoint(self, session_id):
        cursor = self.conn.execute("""
            SELECT state_json, step FROM checkpoints
            WHERE session_id = ?
            ORDER BY step DESC LIMIT 1
        """, (session_id,))
        row = cursor.fetchone()
        if row:
            return json.loads(row[0]), row[1]
        return None, 0
```

---

## 三、PostgreSQL：生产级持久化

### 3.1 连接管理

```python
import psycopg2
from psycopg2 import pool

class PostgresPool:
    """PostgreSQL 连接池"""
    def __init__(self, config):
        self.pool = pool.ThreadedConnectionPool(
            minconn=2,
            maxconn=10,
            **config
        )
    
    def get_conn(self):
        return self.pool.getconn()
    
    def return_conn(self, conn):
        self.pool.putconn(conn)
```

### 3.2 工具使用记录

```python
class ToolUsageStore:
    """工具使用记录和统计"""
    def __init__(self, pool):
        self.pool = pool
    
    def log_tool_call(self, session_id, tool_name, params, result, duration_ms):
        conn = self.pool.get_conn()
        try:
            conn.execute("""
                INSERT INTO tool_usage
                (session_id, tool_name, params, result, duration_ms, created_at)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (session_id, tool_name, json.dumps(params),
                  json.dumps(result), duration_ms, datetime.now()))
            conn.commit()
        finally:
            self.pool.putconn(conn)
    
    def get_tool_stats(self, tool_name, hours=24):
        conn = self.pool.get_conn()
        try:
            cursor = conn.execute("""
                SELECT 
                    COUNT(*) as total_calls,
                    AVG(duration_ms) as avg_duration,
                    COUNT(CASE WHEN result->>'error' IS NOT NULL THEN 1 END) as error_count
                FROM tool_usage
                WHERE tool_name = %s
                AND created_at > NOW() - INTERVAL '%s hours'
            """, (tool_name, hours))
            return cursor.fetchone()
        finally:
            self.pool.putconn(conn)
```

---

## 四、Redis：高性能缓存层

### 4.1 会话缓存

```python
import redis

class SessionCache:
    """基于 Redis 的会话缓存"""
    def __init__(self, host="localhost", port=6379, ttl=3600):
        self.client = redis.Redis(host=host, port=port)
        self.ttl = ttl
    
    def cache_messages(self, session_id, messages):
        key = f"session:{session_id}:messages"
        self.client.setex(key, self.ttl, json.dumps(messages))
    
    def get_cached_messages(self, session_id):
        key = f"session:{session_id}:messages"
        data = self.client.get(key)
        return json.loads(data) if data else None
    
    def cache_tool_result(self, tool_name, params, result):
        key = f"tool_cache:{tool_name}:{hash(json.dumps(params, sort_keys=True))}"
        self.client.setex(key, 300, json.dumps(result))  # 5分钟缓存
    
    def get_cached_tool_result(self, tool_name, params):
        key = f"tool_cache:{tool_name}:{hash(json.dumps(params, sort_keys=True))}"
        data = self.client.get(key)
        return json.loads(data) if data else None
```

### 4.2 速率限制

```python
class RateLimiter:
    """基于 Redis 的速率限制"""
    def __init__(self, client):
        self.client = client
    
    def check_rate_limit(self, user_id, max_requests=10, window=60):
        key = f"rate_limit:{user_id}"
        current = self.client.get(key)
        
        if current and int(current) >= max_requests:
            return False, "请求过于频繁"
        
        self.client.incr(key)
        self.client.expire(key, window)
        return True, None
```

---

## 五、文件系统：日志和检查点

### 5.1 日志存储

```python
class AgentFileLogger:
    """基于文件的 Agent 日志"""
    def __init__(self, log_dir="agent_logs/"):
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)
    
    def log_run(self, run_id, data):
        filename = f"{self.log_dir}/{run_id}_{datetime.now():%Y%m%d_%H%M%S}.jsonl"
        with open(filename, "a") as f:
            f.write(json.dumps(data) + "\n")
    
    def get_logs(self, run_id):
        import glob
        pattern = f"{self.log_dir}/{run_id}_*.jsonl"
        logs = []
        for filename in sorted(glob.glob(pattern)):
            with open(filename) as f:
                for line in f:
                    logs.append(json.loads(line))
        return logs
```

### 5.2 检查点

```python
class CheckpointStore:
    """文件系统检查点"""
    def __init__(self, checkpoint_dir="checkpoints/"):
        self.checkpoint_dir = checkpoint_dir
        os.makedirs(checkpoint_dir, exist_ok=True)
    
    def save(self, session_id, state, step):
        path = f"{self.checkpoint_dir}/{session_id}/step_{step}.json"
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            json.dump(state, f, default=str)
    
    def load_latest(self, session_id):
        import glob
        pattern = f"{self.checkpoint_dir}/{session_id}/step_*.json"
        files = glob.glob(pattern)
        if not files:
            return None
        
        latest = max(files, key=lambda f: int(
            f.split("step_")[1].split(".")[0]
        ))
        with open(latest) as f:
            return json.load(f)
```

---

## 六、数据层架构设计

### 6.1 分层架构

```python
class AgentDataLayer:
    """Agent 数据层统一接口"""
    def __init__(self, config):
        self.config = config
        self._init_stores()
    
    def _init_stores(self):
        # SQLite 对话历史
        self.conversations = ConversationStore(self.config["db_path"])
        
        # Redis 缓存
        self.cache = SessionCache(
            host=self.config.get("redis_host", "localhost")
        )
        
        # 文件日志
        self.logger = AgentFileLogger(self.config.get("log_dir", "logs/"))
        
        # 向量数据库
        if self.config.get("vector_db"):
            self.vector_db = self._init_vector_db()
    
    def save_message(self, session_id, message):
        # 写入数据库
        self.conversations.save_message(session_id, **message)
        
        # 更新缓存
        messages = self.cache.get_cached_messages(session_id) or []
        messages.append(message)
        self.cache.cache_messages(session_id, messages)
    
    def get_messages(self, session_id):
        # 优先从缓存读取
        cached = self.cache.get_cached_messages(session_id)
        if cached:
            return cached
        # 回源到数据库
        return self.conversations.get_conversation(session_id)
```

### 6.2 数据生命周期

```
创建 → 使用 → 归档 → 清理

对话历史：
  创建：新对话开始
  使用：每轮追加
  归档：7天后压缩
  清理：30天后删除

Agent 状态：
  创建：Agent 初始化
  使用：每步更新
  归档：任务完成后
  清理：1天后删除

用户偏好：
  创建：首次交互
  使用：持续更新
  归档：不需要
  清理：用户注销时
```

---

## 七、2026 年趋势

### 7.1 统一存储

从多个存储系统走向统一存储：

- SQLite 存所有结构化数据
- 向量数据库存所有非结构化数据
- Redis 只做缓存

### 7.2 数据层即服务

Agent 数据层变成可配置的服务：

```
Agent → DataLayer API → 存储后端
  ├─ 对话历史 → SQLite/PostgreSQL
  ├─ 知识库 → 向量数据库
  ├─ 缓存 → Redis
  └─ 日志 → 文件/ELK
```

---

## 总结

| 存储方案 | 适合 | 不适合 |
|---------|------|--------|
| SQLite | 对话历史、状态 | 大规模并发 |
| PostgreSQL | 生产级、复杂查询 | 快速缓存 |
| Redis | 缓存、会话 | 持久化数据 |
| 向量数据库 | 知识库、记忆 | 结构化查询 |
| 文件系统 | 日志、检查点 | 频繁读写 |

**选择存储方案的原则：不选"最好的"，选"最合适的"。**

下一篇文章，我们将完成模块四，进入**从 Agent 到 Agentic Workflow**——确定性流程与 Agent 自主决策的混合模式。

---

**思考题**：
1. 你的 Agent 现在用了哪些存储方案？是不是"一个数据库搞定所有"？
2. 对话历史需要存多久？你的清理策略是什么？
3. 如果 Agent 的数据量从 1 万增长到 100 万，你的存储方案还能撑住吗？

---

> 上一篇：[28] Agent 状态管理
> 下一篇：[30] 从 Agent 到 Agentic Workflow
> 系列目录：[README.md](./README.md)