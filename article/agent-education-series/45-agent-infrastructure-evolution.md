# 【AI Agent 系统教学 45】Agent 基础设施演进

> Agent 不只是"模型"，它需要完整的基础设施支撑。
> 从运行时到监控，Agent 基础设施正在成为新的"云原生"。

---

## 前言：Agent 需要"操作系统"

2026 年，Agent 开发已经不只是"写代码"。

就像 Web 应用需要 Web 服务器、数据库、负载均衡，Agent 应用也需要自己的基础设施：

```
Agent 基础设施：
  - 运行时（Runtime）：运行 Agent 的环境
  - 注册中心（Registry）：管理和发现 Agent
  - 监控系统（Monitoring）：追踪 Agent 行为
  - 存储系统（Storage）：持久化 Agent 状态
  - 通信总线（Bus）：Agent 之间通信
  - 安全网关（Gateway）：安全控制
```

---

## 一、Agent 运行时

### 1.1 运行时架构

```python
class AgentRuntime:
    """Agent 运行时"""
    def __init__(self, config):
        self.config = config
        self.sandbox = Sandbox()
        self.resource_manager = ResourceManager()
        self.lifecycle = LifecycleManager()
    
    def start_agent(self, agent_id, agent_code):
        """启动 Agent"""
        # 1. 创建沙箱
        sandbox = self.sandbox.create(agent_id)
        
        # 2. 分配资源
        resources = self.resource_manager.allocate(agent_id, {
            "memory": "256MB",
            "cpu": "0.5 core",
            "storage": "1GB",
        })
        
        # 3. 启动
        process = self.lifecycle.start(agent_id, agent_code, sandbox, resources)
        
        return AgentInstance(agent_id, process, sandbox, resources)
    
    def stop_agent(self, agent_id):
        """停止 Agent"""
        self.lifecycle.stop(agent_id)
        self.resource_manager.release(agent_id)
        self.sandbox.destroy(agent_id)
```

### 1.2 运行时特性

| 特性 | 说明 | 实现 |
|------|------|------|
| 隔离性 | Agent 之间互不影响 | 沙箱、容器 |
| 资源限制 | 限制 CPU、内存、存储 | cgroup、资源配额 |
| 热更新 | 不重启更新 Agent | 蓝绿部署 |
| 弹性伸缩 | 根据负载自动扩缩 | K8s HPA |
| 容错 | Agent 崩溃自动重启 | 健康检查、重启策略 |

---

## 二、Agent 注册中心

### 2.1 服务发现

```python
class AgentRegistry:
    """Agent 注册中心"""
    def __init__(self):
        self.agents = {}
        self.services = {}
    
    def register(self, agent):
        """注册 Agent"""
        self.agents[agent.id] = {
            "agent": agent,
            "status": "active",
            "capabilities": agent.capabilities,
            "endpoint": agent.endpoint,
            "registered_at": datetime.now(),
            "last_heartbeat": datetime.now(),
        }
        
        # 注册提供的服务
        for capability in agent.capabilities:
            if capability not in self.services:
                self.services[capability] = []
            self.services[capability].append(agent.id)
    
    def discover(self, capability):
        """发现提供特定能力的 Agent"""
        agent_ids = self.services.get(capability, [])
        return [
            self.agents[aid] for aid in agent_ids
            if self.agents[aid]["status"] == "active"
        ]
    
    def heartbeat(self, agent_id):
        """心跳检测"""
        if agent_id in self.agents:
            self.agents[agent_id]["last_heartbeat"] = datetime.now()
    
    def check_health(self):
        """健康检查"""
        now = datetime.now()
        for agent_id, info in self.agents.items():
            if (now - info["last_heartbeat"]).seconds > 30:
                info["status"] = "unreachable"
```

---

## 三、Agent 监控系统

### 3.1 监控指标

```python
class AgentMonitor:
    """Agent 监控系统"""
    def __init__(self):
        self.metrics = {
            "latency": [],
            "token_usage": [],
            "error_rate": [],
            "tool_calls": [],
            "memory_usage": [],
        }
    
    def record_metric(self, agent_id, metric_name, value):
        """记录指标"""
        if metric_name in self.metrics:
            self.metrics[metric_name].append({
                "agent_id": agent_id,
                "value": value,
                "timestamp": time.time(),
            })
    
    def get_agent_health(self, agent_id, window="5m"):
        """获取 Agent 健康状态"""
        recent = self._get_recent_metrics(agent_id, window)
        
        return {
            "agent_id": agent_id,
            "status": "healthy" if self._is_healthy(recent) else "unhealthy",
            "avg_latency_ms": self._avg(recent["latency"]),
            "error_rate": self._error_rate(recent["error_rate"]),
            "token_usage": self._sum(recent["token_usage"]),
            "tool_calls": self._sum(recent["tool_calls"]),
        }
```

### 3.2 告警

```python
class AlertSystem:
    """告警系统"""
    def __init__(self):
        self.rules = [
            {"metric": "error_rate", "operator": ">", "threshold": 0.05, "severity": "critical"},
            {"metric": "latency", "operator": ">", "threshold": 5000, "severity": "warning"},
            {"metric": "memory_usage", "operator": ">", "threshold": 0.9, "severity": "critical"},
        ]
    
    def evaluate(self, agent_health):
        """评估告警"""
        alerts = []
        for rule in self.rules:
            value = agent_health.get(rule["metric"])
            if value and self._compare(value, rule["operator"], rule["threshold"]):
                alerts.append({
                    "agent_id": agent_health["agent_id"],
                    "metric": rule["metric"],
                    "value": value,
                    "threshold": rule["threshold"],
                    "severity": rule["severity"],
                    "timestamp": time.time(),
                })
        return alerts
```

---

## 四、Agent 存储系统

### 4.1 存储层级

```python
class AgentStorage:
    """Agent 存储系统"""
    def __init__(self):
        self.layers = {
            "hot": RedisCache(),     # 热数据：当前会话
            "warm": SQLiteDB(),      # 温数据：近期对话
            "cold": ObjectStore(),   # 冷数据：历史数据
        }
    
    def store(self, agent_id, data, importance="normal"):
        """存储数据"""
        if importance == "high":
            # 高重要性：存到所有层
            self.layers["hot"].set(agent_id, data)
            self.layers["warm"].insert(agent_id, data)
            self.layers["cold"].backup(agent_id, data)
        elif importance == "normal":
            # 普通：存到热层和温层
            self.layers["hot"].set(agent_id, data)
            self.layers["warm"].insert(agent_id, data)
        else:
            # 低重要性：只存热层
            self.layers["hot"].set(agent_id, data)
    
    def retrieve(self, agent_id, query):
        """检索数据"""
        # 先从热层查
        result = self.layers["hot"].get(agent_id)
        if result:
            return result
        
        # 再从温层查
        result = self.layers["warm"].query(agent_id, query)
        if result:
            self.layers["hot"].set(agent_id, result)  # 提升到热层
            return result
        
        # 最后从冷层查
        return self.layers["cold"].query(agent_id, query)
```

---

## 五、Agent 网关

### 5.1 网关功能

```python
class AgentGateway:
    """Agent 网关"""
    def __init__(self):
        self.rate_limiter = RateLimiter()
        self.auth = AuthManager()
        self.router = Router()
    
    async def handle_request(self, request):
        """处理请求"""
        # 1. 认证
        user = await self.auth.authenticate(request)
        if not user:
            return Response(status=401, body="Unauthorized")
        
        # 2. 限流
        allowed = self.rate_limiter.check(user.id)
        if not allowed:
            return Response(status=429, body="Too Many Requests")
        
        # 3. 路由到目标 Agent
        agent = self.router.route(request)
        if not agent:
            return Response(status=404, body="Agent Not Found")
        
        # 4. 转发请求
        result = await agent.process(request)
        
        return result
```

---

## 六、2026 年基础设施趋势

### 6.1 Agent 原生云

就像"云原生"一样，Agent 正在成为基础设施的一等公民：

```
K8s + Agent：
  - Agent 作为 Pod 运行
  - 自动伸缩
  - 服务发现
  - 负载均衡
  - 滚动更新
```

### 6.2 Agent 操作系统

```
Agent OS（未来展望）：
  - 进程管理：启动、停止 Agent
  - 资源管理：CPU、内存、存储
  - 通信管理：Agent 间通信
  - 安全管理：权限、沙箱
  - 设备管理：摄像头、麦克风、传感器
```

### 6.3 标准化

```
Agent 基础设施标准化：
  - MCP：工具协议
  - A2A：Agent 通信协议
  - Agent Runtime：运行时标准
  - Agent Registry：注册标准
```

---

## 总结

| 基础设施 | 功能 | 关键技术 |
|---------|------|---------|
| 运行时 | 运行 Agent | 沙箱、容器 |
| 注册中心 | 管理 Agent | 服务发现 |
| 监控系统 | 追踪 Agent | 指标、告警 |
| 存储系统 | 持久化 | 分层存储 |
| 网关 | 安全控制 | 认证、限流 |

**Agent 基础设施正在从"手动搭建"走向"标准化平台"。**

最后一篇文章，我们将完成整个系列，进入**2026 年 Agent 生态全景**。

---

**思考题**：
1. 你现在的 Agent 跑在什么基础设施上？有没有考虑过 Agent 运行时？
2. Agent 监控和普通 API 监控有什么区别？需要额外关注什么？
3. 如果 Agent 达到百万级，你觉得基础设施的瓶颈会是什么？

---

> 上一篇：[44] 从 Agent 到 AGI 的路径
> 下一篇：[46] 2026 年 Agent 生态全景
> 系列目录：[README.md](./README.md)