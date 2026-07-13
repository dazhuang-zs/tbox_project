# 【AI Agent 系统教学 09】提示词工程的底层逻辑

> 你在 Agent 代码里写的那几行 System Prompt，决定了 Agent 是"聪明"还是"智障"。
> 但大部分人写 Prompt 靠的是"玄学"——试到对为止。

---

## 前言：Prompt 是 Agent 的"操作系统"

Agent 的 System Prompt 是什么？它是 Agent 的"系统指令"，定义了 Agent 的角色、行为、工具、规则。

但多数人写 System Prompt 是这样：

```python
system_prompt = """
你是一个有用的 AI 助手。
你可以使用以下工具：
- get_weather(city)
- send_email(to, subject, body)
"""
```

然后跑了一遍，发现 Agent 不听话，就开始加"请你务必""一定要""注意"——越写越长，越写越乱。

**问题出在哪？** 你不是在写 Prompt，你是在"许愿"。你没有理解模型到底是怎么"理解"你的文字的。

---

## 一、模型如何"理解"提示词

### 1.1 提示词是条件概率

从技术角度看，Prompt 的作用是**设定条件概率的输入**。

```
P(回答 | Prompt)
```

模型的任务是：给定 Prompt，生成最可能的 token 序列。

**这意味着**：
- Prompt 中的每个词都在影响输出的概率分布
- 越靠近输入末尾的词，影响越大
- 重复出现的模式会被强化

### 1.2 模型不是"读"你的文字，是"预测"下一个词

```
Prompt："你是一个 AI 助手。"
模型的处理：
1. 在训练数据中搜索"你是一个 AI 助手"的上下文
2. 发现大量"你是一个 AI 助手，可以帮助用户"的句子
3. 所以，输出"你可以帮助用户"的概率很高
```

**关键洞察**：模型不是"理解"了你的 Prompt，而是"匹配"到了训练数据中与你的 Prompt 最相似的模式。

### 1.3 System Prompt 的工作原理

System Prompt 之所以有效，不是因为它是"系统指令"，而是因为它**占据了上下文窗口的前面位置**，设定了后续对话的"语境"。

```
[System Prompt] → 设定角色、工具、规则
[User Message] → 受 System Prompt 影响
[Assistant Response] → 受 System Prompt + User Message 共同影响
[User Message] → 进一步受之前对话影响
...
```

**System Prompt 的位置优势**：在 Attention 中，开头的 token 有"全局可见性"——它们可以影响所有后续的 token。

---

## 二、提示词设计的三个层次

### 2.1 层次一：指令（Instruction）

告诉模型"做什么"。

```
"翻译以下内容为英文："
"用 Python 写一个二分查找函数。"
"总结这篇文章的核心观点。"
```

**关键**：指令要清晰、具体、唯一。模糊的指令得到模糊的输出。

### 2.2 层次二：上下文（Context）

告诉模型"在什么场景下"。

```
"你是一个客服 Agent，专门处理退换货问题。"
"用户刚购买了一个产品，现在对产品不满意。"
"以下是公司的退换货政策：..."
```

**关键**：上下文不是"装饰"，是模型生成的基础。没有上下文，模型只能依赖训练数据中的通用模式。

### 2.3 层次三：约束（Constraint）

告诉模型"不能做什么"。

```
"不要询问用户的个人信息。"
"如果不知道答案，就说'我不确定'。"
"始终用中文回复。"
"输出格式必须为 JSON。"
```

**关键**：约束要具体、可验证。模糊的约束（"请友好回复"）不如具体的约束（"每句话都以'您好'开头"）。

---

## 三、提示词设计的核心原则

### 3.1 原则一：明确输出格式

**错误做法**：
```
"请告诉我北京今天的天气。"
```
（模型可能输出一篇文章、一段话、一个列表）

**正确做法**：
```
"请告诉我北京今天的天气。
输出格式：{'temperature': 温度, 'condition': '天气状况', 'humidity': 湿度}"
```
（模型输出可解析的结构化数据）

### 3.2 原则二：给出示例（Few-shot）

**零样本（Zero-shot）**：
```
"把以下句子翻译成英文：今天天气很好。"
```

**少样本（Few-shot）**：
```
"把以下句子翻译成英文：
今天天气很好。 → The weather is nice today.
昨天下了雨。 → It rained yesterday.
明天会下雪。 → It will snow tomorrow.
现在刮风了。 → "
```

**为什么 Few-shot 有效？** 因为模型在训练数据中见过"示例 → 输出"的模式。给 3 个示例，就是在告诉模型"我正在做这种任务"。

### 3.3 原则三：位置越靠后，影响越大

```python
# 错误做法：把最重要的信息放前面
system_prompt = """
你是 xx 公司的客服 Agent。
你可以使用以下工具：
- search_knowledge_base(query)
- check_order_status(order_id)
- escalate_to_human(issue)
公司退换货政策：...
注意：如果用户询问退款，请先查询订单状态。
注意：不要透露公司内部信息。
"""

# 正确做法：把最重要的信息放最后
system_prompt = """
你是 xx 公司的客服 Agent。
你可以使用以下工具：
- search_knowledge_base(query)
- check_order_status(order_id)
- escalate_to_human(issue)
公司退换货政策：...

最重要的规则：
1. 如果用户询问退款，请先查询订单状态。
2. 不要透露公司内部信息。
"""
```

### 3.4 原则四：减少歧义

**模糊**：
```
"请优化这段代码"  # 优化什么？性能？可读性？安全性？
```

**清晰**：
```
"请优化这段代码的性能，目标是将运行时间减少 50% 以上。"
```

### 3.5 原则五：避免否定指令

**错误**：
```
"不要提到竞争对手的名字。"
"不要输出 Markdown 格式。"
```

**正确**：
```
"只使用中文，不提及任何公司名称。"
"以纯文本格式输出，不要使用 Markdown。"
```

**为什么？** 模型在训练时更多看到的是"应该做什么"，而不是"不应该做什么"。否定指令容易让模型混淆。

---

## 四、提示词模板：Agent 的 System Prompt 设计

### 4.1 标准 System Prompt 模板

```
【角色设定】
你是一个 [角色名称]，专门负责 [任务描述]。

【核心能力】
你可以使用以下工具：
1. [工具名称]([参数]): [工具描述]
2. [工具名称]([参数]): [工具描述]

【行为规则】
1. [规则 1]
2. [规则 2]
...

【输出格式】
[指定输出格式，如 JSON]

【重要提醒】
[最关键的 1-2 条规则，放在最后]
```

### 4.2 Agent 专用示例

```python
system_prompt = """
你是一个智能助手 Agent，专门负责协助用户完成各种任务。

【核心能力】
你可以使用以下工具来完成任务：

1. search_web(query: str): 搜索网络获取最新信息
   - 适合：需要最新信息、不确定答案、需要验证事实
   
2. get_weather(city: str): 查询指定城市的天气
   - 适合：用户询问天气相关问题时

3. send_email(to: str, subject: str, body: str): 发送邮件
   - 需要用户明确指定收件人、主题和内容

【工作流程】
1. 分析用户需求，确定需要哪些工具
2. 按顺序调用工具，每次都等待工具返回结果
3. 根据工具返回的结果，决定下一步操作
4. 如果工具返回错误，尝试修复或告诉用户

【重要规则】
1. 始终用中文回复
2. 如果不知道答案，请使用搜索工具，不要编造
3. 工具调用结果必须如实报告给用户
4. 不要执行任何可能对用户有害的操作
"""
```

### 4.3 动态注入

System Prompt 中的某些部分应该是动态的，根据当前上下文生成：

```python
def build_system_prompt(user_context, available_tools, session_info):
    prompt = f"""
    你是一个帮助你完成任务的 AI Agent。
    
    用户信息：
    - 名称：{user_context.name}
    - 偏好：{user_context.preferences}
    
    当前对话：
    - 已进行轮次：{session_info.turn_count}
    - 已完成任务：{session_info.completed_tasks}
    """
    
    if available_tools:
        prompt += f"""
    你可以使用的工具（当前对话中已加载）：
    {format_tools(available_tools)}
        """
    
    return prompt
```

---

## 五、提示词优化的系统方法

### 5.1 A/B 测试

不要靠"感觉"判断哪个 Prompt 好，做 A/B 测试：

```python
prompt_a = "请把以下内容翻译成英文："
prompt_b = "现在需要你扮演一个翻译专家。请将以下中文内容准确翻译为英文，保持原文风格和语气："

# 测试 100 个用例
results_a = test_translation(prompt_a, 100)
results_b = test_translation(prompt_b, 100)

# 比较结果
print(f"Prompt A 准确率：{results_a.accuracy}")
print(f"Prompt B 准确率：{results_b.accuracy}")
```

### 5.2 迭代优化

```
V1：初始 Prompt
    ↓
评估：找到薄弱环节
    ↓
V2：针对性修改
    ↓
评估：对比 V1 和 V2
    ↓
V3：继续优化
    ↓
...
```

**每次只改一个变量**：同时改多个地方，你不知道哪个改动的效果最好。

### 5.3 反模式：Prompt 越长越好？

**不**。有研究显示：

- Prompt 超过一定长度后，效果不再提升
- 太长反而让模型"迷失重点"
- 核心信息应该在 Prompt 末尾

**建议**：System Prompt 控制在 800-1500 字以内，关键规则放在最后 200 字。

---

## 六、Prompt 在 Agent 中的特殊考量

### 6.1 工具调用 vs 自然回复

Agent 的 Prompt 需要同时控制两种行为：

```python
system_prompt = """
你的行为有两种模式：

模式一：工具调用
当你需要获取信息或执行操作时，输出工具调用：
{"tool": "search_web", "params": {"query": "..."}}

模式二：自然回复
当用户与你对话，或你根据工具结果生成回复时，以自然语言输出。

选择规则：
1. 优先使用工具获取信息，而不是凭记忆回答
2. 工具调用后，根据结果生成回复
3. 如果工具返回错误，分析原因并尝试修复
"""
```

### 6.2 多轮对话中的 Prompt 设计

在 Agent 的多轮对话中，System Prompt 会逐渐在 Attention 中"稀释"。解决方案：

**方案 1：每轮重申关键规则**

```python
def build_message(user_input, history):
    messages = [
        {"role": "system", "content": system_prompt},
        *history,
        # 在每轮用户输入前重申关键规则
        {"role": "system", "content": "提醒：优先使用工具获取信息，不要编造"},
        {"role": "user", "content": user_input},
    ]
    return messages
```

**方案 2：关键规则注入到用户消息中**

```python
def build_message(user_input, history):
    messages = [
        {"role": "system", "content": system_prompt},
        *history,
        # 把关键规则放在用户消息末尾
        {"role": "user", "content": f"{user_input}\n\n[系统提示：请使用工具获取信息，不要凭记忆回答]"},
    ]
    return messages
```

---

## 总结

| 原则 | 含义 | 实践 |
|------|------|------|
| 条件概率 | Prompt 设定输出概率 | 精确措辞比模糊强调更有效 |
| 位置优势 | 末尾信息影响力最大 | 关键规则放最后 |
| 输出格式 | 明确指定输出格式 | 给定模板或示例 |
| 少样本 | 示例比指令更有效 | 给 2-3 个示例 |
| 迭代优化 | 每次改一个变量 | A/B 测试，持续改进 |

**Prompt 不是玄学，是工程。** 理解模型的工作原理，然后系统性地设计、测试、优化。

下一篇文章，我们将深入**结构化提示词**——多角色、多段落、格式约束，以及如何让 Agent 输出完全可控。

---

**思考题**：
1. 你现在的 Agent System Prompt 有多长？哪些部分是可以精简的？
2. 如果你要让 Agent 在 10 轮对话后仍然记得第一条规则，你会怎么做？
3. "少样本"示例在 Agent 的工具调用中应该怎么用？给一个具体的例子？

---

> 上一篇：[08] 模型评估与基准测试
> 下一篇：[10] 结构化提示词：多角色、多段落、格式约束
> 系列目录：[README.md](./README.md)