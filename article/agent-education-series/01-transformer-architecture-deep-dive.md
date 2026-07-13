# 【AI Agent 系统教学 01】Transformer 架构深度拆解

> 想理解 Agent，先理解大模型；想理解大模型，先理解 Transformer。
> 这篇没有一行多余的代码，只有你真正需要知道的底层原理。

---

## 前言：为什么 Agent 学习要从 Transformer 开始？

2026 年，你随便打开一个 Agent 框架——OpenClaw、LangGraph、CrewAI——底层都在调用 LLM。而当前所有主流 LLM（GPT-4o、Claude 3.5、Llama 3、Qwen 2.5、DeepSeek V3）的架构核心，都是 **Transformer**。

这不是历史课。Transformer 的设计直接影响了你作为 Agent 开发者每天遇到的问题：

- **为什么上下文窗口有长度限制？** → 因为 Self-Attention 的计算复杂度是输入长度的平方
- **为什么 Agent 容易"记忆出错"？** → 因为 Attention 机制本身的注意力分散
- **为什么不同模型推理速度差这么多？** → 因为 KV Cache 和 Attention 的实现差异
- **为什么多轮对话会越聊越笨？** → 因为位置编码和上下文窗口的限制

不夸张地说：Transformer 的每一个设计决策，都在 Agent 开发中表现得淋漓尽致。

---

## 一、Transformer 之前：为什么需要它？

### 1.1 序列建模的三大难题

在 Transformer 出现之前（2017 年以前），处理序列数据的主力是 RNN（循环神经网络）和 LSTM。它们有三个硬伤：

| 问题 | 表现 | 后果 |
|------|------|------|
| **顺序计算** | 必须从左到右逐个处理 token | 无法并行，训练慢到怀疑人生 |
| **长距离依赖** | 距离超过 50 个 token，信息几乎消失 | 长文本理解能力极差 |
| **梯度问题** | 反向传播时梯度指数级消失/爆炸 | 训练不稳定，深了训不动 |

### 1.2 Transformer 的破局思路

Transformer 的核心思想可以用一句话概括：

> **把序列建模问题，变成注意力权重分配问题。**

不再沿着时间步逐个处理，而是让每个 token 直接"看"到所有其他 token，用注意力权重决定哪些信息重要。这就是"Transformer"这个名字的由来——它在**转换**（Transform）整个序列，而不是一步步遍历。

---

## 二、整体架构：一图看懂

Transformer 的架构图（来自原论文 "Attention Is All You Need"）分为左右两半：

```
                    ┌──────────────────────┐
                    │   Output Probabilities│
                    └──────────┬───────────┘
                               │
                    ┌──────────▼───────────┐
                    │      Softmax         │
                    └──────────┬───────────┘
                               │
                    ┌──────────▼───────────┐
                    │     Linear            │
                    └──────────┬───────────┘
                               │
          ┌────────────────────▼────────────────────┐
          │            Add & Layer Norm             │
          └────────────────────┬────────────────────┘
                               │
          ┌────────────────────▼────────────────────┐
          │         Feed Forward Network            │
          └────────────────────┬────────────────────┘
                               │
          ┌────────────────────▼────────────────────┐
          │            Add & Layer Norm             │
          └────────────────────┬────────────────────┘
                               │
          ┌────────────────────▼────────────────────┐
          │         Multi-Head Attention            │
          └────────────────────┬────────────────────┘
                               │
┌─────────▼─────────┐   ┌─────▼──────┐
│  Positional       │   │  Positional│
│  Encoding         │   │  Encoding  │
└─────────┬─────────┘   └─────┬──────┘
          │                    │
┌─────────▼─────────┐   ┌─────▼──────┐
│  Input Embedding  │   │  Output    │
│                   │   │  Embedding │
└─────────┬─────────┘   └─────┬──────┘
          │                    │
     Input Tokens         Output Tokens
```

**当代 LLM 实际用的是 Decoder-Only 架构**（右侧部分去掉 Cross-Attention）。GPT、Llama、Qwen、DeepSeek 都是 Decoder-Only。原因很简单：生成任务只需要自回归解码，不需要编码器去理解整个输入。

但不管 Encoder-Decoder 还是 Decoder-Only，核心组件完全相同：

1. **Embedding 层**：把 token 变成向量
2. **Positional Encoding**：告诉模型 token 的位置
3. **Multi-Head Self-Attention**：核心中的核心
4. **Feed-Forward Network**：非线性变换
5. **Layer Normalization + Residual Connection**：稳定训练

---

## 三、核心组件拆解

### 3.1 Embedding：从词到向量

模型不认识"猫"这个字，只认识数字。Embedding 做的就是这个翻译工作。

```
输入："猫追老鼠"
      ↓ Tokenizer 分词
["猫", "追", "老", "鼠"]
      ↓ 查表（可训练的 Embedding 矩阵）
[[0.12, 0.34, -0.56, ...],  // "猫" 的向量，768维
 [0.23, -0.45, 0.67, ...],  // "追" 的向量
 [-0.11, 0.89, -0.22, ...], // "老" 的向量
 [0.54, -0.33, 0.78, ...]]  // "鼠" 的向量
```

**关键理解**：Embedding 是**可训练的**。模型在训练过程中不断调整每个 token 的向量表示，让语义相近的词向量更接近（"猫"和"狗"的向量距离比"猫"和"法律"近）。

Embedding 维度（也叫 hidden_size 或 d_model）是 Transformer 最重要的超参数之一：
- 小模型（如 GPT-2 Small）：768 维
- 中模型（如 Llama 3 8B）：4096 维
- 大模型（如 GPT-4）：推测 8192 维以上

### 3.2 位置编码：给 token 装上 GPS

Attention 机制本身**没有顺序概念**。在 Self-Attention 中，"猫追老鼠"和"鼠追老猫"的计算结果完全一样——因为 Attention 只关心 token 之间的关联强度，不关心谁先谁后。

这显然不行。位置编码就是用来解决这个问题的。

**原始 Transformer（2017）：Sinusoidal 位置编码**

使用正弦和余弦函数生成固定位置向量，不需要训练：

```
PE(pos, 2i) = sin(pos / 10000^(2i/d_model))
PE(pos, 2i+1) = cos(pos / 10000^(2i/d_model))
```

效果：每个位置有一个唯一的"指纹"，而且任意位置的编码可以通过线性变换得到。

**当代主流：RoPE（Rotary Position Embedding）**

Llama、Qwen、DeepSeek 等模型全部使用 RoPE。它的核心思想是：

> **对 Attention 计算中的 Query 和 Key 向量做旋转，旋转角度由位置决定。**

位置越远，旋转角度越大，Query 和 Key 的点积自然衰减。这天然给了模型"距离越近的 token 越重要"的归纳偏置。

RoPE 为什么成为主流？
- 相对位置编码，可以泛化到训练时未见过的长度
- 可以配合 **NTK-aware** 等插值方法扩展到长上下文
- 计算效率高，不影响推理速度

**延伸阅读**：位置编码的选择直接决定了模型能否处理长上下文。GPT-4 的 128K 上下文、Claude 的 200K，背后都是位置编码的改进。

### 3.3 Scaled Dot-Product Attention：核心心脏

这是 Transformer 最核心的计算单元。公式看起来简单，但内涵极深：

```
Attention(Q, K, V) = softmax(Q × K^T / √d_k) × V
```

我们拆开来看每一步：

**Step 1: Q × K^T —— 计算相似度**

```
Q = Query（查询）："当前这个 token 在找什么"
K = Key（键）："每个 token 提供了什么"
```

举例：在处理"猫追老鼠"这句话时，模型在处理"老鼠"这个词时，会问：
- Q：与"老鼠"最相关的词是哪些？
- 对每个位置计算 Q·K： ("老鼠"·"猫") = 0.8, ("老鼠"·"追") = 0.6, ("老鼠"·"老") = 0.3, ("老鼠"·"鼠") = 1.0

**Step 2: √d_k —— 缩放**

为什么除以 √d_k？因为向量维度越高，点积的数值范围越大。如果不缩放，softmax 会进入梯度极小的区域，训练不动。

这是 Transformer 原论文的一个关键工程洞察。

**Step 3: softmax —— 归一化成概率**

```
softmax([0.8, 0.6, 0.3, 1.0]) = [0.27, 0.22, 0.16, 0.35]
```

**Step 4: × V —— 加权求和**

V = Value（值）："每个 token 实际提供的信息"

```
输出 = 0.27 × "猫" + 0.22 × "追" + 0.16 × "老" + 0.35 × "鼠"
```

**最终输出**：每个位置的输出都是所有位置信息的加权混合，权重由 Attention 分数决定。

**这就是"注意力"的全部秘密**：不是真的"关注"，而是加权平均。

### 3.4 Multi-Head Attention：分组并行看问题

单头 Attention 的问题是：**每个 token 只能有一个"注意力模式"**。

但实际中，一个词可能需要关注多种不同的信息：
- 语法关系："老鼠"是"追"的宾语
- 语义关系："老鼠"是"猫"的天敌
- 位置关系："老鼠"在句尾

Multi-Head Attention 的做法是：**把 Q、K、V 分别切分成 h 份，每份独立计算 Attention，然后拼接起来。**

```
输入: [768维]
     ↓ 切分成 12 个头
头1: [64维] → 独立 Attention → [64维]
头2: [64维] → 独立 Attention → [64维]
...
头12: [64维] → 独立 Attention → [64维]
     ↓ 拼接
输出: [768维]
```

**为什么 Multi-Head 有效？**

每个头可以学习不同的注意力模式：
- 头 1-3：关注语法关系（主谓宾）
- 头 4-6：关注语义关系（同义词、上下位）
- 头 7-9：关注位置关系（相邻词）
- 头 10-12：关注长距离依赖

**对 Agent 开发的启示**：当你给 Agent 提供很长的上下文时，不同的 Attention Head 在"争夺"注意力资源。如果上下文充满了无关信息，有用的信号可能被淹没。

### 3.5 Feed-Forward Network：每个位置独立思考

Attention 完成后，每个 token 的表示已经包含了上下文信息。接下来，**逐位置**通过一个两层的全连接网络：

```
FFN(x) = W2 × ReLU(W1 × x + b1) + b2
```

**关键理解**：
- Attention 是"token 之间的信息交换"
- FFN 是"每个 token 独立消化信息"

类比：Attention 是开会讨论（大家互相交换信息），FFN 是散会后各自回家思考（每个人独立处理得到的信息）。

FFN 在模型参数量中占比很大（约 2/3 的总参数），是模型"记住知识"的主要场所。这也是为什么专家混合（MoE）模型要在这里做文章——把 FFN 拆成多个专家网络，每次只激活一部分。

### 3.6 Layer Normalization + Residual Connection

**Residual Connection（残差连接）**：

```
output = Layer(input + Sublayer(input))
```

把输入直接加到子层的输出上。解决深度网络退化问题——让梯度可以直接流回浅层，让模型可以训练 100 层以上。

**Layer Normalization（层归一化）**：

对每个 token 的所有维度做归一化，让数值分布稳定在均值为 0、方差为 1 的范围内。

**Pre-Norm vs Post-Norm**：
- 原始 Transformer：Post-Norm（先子层再归一化）
- 当代模型（GPT、Llama）：Pre-Norm（先归一化再子层）
- Pre-Norm 训练更稳定，不需要 warmup 也能训

---

## 四、Encoder-Decoder vs Decoder-Only

### 4.1 架构对比

| 特性 | Encoder-Decoder | Decoder-Only |
|------|----------------|--------------|
| 代表模型 | T5、BART、早期 Transformer | GPT、Llama、Qwen、DeepSeek |
| 输入处理 | Encoder 双向注意力 | Decoder 单向（因果）注意力 |
| 输出生成 | Decoder 自回归 | 自回归 |
| 适合任务 | 翻译、摘要、分类 | 对话、生成、代码 |
| Agent 应用 | 极少 | 几乎所有 |

### 4.2 为什么 Agent 都用 Decoder-Only？

本质原因：**Agent 的任务是"持续生成"**，不是"理解后输出"。

Agent 的工作模式是：
1. 接收用户输入
2. 思考（内部推理）
3. 生成回复
4. 可能调用工具
5. 继续生成

这个循环天然是自回归的，Decoder-Only 完美匹配。Encoder-Decoder 需要先编码再解码，在多轮交互中需要重复编码，效率低。

### 4.3 因果注意力（Causal Attention）

Decoder-Only 的核心是因果注意力：**每个 token 只能看到自己和前面的 token，不能看到后面的。**

```
"猫追老鼠"
  ↓
"猫" → 只能看到 [猫]
"追" → 只能看到 [猫, 追]
"老" → 只能看到 [猫, 追, 老]
"鼠" → 能看到 [猫, 追, 老, 鼠]
```

实现方式：**Attention Mask**。把未来位置的 Attention 分数设为 -∞，softmax 后变为 0。

```
Attention Mask:
[猫, 追, 老, 鼠]
[1, 0, 0, 0]   "猫" 只看自己
[1, 1, 0, 0]   "追" 看猫和追
[1, 1, 1, 0]   "老" 看前三个
[1, 1, 1, 1]   "鼠" 看全部
```

**对 Agent 开发的意义**：Agent 的"思考过程"（Chain-of-Thought）就是利用因果注意力的特性——模型先生成思考过程的 token，这些 token 成为后续生成的上下文，一步步引导最终输出。

---

## 五、复杂度分析：为什么上下文窗口是"平方级"的

### 5.1 Attention 的计算复杂度

Self-Attention 的时间复杂度是 **O(n² × d)**，其中 n 是序列长度，d 是隐藏维度。

```
n = 4096（4K 上下文）
→ 需要计算 4096² = 16,777,216 个 Attention 分数

n = 32768（32K 上下文）
→ 需要计算 32768² = 1,073,741,824 个 Attention 分数
```

上下文长度翻 8 倍，计算量翻 64 倍。这就是为什么长上下文那么贵。

### 5.2 内存占用

不仅计算量大，Attention 的内存占用也是 O(n²)：
- 存储 Attention 分数矩阵：n × n × 2 字节（FP16）
- n=4096：约 32MB
- n=32768：约 2GB
- n=131072：约 32GB

### 5.3 缓解方案

| 方案 | 原理 | 代价 |
|------|------|------|
| Sparse Attention | 只计算部分 token 对 | 丢失长距离信息 |
| Sliding Window | 只关注附近 token | 丢失远程依赖 |
| Flash Attention | 不显式构建 Attention 矩阵 | 纯工程优化，无信息损失 |
| KV Cache | 复用已计算的 K、V | 线性空间换时间 |

Flash Attention 是当前最实用的方案，它通过分块计算和重计算，把显存占用从 O(n²) 降到 O(n)，速度也翻倍。几乎所有现代推理引擎都用了它。

---

## 六、从 Transformer 到 Agent

### 6.1 理解 Transformer 如何影响 Agent 设计

| Transformer 特性 | 对 Agent 的影响 |
|-----------------|----------------|
| 固定上下文窗口 | Agent 的"记忆"有限，需要外部记忆系统 |
| 注意力分散 | 上下文越长，Agent 越容易忽略关键信息 |
| 因果注意力 | Agent 的思考必然是线性的，无法并行思考 |
| 逐 token 生成 | Agent 的响应速度受限于 token 生成速度 |
| 位置编码 | Agent 对长对话的顺序敏感 |
| Attention 头分工 | 不同头关注不同维度，但资源有限 |

### 6.2 一个具体例子

为什么 Agent 在多轮对话中容易"忘记"前面的信息？

```
轮次 1: 用户说"帮我写一个 Python 爬虫"
轮次 10: 用户说"用之前那个爬虫，但改成异步版本"
```

从 Transformer 的角度看：
- 轮次 1 的信息在 Attention 中与轮次 10 的信息竞争
- 如果轮次 1-9 积累了 3000 个 token，轮次 10 的"异步"关键词需要从 3000+ 个 token 中"脱颖而出"
- 不同 Attention Head 可能被不同信息吸引，导致轮次 1 的细节被稀释

这就是为什么 Agent 需要 **显式的记忆管理** 和 **上下文压缩**，而不是依赖 Transformer 的注意力机制。

---

## 七、2026 年 Transformer 的进化方向

### 7.1 当前最新进展

| 方向 | 代表工作 | 核心改进 |
|------|---------|---------|
| **Attention 加速** | Flash Attention 3 | 利用 Hopper GPU 硬件特性，进一步降低显存 |
| **长上下文** | 通义千问 2.5（1M token）、Gemini 1.5（10M token） | 结合 RoPE 改进 + 稀疏注意力 |
| **MoE 架构** | DeepSeek V3、Mixtral 8x22B | 只激活部分参数，降低推理成本 |
| **线性注意力** | Mamba、RWKV | 完全替代 Attention，线性复杂度 |
| **推理优化** | Speculative Decoding、Medusa | 多个 token 同时预测，加速生成 |

### 7.2 Attention 会被替代吗？

Mamba（State Space Model）和 RWKV 这类替代方案，在长序列任务上展现出了潜力。但 2026 年的现状是：

- **Attention 在需要"精确检索"的任务上依然不可替代**——比如 Agent 需要从上下文中找到某个具体信息
- 线性注意力适合"全局理解"但精确性不足
- 主流趋势是 **混合架构**：Attention + SSM 的组合

对 Agent 开发者来说，短期内 Attention 依然是核心，但需要关注混合架构的发展。

---

## 总结

Transformer 的核心，就是把序列建模变成了注意力权重分配。从此，序列长度不再是模型能力的瓶颈——但计算量成了。

作为 Agent 开发者，你不需要重写 Attention，但需要理解：

1. **Agent 的所有问题都能在 Transformer 层面找到根源**（记忆、速度、上下文长度）
2. **Attention 的 O(n²) 复杂度决定了 Agent 的工程上限**
3. **位置编码的选择决定了 Agent 能处理多长的对话**
4. **因果注意力的线性特性决定了 Agent 的思考模式**

下一篇文章，我们将深入 LLM 的**预训练过程**，理解 Scaling Law、Chinchilla 最优计算，以及模型究竟是怎么"学会"知识的。

---

**思考题**：
1. 如果 Attention 不是唯一的"信息交换"机制，你还能想到哪些方式让 token 之间共享信息？
2. 为什么 Agent 的"记忆"不能完全依赖 Transformer 的上下文窗口？
3. Flash Attention 是怎么做到"不构建 Attention 矩阵"的？它的核心思路是什么？

---

> 下一篇：[02] 从 GPT 到 LLM：预训练与扩展定律
> 系列目录：[README.md](./README.md)