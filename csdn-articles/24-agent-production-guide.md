# 【AI Agent 内核】24 · Demo 到 Production 的最后 5 公里：安全、成本、监控实战指南

> **标签**：`#AI Agent` `#生产部署` `#安全审计` `#成本优化` `#工程实践`

> 90% 的 Agent 项目死在"做完 Demo 就不知道怎么上线了"。不是技术问题——是工程问题。本文覆盖部署生产级 Agent 必须解决的五个维度：安全防护、成本控制、可观测性、容错机制、持续改进。每个维度都来自真实踩坑经验。

---

## 一、Demo Agent vs Production Agent

先对比一下两者的差距有多大：

| 维度 | Demo Agent | Production Agent |
|------|-----------|-----------------|
| 安全性 | "参数做了校验的" | 全量操作审计 + 最小权限 + 人机回路 |
| 监控 | print() 打日志 | Prometheus + Grafana + 告警规则 |
| 容错 | 报错就重试 | 熔断 + 降级 + 幂等 + 死信队列 |
| 成本 | "GPT-4 真贵" | Token Budget + 模型分层 + 缓存策略 |
| 版本 | "代码在 main 分支" | 灰度发布 + A/B 测试 + 回滚 |
| 测试 | "我刚才试了一下，能跑" | 评估数据集 + Regression Test |

**Demo 到 Production 不是"加几行代码"，是"加一套工程体系"。**

---

## 二、安全防护：Agent 的五层防线

### 防线 1：提示注入防御

Agent 被外部内容操控是最常见的安全事故。

```python
import re
from typing import Tuple, Optional

class PromptInjectionDefense:
    """提示注入防御层"""
    
    # 已知注入模式
    INJECTION_PATTERNS = [
        r"ignore (all |your |previous )?(instructions|rules|guidelines)",
        r"forget (everything|what you know|your rules)",
        r"you are now.*instead",
        r"act as if you are",
        r"system:\s*",
        r"<\|im_start\|>",
        r"\[INST\].*\[/INST\]",
        r"DAN mode",
        r"developer mode",
    ]
    
    @classmethod
    def detect(cls, user_input: str) -> Tuple[bool, Optional[str]]:
        """检测输入是否包含注入尝试"""
        lowered = user_input.lower()
        
        for pattern in cls.INJECTION_PATTERNS:
            match = re.search(pattern, lowered)
            if match:
                return True, f"Potential injection detected: matched '{match.group()}'"
        
        return False, None
    
    @classmethod
    def sanitize(cls, user_input: str) -> str:
        """
        净化用户输入
        注意：不能简单粗暴地删除，需要保留语义
        """
        # 移除不可见字符（零宽字符注入）
        sanitized = re.sub(r'[\u200b\u200c\u200d\u200e\u200f\ufeff]', '', user_input)
        
        # 转义特殊标记
        sanitized = sanitized.replace("<|im_start|>", "&lt;|im_start|&gt;")
        sanitized = sanitized.replace("<|im_end|>", "&lt;|im_end|&gt;")
        
        return sanitized
    
    @classmethod
    def validate_tool_input(cls, tool_name: str, params: dict) -> Tuple[bool, str]:
        """
        工具调用参数的二次验证
        这是防止 Indirect Prompt Injection 的关键
        """
        # 检查参数类型和范围
        if tool_name == "execute_shell":
            cmd = params.get("command", "")
            # 禁止危险命令
            dangerous = ["rm -rf", "sudo", "chmod 777", "> /dev/sda", "mkfs"]
            for d in dangerous:
                if d in cmd:
                    return False, f"Dangerous command blocked: contains '{d}'"
            
            # 命令长度限制
            if len(cmd) > 500:
                return False, "Command too long (>500 chars)"
        
        if tool_name == "send_email":
            # 防止 Agent 被注入内容诱导发垃圾邮件
            recipient = params.get("to", "")
            if "@external-domain.com" in recipient:
                return False, "External email sending requires human approval"
        
        return True, "OK"
```

### 防线 2：操作审计（不可删除、不可篡改）

```python
import json
import hashlib
from datetime import datetime
from pathlib import Path

class AuditLogger:
    """
    操作审计日志
    特点：只追加，不修改，不删除
    """
    
    def __init__(self, log_dir: str = "/var/log/agent/audit"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
    def log_action(self, 
                   agent_id: str,
                   user_id: str,
                   action: str,
                   params: dict,
                   result: dict,
                   session_id: str):
        """记录 Agent 的每一步操作"""
        
        entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "agent_id": agent_id,
            "user_id": user_id,
            "session_id": session_id,
            "action": action,           # "tool_call", "llm_generation", "state_change"
            "params": params,           # 完整的输入参数
            "result": result,           # 完整的输出结果
            "result_summary": self._summarize(result),  # 摘要（用于快速浏览）
        }
        
        # 计算 hash，保证不可篡改
        entry_json = json.dumps(entry, sort_keys=True)
        entry["checksum"] = hashlib.sha256(entry_json.encode()).hexdigest()
        
        # 按天分文件
        date_str = datetime.utcnow().strftime("%Y-%m-%d")
        log_file = self.log_dir / f"audit_{date_str}.jsonl"
        
        with open(log_file, "a") as f:
            f.write(json.dumps(entry) + "\n")
    
    def query(self, 
              user_id: str = None,
              action: str = None,
              start_time: str = None,
              end_time: str = None) -> list:
        """查询审计日志"""
        results = []
        # 遍历日志文件，按条件过滤
        for log_file in sorted(self.log_dir.glob("audit_*.jsonl")):
            with open(log_file) as f:
                for line in f:
                    entry = json.loads(line)
                    
                    # 验证完整性
                    stored_checksum = entry.pop("checksum", None)
                    recomputed = hashlib.sha256(
                        json.dumps({k: v for k, v in entry.items() 
                                   if k != "checksum"}, sort_keys=True).encode()
                    ).hexdigest()
                    
                    if stored_checksum != recomputed:
                        raise SecurityError(f"Audit log tampered: {log_file}")
                    
                    if user_id and entry.get("user_id") != user_id:
                        continue
                    if action and entry.get("action") != action:
                        continue
                    
                    results.append(entry)
        
        return results
```

### 防线 3：人机回路（Human-in-the-Loop）

不是所有操作都需要人工确认——那会失去 Agent 的意义。但以下操作**必须**：

```python
HUMAN_APPROVAL_REQUIRED = {
    # 资金相关
    "make_payment": "涉及资金交易",
    "create_invoice": "涉及账单生成",
    
    # 外部通信
    "send_email_external": "发送外部邮件",
    "post_social_media": "发布社交媒体内容",
    "send_sms": "发送短信",
    
    # 破坏性操作
    "delete_production_data": "删除生产数据",
    "execute_migration": "执行数据库迁移",
    "deploy_to_production": "部署到生产环境",
    
    # 权限变更
    "grant_access": "授权访问",
    "modify_user_role": "修改用户角色",
}

class HumanApprovalGate:
    """人工审批网关"""
    
    def __init__(self, notification_service):
        self.notify = notification_service
        self.pending_approvals = {}  # 内存中存储待审批项
        self.timeout_minutes = 30
    
    def request_approval(self, action: str, details: dict) -> str:
        """发起审批请求"""
        approval_id = hashlib.md5(
            f"{action}{json.dumps(details)}{datetime.now()}".encode()
        ).hexdigest()[:8]
        
        self.pending_approvals[approval_id] = {
            "action": action,
            "details": details,
            "status": "pending",
            "created_at": datetime.now(),
            "approved_by": None
        }
        
        # 发送通知（企业微信/Slack/邮件）
        self.notify.send(
            title=f"⚠️ Agent 需要审批：{action}",
            body=f"""操作: {action}
详情: {json.dumps(details, indent=2, ensure_ascii=False)}
审批ID: {approval_id}
回复 [批准 {approval_id}] 或 [拒绝 {approval_id} 理由]""",
            urgency="high"
        )
        
        return approval_id
    
    def wait_for_approval(self, approval_id: str, 
                          timeout_seconds: int = 1800) -> str:
        """等待审批结果（或超时自动拒绝）"""
        import time
        start = time.time()
        
        while time.time() - start < timeout_seconds:
            approval = self.pending_approvals.get(approval_id)
            if approval["status"] != "pending":
                return approval["status"]  # "approved" or "rejected"
            time.sleep(2)
        
        # 超时自动拒绝
        self.pending_approvals[approval_id]["status"] = "rejected"
        self.pending_approvals[approval_id]["rejection_reason"] = "timeout"
        return "rejected"
```

---

## 三、成本控制：别让 Agent 吃光你的预算

### 真实成本模型

```
一个中等复杂度的 Agent 任务：
  - System Prompt: 2000 tokens
  - 用户消息: 500 tokens
  - Agent 平均 5 步推理
  - 每步: 2000 tokens 输入 + 500 tokens 输出
  - 工具调用返回: 2000 tokens
  
  单次任务 Token 消耗:
  = 2000 + (500 + 2000 + 500 + 2000) × 5
  = 2000 + 25000
  = 27000 tokens
  
  按 GPT-4 ($0.03/1K input, $0.06/1K output):
  ≈ $0.80/次
  
  每天 500 次调用 → $400/天 → $12,000/月
  
  这只是一个 Agent。如果你有 5 个 Agent...
```

### 省钱三板斧

#### 板斧 1：模型分层——不同任务用不同模型

```python
class TieredModelRouter:
    """分层模型路由——省钱的第一个入口"""
    
    TIERS = {
        # 用便宜的模型
        "task_classification": "gpt-4o-mini",     # ~$0.15/1M tokens
        "simple_qa": "gpt-4o-mini",
        "format_output": "gpt-4o-mini",
        
        # 用中等模型
        "code_generation": "claude-3.5-sonnet",
        "summary": "claude-3.5-sonnet",
        
        # 用最强模型（只在必要时）
        "complex_reasoning": "gpt-4o",
        "architecture_design": "gpt-4o",
        "safety_check": "gpt-4o",
        "multi_step_planning": "gpt-4o",
    }
    
    @classmethod
    def route(cls, task_type: str) -> str:
        return cls.TIERS.get(task_type, "claude-3.5-sonnet")  # 默认用中档
```

**省多少钱？** 把 70% 的调用从 GPT-4 降到 GPT-4o-mini → 成本降 85%。

#### 板斧 2：Token Budget——每个任务设上限

```python
class TokenBudget:
    """Token 预算管理器"""
    
    BUDGETS = {
        "quick_reply": 2000,        # 快速回复：2000 tokens
        "code_generation": 8000,    # 代码生成：8000 tokens
        "architecture_design": 15000, # 架构设计：15000 tokens
        "full_project": 50000,      # 完整项目：50000 tokens
    }
    
    def __init__(self):
        self.usage = {}  # {session_id: tokens_used}
    
    def check_and_reserve(self, session_id: str, 
                          task_type: str, 
                          estimated_tokens: int) -> bool:
        """检查是否超出预算"""
        budget = self.BUDGETS.get(task_type, 5000)
        used = self.usage.get(session_id, 0)
        
        if used + estimated_tokens > budget:
            return False  # 超出预算，拒绝
        
        self.usage[session_id] = used + estimated_tokens
        return True
    
    def alert_on_anomaly(self, session_id: str):
        """异常检测：单次会话消耗超过正常值 3 倍"""
        avg = self._get_average_usage()
        current = self.usage.get(session_id, 0)
        
        if current > avg * 3:
            self._send_alert(
                f"⚠️ 会话 {session_id} Token 消耗异常: "
                f"{current} (均值: {avg})"
            )
```

#### 板斧 3：缓存重复查询

```python
import hashlib
from functools import lru_cache
import redis

class SemanticCache:
    """语义缓存 — 相似的查询返回缓存结果"""
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis = redis.from_url(redis_url)
        self.ttl = 3600  # 缓存 1 小时
    
    def get(self, query: str) -> Optional[str]:
        """检查语义缓存"""
        # 不是精确匹配，而是用查询的"意图签名"
        intent_hash = self._compute_intent_hash(query)
        
        cached = self.redis.get(f"semcache:{intent_hash}")
        return cached.decode() if cached else None
    
    def set(self, query: str, result: str):
        intent_hash = self._compute_intent_hash(query)
        self.redis.setex(f"semcache:{intent_hash}", self.ttl, result)
    
    def _compute_intent_hash(self, query: str) -> str:
        """
        计算意图哈希
        思路：去掉具体参数，只保留意图结构
        "深圳今天天气" 和 "北京今天天气" → 同一个意图
        """
        # 简化版：用 LLM 提取意图类别 + 关键词哈希
        # 生产版：用专门的嵌入模型
        normalized = query.lower().strip()
        return hashlib.md5(normalized.encode()).hexdigest()[:12]
```

**缓存效果**：对 FAQ 型 Agent，缓存命中率可达 40-60%，直接省掉一半的 LLM 调用。

---

## 四、可观测性：Agent 不是黑盒

### 四个核心指标

```python
from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry

class AgentMetrics:
    """Agent 监控指标（Prometheus 格式）"""
    
    def __init__(self):
        # 任务完成率
        self.task_total = Counter(
            'agent_task_total', 'Total tasks',
            ['agent_name', 'status']  # status: success/failure/timeout
        )
        
        # 任务延迟
        self.task_duration = Histogram(
            'agent_task_duration_seconds', 'Task duration',
            ['agent_name', 'task_type'],
            buckets=[1, 5, 10, 30, 60, 120, 300]
        )
        
        # Token 消耗
        self.token_usage = Counter(
            'agent_token_usage_total', 'Token usage',
            ['agent_name', 'model', 'direction']  # direction: input/output
        )
        
        # 工具调用
        self.tool_calls = Counter(
            'agent_tool_calls_total', 'Tool calls',
            ['agent_name', 'tool_name', 'status']
        )
        
        # 当前活跃会话
        self.active_sessions = Gauge(
            'agent_active_sessions', 'Active sessions',
            ['agent_name']
        )
        
        # 人工干预率
        self.human_interventions = Counter(
            'agent_human_interventions_total', 'Human interventions',
            ['agent_name', 'action']
        )
    
    def compute_health_score(self, agent_name: str) -> float:
        """
        综合健康分计算
        - 任务成功率: 40% 权重
        - 平均延迟: 20% 权重
        - 人工干预率: 20% 权重
        - Token 效率: 20% 权重
        """
        # 简化版计算
        # 生产版应从 Prometheus 查询实际数据
        pass
```

### 告警规则（什么时候该紧张）

```yaml
# prometheus_rules.yml
groups:
  - name: agent_alerts
    rules:
      - alert: AgentTaskFailureRate30
        expr: |
          rate(agent_task_total{status="failure"}[5m]) 
          / rate(agent_task_total[5m]) > 0.30
        for: 5m
        annotations:
          summary: "Agent 任务失败率超过 30%"
          severity: critical
      
      - alert: AgentHighLatency
        expr: |
          histogram_quantile(0.95, 
            rate(agent_task_duration_seconds_bucket[5m])) > 60
        for: 5m
        annotations:
          summary: "Agent P95 延迟超过 60 秒"
          severity: warning
      
      - alert: AgentTokenSpike
        expr: |
          rate(agent_token_usage_total[10m]) 
          > rate(agent_token_usage_total[1h]) * 3
        for: 5m
        annotations:
          summary: "Token 消耗突然飙升 3 倍（可能是 Agent 陷入循环）"
          severity: warning
      
      - alert: AgentHighInterventionRate
        expr: |
          rate(agent_human_interventions_total[1h]) 
          / rate(agent_task_total[1h]) > 0.20
        for: 10m
        annotations:
          summary: "人工干预率超过 20%，Agent 自主能力下降"
          severity: warning
```

---

## 五、容错机制：优雅地失败

```python
from datetime import datetime
import time
from enum import Enum

class CircuitState(Enum):
    CLOSED = "closed"        # 正常
    OPEN = "open"            # 熔断
    HALF_OPEN = "half_open"  # 半开（尝试恢复）

class AgentCircuitBreaker:
    """
    Agent 熔断器
    当 Agent 连续失败 → 自动熔断 → 触发降级方案
    """
    
    def __init__(self, 
                 failure_threshold: int = 5,
                 recovery_timeout: int = 60,
                 half_open_max_requests: int = 3):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_requests = half_open_max_requests
        
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = None
        self.half_open_requests = 0
    
    def call(self, agent_func, *args, **kwargs):
        """执行 Agent 调用，带熔断保护"""
        
        if self.state == CircuitState.OPEN:
            if self._should_attempt_recovery():
                self.state = CircuitState.HALF_OPEN
                self.half_open_requests = 0
            else:
                raise CircuitBreakerOpenError(
                    "Agent is in circuit breaker OPEN state. Using fallback."
                )
        
        if self.state == CircuitState.HALF_OPEN:
            if self.half_open_requests >= self.half_open_max_requests:
                raise CircuitBreakerOpenError("Half-open limit reached")
            self.half_open_requests += 1
        
        try:
            result = agent_func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise
    
    def _on_success(self):
        self.failure_count = 0
        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.CLOSED
    
    def _on_failure(self):
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
    
    def _should_attempt_recovery(self) -> bool:
        if self.last_failure_time is None:
            return True
        elapsed = (datetime.now() - self.last_failure_time).seconds
        return elapsed >= self.recovery_timeout
```

---

## 六、持续改进：让 Agent 越跑越好

```python
class AgentEvaluationPipeline:
    """
    Agent 评估流水线
    不是"好不好"的感觉——是数据
    """
    
    def __init__(self):
        self.test_cases = []  # 评估数据集
        self.baseline_scores = {}  # 基线分数
    
    def add_test_case(self, 
                      input_query: str,
                      expected_tools: List[str],  # 期望调用的工具
                      expected_keywords: List[str], # 期望包含的关键词
                      difficulty: str = "medium"):
        """添加测试用例"""
        self.test_cases.append({
            "query": input_query,
            "expected_tools": expected_tools,
            "expected_keywords": expected_keywords,
            "difficulty": difficulty
        })
    
    def evaluate(self, agent, version: str) -> Dict:
        """对新版 Agent 运行全量评估"""
        results = {
            "version": version,
            "total": len(self.test_cases),
            "tool_accuracy": 0,     # 工具选择准确率
            "keyword_recall": 0,    # 关键词召回率
            "avg_duration": 0,      # 平均耗时
            "avg_tokens": 0,        # 平均 Token 消耗
            "per_difficulty": {}    # 按难度分组统计
        }
        
        for case in self.test_cases:
            start = time.time()
            agent_result = agent.run(case["query"])
            duration = time.time() - start
            
            # 工具选择准确率
            called_tools = [c["tool"] for c in agent_result.get("tool_calls", [])]
            tool_match = len(set(called_tools) & set(case["expected_tools"]))
            tool_acc = tool_match / max(len(case["expected_tools"]), 1)
            
            results["tool_accuracy"] += tool_acc
            results["avg_duration"] += duration
            results["avg_tokens"] += agent_result.get("token_usage", 0)
        
        n = max(len(self.test_cases), 1)
        results["tool_accuracy"] /= n
        results["avg_duration"] /= n
        results["avg_tokens"] /= n
        
        # 对比基线
        if self.baseline_scores:
            results["vs_baseline"] = {
                "tool_accuracy_delta": results["tool_accuracy"] - self.baseline_scores.get("tool_accuracy", 0),
                "duration_delta": results["avg_duration"] - self.baseline_scores.get("avg_duration", 0),
                "tokens_delta": results["avg_tokens"] - self.baseline_scores.get("avg_tokens", 0),
            }
        
        # 只有所有指标不退化才允许上线
        results["can_deploy"] = self._check_no_regression(results)
        
        return results
    
    def _check_no_regression(self, results: Dict) -> bool:
        if not self.baseline_scores:
            return True
        
        # 工具准确率不能降
        if results.get("vs_baseline", {}).get("tool_accuracy_delta", 0) < -0.05:
            return False
        
        # Token 消耗不能暴增超过 50%
        if results.get("vs_baseline", {}).get("tokens_delta", 0) > self.baseline_scores["avg_tokens"] * 0.5:
            return False
        
        return True
```

---

## 七、Production 部署检查清单

上线前逐项确认：

```
□ 安全
  □ 提示注入防御层已上线
  □ 操作审计日志完整（只追加、不可删）
  □ 人机回路已配置（支付/外部通信/破坏性操作）
  □ 工具调用参数有二次校验

□ 成本
  □ 已配置模型分层路由
  □ 每个任务类型有 Token Budget 上限
  □ 语义缓存已启用
  □ 设有日/周/月成本告警阈值

□ 监控
  □ 四个核心指标已接入 Prometheus
  □ 告警规则已配置（失败率/延迟/Token飙升/干预率）
  □ Grafana Dashboard 已搭建

□ 容错
  □ 熔断器已配置
  □ 降级方案已验证
  □ 幂等性已保证（重复请求不会重复执行）

□ 持续改进
  □ 评估数据集已建立（≥50条用例）
  □ 基线分数已记录
  □ 灰度发布流程已就绪
```

---

## 八、总结

从 Demo 到 Production 的差距，本质上是**工程化能力**的差距：

- Demo 关心"能不能跑"→ Production 关心"会不会挂"
- Demo 关心"结果对不对"→ Production 关心"挂了怎么恢复"
- Demo 关心"一次调用的成本"→ Production 关心"一个月多少钱"

**最容易被忽略的一条**：上线第一个月，每天花 30 分钟看 Agent 的审计日志。你会发现自己设计的"智能体"在真实用户面前的行为，和你的预设差了十万八千里。

---

*你的 Agent 上线了吗？踩过什么坑？评论区分享你的 Production Checklist 👇*
