# 【AI Agent 系统教学 27】Agent Loop 的工程实现

> Agent 的核心是"循环"——感知、思考、行动、再感知。
> 但把这个"循环"写好，比大多数人想象的要难。

---

## 前言：循环是最容易出 bug 的地方

Agent Loop 看起来简单：

```python
while True:
    response = llm.generate(messages)
    if tool_call := extract_tool(response):
        result = execute(tool_call)
        messages.append(result)
    else:
        break
```

但这 10 行代码在生产环境中会遇到：

- **无限循环**：模型一直在调用工具，永远不会"结束"
- **错误累积**：一个工具调用失败，后续全部出错
- **超时**：一个工具调用卡住，整个 Agent 卡死
- **上下文爆炸**：每次循环都追加内容，上下文无限增长
- **状态不一致**：中间状态没有被正确维护

---

## 一、循环结构

### 1.1 基础循环

```python
class AgentLoop:
    def __init__(self, llm, tools, max_steps=10):
        self.llm = llm
        self.tools = tools
        self.max_steps = max_steps
        self.step = 0
    
    def run(self, messages):
        while self.step < self.max_steps:
            # 1. 生成
            response = self.llm.generate(messages)
            
            # 2. 检查是否结束
            if not self._has_tool_call(response):
                return response.content
            
            # 3. 执行工具
            tool_results = self._execute_tools(response)
            for result in tool_results:
                messages.append(result)
            
            self.step += 1
        
        raise MaxStepsExceeded(f"超过最大步数 {self.max_steps}")
```

### 1.2 安全退出

```python
class SafeAgentLoop:
    def __init__(self, max_steps=10, timeout_seconds=30):
        self.max_steps = max_steps
        self.timeout = timeout_seconds
    
    def run(self, messages):
        start_time = time.time()
        
        for step in range(self.max_steps):
            # 超时检查
            if time.time() - start_time > self.timeout:
                return self._timeout_response()
            
            response = self.llm.generate(messages)
            
            if not self._has_tool_call(response):
                return response
            
            # 安全检查：如果工具调用次数过多，强制结束
            if self._too_many_same_tool(response):
                return self._force_finish()
            
            # 执行工具
            results = self._execute_tools(response)
            for result in results:
                messages.append(result)
        
        return self._max_steps_response()
```

---

## 二、错误处理

### 2.1 工具执行错误

```python
class ToolExecutor:
    def __init__(self, tools):
        self.tools = tools
    
    def execute(self, tool_call):
        name = tool_call.function.name
        arguments = tool_call.function.arguments
        
        try:
            tool = self.tools[name]
            result = tool(**arguments)
            return {
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(result, ensure_ascii=False),
            }
        except KeyError:
            return {
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps({"error": f"未知工具：{name}"}),
            }
        except json.JSONDecodeError:
            return {
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps({"error": f"参数格式错误：{arguments}"}),
            }
        except Exception as e:
            return {
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps({"error": f"执行失败：{str(e)}"}),
            }
```

### 2.2 重试策略

```python
class RetryAgent:
    def __init__(self, max_retries=3, retry_delay=1):
        self.max_retries = max_retries
        self.retry_delay = retry_delay
    
    def execute_with_retry(self, tool_call):
        for attempt in range(self.max_retries):
            try:
                return self._execute(tool_call)
            except TemporaryError as e:
                if attempt == self.max_retries - 1:
                    raise
                time.sleep(self.retry_delay * (attempt + 1))
            except PermanentError:
                # 永久错误，不重试
                return {"error": str(e)}
```

### 2.3 优雅降级

```python
def execute_with_fallback(tool_call, tools):
    """
    工具调用失败后的降级策略
    """
    try:
        return tools[tool_call.name](**tool_call.args)
    except NetworkError:
        # 网络错误：使用缓存
        return cache.get(tool_call.name, tool_call.args)
    except RateLimitError:
        # 限流：等待后重试
        time.sleep(5)
        return tools[tool_call.name](**tool_call.args)
    except NotFoundError:
        # 找不到：返回空结果，让模型处理
        return {"status": "not_found", "message": "未找到相关信息"}
```

---

## 三、超时控制

### 3.1 整体超时

```python
import signal

class TimeoutAgent:
    def __init__(self, timeout=30):
        self.timeout = timeout
    
    def run(self, task):
        result = [None]
        
        def handler(signum, frame):
            raise TimeoutError("Agent 执行超时")
        
        signal.signal(signal.SIGALRM, handler)
        signal.alarm(self.timeout)
        
        try:
            result[0] = self._execute(task)
        except TimeoutError:
            result[0] = self._generate_timeout_response(task)
        finally:
            signal.alarm(0)
        
        return result[0]
```

### 3.2 单步超时

```python
async def run_with_step_timeout(agent, messages, step_timeout=10):
    """
    单步超时控制
    """
    for step in range(agent.max_steps):
        try:
            response = await asyncio.wait_for(
                agent.llm.generate_async(messages),
                timeout=step_timeout,
            )
        except asyncio.TimeoutError:
            return {
                "status": "timeout",
                "message": f"第 {step+1} 步超时",
                "partial_result": messages,
            }
```

---

## 四、上下文管理

### 4.1 上下文窗口管理

```python
class ContextWindowManager:
    def __init__(self, max_tokens=32000, reserve_tokens=2000):
        self.max_tokens = max_tokens
        self.reserve = reserve_tokens
    
    def manage(self, messages):
        """管理上下文窗口"""
        total = self._count_tokens(messages)
        
        if total <= self.max_tokens:
            return messages
        
        # 需要压缩
        # 策略：保留 System Prompt 和工具结果，压缩历史对话
        system = [m for m in messages if m["role"] == "system"]
        tool_results = [m for m in messages if m["role"] == "tool"]
        history = [m for m in messages if m["role"] in ("user", "assistant")]
        
        # 压缩历史（保留最近的部分）
        while self._count_tokens(system + tool_results + history) > self.max_tokens - self.reserve:
            history.pop(0)  # 丢弃最早的对话
        
        return system + tool_results + history
```

### 4.2 循环检测

```python
class LoopDetector:
    def __init__(self, window_size=5):
        self.window_size = window_size
        self.history = []
    
    def detect(self, action):
        """检测是否陷入循环"""
        self.history.append(action)
        
        if len(self.history) < self.window_size * 2:
            return False
        
        # 检查最近的动作是否有重复模式
        recent = self.history[-self.window_size:]
        prev = self.history[-self.window_size*2:-self.window_size]
        
        return recent == prev  # 相同模式出现两次
    
    def get_loop_info(self):
        """获取循环信息"""
        return {
            "detected": len(self.history) > 10,
            "pattern": self.history[-5:],
            "suggestion": "尝试不同的工具或策略",
        }
```

---

## 五、可观测性

### 5.1 日志记录

```python
class AgentLogger:
    def __init__(self):
        self.logs = []
    
    def log_step(self, step, action, result, duration):
        self.logs.append({
            "step": step,
            "action": action,
            "result": result,
            "duration": duration,
            "timestamp": time.time(),
        })
    
    def get_summary(self):
        """生成执行摘要"""
        total_time = sum(log["duration"] for log in self.logs)
        tool_calls = [l for l in self.logs if l["action"]["type"] == "tool_call"]
        return {
            "total_steps": len(self.logs),
            "total_time": total_time,
            "tool_calls": len(tool_calls),
            "errors": len([l for l in self.logs if "error" in l["result"]]),
        }
```

### 5.2 追踪

```python
class AgentTracer:
    """
    Agent 执行追踪，用于调试和分析
    """
    def trace(self, agent_run):
        return {
            "id": agent_run.id,
            "task": agent_run.task,
            "steps": [
                {
                    "number": s.number,
                    "thought": s.thought,
                    "action": s.action,
                    "observation": s.observation,
                    "duration_ms": s.duration_ms,
                }
                for s in agent_run.steps
            ],
            "result": agent_run.result,
            "total_duration_ms": agent_run.total_duration,
            "total_tokens": agent_run.total_tokens,
            "errors": agent_run.errors,
        }
```

---

## 六、最佳实践模板

### 6.1 生产级 Agent Loop

```python
class ProductionAgent:
    def __init__(self, llm, tools):
        self.llm = llm
        self.tools = ToolExecutor(tools)
        self.loop = SafeAgentLoop(max_steps=10, timeout=30)
        self.context = ContextWindowManager(max_tokens=32000)
        self.detector = LoopDetector()
        self.logger = AgentLogger()
    
    def run(self, task):
        messages = [{"role": "system", "content": self._build_system_prompt()}]
        messages.append({"role": "user", "content": task})
        
        try:
            result = self.loop.run(messages)
            return result
        except MaxStepsExceeded:
            return self._handle_max_steps(messages)
        except TimeoutError:
            return self._handle_timeout(messages)
        finally:
            self._log_run(task, messages)
```

---

## 总结

| 工程问题 | 解决方案 |
|---------|---------|
| 无限循环 | 最大步数限制 + 超时控制 |
| 工具错误 | 异常处理 + 重试 + 降级 |
| 上下文爆炸 | 窗口管理 + 压缩 |
| 循环检测 | 模式匹配 + 策略切换 |
| 可观测性 | 日志 + 追踪 + 监控 |

**Agent Loop 的工程实现，决定了 Agent 在"正常"和"异常"情况下的表现。**

下一篇文章，我们将深入**Agent 状态管理**——会话状态、对话历史、中断与恢复。

---

**思考题**：
1. 你的 Agent 遇到过"无限循环"吗？你是怎么处理的？
2. 超时控制应该放在 Agent 整体还是单步？为什么？
3. 你会在 Agent Loop 中加入"循环检测"吗？如果检测到循环，你会怎么做？

---

> 上一篇：[26] Agent 编排框架
> 下一篇：[28] Agent 状态管理
> 系列目录：[README.md](./README.md)