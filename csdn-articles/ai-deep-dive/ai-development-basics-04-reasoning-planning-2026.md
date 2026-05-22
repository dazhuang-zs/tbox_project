# AI 开发基础（第4篇）：Reasoning 与 Planning - 让模型"想清楚再动手"

> **适合读者**：已读完第3篇（Agent Loop），想让Agent处理更复杂的任务  
> **预计阅读时间**：35分钟  
> **代码示例**：全部可运行（Python 3.10+）

---

## 前言：为什么Agent需要"思考"？

第3篇的Agent有个问题：**它是一步一步试的。**

```
用户：帮我订北京到上海的机票，最便宜的，上午出发，国航或东航

没有推理能力的Agent：
  → 调用搜索机票API（参数可能传错）
  → 收到结果，发现不是最便宜的
  → 再调一次（参数又错了）
  → 反复试3-4次才对
```

**有推理能力的Agent**：
```
  → 先想：用户要求=北京→上海+最便宜+上午+国航/东航
  → 拆解成4个过滤条件
  → 一次调用API，传对参数
  → 直接拿到正确结果
```

**Reasoning（推理）**让模型"想清楚"，**Planning（规划）**让模型"安排好顺序"。两者结合，Agent才能处理复杂任务。

---

## 一、Reasoning：模型如何"思考"

### 1.1 两种思考模式

| 模式 | 特点 | 类比 |
|------|------|------|
| **System 1（快思考）** | 直觉、快速、不需要显式推理 | 你看到"2+3"直接答5 |
| **System 2（慢思考）** | 分析、分步、显式推理 | 你看到"237×418"需要一步步算 |

默认情况下，LLM用System 1。但复杂任务需要System 2。

### 1.2 Chain-of-Thought（思维链）

**核心思想**：让模型"把思考过程写出来"，再给出最终答案。

**不用CoT**：
```python
messages = [
    {"role": "user", "content": "一个旅馆有6层，每层12个房间。如果已经入住了78位客人，还有多少空房间？"}
]
```

**用CoT**：
```python
messages = [
    {"role": "user", "content": """一个旅馆有6层，每层12个房间。如果已经入住了78位客人，还有多少空房间？

请一步步思考。"""}
]
```

区别：加了一句"请一步步思考"。

**为什么有效？**

LLM生成Token是顺序的。不用CoT时，它从问题直接跳到答案，中间可能跳过关键步骤。用CoT后，它必须先生成推理过程（Token），推理过程本身成了额外的"上下文"，帮助后续Token生成更准确。

**实测对比**：

```python
import time
from openai import OpenAI

client = OpenAI(api_key="your-key", base_url="https://api.deepseek.com")

question = "小明有25个苹果，给了小红1/3，又买了8个，又给了小华总数的20%，最后还剩多少个？"

# 不用CoT
resp_no_cot = client.chat.completions.create(
    model="deepseek-chat",
    messages=[{"role": "user", "content": question}],
    temperature=0.0,
)
print(f"无CoT: {resp_no_cot.choices[0].message.content}")

# 用CoT
resp_cot = client.chat.completions.create(
    model="deepseek-chat",
    messages=[{"role": "user", "content": f"{question}\n\n请一步步计算。"}],
    temperature=0.0,
)
print(f"有CoT: {resp_cot.choices[0].message.content}")
```

**典型结果**：
- 无CoT：直接给答案（可能算错）
- 有CoT：25÷3≈8.33... → 25-8.33=16.67... → 16.67+8=24.67 → 24.67×0.8=19.73

CoT在数学、逻辑推理上的提升非常显著。

### 1.3 在Agent中使用CoT

**第3篇的Agent Loop + CoT**：

```python
system_prompt = """你是一个任务执行助手。

思考规则：
1. 收到用户需求后，先分析需求，拆解成子任务
2. 确定每个子任务需要调用哪个工具
3. 考虑子任务之间的依赖关系，安排执行顺序
4. 如果某个工具调用失败，思考替代方案
5. 完成所有子任务后，整合结果给出最终回复

请先在<think标签中写出你的思考过程，然后再调用工具或给出回复。"""

messages = [
    {"role": "system", "content": system_prompt},
    {"role": "user", "content": "帮我订北京到上海最便宜的上午机票，国航或东航"}
]

response = client.chat.completions.create(
    model="deepseek-chat",
    messages=messages,
    tools=tools,
)

# 检查LLM是否在回复中包含了思考过程
content = response.choices[0].message.content
if "<think" in content:
    print("LLM的思考过程已输出")
    # 实际项目中可以解析think标签，用于调试和审计
```

**效果**：Agent不再是"乱调工具"，而是先想清楚再动手，工具调用的准确率提升明显。

### 1.4 自我纠错（Self-Correction）

更强的推理能力：模型能发现自己之前的错误并修正。

```python
system_prompt = """你是一个严谨的分析助手。

工作流程：
1. 先给出初步答案
2. 然后检查答案是否正确
3. 如果发现错误，修正并给出最终答案
4. 如果没有错误，确认答案

输出格式：
- 初步分析：...
- 自检：...
- 最终答案：..."""

messages = [
    {"role": "system", "content": system_prompt},
    {"role": "user", "content": "一个项目预算100万，人力成本占60%，其中前端占人力30%，后端占50%，测试占20%。前端的具体预算是多少？"}
]
```

**输出示例**：
```
- 初步分析：总预算100万，人力成本=100×60%=60万，前端=60×30%=18万
- 自检：30%+50%+20%=100%，人力成本分配合理。60万×30%=18万，计算正确。
- 最终答案：前端预算18万。
```

**真实项目经验**：
在CSDN文章生成项目中，LLM有时会编造不存在的API参数。加上自我纠错提示后，它会先写出代码，然后"检查"一遍，发现编造的部分并标注"需要确认"。

---

## 二、Reasoning 模式对比

### 2.1 OpenAI o1/o3 的"内置推理"

2024年底开始，OpenAI推出了o系列模型（o1、o3），它们**内置了推理能力**，不需要你手动加"请一步步思考"。

```python
# o3模型：自动推理，不需要CoT提示
response = client.chat.completions.create(
    model="o3-mini",
    messages=[{"role": "user", "content": "237 × 418 = ?"}],
)
# o3内部会自动思考，输出直接是答案
```

**vs 手动CoT**：

| 对比项 | 手动CoT（普通模型+提示词） | 内置推理（o3等） |
|--------|------------------------|----------------|
| 推理质量 | 中等，依赖提示词质量 | 高，模型专门训练过 |
| 推理Token | 可见（在输出中） | 不可见（内部消耗） |
| 成本 | 低（只付输出Token） | 高（内部推理Token也计费） |
| 速度 | 快 | 慢（内部推理需要时间） |
| 适用场景 | 简单推理任务 | 复杂数学、编程、逻辑 |

### 2.2 DeepSeek-R1 的推理模式

DeepSeek也推出了推理模型，有两种模式：

```python
# 普通模式（快速，不推理）
response_normal = client.chat.completions.create(
    model="deepseek-chat",
    messages=messages,
)

# 推理模式（慢，强推理）
response_reasoner = client.chat.completions.create(
    model="deepseek-reasoner",
    messages=messages,
)
```

**真实项目中的选择策略**：

| 任务类型 | 推荐模型 | 原因 |
|---------|---------|------|
| 简单问答、聊天 | deepseek-chat | 快、便宜 |
| 数学计算、逻辑推理 | deepseek-reasoner | 推理准确 |
| 代码生成 | deepseek-chat + CoT | 性价比高 |
| 复杂分析、多步推理 | o3-mini 或 deepseek-reasoner | 推理质量优先 |

---

## 三、Planning：先想清楚再动手

### 3.1 ReAct：Reasoning + Acting

ReAct是目前最主流的Agent推理模式。核心思想：**每一步都先想（Reason），再执行（Act）。**

```
用户：北京有哪些值得去的博物馆？

Thought 1: 用户想了解北京的博物馆，我需要搜索北京的博物馆信息
Action 1: search_poi(keyword="博物馆", city="北京")
Observation 1: [故宫博物院、国家博物馆、首都博物馆...]

Thought 2: 搜索结果很多，用户可能需要了解每个博物馆的特色。我加上评分和简介信息。
Action 2: get_poi_detail(name="故宫博物院")
Observation 2: 故宫博物院，评分4.9，中国最大的古代文化艺术博物馆...

Thought 3: 我已经有了足够的信息，可以给用户推荐了。
Answer: 北京最值得去的博物馆推荐：...
```

**代码实现**：

```python
def run_react_agent(user_input: str, max_steps: int = 10):
    """ReAct模式Agent"""
    messages = [
        {"role": "system", "content": """你是一个ReAct风格的Agent。
每一步按以下格式输出：
Thought: 你的思考过程
Action: 工具名称(参数)
当你有足够信息时，输出：
Thought: 我已经收集到足够信息
Answer: 最终回复"""},
        {"role": "user", "content": user_input},
    ]
    
    for step in range(max_steps):
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            temperature=0.0,
        )
        
        content = response.choices[0].message.content
        messages.append({"role": "assistant", "content": content})
        
        print(f"\n[Step {step + 1}]")
        print(content)
        
        # 解析Action
        if "Answer:" in content:
            # 提取最终答案
            answer = content.split("Answer:")[-1].strip()
            return answer
        
        if "Action:" in content:
            # 解析工具调用
            action_line = content.split("Action:")[-1].strip()
            # 简单解析：tool_name(args)
            # 实际项目中用更健壮的解析方式
            tool_name, args_str = action_line.split("(", 1)
            args_str = args_str.rstrip(")")
            args = json.loads(args_str) if args_str else {}
            
            result = tool_map[tool_name](**args)
            
            # 将观察结果加入对话
            messages.append({"role": "user", "content": f"Observation: {result}"})
    
    return "达到最大步数限制"
```

### 3.2 Plan-and-Execute：先规划全部，再逐步执行

ReAct的问题是：**每步只看当前，不规划全局。** 如果任务有5个子任务，ReAct可能走弯路。

**Plan-and-Execute**：先一次性规划好所有步骤，再按顺序执行。

```python
def run_plan_execute_agent(user_input: str):
    """Plan-and-Execute模式Agent"""
    
    # 第1步：规划（Planning）
    plan_messages = [
        {"role": "system", "content": """你是一个任务规划专家。
分析用户需求，拆解成有序的步骤列表。
每步格式：步骤N: [工具名称] 描述
最后一步必须是：总结"""
        },
        {"role": "user", "content": f"帮我规划一个任务：{user_input}"}
    ]
    
    plan_response = client.chat.completions.create(
        model="deepseek-chat",
        messages=plan_messages,
        temperature=0.0,
    )
    
    plan = plan_response.choices[0].message.content
    print(f"📋 任务计划：\n{plan}\n")
    
    # 第2步：逐步执行（Execution）
    # （实际项目中这里需要解析plan，逐步调用工具）
    # 简化示例：直接用plan作为上下文，让Agent执行
    
    execute_messages = [
        {"role": "system", "content": f"""你是一个任务执行助手。按以下计划执行：
{plan}

每完成一步，输出进度和结果。如果某步失败，尝试替代方案。"""},
        {"role": "user", "content": "请开始执行计划。"}
    ]
    
    # 用Agent Loop执行（复用第3篇的代码）
    return run_agent_loop(execute_messages, tools, tool_map, max_rounds=10)
```

**对比**：

| 模式 | 优点 | 缺点 | 适用场景 |
|------|------|------|---------|
| **ReAct** | 灵活，可以中途调整 | 可能走弯路 | 探索性任务 |
| **Plan-and-Execute** | 全局最优，效率高 | 计划可能不准，不灵活 | 步骤明确的任务 |

### 3.3 实际项目中的选择

**智能行程规划助手**的经验：

- 第一版用ReAct，Agent经常"搜完景点就忘了查天气"
- 第二版改Plan-and-Execute，先列出"查天气→搜景点→搜餐厅→算路线→生成行程"的完整计划，再执行
- 最终方案：**混合模式**。简单任务用ReAct（如查个天气），复杂任务用Plan-and-Execute（如规划3天行程）

```python
def smart_agent(user_input: str):
    """根据任务复杂度自动选择推理模式"""
    
    # 先判断复杂度
    complexity_prompt = f"""判断以下任务的复杂度。
任务：{user_input}
如果任务需要3个以上步骤或有依赖关系，输出"complex"。
否则输出"simple"。
只输出一个词。"""
    
    judgment = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": complexity_prompt}],
        temperature=0.0,
    ).choices[0].message.content.strip()
    
    if "complex" in judgment:
        print("🔍 复杂任务，使用Plan-and-Execute模式")
        return run_plan_execute_agent(user_input)
    else:
        print("⚡ 简单任务，使用ReAct模式")
        return run_react_agent(user_input)
```

---

## 四、推理能力的量化评估

### 4.1 怎么知道推理有没有用？

**简单方法**：对比有推理和无推理的正确率。

```python
import json

def evaluate_reasoning(questions: list):
    """评估推理能力"""
    results = {"no_reasoning": [], "cot": [], "plan_execute": []}
    
    for q in questions:
        # 无推理
        resp1 = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": q["question"]}],
            temperature=0.0,
        )
        answer1 = resp1.choices[0].message.content
        
        # CoT
        resp2 = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": f"{q['question']}\n\n请一步步思考。"}],
            temperature=0.0,
        )
        answer2 = resp2.choices[0].message.content
        
        # 判断正确性（简化：检查是否包含预期答案）
        results["no_reasoning"].append(q["expected"] in answer1)
        results["cot"].append(q["expected"] in answer2)
    
    # 汇总
    total = len(questions)
    print(f"评测结果（共{total}题）：")
    print(f"  无推理正确率：{sum(results['no_reasoning'])/total*100:.0f}%")
    print(f"  CoT正确率：   {sum(results['cot'])/total*100:.0f}%")

# 示例评测
questions = [
    {"question": "小王有100元，买了3本书每本15元，又买了2支笔每支8元，还剩多少？", "expected": "46"},
    {"question": "一个水池有两个水管，A管6小时注满，B管4小时注满，两管同时开几小时注满？", "expected": "2.4"},
]
evaluate_reasoning(questions)
```

### 4.2 推理Token的成本

**推理不是免费的。** CoT的"思考过程"也要消耗Token。

| 场景 | 无CoT Token消耗 | 有CoT Token消耗 | 增加比例 |
|------|----------------|----------------|---------|
| 简单问答 | ~200 | ~500 | 150% |
| 数学题 | ~300 | ~1200 | 300% |
| 复杂分析 | ~500 | ~3000 | 500% |

**优化建议**：
- 简单任务不用CoT（省Token）
- 判断任务复杂度后再决定是否启用推理（见3.3节的smart_agent）
- 推理模型的内部Token也计费，注意控制使用场景

---

## 五、常见误区与最佳实践

### 5.1 误区

| 误区 | 真相 |
|------|------|
| "CoT总是有用的" | 简单任务加CoT反而增加延迟和成本，不提升准确率 |
| "推理模型一定比普通模型好" | 简单对话用推理模型是浪费钱，速度还慢 |
| "Plan-and-Execute总是最优" | 如果任务有不确定性，固定计划反而限制灵活性 |
| "CoT提示词越长越好" | 过长的提示词会占用上下文窗口，效果不一定更好 |

### 5.2 最佳实践

1. **先判断复杂度，再选择推理模式**
2. **CoT提示词要具体**：不要只说"思考"，要说"按以下步骤分析：1... 2... 3..."
3. **推理模型用于关键决策**：如代码审查、数据分析、方案评估
4. **普通模型用于日常任务**：如聊天、翻译、格式化
5. **混合模式最实用**：简单任务ReAct，复杂任务Plan-and-Execute

---

## 六、本章总结

**你学到了什么**：

1. **System 1 vs System 2**：LLM默认用快思考，复杂任务需要慢思考
2. **Chain-of-Thought**：让模型"写出思考过程"，简单有效，一个提示词就生效
3. **推理模型**：o3、DeepSeek-R1等内置推理能力，不需要手动CoT，但更贵更慢
4. **ReAct**：每步"先想再做"，适合探索性任务
5. **Plan-and-Execute**：先规划全局再执行，适合步骤明确的复杂任务
6. **混合模式**：根据任务复杂度自动选择推理策略，最实用

**关键公式**：
```
ReAct = Thought → Action → Observation → Thought → ... → Answer
Plan-and-Execute = Plan(全部步骤) → Execute(逐步) → Review
```

**下一篇预告**：
- 第5篇：Skills 与 MCP - Agent的能力扩展
- 你会学到：怎么把Agent的能力模块化、标准化，让不同模型复用同一套工具

---

## 参考资料

1. Chain-of-Thought论文：https://arxiv.org/abs/2201.11903
2. ReAct论文：https://arxiv.org/abs/2210.03629
3. Plan-and-Execute综述：https://arxiv.org/abs/2308.11439
4. Self-Correction in LLMs：https://arxiv.org/abs/2303.11351

---

**上一篇**：第3篇 Agent Loop 与 Tool Use  
**下一篇**：第5篇 Skills 与 MCP
