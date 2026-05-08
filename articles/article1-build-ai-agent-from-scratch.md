# 读完《Build an AI Agent (From Scratch)》，我把自己之前写的 Agent 代码全删了

> 不是夸张。这本书让我意识到，我之前写的那些 Agent——用 LangChain 一行 `create_agent()` 跑通 Demo 就沾沾自喜的东西——本质上和一个套壳的 while 循环没什么区别。

---

## 我为什么翻开这本书

说出来不怕你笑话。今年年初，我在公司内部做了一个"智能运维助手"的 Agent 项目，用的是当时最火的框架——LangChain。Demo 跑通那天晚上，我甚至发了条朋友圈："两周搞定 AI Agent，也没那么难嘛。"

然后生产环境给了我三记耳光。

第一记：Agent 在一个多步骤的数据库巡检任务中，把第二步查出来的主机名搞丢了，第三步直接对着一台不存在的主机发指令——没有报错，没有回退，它就那么自信地"完成"了巡检，给我发了一条"所有主机状态正常"的总结。

第二记：我让 Agent 调用一个内部 API 重启服务，它把 POST 请求发成了 GET，API 返回 405，它把这个 405 当成了"服务重启成功"的响应码。因为 LangChain 的 tool 封装把那层错误给"消化"了——Agent 根本不知道工具调用失败了。

第三记最狠：运营同事发现 Agent 在一周内重复执行了 47 次同一个检查任务。因为它"记不住"自己做过什么。上一轮的上下文窗口一过期，它就以为这是全新任务。

三记耳光让我明白一件事：**框架给你的是"看起来能跑"，但从"能跑"到"跑得靠谱"，中间隔着一整个 Agent 的底层理解。**

所以我翻开了这本书——Jungjun Hur 和 Younghee Song 写的《Build an AI Agent (From Scratch)》，2026 年 Manning 出版。

选择这本书而不是其他 Agent 书籍的原因很简单：它承诺"不依赖任何框架"。没有 LangChain，没有 CrewAI，没有 AutoGPT。从零开始，用纯 Python 搭一个完整的 Agent 系统。

我用两周时间把这本书啃完了。下面是我学到的、被颠覆的、以及我认为最有价值的 8 个认知。

---

## 一、ReAct 循环不是"边想边做"，它是一个精确的状态机

这是我读这本书的第一个"啊哈时刻"。

之前我一直以为 ReAct 就是让 LLM 先输出一段"思考"，然后调用工具，然后再"思考"，如此循环。说白了就是一个 while True 循环里面塞了一个 LLM 调用。书里第一章就把这个认知打碎了。

### 你以为的 ReAct

```python
while not done:
    thought = llm.think(context)
    action = llm.decide_action(thought)
    observation = execute(action)
    context.append(thought, action, observation)
```

这个伪代码我过去写过无数次。看起来没问题？问题大了。

### 真正的 ReAct 状态机

书里画了一张让我印象特别深的数据流图（我用文字描述）：

```
[用户输入] 
    → [Thought: 解析意图 + 提取实体 + 判断是否需要工具]
        → [需要工具?] 
            → YES → [Action: 选择工具 + 构造参数 + 执行]
                → [Observation: 原始结果抓取]
                    → [Parser: 结构化解析 + 错误检测]
                        → [Thought: 基于结构化结果重新判断]
            → NO → [Final Answer: 组装最终响应]
```

注意这里的关键差异：

**1. Thought 不止是"想一想"**

书里把 Thought 拆成了三个子步骤：(a) 意图解析——用户到底要什么；(b) 实体提取——任务涉及哪些对象；(c) 工具需求判断——这个任务是否超出了 LLM 自身的知识边界。

我过去的实现里，Thought 就是一句话：`"I need to use the database tool to check the server status."` 而书里要求 Thought 产出一个结构化的决策对象：

```json
{
  "intent": "database_query",
  "entities": ["server-01", "server-02"],
  "requires_tool": true,
  "tool_candidates": ["db_query_tool"],
  "confidence": 0.92,
  "reasoning": "需要查询实时状态，LLM 自身知识可能过期"
}
```

为什么要这样？因为**非结构化的 Thought 无法被程序化验证**。如果 Thought 就是一句话，你怎么判断它想得对不对？你怎么在后续步骤中引用它的决策？你怎么在出问题时回溯它的推理链？

**2. Observation 不是"工具返回什么就用什么"**

这是我最深的踩坑点。工具返回的原始结果（比如 API 返回的 JSON、数据库查询的 ResultSet）不能直接喂给下一轮 Thought。

书里明确给出了 Observation 的三层处理管道：

```
原始输出 → 截断（token 预算控制）→ 结构化解析（提取关键字段）→ 错误检测（判断是否执行成功）→ 注入上下文
```

我之前直接把 `response.text` 拼到 prompt 里，2000 行的 JSON 直接塞进去，把上下文窗口撑爆了都不知道。而且如果工具调用失败了（网络超时、权限不足、参数错误），我完全没有错误检测层——LLM 拿到的就是一段乱码或者 HTTP 错误页的 HTML，然后它就开始"一本正经地胡说八道"。

**3. 终止条件不是"LLM 说完了"**

我过去的 Agent 循环终止条件就是 LLM 返回了 `Final Answer`。但书里提出了一个让我重新审视的指标：**循环预算（loop budget）**。

```python
MAX_LOOPS = 10  # 硬上限，防止死循环
MAX_TOKEN_BUDGET = 8000  # 上下文总量上限
MIN_CONFIDENCE_THRESHOLD = 0.7  # 低于这个置信度，应该让 Agent 承认"我不确定"
```

这三个数字比任何 prompt engineering 都重要。LLM 不会自己停下来——它会在信息不足时继续编，在工具失败时换一个工具继续试，在上下文溢出时截断关键信息。**Agent 需要程序化的护栏，不是语言层面的"请你停下来"。**

---

## 二、MCP 工具系统：少了一个中间层，你的 Agent 就是个瞎子

MCP（Model Context Protocol）是 2025 年底 Anthropic 推出的协议，2026 年已经成为 Agent 工具调用的标配。这本书花了两整章来讲 MCP 的集成。

我之前对 MCP 的理解就是"一个标准化的 function call 协议"。读完这两章我才明白，**MCP 解决的不是"怎么调用工具"，而是"Agent 怎么知道自己有什么工具、这些工具能干什么、用错了怎么办"**。

### 工具注册：不是写个函数签名就完了

书里给出了 MCP 工具注册的完整流程，核心是三层元数据：

```python
tool_schema = {
    "name": "restart_service",
    "description": "重启指定的后端服务。⚠️ 此操作会导致服务中断 3-5 秒。",
    "parameters": {
        "service_name": {
            "type": "string",
            "description": "服务名称，必须是 k8s deployment 的精确名称",
            "enum": ["user-service", "order-service", "payment-service"]  # 限制可选值
        },
        "namespace": {
            "type": "string", 
            "default": "production",
            "description": "K8s 命名空间，默认 production"
        }
    },
    "requires_confirmation": True,  # 危险操作需要二次确认
    "timeout_seconds": 30,
    "max_retries": 2,
    "expected_output_schema": {  # 告诉 Agent 返回值的格式
        "status": "string",
        "previous_version": "string", 
        "new_version": "string"
    }
}
```

注意这几个我之前完全没考虑的点：

- **`requires_confirmation`**：危险操作需要 Human-in-the-loop 确认。我之前用 LangChain 的时候，Agent 会毫不犹豫地执行任何工具——删库、重启、发邮件，全都不带犹豫的。
- **`enum` 参数限制**：LLM 在没有约束的情况下，可能会传 `"user_service"`（下划线）给一个只接受 `"user-service"`（连字符）的 API。加了 enum，LLM 就不会创造不存在的值。
- **`expected_output_schema`**：这是书里最让我惊喜的设计。告诉 Agent "这个工具返回什么格式"，让后续的 Observation 解析有据可依。

### 工具发现：Agent 怎么知道该用哪个工具？

书里讲了一个我之前从来没想过的问题：当你有 50 个工具时，Agent 怎么选？

方案 A：把所有 50 个工具的 schema 全部塞进 system prompt。结果：上下文窗口爆炸 + LLM 选择困难。

方案 B（书里推荐的做法）：**动态工具检索**。

```python
# 根据用户意图，只检索相关的工具
relevant_tools = tool_registry.search(
    query=user_intent,
    top_k=5,  # 只给 Agent 最相关的 5 个工具
    min_relevance_score=0.6
)
```

书里给出的实现方案是用向量检索——把每个工具的描述 embed 成向量，用户的 query 也 embed，然后做语义匹配。工具注册时不仅要写参数 schema，还要写充分的语义描述（这个工具解决什么问题、适用什么场景、有什么限制）。

这个设计的哲学是：**Agent 的认知负荷是有限的。给它越多选择，它的决策质量越差。**5 个精准的工具比 50 个"可能有用"的工具效果好得多。

### 错误回传：让 Agent 知道"调用失败了"

这是我之前最大的盲区。书里单独一节讲"工具调用失败时的信息传递"，我读完之后后背发凉。

我的旧代码：

```python
try:
    result = tool.execute(params)
except Exception as e:
    result = f"Error: {str(e)}"  # 直接拼进 prompt
```

书里的做法：

```python
# 结构化的错误信息
tool_result = {
    "success": False,
    "error_type": "NETWORK_TIMEOUT",  # 分类错误
    "error_message": "请求超时（30s），目标服务可能负载过高",
    "retry_suggestion": "可以尝试增加超时时间到 60s，或先检查服务健康状态",
    "alternative_tools": ["check_service_health"],  # 推荐替代工具
    "partial_result": None  # 有没有部分结果可用？
}
```

关键差异：**不是把错误信息丢给 LLM 让它自己理解，而是用结构化数据引导 LLM 的下一步决策。**LLM 拿到 `"NETWORK_TIMEOUT"` 这种明确分类，比拿到一段 `"connect timeout error occurred at line 42"` 的原始错误信息，做出的下一步决策质量要高一个数量级。

---

## 三、记忆系统：向量数据库只是冰山一角

如果你和我一样，觉得给 Agent 加个向量数据库就是"有记忆了"——那这一章可能会让你和我一样沉默。

书里把 Agent 的记忆系统分成了三层，每一层解决不同的问题。

### 第一层：事实记忆（Factual Memory）

这是最基础的一层——也是大多数 Agent 项目止步的一层。存用户偏好、项目信息、历史对话的关键事实。

实现方式：向量数据库 + 结构化存储。

```
用户偏好：{"preferred_model": "gpt-4", "timezone": "Asia/Shanghai"}
项目上下文：{"current_project": "order-system-migration", "deadline": "2026-06-01"}
历史事实：{"last_deployment_time": "2026-05-07T14:30:00Z"}
```

### 第二层：上下文记忆（Contextual Memory）

书里用了一整节讲"上下文窗口管理"，这是我读得最认真的部分。

核心问题：LLM 的上下文窗口是有限的（128K 看起来很大，但实际上——你把 50 轮对话记录、5 个工具返回的完整 JSON、3 个文档片段全塞进去，128K 瞬间就满了。）

书里给出的方案是**滑动窗口 + 摘要压缩**：

```python
class ContextManager:
    def __init__(self, max_tokens=8000, summary_threshold=4000):
        self.messages = []
        self.summary = ""
        self.max_tokens = max_tokens
        self.summary_threshold = summary_threshold
    
    def add_message(self, message):
        self.messages.append(message)
        if self.token_count > self.summary_threshold:
            # 触发压缩：将最早的 N 条消息总结成一段
            old_messages = self.messages[:N]
            self.summary = llm.summarize(old_messages)  # 不是简单截断，而是智能总结
            self.messages = self.messages[N:]
    
    def get_context(self):
        # 组装：摘要（固化记忆）+ 近期消息（活跃上下文）
        return self.summary + "\n---\n" + "\n".join(self.messages)
```

关键洞察：**截断不是删除。**旧消息中可能包含后续步骤需要的关键信息（比如第一步查出来的服务器 IP，第四步还要用到）。所以在截断之前，必须先提取并保存"长期有用"的信息——这就是摘要层的作用。

### 第三层：目标记忆（Goal Memory）

这是三层中最容易被忽视的一层——也是让我那 47 次重复执行的悲剧发生的原因。

目标记忆解决的问题：**Agent 在执行多步骤任务时，需要记住"我做到哪了"和"我本来要干什么"**。

书里给出的数据结构：

```python
task_state = {
    "task_id": "daily-inspection-20260508",
    "goal": "完成生产环境 12 台服务器的日常巡检",
    "subtasks": [
        {"id": 1, "name": "CPU使用率检查", "status": "completed", "result": "正常"},
        {"id": 2, "name": "内存使用率检查", "status": "completed", "result": "3台超过80%"},
        {"id": 3, "name": "磁盘空间检查", "status": "in_progress"},
        {"id": 4, "name": "服务健康检查", "status": "pending"},
        {"id": 5, "name": "生成巡检报告", "status": "pending"}
    ],
    "created_at": "2026-05-08T08:00:00Z",
    "last_updated": "2026-05-08T08:15:00Z",
    "context_cache": {  # 子任务之间共享的数据
        "high_memory_servers": ["server-03", "server-07", "server-11"],
        "inspection_start_time": "2026-05-08T08:00:00Z"
    }
}
```

有了这个结构，Agent 就不会在中午 12 点再跑一次巡检——因为它能查到"今天 8 点已经跑过了，而且全都完成了"。我之前的 Agent 之所以重复执行 47 次，就是因为没有这一层。

**三层记忆的协作关系：**

- 事实记忆 = "我知道什么"（知识库）
- 上下文记忆 = "我刚才在聊什么"（短期记忆）
- 目标记忆 = "我要做什么，做到哪了"（任务状态）

三者缺一不可。书里有一句话我划线了：*"一个没有目标记忆的 Agent，就像一个人每天早上醒来就忘了昨天在做什么——但他还记得所有的事实和数据。这比完全失忆更危险，因为他会基于正确的事实，做出错误的决策。"*

---

## 四、反思与自我纠错：Agent 怎么"意识到自己错了"

这一章的内容，大概是我整本书收获最大的部分。因为它直接回应了我最核心的困惑：**LLM 天生不会"发现自己错了"——它只会沿着自己生成的 token 继续往下编。那 Agent 怎么拥有自我纠错能力？**

### 不是"再问一遍"，而是"带着标准去检查"

我过去的"反思"实现就是：在 Agent 输出结果之后，再调一次 LLM，问它"你确定吗？有没有错误？"

这基本没用。LLM 会说"我确定，没有错误"——哪怕它刚才把 405 当成 200 了。

书里给出的方案是**结构化自我评估**——不是让 LLM 自由评判，而是让它对照一个检查清单逐项打分：

```python
self_critique_prompt = """
请逐项检查你的上一个回答：

1. 事实准确性：回答中的每个具体数据/事实是否正确？（逐条列出，标记 ✓ 或 ✗）
2. 逻辑一致性：前一个观点和下一个观点之间有没有矛盾？
3. 完整性：用户的问题是否被完全覆盖？有没有遗漏的部分？
4. 工具调用正确性：如果使用了工具，参数是否正确？返回值是否被正确解析？
5. 安全边界：回答中是否包含不应执行的操作或不应透露的信息？

如果任何一项标记为 ✗，必须给出修正方案。
如果所有项都是 ✓，直接回复 "CHECK_PASSED"。
"""
```

注意两个关键设计：
- **逐项打分**而不是自由评论——这迫使 LLM 进行结构化思考，降低了"糊弄过去"的概率
- **强制修正**——标记了 ✗ 就必须给修正方案，不能只认错不改错

### 多轮反思：不是越多越好

书里做了一个实验，让我印象很深：

| 反思轮次 | 回答准确率 | 平均耗时 |
|---------|-----------|---------|
| 无反思 | 72% | 2.3s |
| 1轮反思 | 89% | 5.1s |
| 2轮反思 | 91% | 8.7s |
| 3轮反思 | 88% | 14.2s |

注意：**3轮反思的准确率反而下降了**。原因是过度反思会导致"过度修正"——Agent 开始怀疑自己本来正确的判断，改来改去反而改错了。

书里的建议是：**默认一轮反思即可。只在以下情况追加第二轮：**
- 第一轮发现了 ✗ 标记
- 任务涉及安全或资金操作
- 用户明确要求"再确认一遍"

### 反思的时机：不是"等做完了再检查"

书里还提了一个概念叫 **"中途反思"（mid-task reflection）**——在任务的中间步骤就进行反思，而不是等到最后。

```python
# 不是这样（事后反思）
for step in task:
    execute(step)
reflect_on_result()  # 做完了才检查

# 而是这样（中途反思）
for i, step in enumerate(task):
    execute(step)
    if should_reflect(i, task):  # 每 N 步检查一次
        result = reflect_on_progress()
        if result.needs_replan:
            replan_remaining_steps()
```

这个设计节省了大量的"错误传播时间"——不会等到第五步才发现第二步就错了。

---

## 五、代码执行 Agent：最容易被忽视的设计

书里有一整章讲 Code Execution Agent——Agent 写代码然后执行代码的那种。这个模式在数据分析、自动化运维、代码审查等场景非常常见。

表面上看，让 Agent 执行代码就是：LLM 生成代码 → `exec()` 跑一下 → 把输出喂回去。但书里给出了 5 个我在生产环境中全都踩过的坑。

### 1. 沙箱隔离：永远不要在主进程里跑 Agent 生成的代码

这是最基本的安全原则，但我见过太多 Demo 直接在主进程 `exec()` 了。书里给的方案是 Docker 沙箱：

```python
# 在隔离容器中执行
docker run --rm \
    --network=none \        # 禁止网络访问
    --memory=512m \         # 内存限制
    --cpu-quota=50000 \     # CPU 限制（50% 一个核）
    --read-only \           # 只读文件系统
    --tmpfs /tmp:size=100m \ # 临时写入空间
    agent-sandbox:latest \
    python -c "用户生成的代码"
```

### 2. 超时控制：不是设个 timeout 就完了

书里给出了多层次的超时策略：

```python
EXECUTION_TIMEOUT = 30  # 总执行时间
STEP_TIMEOUT = 5  # 单步超时（用于调试）
OUTPUT_MAX_CHARS = 10000  # 输出截断
MEMORY_LIMIT_MB = 512  # 内存硬限制
```

`exec()` 之后如果输出了 10 万行日志，你不能全塞回给 LLM——上下文窗口会爆。书里建议**截断 + 摘要**：只保留前 100 行和后 50 行，中间用 `...(省略 98450 行)...` 代替。

### 3. 输出解析：区分"执行成功但结果为空"和"执行失败"

```python
result = execute_code(code)

if result.exit_code == 0:
    if result.stdout.strip():
        return {"status": "success", "output": result.stdout[:OUTPUT_MAX_CHARS]}
    else:
        return {"status": "success", "output": "(执行成功，无输出)"}
elif result.exit_code != 0:
    return {
        "status": "error", 
        "error_type": classify_error(result.stderr),  # 分类错误类型
        "error_message": result.stderr[:1000],
        "suggestion": generate_fix_suggestion(result.stderr)  # 给 LLM 修复建议
    }
```

`classify_error()` 和 `generate_fix_suggestion()` 这两个函数是书里给的彩蛋——用一个小的规则引擎对 Python 常见错误做分类（SyntaxError / ImportError / NameError / RuntimeError 等），然后给出对应的修复提示。这比直接把 stderr 甩给 LLM 效率高得多。

### 4. 文件系统隔离

Agent 可能会 `import os; os.remove("/")`。书里强调了两点：
- 容器内只挂载必要的目录
- 任何文件写入操作都需要 `requires_confirmation: True`

### 5. 结果缓存：同样的代码不要跑两遍

```python
code_hash = hashlib.sha256(code.encode()).hexdigest()
if code_hash in execution_cache:
    return execution_cache[code_hash]
result = execute_code(code)
execution_cache[code_hash] = result
return result
```

---

## 六、从单 Agent 到多 Agent：书在哪里收尾

这本书的主体内容聚焦在单 Agent 上，但最后一章专门讲了如何从单 Agent 过渡到多 Agent 系统。

书里把多 Agent 的过渡分成了三个渐进阶段：

**阶段1：工具化拆分**
把原本内嵌在 Agent 逻辑里的能力拆成独立的工具服务——但这还是"一个大脑控制多只手"。

**阶段2：专业化 Agent**
创建多个各司其职的 Agent（比如 Code Agent / Research Agent / Review Agent），但它们之间通过一个中心调度器通信。

**阶段3：真正的多 Agent 协作**
Agent 之间可以互相发现、互相委派任务、共享上下文——这就需要 A2A 协议和更复杂的编排机制了。

书里对阶段 3 只是"指了个方向"，并没有深入展开。作者的建议是：**先去读 Val Andrei Fajardo 的《Build a Multi-Agent System (from Scratch)》**。这也是我接下来要看的那本书。

---

## 七、8 个可以直接用到项目里的具体建议

不是大道理，是读完这本书之后我立刻改了的 8 件事：

1. **把 Thought 改成结构化 JSON**，而不是自由文本。意图/实体/置信度三个字段必须有。

2. **在每次工具调用后加一个 `validate_observation()` 函数**。检查返回值格式、错误码、数据完整性。别让 Agent 拿着错误数据继续推理。

3. **给每个工具设 `requires_confirmation` 字段**。删库、发邮件、重启服务——这些操作必须经过二次确认。

4. **为 Agent 设置 `max_loops` 和 `max_tokens_per_task`**。LLM 自己不会停下来，你要帮它停下来。

5. **记忆系统三层必须全有**。事实记忆/上下文记忆/目标记忆——少任何一层都可能在特定场景崩溃。

6. **反思用结构化检查清单，不要自由问"你确定吗"**。逐项打分的效果远好于开放式反思。

7. **代码执行必须用 Docker 沙箱 + 多层次超时控制**。`--network=none`、`--read-only`、`--memory=512m` 三项必须配齐。

8. **工具超过 10 个就要做动态检索**。不要把 50 个工具的 schema 全塞进 prompt。

---

## 八、这本书的边界：你应该什么时候放下它

每本书都有它擅长和不擅长的地方。读完这本，我认为它的边界非常清晰：

**这本书适合你，如果：**
- 你想真正理解 Agent 的内部运作，而不是"调包侠"
- 你在用现有框架时遇到了"黑盒问题"——Agent 的行为不符合预期但不知道为什么
- 你需要一个轻量级、高度可控的 Agent 实现，不想依赖庞大的框架依赖
- 你正在从零设计自己的 Agent 系统

**这本书不适合你，如果：**
- 你需要的是"5分钟搭一个 Agent"的快速入门——这本书的定位就是反"快速入门"的
- 你的项目已经深度绑定了某个框架（LangChain/CrewAI），迁移成本太高
- 你主要关心的是多 Agent 协作——这本书的重点在单 Agent，多 Agent 只是最后一章的一个引子

**这本书没讲到（但很重要）的：**
- A2A 协议和多 Agent 协作机制——需要另外的专门书籍
- 生产环境的可观测性（分布式追踪、监控告警）——这本书侧重于 Agent 核心逻辑
- 安全攻防——书里只有 Docker 沙箱这一层，真正的安全审计需要更深入的方案
- 成本优化——大规模部署时的 token 成本控制策略

---

## 写在最后

这本书的英文原版书名里有个括号——"(From Scratch)"。我觉得这俩词才是整本书的核心哲学。

作者在前言里写了段话，我印象很深，大意是：**"框架是好东西，但框架是一种交换——你交出了控制权，换来了开发速度。只有当你从零构建过一次，你才知道框架替你做了哪些决定，以及这些决定在什么情况下是错的。"**

如果你和我一样，在用 LangChain 或 CrewAI 的时候有过"它为什么这样做？"的困惑，这本书会给你答案。不是因为它教你怎么用框架——恰恰相反，因为它教你不用框架。

读完之后我把之前写的 Agent 代码全删了，用书里的思路重写了一遍。新代码只有 800 行，没有任何框架依赖，但它第一次让我觉得——**我知道每一行在干什么**。

---

*书名：《Build an AI Agent (From Scratch)》*
*作者：Jungjun Hur, Younghee Song*
*出版社：Manning Publications, 2026*
*适合读者：有 Python 基础、用过 LLM API、想深入理解 Agent 底层原理的开发者*

**下一篇预告：读《Build a Multi-Agent System (from Scratch)》——当三个 Agent 开始互相甩锅时，我才意识到自己完全不懂 A2A 协议。**
