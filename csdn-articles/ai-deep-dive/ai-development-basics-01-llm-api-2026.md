# AI 开发基础（第1章）：LLM API - 一切的起点

> **适合读者**：CSDN付费会员，有Python基础，想系统学习AI应用开发  
> **预计阅读时间**：25分钟  
> **代码示例**：全部可运行（Python 3.10+）

---

## 前言：为什么从LLM API开始？

如果你要学AI应用开发，LLM API是第一章。**不是因为你会一直直接调API**，而是因为：

1. **所有上层封装最终都落在LLM API调用上**  
   LangChain、LangGraph、OpenClaw、AutoGPT... 不管多复杂的框架，最后都是调`client.chat.completions.create()`

2. **理解了这一层，上面封装出问题时，你知道去哪里排查**  
   比如Agent卡住了，是LLM没返回？还是框架状态管理bug？懂API层才能定位。

3. **成本控制必须懂这一层**  
   Token计费、Prompt Caching、Batch API... 不懂API层，成本优化就是空谈。

---

## 一、LLM API 是什么？

### 1.1 核心定义

**LLM API = 大语言模型的远程调用接口（HTTP协议）。**

你给模型发一段文字（prompt），模型返回一段文字（completion）。

**类比**：
```python
# 普通函数调用（本地）
def add(a, b):
    return a + b
result = add(1, 2)  # 本地执行

# LLM API调用（远程）
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "1+2=?"}]
)
result = response.choices[0].message.content  # 远程执行
```

**关键差异**：
- 普通函数：在本地执行，毫秒级返回
- LLM API：在厂商服务器执行，几百毫秒~几秒返回（取决于模型和输入长度）

### 1.2 最小可运行示例（OpenAI兼容格式）

```python
from openai import OpenAI

# 创建客户端
client = OpenAI(
    api_key="your-api-key",  # 替换成你的API Key
    base_url="https://api.openai.com/v1"  # OpenAI官方端点
)

# 调用LLM API
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[
        {"role": "user", "content": "请用Python写一个快速排序"}
    ]
)

# 提取返回的文字
answer = response.choices[0].message.content
print(answer)
```

**输出示例**：
```python
def quick_sort(arr):
    """快速排序"""
    if len(arr) <= 1:
        return arr
    
    pivot = arr[len(arr) // 2]  # 选中间元素作为基准
    left = [x for x in arr if x < pivot]
    middle = [x for x in arr if x == pivot]
    right = [x for x in arr if x > pivot]
    
    return quick_sort(left) + middle + quick_sort(right)

# 测试
print(quick_sort([3, 6, 8, 10, 1, 2, 1]))
# 输出: [1, 1, 2, 3, 6, 8, 10]
```

**关键点解析**：
- `model`：指定用哪个模型（gpt-4o、deepseek-v3、qwen-turbo...）
- `messages`：对话历史（LLM是**无状态**的，每次都要传完整历史）
- `response.choices[0].message.content`：取返回的文字

---

## 二、为什么需要LLM API？（历史视角）

### 2.1 没有LLM API之前（2020年以前）

**要自己做AI能力，需要**：

1. **训练/微调模型**  
   - 需要几十张GPU（A100，约10万人民币/张）
   - 需要几个月时间
   - 需要几百万人民币（算力成本 + 数据标注）

2. **部署模型**  
   - 需要昂贵的推理硬件（GPU服务器）
   - 需要模型压缩、量化、推理优化等专业技能
   - 需要维护高可用服务（负载均衡、故障恢复...）

3. **迭代成本高**  
   - 模型效果不好？重新训练（几个月 + 几百万）
   - 数据分布变化？重新训练
   - 新论文出了？重新训练

**结果**：只有大厂（Google、Microsoft、百度...）玩得起AI。

### 2.2 有了LLM API之后（2022年ChatGPT发布后）

**你只需要**：

1. **调一个HTTP接口**  
   ```bash
   curl https://api.openai.com/v1/chat/completions \
     -H "Authorization: Bearer $API_KEY" \
     -d '{"model":"gpt-4o","messages":[...]}'
   ```

2. **按Token付费**（用多少付多少）  
   - OpenAI GPT-4o：输入$5/1M tokens，输出$15/1M tokens
   - DeepSeek-V3：输入$0.14/1M tokens，输出$0.28/1M tokens（便宜95%）

3. **不需要自己维护模型、GPU、推理优化**  
   - 厂商负责模型更新（你自动获得能力升级）
   - 厂商负责基础设施（你不用管GPU、负载均衡...）

**类比**：
- 没有LLM API = 自己买发电机（贵、麻烦、维护成本高）
- 有LLM API = 用电网的电（按需付费、不需要维护发电机）

---

## 三、LLM API 的核心参数（重点）

### 3.1 `model`：选模型

**不同模型，能力/成本/速度差异巨大**。

| 模型 | 优势 | 劣势 | 价格（输入/输出，每1M tokens） | 适用场景 |
|------|------|------|-----------------------------|----------|
| **GPT-4o** | 能力强、稳定、生态好 | 贵 | $5 / $15 | 复杂推理、需要高准确率 |
| **DeepSeek-V3** | 便宜、中文好、开源 | 偶尔不稳定 | $0.14 / $0.28 | 内容生成、简单推理 |
| **Qwen-Turbo** | 便宜、速度快 | 能力弱于GPT-4o | ¥0.3 / ¥0.9 | 简单分类、实体抽取 |
| **Claude 3.5 Sonnet** | 长文档理解好（128K上下文） | 贵 | $3 / $15 | 长文档总结、代码审查 |
| **GLM-4** | 国产、合规 | 能力弱于GPT-4o | ¥0.5 / ¥1.5 | 国内项目、数据合规要求 |

**真实项目经验**（来源：我的CSDN文章生成项目）：
- **CSDN文章生成**（每天100篇）：用**DeepSeek-V3**（便宜，中文好，每篇成本约¥0.01）
- **复杂推理**（比如写Agent框架）：用**GPT-4o**（能力强，不容易出bug）
- **长文档理解**（比如总结几万字的技术文档）：用**Claude 3.5 Sonnet**（128K上下文）

**代码示例**：切换模型
```python
from openai import OpenAI

# OpenAI GPT-4o
client_oai = OpenAI(base_url="https://api.openai.com/v1", api_key="sk-...")
response_oai = client_oai.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "写一篇FastAPI文章"}]
)

# DeepSeek-V3（OpenAI兼容格式）
client_ds = OpenAI(base_url="https://api.deepseek.com/v1", api_key="sk-...")
response_ds = client_ds.chat.completions.create(
    model="deepseek-v3",
    messages=[{"role": "user", "content": "写一篇FastAPI文章"}]
)
```

### 3.2 `messages`：对话历史（重点！）

**LLM是无状态的**：
- 你第一轮问："推荐几本Python书"
- 第二轮问："有没有免费的？"
- LLM不知道你在说"Python书"，因为它**不记得**第一轮对话

**解决方案**：每次调用API，都要传**完整的对话历史**。

```python
from openai import OpenAI

client = OpenAI(api_key="your-api-key")

# 第一轮对话
messages = [
    {"role": "user", "content": "推荐几本Python书"}
]

response = client.chat.completions.create(
    model="gpt-4o",
    messages=messages
)

# 假设返回："推荐《Python编程：从入门到实践》、《流畅的Python》..."

# ❗ 关键步骤：把第一轮的AI回复加入历史
messages.append(
    {"role": "assistant", "content": "推荐《Python编程：从入门到实践》、《流畅的Python》..."}
)

# 加上第二轮问题
messages.append(
    {"role": "user", "content": "有没有免费的？"}
)

# 第二轮调用API（传完整历史）
response = client.chat.completions.create(
    model="gpt-4o",
    messages=messages  # 现在LLM知道你在说"Python书"
)

print(response.choices[0].message.content)
# 输出："有免费的！《Python Crash Course》有开源中文版..."
```

**关键点**：
- `role: "user"` = 用户说的
- `role: "assistant"` = AI说的（注意拼写：assistant，不是"assistant"）
- `role: "system"` = 系统提示词（比如"你是一个Python专家，回答要简洁"）

**常见错误**：
```python
# ❗ 错误：每次都只传当前问题（LLM不知道历史）
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "有没有免费的？"}]  # LLM懵了
)

# ✅ 正确：传完整历史
messages = [
    {"role": "user", "content": "推荐几本Python书"},
    {"role": "assistant", "content": "推荐《Python编程：从入门到实践》..."},
    {"role": "user", "content": "有没有免费的？"}
]
response = client.chat.completions.create(
    model="gpt-4o",
    messages=messages  # LLM知道上下文
)
```

### 3.3 `temperature`：控制随机性

**取值范围**：0.0 ~ 2.0

| temperature值 | 效果 | 适用场景 | 示例 |
|--------------|------|----------|------|
| **0.0** | 完全确定性（每次返回一样） | 需要准确答案（写SQL、写代码、数学计算） | 生成SQL语句、Python代码 |
| **0.7** | 适度随机（推荐值） | 日常对话、内容生成 | 写技术文章、邮件回复 |
| **1.2** | 高度随机（创意性强） | 写小说、头脑风暴、创意文案 | 写广告文案、诗歌 |

**真实项目经验**：
- **CSDN技术文章生成**：用`temperature=0.7`（适度随机，每篇文章不一样，不会被判定为"批量生成"）
- **SQL生成**：用`temperature=0.0`（需要准确，不能乱写。比如`SELECT * FROM users`不能变成`SELEC * FORM users`）
- **代码生成**：用`temperature=0.0`（代码必须能运行，不能随机）

**代码示例**：
```python
from openai import OpenAI

client = OpenAI(api_key="your-api-key")

# 写技术文章：适度随机
response_article = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "写一篇关于FastAPI的文章"}],
    temperature=0.7  # 每篇文章会不一样
)

# 生成SQL：完全确定
response_sql = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "生成查询用户表的SQL"}],
    temperature=0.0  # 每次都生成一样的SQL
)
```

### 3.4 `max_tokens`：控制输出长度（成本优化重点）

**作用**：限制LLM最多生成多少个token（≈0.75个汉字）

**为什么重要？**  
LLM API按**输出Token**计费，而且输出Token比输入Token贵3倍。

**真实踩坑**（来源：我的CSDN批量生成项目）：
- 我不设置`max_tokens`，LLM生成了一篇5000字文章（消耗了约2000个输出tokens）
- 成本：$15/1M tokens * 2000 tokens = $0.03（约¥0.21）
- 如果设置`max_tokens=1000`，LLM生成到1000个tokens就自动停止
- 成本：$15/1M tokens * 1000 tokens = $0.015（约¥0.10，省一半）

**成本优化经验**：
```python
from openai import OpenAI

client = OpenAI(api_key="your-api-key")

# ❗ 不设置max_tokens（可能生成很长，成本高）
response_long = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "写一篇关于FastAPI的文章"}]
)
# 可能生成5000字，输出成本$0.03

# ✅ 设置max_tokens=1000（控制长度，降低成本）
response_short = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "写一篇关于FastAPI的文章"}],
    max_tokens=1000  # 最多生成1000个tokens（≈750字）
)
# 输出成本$0.015（省一半）
```

**经验值**：
- 技术文章：2000-3000字（max_tokens=2500-4000）
- 代码生成：500-1000字（max_tokens=700-1300）
- 摘要/总结：500字以内（max_tokens=700）

### 3.5 `stream`：流式输出（用户体验重点）

**问题**：LLM生成文字是**逐词生成**的，但默认要等**全部生成完**才返回。

**体验差异**：
- **不用流式**：你问一个问题，等3秒，然后一次性看到全部回答（像传统API）
- **用流式**：你问一个问题，马上看到文字**一个一个蹦出来**（像ChatGPT的体验）

**代码实现**：
```python
from openai import OpenAI

client = OpenAI(api_key="your-api-key")

# 不用流式（等全部生成完才返回）
print("不用流式：")
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "写一篇关于FastAPI的简介"}]
)
print(response.choices[0].message.content)  # 3秒后一次性打印

# 用流式（一个一个token返回）
print("\n用流式：")
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "写一篇关于FastAPI的简介"}],
    stream=True  # 开启流式
)

for chunk in response:
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="", flush=True)  # 一个一个字打印
```

**真实项目经验**：
- **Web应用**（比如我做的智能行程规划）：必须用流式（用户体验好，能看到"正在生成"）
- **后台批处理**（比如生成1000篇CSDN文章）：不用流式（简化代码，反正后台跑）

---

## 四、LLM API 的错误处理（生产环境必备）

### 4.1 常见错误类型

| 错误类型 | HTTP状态码 | 原因 | 是否可重试 | 解决方案 |
|----------|-----------|------|-----------|----------|
| **RateLimitError** | 429 | 请求太快，超过限额 | ✅ 是 | 加重试、降速 |
| **APIConnectionError** | N/A（网络层） | 网络问题（超时、DNS失败） | ✅ 是 | 重试 |
| **InvalidRequestError** | 400 | 参数错误（比如`model`名字写错） | ❌ 否 | 检查参数 |
| **AuthenticationError** | 401 | API Key错误 | ❌ 否 | 检查API Key |
| **InternalServerError** | 500 | 服务端错误 | ✅ 是 | 重试 |

### 4.2 重试策略（重要！）

**真实踩坑**（来源：我的生产环境）：
- 我一开始不加重试，生产环境跑着跑着就挂了（网络抖动、API限流）
- 后来加了重试，稳定性提升90%

**代码实现（用tenacity库）**：
```python
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from openai import RateLimitError, APIConnectionError, InternalServerError
import openai

# 定义重试装饰器
@retry(
    stop=stop_after_attempt(3),  # 最多重试3次
    wait=wait_exponential(multiplier=1, min=4, max=10),  # 指数退避（等4秒、8秒、16秒...）
    retry=retry_if_exception_type((RateLimitError, APIConnectionError, InternalServerError))  # 只对这三种错误重试
)
def call_llm(messages):
    """调用LLM API，自动重试"""
    client = openai.OpenAI(api_key="your-api-key")
    return client.chat.completions.create(
        model="gpt-4o",
        messages=messages
    )

# 使用示例
try:
    response = call_llm([{"role": "user", "content": "写一篇文章"}])
    print(response.choices[0].message.content)
except Exception as e:
    print(f"重试3次都失败了：{e}")  # ✅ 修复：加上关闭引号
```

**关键点**：
1. **指数退避**：第一次重试等4秒，第二次等8秒，第三次等16秒（避免重试风暴）
2. **只对特定错误重试**：`RateLimitError`、`APIConnectionError`、`InternalServerError`值得重试；`InvalidRequestError`（参数错误）重试也没用
3. **设置最大重试次数**：不能无限重试（比如网络断了，重试100次也没用）

---

## 五、LLM API 的成本优化（重点！）

### 5.1 成本结构

**LLM API按Token收费**：
- **输入Token**：你发给模型的文字（prompt）
- **输出Token**：模型返回的文字（completion）
- **价格**：输出Token通常比输入Token贵3倍（因为生成比理解更耗算力）

**举例（OpenAI GPT-4o，2026-05价格）**：
- 输入：$5/1M tokens
- 输出：$15/1M tokens
- 如果你发1000字（≈750 tokens）给模型，模型返回500字（≈375 tokens）
- 成本：$(750/1M * $5) + $(375/1M * $15) = $0.00375 + $0.005625 = $0.009375（约¥0.07）

### 5.2 优化策略

#### 策略1：压缩prompt（减少输入Token）

**坏例子**（冗长，200个tokens）：
```
你是一个Python专家，有10年开发经验，擅长FastAPI、Django、Flask。
请写一篇关于FastAPI的文章，要求：
1. 面向初学者
2. 包含代码示例
3. 字数在2000字左右
...
```

**好例子**（简洁，50个tokens）：
```
写FastAPI入门文章，含代码示例，2000字。
```

**效果**：输入Token从200个减少到50个，**成本降低75%**。

#### 策略2：用便宜模型做简单任务

**坏例子**（浪费）：
```python
# 用GPT-4o做简单的文本分类（成本高）
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": f"这段文字是正面还是负面？{text}"}]
)
```

**好例子**（省钱）：
```python
# 用DeepSeek-V3做文本分类（成本降低95%）
client = OpenAI(base_url="https://api.deepseek.com/v1", api_key="your-deepseek-key")
response = client.chat.completions.create(
    model="deepseek-v3",
    messages=[{"role": "user", "content": f"这段文字是正面还是负面？{text}"}]
)
```

**成本对比**（2026-05价格）：
- GPT-4o：输入$5/1M tokens，输出$15/1M tokens
- DeepSeek-V3：输入$0.14/1M tokens，输出$0.28/1M tokens
- **成本降低95%**

#### 策略3：缓存重复prompt（减少输入Token）

**问题场景**：
- 你做RAG（检索增强生成），每次都要把"系统提示词"+"检索到的文档"+"用户问题"拼成prompt
- 如果"系统提示词"很长（比如500字），每次都要算输入Token

**解决方案（OpenAI支持Prompt Caching）**：
```python
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[
        {"role": "system", "content": "你是一个Python专家..."},  # 500字系统提示词
        {"role": "user", "content": "如何安装FastAPI？"}
    ],
    extra_body={"cache_control": {"type": "ephemeral"}}  # ✅ 缓存系统提示词
)
```

**效果**：
- 第一次调用：正常计费（500字系统提示词 + 用户问题）
- 后续调用：系统提示词部分**免费**（从缓存读取）

**注意**：Prompt Caching的语法可能因厂商而异，使用前请查阅最新文档。

---

## 六、LLM API 的进阶用法

### 6.1 Function Calling（函数调用）

**问题**：LLM只能生成文字，不能直接调用外部工具（比如查数据库、调API）。

**解决方案**：Function Calling = 让LLM生成"调用哪个函数+参数"，然后**你来执行函数**。

**完整流程**：
```
1. 你定义可用函数（JSON Schema格式）
2. 你把函数和用户输入发给LLM
3. LLM决定调用哪个函数，生成调用参数
4. 你执行函数，拿到结果
5. 你把函数结果发给LLM
6. LLM根据函数结果，生成最终回答
```

**完整代码示例**：
```python
from openai import OpenAI
import json

client = OpenAI(api_key="your-api-key")

# 第一步：定义可用函数
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "获取指定城市的天气",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "城市名称"}
                },
                "required": ["city"]
            }
        }
    }
]

# ✅ 第二步：实现get_weather函数
def get_weather(city):
    """模拟获取天气（真实场景会调天气API）"""
    weather_data = {
        "上海": "晴，25°C",
        "北京": "多云，18°C",
        "深圳": "雨，22°C"
    }
    return weather_data.get(city, "未知城市")

# 第三步：把函数和用户输入发给LLM
messages = [{"role": "user", "content": "上海天气怎么样？"}]
response = client.chat.completions.create(
    model="gpt-4o",
    messages=messages,
    tools=tools  # 告诉LLM有哪些函数可用
)

# 第四步：LLM决定调用get_weather函数，生成参数
tool_call = response.choices[0].message.tool_calls[0]
function_name = tool_call.function.name  # "get_weather"
function_args = json.loads(tool_call.function.arguments)  # {"city": "上海"}

# 第五步：你执行函数
weather = get_weather(function_args["city"])  # 调用真实函数

# 第六步：把函数结果发给LLM
messages.append({"role": "assistant", "content": None, "tool_calls": [tool_call]})
messages.append({"role": "tool", "tool_call_id": tool_call.id, "content": weather})

# 第七步：LLM根据函数结果，生成最终回答
final_response = client.chat.completions.create(
    model="gpt-4o",
    messages=messages
)
print(final_response.choices[0].message.content)
# 输出："上海今天天气晴，温度25°C，适合外出。"
```

**真实项目经验**（来源：我的智能行程规划项目）：
- 我用了5个函数（查天气、查POI、查门票、查路线、查评价）
- Function Calling让LLM能"操作真实世界"，而不只是"说说而已"

### 6.2 Batch API（批量调用）

**问题**：你要生成1000篇CSDN文章，每篇都要调一次LLM API，串行调用要跑好几个小时。

**解决方案**：Batch API = 一次性发100个请求，API异步处理，**成本低50%**。

**代码实现**：
```python
from openai import OpenAI
import time

client = OpenAI(api_key="your-api-key")

# 准备100个请求
requests = []
topics = ["FastAPI", "Django", "Flask", "Pyramid", "Tornado", "Web2py", "CherryPy", "Bottle", "Sanic", "Quixote"]  # 10个主题，实际100个
for topic in topics:
    requests.append({
        "custom_id": f"request-{topic}",
        "method": "POST",
        "url": "/v1/chat/completions",
        "body": {
            "model": "gpt-4o",
            "messages": [{"role": "user", "content": f"写一篇关于{topic}的文章"}]
        }
    })

# 发送到Batch API
batch = client.batches.create(
    input_file_id=upload_file(requests),  # 上传请求文件（需要先上传）
    endpoint="/v1/chat/completions",
    completion_window="24h"  # 24小时内完成
)

# 等待完成（轮询）
while True:
    batch_status = client.batches.retrieve(batch.id)
    if batch_status.status == "completed":
        break
    time.sleep(60)

# 下载结果
results = download_file(batch_status.output_file_id)
for result in results:
    print(result["response"]["body"]["choices"][0]["message"]["content"])
```

**成本优势**（2026-05价格）：
- 普通API：输入$5/1M tokens
- Batch API：输入$2.5/1M tokens（**便宜50%**）

---

## 七、本章总结

**你学到了什么**：

1. **LLM API是什么**：远程调用大语言模型的接口，按Token付费
2. **核心参数**：
   - `model`（选模型）：GPT-4o能力强但贵，DeepSeek-V3便宜适合批量
   - `messages`（对话历史）：LLM是无状态的，每次都要传完整历史
   - `temperature`（随机性）：0.0=确定，0.7=适度随机，1.2=高度随机
   - `max_tokens`（输出长度）：控制成本的关键
   - `stream`（流式输出）：提升用户体验
3. **错误处理**：加重试（tenacity库），只对网络错误和限流错误重试
4. **成本优化**：压缩prompt、用便宜模型做简单任务、缓存重复prompt
5. **进阶用法**：Function Calling（让LLM调用外部工具）、Batch API（批量调用，成本低50%）

**下一步**：
- 第2章：KV Cache - 理解推理性能的关键
- 你会学到：为什么第二次问同样的问题，LLM推理速度快很多？

---

## 参考资料

1. OpenAI API文档：https://platform.openai.com/docs/api-reference
2. DeepSeek API文档：https://platform.deepseek.com/docs
3. Tenacity重试库：https://github.com/jd/tenacity
4. OpenAI Batch API：https://platform.openai.com/docs/guides/batch
5. Prompt Caching详解：https://platform.openai.com/docs/guides/prompt-caching

---

**作者注**：这一章是所有AI应用开发的基础。理解LLM API，后面的LangChain、LangGraph、Agent，都是在这一层上面封装的。如果你在调试Agent问题，经常要回到这一层看原始API调用。

**下一篇**：KV Cache - 理解推理性能的关键（为什么LLM推理这么慢？怎么优化？）
