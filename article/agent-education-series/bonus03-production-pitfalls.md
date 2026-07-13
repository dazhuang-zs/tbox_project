# 【AI Agent 系统教学】番外篇 03：生产环境 Agent 部署踩坑实录

> 教程里的 Agent 完美运行，生产环境的 Agent 天天出事。
> 这些坑，你不踩别人也会踩。

---

## 前言：theory vs reality

教程里你看到的 Agent：

```
用户输入 → Agent 完美处理 → 输出
```

生产环境你遇到的 Agent：

```
用户输入 → Agent 误解 → 调用错误工具 → 工具返回错误
→ Agent 尝试重试 → 陷入循环 → 超时 → 用户投诉
```

---

## 坑一：上下文爆炸

### 现象

Agent 运行 50 轮后，上下文从 1K 涨到 50K，响应时间从 1 秒涨到 10 秒，token 费用翻了 10 倍。

### 根因

每次 Agent 循环都往 messages 里追加内容，从不清理。

```python
# 错误做法
messages.append({"role": "user", "content": user_input})
messages.append({"role": "assistant", "content": agent_response})
# 从不清理，一直涨
```

### 解决方案

```python
class ContextManager:
    def __init__(self, max_tokens=32000):
        self.max_tokens = max_tokens
        self.system_prompt = None
        self.history = []
    
    def add_message(self, message):
        self.history.append(message)
        self._trim()
    
    def _trim(self):
        total = self._count_tokens()
        while total > self.max_tokens:
            # 只删除历史对话，保留系统提示和用户偏好
            for i, msg in enumerate(self.history):
                if msg["role"] in ("user", "assistant"):
                    self.history.pop(i)
                    break
            total = self._count_tokens()
```

---

## 坑二：无限循环

### 现象

Agent 一直在调用工具，永远不会"结束"。有个生产环境的 Agent 在无人值守的情况下调了 2000 次 API，花了 200 美元。

### 根因

Agent 的工具调用结果又触发了新的工具调用，形成死循环。

```python
# 场景：Agent 搜索"天气"，结果包含"建议查看历史天气"
# Agent 又去搜索"历史天气"...
# 结果又包含"建议查看温度趋势"...
# 无限循环
```

### 解决方案

```python
class LoopGuard:
    def __init__(self, max_steps=10, timeout=30):
        self.max_steps = max_steps
        self.timeout = timeout
        self.action_history = []
    
    def check_loop(self, action):
        self.action_history.append(action)
        
        # 检测重复模式
        if len(self.action_history) >= 6:
            recent = self.action_history[-3:]
            prev = self.action_history[-6:-3]
            if recent == prev:
                return True, "检测到循环模式"
        
        # 检测相同工具重复调用
        tool_calls = [a for a in self.action_history if a.get("type") == "tool_call"]
        if len(tool_calls) > self.max_steps:
            return True, "工具调用次数过多"
        
        return False, None
```

---

## 坑三：工具调用格式错误

### 现象

模型输出的 JSON 格式不对，导致工具执行失败。有时是多余的逗号，有时是忘记关闭引号，有时是字段名拼错。

### 根因

模型不是代码生成器，它的 JSON 输出没有校验。

### 解决方案

**方案一：约束解码**

```python
# 使用约束解码，保证输出格式正确
from guidance import json as json_guidance

tool_call_schema = {
    "type": "object",
    "properties": {
        "tool": {"type": "string", "enum": ["search", "weather"]},
        "params": {"type": "object"},
    },
    "required": ["tool", "params"],
}

# 约束解码保证输出符合 schema
response = guidance.generate(prompt, schema=tool_call_schema)
```

**方案二：容错解析**

```python
def safe_parse_json(text):
    """安全解析 JSON，处理常见格式错误"""
    # 尝试直接解析
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    
    # 尝试修复常见错误
    fixes = [
        lambda s: s.strip().strip("```json").strip("```"),
        lambda s: s.replace("'", '"'),
        lambda s: s.replace("True", "true").replace("False", "false"),
        lambda s: s.rstrip(",") + "}" if not s.strip().endswith("}") else s,
    ]
    
    for fix in fixes:
        try:
            return json.loads(fix(text))
        except json.JSONDecodeError:
            continue
    
    return None  # 无法修复
```

---

## 坑四：模型"自由发挥"

### 现象

Agent 不调用工具，而是用自己的"知识"回答。结果回答错了，因为模型的知识是过时的。

### 根因

System Prompt 中的"请使用工具"不够强，模型倾向于"自己回答"。

### 解决方案

```python
# 错误做法
system_prompt = "请使用工具获取信息。"

# 正确做法
system_prompt = """
规则（优先级最高）：
1. 对于任何需要事实信息的问题，必须先调用工具
2. 如果你没有调用工具就直接回答，将被视为错误
3. 即使你非常确定答案，也要调用工具验证
4. 如果工具返回的结果与你的知识不符，以工具结果为准
5. 工具运行失败时，告诉用户错误信息，而不是自己编造答案
"""

# 再加一个"测试"：每轮对话检查 Agent 是否调用了工具
def verify_tool_usage(agent_response):
    if "需要事实信息" in agent_response and not has_tool_call(agent_response):
        return False, "Agent 没有调用工具就回答了事实性问题"
    return True, None
```

---

## 坑五：多 Agent 死锁

### 现象

两个 Agent 互相等待对方的响应，谁也不先说话。

### 根因

Agent A 问 Agent B 一个问题，Agent B 反问 Agent A，形成死锁。

### 解决方案

```python
class DeadlockDetector:
    def __init__(self, timeout=10):
        self.timeout = timeout
        self.waiting = {}
    
    def register_wait(self, agent_a, agent_b):
        """注册等待关系"""
        self.waiting[(agent_a, agent_b)] = time.time()
        
        # 检测循环等待
        if self._detect_cycle():
            return self._break_deadlock()
        
        return None
    
    def _detect_cycle(self):
        """检测循环等待"""
        # 如果有 A→B 和 B→A 同时存在，就是死锁
        return (("agent_a", "agent_b") in self.waiting and 
                ("agent_b", "agent_a") in self.waiting)
    
    def _break_deadlock(self):
        """打破死锁"""
        # 让优先级低的 Agent 先回答
        return {
            "action": "force_response",
            "from": "agent_b",  # 让 B 先回答
            "message": "请先回答 A 的问题，B 的问题稍后处理",
        }
```

---

## 坑六：忘记熔断

### 现象

第三方 API 挂了，Agent 一直在重试。重试了 50 次，全失败。

### 根因

没有熔断机制，重试策略没有上限。

### 解决方案

```python
class CircuitBreaker:
    def __init__(self, failure_threshold=3, recovery_timeout=30):
        self.failure_count = 0
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.last_failure_time = None
        self.state = "closed"
    
    def call(self, fn, *args, **kwargs):
        if self.state == "open":
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "half_open"
            else:
                raise CircuitBreakerOpen("熔断器打开，请求被拒绝")
        
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
                log_alert(f"熔断器打开：{fn.__name__} 连续失败 {self.failure_count} 次")
            
            raise e
```

---

## 七、踩坑总结

### 常见坑一览

| 坑 | 发生率 | 危害 | 预防 |
|----|-------|------|------|
| 上下文爆炸 | 90% | 高 | 上下文管理 |
| 无限循环 | 60% | 高 | 步数限制 + 循环检测 |
| 格式错误 | 80% | 中 | 约束解码 + 容错解析 |
| 自由发挥 | 50% | 高 | 强制工具调用规则 |
| 多 Agent 死锁 | 30% | 高 | 超时 + 死锁检测 |
| 忘记熔断 | 40% | 中 | 熔断器 |

### 黄金法则

```
1. 永远假设 Agent 会出错
2. 永远设置最大步数
3. 永远设置超时
4. 永远验证工具调用结果
5. 永远有降级方案
6. 永远记录日志
```

---

> 上一篇：[番外02] 主流 Agent 框架深度横评
> 下一篇：[番外04] 从零搭建完整 Agent 项目
> 系列目录：[README.md](./README.md)