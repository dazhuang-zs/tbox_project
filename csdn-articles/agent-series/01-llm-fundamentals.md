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

## 八、关键面试题

**Q1：Token 和字有什么区别？**

Token 是 LLM 处理的最小单位。中文 1 个字可能占 1-2 Token，英文 1 个单词通常 1 Token。API 按 Token 计费。

**Q2：为什么 Context Window 越大越好？**

越大能处理的信息越多。但上下文管理同样重要——多轮对话、RAG 检索、工具返回都在消耗 Token。

**Q3：Temperature=0 和 Temperature=1 的区别？**

T=0 确定性强，每次输出一样，适合代码；T=1 有创造力，适合写作。本质是控制 Token 概率分布的平滑度。

---

> 下一篇：**《Prompt Engineering 实战：System Prompt、Few-shot、思维链一次性讲透》**——写好 Prompt 是 Agent 开发的第一步。好的 System Prompt 值 100 行代码。

*系列文章：00-总纲 → ①-LLM 原理 → ②-Prompt 工程 → ③-Function Calling → ④-RAG 实战 → ⑤-Agent 模式 → ⑥-LangGraph → ⑦-MCP → ⑧-Multi-Agent*
