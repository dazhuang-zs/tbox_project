# LLM 底层原理速成：Token、Transformer、Context Window 一次性讲透

> 没有数学公式，没有矩阵乘法。本文用图解 + 代码 + 类比，让你一次性理解 LLM 的核心原理。读完你就能回答面试题：「Token 是什么」「为什么 Context Window 有上限」「Temperature 到底怎么调」。

---

## 一、LLM 不认字，只认 Token

### 什么是 Token

你把一句话发给 ChatGPT，它看到的不是汉字，而是一串数字。Token 就是「LLM 的最小阅读单位」。

```python
# 你可以用 tiktoken 自己试试
import tiktoken

enc = tiktoken.get_encoding("cl100k_base")  # GPT-4 的编码器
text = "今天天气真好"
tokens = enc.encode(text)

print(f"原文：{text}")
print(f"Token 数量：{len(tokens)}")
print(f"Token IDs：{tokens}")

# 输出：
# 原文：今天天气真好
# Token 数量：5
# Token IDs：[57668, 239, 163, 234, 102]
```

### 中英文 Token 差异

| 内容 | 大致 Token 数 | 说明 |
|------|:--:|------|
| 1 个英文字母 | ~0.3 Token | "a" = 1 Token |
| 1 个英文单词 | 1-2 Token | "hello" = 1 Token, "incomprehensible" = 4 Token |
| 1 个中文字 | 1-2 Token | "我" = 1 Token, "龘" = 3 Token |
| 1000 个中文字 | ~1500 Token | |

> **为什么重要？** 因为 API 按 Token 计费。DeepSeek 约 ¥0.001/千 Token，Claude 约 $3/百万 Token。你写的每篇 CSDN 文章，生成一次约 3000-5000 Token。

---

## 二、LLM 怎么「理解」文字：Embedding

LLM 不能直接处理文字，必须把 Token 转成向量（一组数字）：

```
"猫" → [0.12, -0.45, 0.78, ..., 0.33]  # 几千个数字
"狗" → [0.11, -0.43, 0.76, ..., 0.31]  # 和"猫"很接近
"电脑" → [-0.54, 0.92, -0.15, ..., 0.67]  # 和"猫"很远
```

语义相近的词，向量也相近。这就是 Embedding 的本质——把语义关系编码成空间距离。

> 这也是向量数据库能做「语义搜索」的基础。你搜「怎么优化性能」，它找到「代码优化技巧」，虽然字面不匹配，但语义相近。

---

## 三、Transformer：LLM 的核心引擎

GPT、Claude、DeepSeek 都基于同一个架构：**Transformer**。不用背公式，理解三个核心机制就够了：

### 3.1 Self-Attention（自注意力）：看整句话

传统 RNN 从左到右读，读到后面忘了前面：

```
"我 今天 在 一家 很 好吃 的 餐厅 吃了 饭"
 ↑________________________________________↓
        RNN 读到"饭"时，"我"的信息已经很模糊了
```

Transformer 一次看整句，每个词都和其他所有词建立联系：

```
"我 今天 在 一家 很 好吃 的 餐厅 吃了 饭"
  ↕   ↕   ↕   ↕   ↕   ↕   ↕   ↕   ↕   ↕
每个词都和所有词互相关联
```

所以 Transformer 能理解「**很**好吃」中的「很」修饰的是「好吃」，而不是「餐厅」。这靠的是**注意力分数**——每个词对其他词的关注程度。

### 3.2 Positional Encoding（位置编码）：记住顺序

Self-Attention 不关心词的位置（「猫追狗」和「狗追猫」对它来说一样）。位置编码给每个位置加一个独特的信号，让模型知道谁在前谁在后。

### 3.3 Multi-Head Attention（多头注意力）：多个视角

不是「一个注意力」在看，而是「8 个头」同时从不同角度关注：

- 头 1：关注语法关系（主语-谓语）
- 头 2：关注指代（「它」指谁）
- 头 3：关注修饰关系（形容词-名词）

---

## 四、GPT 怎么生成下一个字：自回归

GPT 全称 **G**enerative **P**re-trained **T**ransformer。它的工作机制叫「自回归」：

```
输入："今天天气"  →  GPT 预测下一个 Token → "真"
输入："今天天气真" →  GPT 预测下一个 Token → "好"
输入："今天天气真好" →  GPT 预测下一个 Token → "！"
```

每次只生成一个 Token，生成的 Token 会被拼到输入里，再预测下一个。这就是为什么它叫「生成式」——一个字一个字地「生」出来。

> 这也是为什么你看到 ChatGPT 一个字一个字往外蹦——不是网速慢，是它真的在逐 Token 生成。

---

## 五、Context Window：LLM 的「视野」

LLM 能同时「看到」的前文长度有限，这个限制就是 **Context Window（上下文窗口）**。

| 模型 | Context Window | 相当于 |
|------|:--:|------|
| GPT-4 | 128K Token | ~300 页书 |
| Claude 3.5 Sonnet | 200K Token | ~500 页书 |
| DeepSeek V3 | 128K Token | ~300 页书 |
| GPT-3.5 (2022) | 4K Token | ~10 页书 |
| 人类 | 约 7±2 个信息块 | 一顿饭前的事 |

### 超出窗口会怎样？

LLM 会「失忆」——最前面的对话被丢弃。这解释了为什么和 ChatGPT 聊久了，它开始胡说八道或者忘记你之前的要求。

### Agent 开发中的影响

```
对话第 1 轮：80 Token
对话第 2 轮：160 Token
对话第 3 轮：240 Token（× 10 轮 = 2400 Token）
+ 系统提示：500 Token
+ RAG 检索文档：3000 Token
+ 工具返回：2000 Token
──────────────────────────
总计：~8000 Token / 次查询

128K Context Window 看起来很大，但多轮对话 + 文档 + 工具返回
→ 很快用满
```

> **解决方案**：对话摘要（Summarization）、滑动窗口、分层记忆。这些在第 8 周「Agent 记忆系统」中详细讲。

---

## 六、Temperature 和 Top-p：控制「多大胆」

### Temperature（温度）：控制随机性

| Temperature | 效果 | 适用场景 |
|:----------:|------|------|
| 0 | 每次输出完全一样 | 代码生成、数学计算 |
| 0.3-0.5 | 稳定、可预测 | 客服、FAQ 回答 |
| 0.7-1.0 | 有创意、多样 | 写作、头脑风暴 |
| 1.5+ | 随机乱说 | 不建议 |

```python
# 同一个问题，不同 Temperature 的输出差异

# Temperature = 0（每次完全一样）
# "建议使用索引优化、查询重写和数据库分片来提升性能。"

# Temperature = 1.5（放飞自我）
# "哦我的朋友，数据库就像一匹野马，你要用缰绳（索引）和鞭子（缓存）..."
```

> **原理**：Temperature 控制概率分布的「平滑度」。T=0 时只选概率最高的 Token；T 越高，低概率 Token 也有机会被选中。

### Top-p（核采样）

只从「累积概率达到 p」的候选 Token 中随机选。p=0.9 意味着只考虑前 90% 概率的 Token。

> **实战建议**：调一个参数就好。代码类 T=0，对话类 T=0.7，其他用默认。

---

## 七、用一个完整例子串起来

假设你问：「帮我写一个 Python 排序函数，加注释」

```
1. Tokenization
   "帮我写一个 Python 排序函数，加注释" 
   → [57668, 239, 163, 234, 102, 8493, 1122, ...] (15 个 Token)

2. Embedding
   每个 Token → 几千维向量

3. Transformer 处理
   Self-Attention 理解："排序函数"和"注释"是修饰关系
   多层堆叠（GPT-4 有 120 层）逐层抽象

4. 自回归生成
   逐 Token 输出：
   "def" → " " → "sort" → "(" → "arr" → ":" → ...

5. Temperature = 0（代码任务）
   每次都选最高概率的 Token
   保证代码一致性和正确性
```

---

## 八、生产实战：你没在文档里见过的坑

### 8.1 Token 成本快速算

假设你每天让 Agent 处理 50 个用户请求，每个请求平均 3 轮对话：

```
单次请求 Token 消耗：
  System Prompt:  500 Token
  用户问题:        200 Token
  RAG 检索结果:    3000 Token
  LLM 回答:        800 Token
  ─────────────────────────
  单次:           4500 Token

日消耗：50 × 3 × 4500 = 675,000 Token
月消耗：675,000 × 30 ≈ 2000 万 Token

费用对比（2026 年 5 月）：
  DeepSeek V3:  2000万 × ¥0.001/千 = ¥20/月   ← 便宜
  Claude Sonnet: 2000万 × $3/百万 = $60/月     ← 中等
  GPT-4o:       2000万 × $5/百万 = $100/月     ← 贵
```

> **实战经验**：Agent 开发初期用 DeepSeek 跑通流程，上线后根据任务复杂度选择——简单任务 DeepSeek，复杂推理切 Claude。混合模型策略能省 60-70% 成本。

### 8.2 Context Window 满了会发生什么——真实事故

一个 Agent 跑了 30 轮对话后开始「精神分裂」：忘记自己的 System Prompt、重复执行已完成的任务、甚至输出和当前话题完全无关的内容。

根因：对话历史 + RAG 文档 + 工具返回 > Context Window，LLM 自动截断了最前面的 System Prompt 和早期对话。

```python
# 生产环境的上下文管理策略
def manage_context(messages: list, max_tokens: int = 100000) -> list:
    """防止上下文溢出"""
    total = estimate_tokens(messages)
    
    if total <= max_tokens:
        return messages
    
    # 策略 1：保留 System Prompt（最重要的）
    system_msgs = [m for m in messages if m["role"] == "system"]
    
    # 策略 2：对早中期对话做摘要
    early_msgs = messages[len(system_msgs):len(messages)//2]
    summary = summarize_conversation(early_msgs)
    
    # 策略 3：保留最近的对话（最相关）
    recent_msgs = messages[len(messages)//2:]
    
    return system_msgs + [{"role": "system", "content": f"对话摘要：{summary}"}] + recent_msgs
```

> 我在生产环境的经验是：**设一个 Token 预算告警阈值（比如 80% Context Window），触发时自动压缩早期对话。** 等到满了再处理就晚了。

### 8.3 为什么同一个 Prompt，有时好有时坏

LLM 本质上是概率模型。Temperature=0 也不能保证 100% 可复现。两个原因：

1. **GPU 浮点运算的非确定性**：同一计算在不同 GPU 上可能产生微小差异，累积后影响 Token 选择
2. **Provider 端可能修改了推理参数**：API 背后可能有负载均衡、模型热更新

```python
# 生产环境做稳定性测试
import statistics

def test_prompt_stability(prompt: str, n: int = 5) -> dict:
    """同一个 Prompt 跑 n 次，看输出稳定性"""
    outputs = []
    for _ in range(n):
        response = llm.chat([{"role": "user", "content": prompt}])
        outputs.append(response)
    
    # 检查输出长度方差
    lengths = [len(o) for o in outputs]
    
    # 如果输出长度标准差 > 均值的 20%，说明不够稳定
    if statistics.stdev(lengths) > statistics.mean(lengths) * 0.2:
        print("⚠️ Prompt 输出不够稳定，建议加更多约束")
    
    return {"outputs": outputs, "length_std": statistics.stdev(lengths)}
```

### 8.4 模型选型：不是越贵越好

| 任务类型 | 推荐模型 | 理由 |
|---------|---------|------|
| 代码生成 | Claude Sonnet / DeepSeek V3 | 代码能力强，性价比高 |
| 代码审查 / 复杂重构 | Claude Opus | 推理深度够 |
| 中文问答 / 摘要 | DeepSeek V3 / Qwen3-Max | 中文理解好 |
| JSON 结构化输出 | GPT-4o / DeepSeek V3 | JSON mode 稳定 |
| 超长文档分析 | Gemini 2.5 Pro (1M context) | Context Window 最大 |
| 成本敏感场景 | DeepSeek V3 | 白菜价 |

> 一个真实案例：代码审查 Agent 用 Claude Opus 每月烧 $200，换成「Sonnet 审查 + Opus 复核关键文件」后降到 $60，审查质量基本一致。

### 8.5 调试 Token 级别的问题

```python
# 用 logprobs 看 LLM 为什么不按你想要的输出
response = client.chat.completions.create(
    model="deepseek-chat",
    messages=[...],
    logprobs=True,       # 返回每个 Token 的概率
    top_logprobs=3       # 返回 Top-3 候选 Token 及其概率
)

# 如果某个 Token 的概率最高但也不到 30%，说明 LLM 很犹豫
# → 你的 Prompt 不够明确，需要加约束
for token_info in response.choices[0].logprobs.content:
    print(f"Token: {token_info.token}")
    for alt in token_info.top_logprobs:
        print(f"  候选: {alt.token} ({alt.logprob:.2%})")
```

---

## 九、关键面试题

**Q1：Token 和字有什么区别？**

Token 是 LLM 处理的最小单位。中文 1 个字可能占 1-2 Token，英文 1 个单词通常 1 Token。API 按 Token 计费。

**Q2：生产环境怎么管理 Context Window？**

三个策略：① System Prompt 永远不截断；② 早期对话自动摘要压缩；③ 设 Token 预算告警（80% 触发）。不能等满了再处理。

**Q3：如何降低 Token 成本？**

混合模型策略——简单任务用便宜模型（DeepSeek），复杂推理用强模型（Claude）。50% 的 Agent 请求其实不需要最强模型。

**Q4：Temperature=0 能保证输出一致吗？**

不能。GPU 浮点非确定性 + Provider 端可能的模型更新会导致差异。生产环境需要监控输出稳定性。

---

> 下一篇：**《Prompt Engineering 实战：System Prompt、Few-shot、思维链一次性讲透》**——写好 Prompt 是 Agent 开发的第一步。好的 System Prompt 值 100 行代码。

*系列文章：00-总纲 → ①-LLM 原理 → ②-Prompt 工程 → ③-Function Calling → ④-RAG 实战 → ⑤-Agent 模式 → ⑥-LangGraph → ⑦-MCP → ⑧-Multi-Agent*
