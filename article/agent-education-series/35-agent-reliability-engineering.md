# 【AI Agent 系统教学 35】Agent 可靠性工程

> Agent 不是"永远正确"的。好的 Agent 设计不是避免错误，而是优雅地处理错误。
> 可靠性工程，就是让 Agent 在出错时"不崩"、"不坏"、"还可控"。

---

## 前言：Agent 一定会出错

Agent 运行在生产环境中，面对的是：

- 模型可能输出格式错误
- 工具可能返回异常
- 网络可能超时
- 用户可能输入意想不到的内容
- 上下文可能超出限制

**可靠性工程的目标不是让 Agent 不出错，而是让 Agent 在出错时仍然可控。**

---

## 一、容错设计

### 1.1 错误分类

```python
class AgentError(Enum):
    # 可恢复错误
    TOOL_TIMEOUT = "tool_timeout"            # 工具超时
    TOOL_RATE_LIMIT = "tool_rate_limit"      # 工具限流
    TOOL_TEMPORARY_FAILURE = "tool_temp_fail" # 工具临时故障
    MODEL_OUTPUT_FORMAT = "model_format"     # 模型输出格式错误
    NETWORK_ERROR = "network_error"          # 网络错误
    
    # 不可恢复错误
    TOOL_NOT_FOUND = "tool_not_found"        # 工具不存在
    INVALID_PARAMS = "invalid_params"        # 参数无效
    CONTEXT_OVERFLOW = "context_overflow"   # 上下文溢出
    PERMISSION_DENIED = "permission_denied"  # 权限不足
    MAX_RETRIES_EXCEEDED = "max_retries"     # 超过最大重试次数
```

### 1.2 错误处理策略

```python
class ErrorHandler:
    """错误处理策略"""
    def __init__(self):
        self.strategies = {
            AgentError.TOOL_TIMEOUT: self._retry_strategy,
            AgentError.TOOL_RATE_LIMIT: self._backoff_strategy,
            AgentError.MODEL_OUTPUT_FORMAT: self._reparse_strategy,
            AgentError.NETWORK_ERROR: self._retry_strategy,
            AgentError.TOOL_NOT_FOUND: self._fallback_strategy,
            AgentError.PERMISSION_DENIED: self._notify_user_strategy,
        }
    
    def handle(self, error, context):
        strategy = self.strategies.get(error.type)
        if strategy:
            return strategy(error, context)
        return self._default_strategy(error, context)
    
    def _retry_strategy(self, error, context):
        """重试策略"""
        if context["retry_count"] < 3:
            return {"action": "retry", "delay": 1 * context["retry_count"]}
        return {"action": "fail", "message": "重试次数耗尽"}
    
    def _backoff_strategy(self, error, context):
        """退避策略"""
        delay = min(2 ** context["retry_count"], 30)
        return {"action": "retry", "delay": delay}
    
    def _reparse_strategy(self, error, context):
        """重新解析策略"""
        return {"action": "reparse", "model": "try_again"}
    
    def _fallback_strategy(self, error, context):
        """降级策略"""
        return {"action": "fallback", "alternative": "ask_user"}
```

---

## 二、重试与退避

### 2.1 智能重试

```python
class SmartRetry:
    """智能重试机制"""
    def __init__(self, max_retries=3, base_delay=1, max_delay=30):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
    
    def execute(self, fn, *args, **kwargs):
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                return fn(*args, **kwargs)
            except RetryableError as e:
                last_error = e
                delay = self._calculate_delay(attempt)
                time.sleep(delay)
            except FatalError as e:
                raise e  # 不可恢复错误，直接抛出
        
        raise MaxRetriesError(f"重试 {self.max_retries} 次后仍失败") from last_error
    
    def _calculate_delay(self, attempt):
        """计算退避延迟"""
        # 指数退避 + 随机抖动
        delay = min(self.base_delay * (2 ** attempt), self.max_delay)
        jitter = random.uniform(0, delay * 0.1)
        return delay + jitter
```

### 2.2 熔断机制

```python
class CircuitBreaker:
    """熔断器"""
    def __init__(self, failure_threshold=5, recovery_timeout=30):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half_open
    
    def call(self, fn, *args, **kwargs):
        if self.state == "open":
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "half_open"
            else:
                raise CircuitBreakerOpenError("熔断器已打开")
        
        try:
            result = fn(*args, **kwargs)
            if self.state == "half_open":
                self.state = "closed"
                self.failure_count = 0
            return result
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.failure_count >= self.failure_threshold:
                self.state = "open"
            
            raise e
```

---

## 三、降级策略

### 3.1 降级模式

```python
class DegradationManager:
    """降级管理器"""
    def __init__(self):
        self.levels = {
            0: {"name": "full", "description": "完整功能"},
            1: {"name": "reduced", "description": "简化功能"},
            2: {"name": "minimal", "description": "最小功能"},
            3: {"name": "fallback", "description": "兜底方案"},
        }
        self.current_level = 0
    
    def degrade(self, reason):
        """降级"""
        self.current_level = min(self.current_level + 1, 3)
        
        if self.current_level == 1:
            # 关闭非核心工具
            self.disable_tools(["send_email", "run_code"])
        elif self.current_level == 2:
            # 只保留最核心的工具
            self.disable_all_tools_except(["search", "weather"])
        elif self.current_level == 3:
            # 只做对话，不做任何操作
            self.disable_all_tools()
    
    def get_agent_config(self):
        """获取当前级别的 Agent 配置"""
        return {
            "level": self.current_level,
            "tools": self.allowed_tools,
            "max_steps": 10 - self.current_level * 2,
            "timeout": 30 - self.current_level * 5,
        }
```

### 3.2 优雅降级示例

```python
async def execute_with_degradation(tool_call, tools, degradation):
    """带降级的工具执行"""
    try:
        return await execute_tool(tool_call, tools)
    except ToolUnavailableError:
        # 工具不可用 → 降级
        degradation.degrade("工具不可用")
        return {"status": "degraded", "message": "该功能暂时不可用"}
    except RateLimitError:
        # 限流 → 降级
        return {"status": "rate_limited", "message": "请稍后再试"}
```

---

## 四、监控与追踪

### 4.1 执行追踪

```python
class AgentTracer:
    """Agent 执行追踪"""
    def __init__(self):
        self.traces = {}
    
    def start_trace(self, run_id):
        self.traces[run_id] = {
            "steps": [],
            "start_time": time.time(),
            "status": "running",
        }
    
    def log_step(self, run_id, step):
        trace = self.traces.get(run_id)
        if trace:
            trace["steps"].append({
                **step,
                "timestamp": time.time(),
            })
    
    def end_trace(self, run_id, status="completed"):
        trace = self.traces.get(run_id)
        if trace:
            trace["status"] = status
            trace["duration"] = time.time() - trace["start_time"]
    
    def get_trace_report(self, run_id):
        """生成追踪报告"""
        trace = self.traces.get(run_id)
        if not trace:
            return None
        
        return {
            "run_id": run_id,
            "duration": trace["duration"],
            "steps": len(trace["steps"]),
            "status": trace["status"],
            "tool_calls": [
                s for s in trace["steps"] if s.get("type") == "tool_call"
            ],
            "errors": [
                s for s in trace["steps"] if s.get("error")
            ],
        }
```

### 4.2 健康检查

```python
class HealthChecker:
    """Agent 健康检查"""
    def __init__(self, components):
        self.components = components
    
    def check_all(self):
        """检查所有组件"""
        results = {}
        for name, component in self.components.items():
            try:
                status = component.health_check()
                results[name] = {"status": "ok", "details": status}
            except Exception as e:
                results[name] = {"status": "error", "error": str(e)}
        
        return results
    
    def is_healthy(self):
        """总体健康状态"""
        results = self.check_all()
        return all(r["status"] == "ok" for r in results.values())
```

---

## 五、测试

### 5.1 测试层次

```python
class AgentTestSuite:
    """Agent 测试套件"""
    def __init__(self, agent):
        self.agent = agent
    
    def run_all(self):
        results = {
            "unit": self.run_unit_tests(),
            "integration": self.run_integration_tests(),
            "scenario": self.run_scenario_tests(),
            "stress": self.run_stress_tests(),
        }
        return results
    
    def run_scenario_tests(self):
        """场景测试"""
        scenarios = [
            # 正常场景
            {"name": "simple_query", "input": "北京天气", "expect": "success"},
            # 异常场景
            {"name": "empty_input", "input": "", "expect": "error"},
            {"name": "very_long_input", "input": "A" * 10000, "expect": "success"},
            # 恢复场景
            {"name": "tool_failure", "input": "执行一个不存在的工具", "expect": "graceful"},
            # 边界场景
            {"name": "max_steps", "input": "重复做10次", "expect": "max_steps"},
        ]
        
        results = []
        for scenario in scenarios:
            try:
                result = self.agent.run(scenario["input"])
                success = result["status"] == scenario["expect"]
                results.append({"scenario": scenario["name"], "success": success})
            except Exception as e:
                results.append({"scenario": scenario["name"], "success": False, "error": str(e)})
        
        return results
```

### 5.2 混沌工程

```python
class ChaosTesting:
    """混沌测试"""
    def __init__(self, agent):
        self.agent = agent
    
    def inject_failures(self, tool_name, failure_rate=0.1):
        """注入故障"""
        original_execute = self.agent.tools[tool_name].execute
        
        def faulty_execute(*args, **kwargs):
            if random.random() < failure_rate:
                raise RandomFailureError("注入的随机故障")
            return original_execute(*args, **kwargs)
        
        self.agent.tools[tool_name].execute = faulty_execute
    
    def test_recovery(self):
        """测试恢复能力"""
        # 注入故障
        self.inject_failures("search_web", 0.3)
        
        # 运行测试
        results = []
        for _ in range(10):
            try:
                result = self.agent.run("搜索一些信息")
                results.append(result["status"])
            except Exception as e:
                results.append("crashed")
        
        # 恢复率
        recovery_rate = results.count("success") / len(results)
        return {"recovery_rate": recovery_rate, "results": results}
```

---

## 六、可靠性指标

### 6.1 关键指标

| 指标 | 定义 | 目标 |
|------|------|------|
| 成功率 | 任务完成的比例 | > 95% |
| 平均恢复时间 | 从故障中恢复的时间 | < 5s |
| 错误率 | 出错的工具调用比例 | < 5% |
| 熔断率 | 熔断器打开的比例 | < 0.1% |
| 降级率 | 系统降级的比例 | < 1% |

### 6.2 持续改进

```python
class ReliabilityMonitor:
    """可靠性监控"""
    def __init__(self):
        self.metrics = {
            "total_requests": 0,
            "successful": 0,
            "failed": 0,
            "retried": 0,
            "degraded": 0,
        }
    
    def record(self, result):
        self.metrics["total_requests"] += 1
        if result["status"] == "success":
            self.metrics["successful"] += 1
        elif result["status"] == "failed":
            self.metrics["failed"] += 1
            if result.get("retried"):
                self.metrics["retried"] += 1
    
    def get_reliability_score(self):
        """计算可靠性分数"""
        if self.metrics["total_requests"] == 0:
            return 1.0
        
        success_rate = self.metrics["successful"] / self.metrics["total_requests"]
        retry_rate = self.metrics["retried"] / max(1, self.metrics["failed"])
        
        # 综合评分
        return success_rate * 0.7 + (1 - 1/(retry_rate + 1)) * 0.3
```

---

## 总结

| 策略 | 解决的问题 | 实现方式 |
|------|-----------|---------|
| 容错设计 | 系统不崩溃 | 错误分类、分级处理 |
| 重试退避 | 临时故障恢复 | 指数退避、随机抖动 |
| 熔断机制 | 防止级联故障 | 状态机、阈值控制 |
| 降级策略 | 保持基本可用 | 分级降级、工具禁用 |
| 监控追踪 | 发现问题 | 追踪、日志、健康检查 |
| 测试验证 | 预防问题 | 单元测试、混沌工程 |

**可靠性不是"测试出来的"，是"设计出来的"。**

下一篇文章，我们将完成模块五，进入**Agent 个性化与角色定制**。

---

**思考题**：
1. 你的 Agent 现在有"降级"策略吗？如果核心工具挂了，Agent 会怎么样？
2. 重试多少次比较合适？不同场景下重试策略有什么不同？
3. 混沌工程在 Agent 场景中实用吗？你会怎么设计一个 Agent 的混沌测试？

---

> 上一篇：[34] Agent 安全与治理
> 下一篇：[36] Agent 个性化与角色定制
> 系列目录：[README.md](./README.md)