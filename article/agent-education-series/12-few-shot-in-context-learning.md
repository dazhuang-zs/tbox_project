# 【AI Agent 系统教学 12】少样本学习与上下文学习

> 给模型看 3 个例子，它就能学会一个新任务——这就是 Agent 的核心能力之一。
> 但"怎么给例子"是一门学问。

---

## 前言：示例比指令更有效

在 Agent 开发中，你可能遇到过这种情况：

```
指令：请用 JSON 格式输出，包含 tool 和 params 字段。

模型输出：好的，我会用 JSON 格式输出。{"tool": "search", "params": "query"}（格式错误）
```

但如果你给了一个示例：

```
示例：
用户：北京天气怎么样？
助手：{"tool": "get_weather", "params": {"city": "北京"}}

你的任务：深圳天气怎么样？
模型输出：{"tool": "get_weather", "params": {"city": "深圳"}}
```

模型立刻学会了。**一个示例比十行指令更有效。**

这就是 In-Context Learning（上下文学习）的力量。

---

## 一、In-Context Learning 的本质

### 1.1 什么是 ICL

In-Context Learning 是模型在推理时，通过上下文中的示例来学习新任务的能力——不需要微调，不需要更新参数。

**给模型看 3 个示例**，它就能在"推理时"学会一个全新的任务。

### 1.2 ICL 的底层机制

ICL 的背后是**模式匹配**：

```
模型在训练数据中见过大量"示例 → 输出"的模式。
给定新的示例，模型匹配到训练数据中的相似模式。
然后，模型"延续"这个模式，生成对应的输出。

关键：模型不是"理解"了你给的任务，而是"延续"了你给的模式。
```

### 1.3 ICL vs 微调

| 维度 | ICL（Few-shot） | 微调（Fine-tuning） |
|------|---------------|-------------------|
| 参数更新 | 否 | 是 |
| 数据需求 | 2-5 个示例 | 1000+ 条数据 |
| 成本 | 低（仅推理） | 高（训练 + 部署） |
| 灵活性 | 高（随时换任务） | 低（一个模型一个任务） |
| 持久性 | 仅当前对话 | 永久 |
| 适合场景 | 快速验证、低频任务 | 高频、稳定任务 |

---

## 二、Few-shot 示例设计

### 2.1 示例选择

**选择策略**：

```python
def select_examples(user_input, example_pool, k=3):
    """从示例池中选择最相关的 K 个示例"""
    # 策略 1：随机选择（简单，但效果不稳定）
    if strategy == "random":
        return random.sample(example_pool, k)
    
    # 策略 2：语义相似度选择（推荐）
    if strategy == "similarity":
        input_embedding = embed(user_input)
        similarities = [
            cosine_similarity(input_embedding, embed(e.input))
            for e in example_pool
        ]
        top_k = argsort(similarities, k, reverse=True)
        return [example_pool[i] for i in top_k]
    
    # 策略 3：多样性选择（覆盖不同场景）
    if strategy == "diversity":
        # 聚类后从每个簇选一个
        clusters = cluster(example_pool, k)
        return [random.choice(cluster) for cluster in clusters]
```

### 2.2 示例的排列顺序

示例的顺序影响效果：

```
效果最好：从简单到复杂
效果次之：随机排列
效果最差：从复杂到简单
```

**为什么？** 模型在"延续"你的示例模式。如果示例从简单到复杂，模型学会了"递增"的模式。反之，一开始就遇到复杂示例，模型可能"学不会"。

### 2.3 示例的表示格式

```python
# 格式 1：自然语言（最通用）
examples = """
用户：北京天气怎么样？
助手：今天北京晴，25度。

用户：深圳天气怎么样？
助手：今天深圳多云，30度。
"""

# 格式 2：结构化（适合工具调用）
examples = """
用户：帮我查一下北京天气
助手：{"tool": "get_weather", "params": {"city": "北京"}}

用户：帮我查一下深圳天气
助手：{"tool": "get_weather", "params": {"city": "深圳"}}
"""

# 格式 3：对话格式（适合多轮）
examples = [
    {"role": "user", "content": "北京天气怎么样？"},
    {"role": "assistant", "content": "{"tool": "get_weather", "params": {"city": "北京"}}"},
    {"role": "user", "content": "深圳天气怎么样？"},
    {"role": "assistant", "content": "{"tool": "get_weather", "params": {"city": "深圳"}}"},
]
```

---

## 三、ICL 的局限性

### 3.1 示例越多不一定越好

| 示例数量 | 效果 | 说明 |
|---------|------|------|
| 0（Zero-shot） | 差 | 模型可能自由发挥 |
| 1（One-shot） | 中等 | 示例可能不够全面 |
| 3（3-shot） | 好 | 覆盖主要模式 |
| 5（5-shot） | 很好 | 覆盖更多边缘情况 |
| 10+ | 边际递减 | 多了反而可能混淆 |

**最佳实践**：2-5 个示例最有效。超过 10 个，收益递减。

### 3.2 示例质量 > 示例数量

```
❌ 5 个低质量示例：
  示例 1：格式错误
  示例 2：内容不相关
  示例 3：答案不准确
  示例 4：格式不一致
  示例 5：答案正确但格式混乱

✅ 2 个高质量示例：
  示例 1：格式正确，内容相关，答案准确
  示例 2：覆盖不同场景，格式一致
```

### 3.3 示例与真实输入的差异

如果示例与真实输入差异太大，ICL 的效果会急剧下降：

```python
# ❌ 示例与真实输入不匹配
examples = """
用户：北京天气怎么样？  →  助手：{"tool": "get_weather", "params": {"city": "北京"}}
"""
user_input = "帮我算一下 2+2"  # 完全不同的任务类型

# ✅ 示例与真实输入匹配
examples = """
用户：帮我算一下 3+4  →  助手：7
用户：2+2  →  助手：4
"""
user_input = "帮我算一下 2+2"
```

---

## 四、Agent 中的 ICL 实战

### 4.1 动态示例注入

在 Agent 中，根据用户输入动态选择最合适的示例：

```python
class AgentWithICL:
    def __init__(self):
        self.example_pool = {
            "weather": [
                {"input": "北京天气", "output": '{"tool": "get_weather", "city": "北京"}'},
                {"input": "上海明天天气", "output": '{"tool": "get_weather", "city": "上海"}'},
            ],
            "search": [
                {"input": "搜索Python教程", "output": '{"tool": "search_web", "query": "Python教程"}'},
            ],
            "email": [
                {"input": "发邮件给张三", "output": '{"tool": "send_email", "to": "张三"}'},
            ],
        }
    
    def respond(self, user_input):
        intent = self.classify_intent(user_input)
        examples = self.example_pool.get(intent, [])
        
        prompt = self.build_prompt_with_examples(user_input, examples)
        return self.llm.generate(prompt)
```

### 4.2 示例作为 Few-shot 缓存

高频使用的示例可以缓存，减少 API 调用：

```python
class ExampleCache:
    def __init__(self, max_size=100):
        self.cache = {}
        self.max_size = max_size
    
    def get(self, intent):
        if intent in self.cache:
            return self.cache[intent]
        return self.default_examples
    
    def update(self, intent, new_example):
        if intent not in self.cache:
            self.cache[intent] = []
        self.cache[intent].append(new_example)
        if len(self.cache[intent]) > self.max_size:
            self.cache[intent].pop(0)
```

### 4.3 示例的自我进化

Agent 可以从成功和失败的交互中学习，优化示例池：

```python
def update_example_pool(agent, interaction, success):
    if success:
        # 成功案例：添加到示例池
        intent = classify_intent(interaction.user_input)
        agent.example_pool[intent].append({
            "input": interaction.user_input,
            "output": interaction.agent_output,
        })
    else:
        # 失败案例：分析原因，如果有更好的输出，替换低质量示例
        if interaction.corrected_output:
            replace_low_quality_example(agent, interaction)
```

---

## 五、ICL 的优化技巧

### 5.1 格式统一

所有示例使用相同的格式，降低模型的"格式切换成本"。

### 5.2 覆盖边缘情况

至少有一个示例覆盖"不知道"或"出错"的情况：

```python
examples = [
    # 正常情况
    {"input": "北京天气", "output": "{"tool": "get_weather", "city": "北京"}"},
    # 边缘情况：不知道
    {"input": "2027年世界杯冠军是谁？", "output": "我不知道，让我搜索一下。"},
    # 边缘情况：工具出错
    {"input": "查xx市天气", "output": "{"tool": "get_weather", "city": "xx"}"},
    # 工具返回错误后的处理
    # ...
]
```

### 5.3 标注示例的"思考过程"

```python
examples = [
    {
        "input": "北京天气怎么样？",
        "thought": "用户想知道北京天气，需要调用天气查询工具。",
        "output": '{"tool": "get_weather", "params": {"city": "北京"}}',
    }
]
```

### 5.4 示例的 token 预算

| 示例数量 | 平均 token 消耗 | 推荐 |
|---------|---------------|------|
| 0 | 0 | 简单任务 |
| 1 | 50-100 | 快速验证 |
| 3 | 200-300 | 日常使用 |
| 5 | 500-800 | 复杂任务 |
| 10+ | 1000+ | 不推荐（token 浪费） |

---

## 总结

| 概念 | 一句话 | 对 Agent 的意义 |
|------|--------|----------------|
| ICL | 模型从示例中学习 | 零成本的"任务适配" |
| Few-shot | 给 2-5 个示例 | 比指令更有效 |
| 示例选择 | 选最相关的 | 动态选择 > 固定选择 |
| 示例顺序 | 从简单到复杂 | 模型更容易"学会" |
| 动态注入 | 根据输入选示例 | 适配不同场景 |

下一篇文章，我们将进入**提示词攻击与防御**——Prompt Injection、Jailbreak，以及如何保护你的 Agent。

---

**思考题**：
1. 如果你的 Agent 需要处理 10 种不同的任务类型，每个类型只给 3 个示例，总共 30 个示例会不会太多？怎么优化？
2. 示例的"思考过程"字段有用吗？在什么场景下有用？
3. 你会在 Agent 中实现"示例自我进化"吗？怎么防止"坏示例"污染示例池？

---

> 上一篇：[11] 思维链与推理增强
> 下一篇：[13] 提示词攻击与防御
> 系列目录：[README.md](./README.md)