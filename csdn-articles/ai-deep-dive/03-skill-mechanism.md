# 强烈推荐收藏！AI Skill 机制全解：从 CLAUDE.md 到生产级 Skill——原理、边界、对比、实战一次讲透

> Claude Code 有个神奇的目录叫 `.claude`，里面放一个 `CLAUDE.md`，AI 的能力瞬间变强。OpenClaw 更进一步，用 `SKILL.md` 把一套指令+工具+知识打包成一个可复用的插件。这篇文章扒开 Skill 机制，从文件结构讲到加载机制，再对比 MCP Server 和 Function Calling，最后给你一个生产级 Skill 的完整写法。

---

## 一、起源：一条 CLAUDE.md 的进化史

### 1.1 最开始：往 System Prompt 塞东西

```python
System_Prompt = """
你是 Python 专家。
项目使用 FastAPI + SQLAlchemy + PostgreSQL。
代码风格：类型标注必须完整，函数必须有 docstring。
测试用 pytest，覆盖率不能低于 80%。
"""
```

问题很明显：System Prompt 越来越长，每次请求都得多烧几百 Token。更糟的是——**换一个项目，这些规则要全部重写。**

### 1.2 进化 1：CLAUDE.md —— 项目级指令文件

Claude Code 引入了 `.claude/CLAUDE.md`：

```markdown
# 项目背景
这是一个为 HarmonyOS 开发者提供 AI 辅助的工具。

## 技术栈
- 后端：Python 3.11 + FastAPI + Milvus
- 前端：Next.js 14 + TypeScript
- LLM：MiMo API 为主，DeepSeek 为备

## 代码规范
- 所有 API 接口必须有 Pydantic 模型
- 错误处理不能吞异常
- 数据库操作放 service 层，router 只做路由
```

Claude Code 在每次对话开始时自动加载这个文件，注入到上下文中。你不需要每次解释项目背景。

### 1.3 进化 2：SKILL.md —— 可复用的能力包

OpenClaw 把 CLAUDE.md 的思想推向下一层：

```
Skill = 指令（怎么用）+ 工具（能做什么）+ 知识（知道什么）
```

一个 Skill 是一个独立的目录，包含：

```
my-skill/
├── SKILL.md          # 核心：指令+知识+工具声明
├── scripts/          # 可执行脚本
│   └── deploy.sh
└── examples/         # 使用示例
    └── usage.md
```

---

## 二、原理：Skill 到底是什么

### 2.1 三层结构

```
                    Skill
                      │
    ┌─────────────────┼─────────────────┐
    ▼                 ▼                 ▼
  指令层             工具层             知识层
  (Instructions)    (Tools)          (Knowledge)
     │                 │                 │
  AI 的「人设」      能做什么          知道什么
  行为规范           可调用的脚本/API   领域知识/最佳实践
```

### 2.2 Skill 加载机制

```python
# Skill 加载的伪代码
class SkillLoader:
    def load(self, skill_dir: str) -> dict:
        skill = {}
        
        # 1. 解析 SKILL.md
        with open(f"{skill_dir}/SKILL.md") as f:
            skill["instructions"] = f.read()
        
        # 2. 发现可执行工具
        if os.path.exists(f"{skill_dir}/scripts"):
            skill["tools"] = self._scan_scripts(f"{skill_dir}/scripts")
        
        # 3. 加载示例和知识
        if os.path.exists(f"{skill_dir}/examples"):
            skill["examples"] = self._load_examples(f"{skill_dir}/examples")
        
        return skill
    
    def inject(self, skill: dict, system_prompt: str) -> str:
        """把 Skill 注入到 System Prompt"""
        return f"""
{system_prompt}

## 加载的 Skill: {skill['name']}
{skill['instructions']}

## 可用工具
{self._format_tools(skill['tools'])}
"""
```

> **核心机制**：Skill 不是一个运行时的插件系统，而是**在对话开始时把内容注入 System Prompt**。这是一种「编译时注入」而不是「运行时加载」。

---

## 三、Skill vs MCP Server vs Function Calling

这是最容易被混淆的地方：

| 维度 | Skill | MCP Server | Function Calling |
|------|-------|-----------|:--:|
| **是什么** | 指令 + 知识 + 工具声明 | 工具接入协议 | LLM 的推理能力 |
| **谁执行** | AI 按指令自己写代码/调工具 | 你的代码执行工具 | LLM 输出结构化调用 |
| **可复用性** | ✅ 跨项目复用 | ✅ 跨 AI 应用复用 | ❌ 每次重新定义 |
| **运行位置** | 上下文注入 | 独立进程 | LLM 内部 |
| **适合** | 领域知识 + 行为规范 | 外部 API/工具接入 | 单次工具调用 |
| **关系** | Skill 可以声明 MCP 工具 | MCP 给 Skill 提供工具能力 | MCP 底层的调用格式 |

```
一个完整的能力体系：

Skill（指令 + 知识）
  ├── 调用 Function Calling（让 LLM 自己选工具）
  └── 声明 MCP Server 连接（让外部服务提供工具）
         └── MCP Server 内部用 Function Calling 格式返回
```

---

## 四、实战：写一个生产级 Skill

### 4.1 场景：CSDN 文章发布 Skill

```markdown
# CSDN Article Publisher Skill

## 触发条件
当用户说「发文章」「发布到 CSDN」「推送到博客」时自动激活。

## 工作流程
1. 确认文章标题和内容已经准备好
2. 用 CSDN API 保存到草稿箱
3. 返回文章链接供用户预览
4. 用户确认后才正式发布

## 代码规范
- 使用项目已有的 `src/publish/service.py` 中的 publish 函数
- 不要重新实现 CSDN API 调用
- 文章内容必须用 Markdown 格式

## 安全规则
- 发布前必须让用户预览确认
- 不在用户不知情的情况下修改已发布文章
- 用户的 CSDN Cookie 不在日志中打印

## 示例
用户：帮我把这篇文章发到 CSDN
AI：好的，我先确认一下标题和内容... [展示预览] 确认发布吗？
```

### 4.2 Skill 的测试策略

```python
import pytest

def test_skill_triggers_on_keywords():
    """测试 Skill 在正确关键词下激活"""
    trigger_phrases = ["发文章", "发布到 CSDN", "推送到博客"]
    skill = load_skill("csdn-publisher")
    
    for phrase in trigger_phrases:
        assert skill.should_activate(phrase), f"应在 '{phrase}' 时激活"


def test_skill_respects_confirm_rule():
    """测试 Skill 遵守'发布前确认'规则"""
    skill = load_skill("csdn-publisher")
    response = skill.execute("发布这篇文章到 CSDN")
    
    assert "确认" in response, "必须要求用户确认"
    assert "预览" in response.lower() or "preview" in response.lower()
```

---

## 五、Skill 设计的黄金法则

### 5.1 单一职责

```markdown
# ❌ 一个 Skill 干三件事
## CSDN + GitHub + Email Publisher

# ✅ 一个 Skill 干一件事
## CSDN Article Publisher
```

### 5.2 指令越具体，AI 越靠谱

```markdown
# ❌ 模糊
"写代码时注意质量"

# ✅ 精确
"所有函数必须有 type hints，返回类型不能省略。如果返回 None，
必须写 -> None。所有公开函数必须有 docstring，包含参数说明和返回值说明。"
```

### 5.3 给例子比给规则有效

```markdown
## 输出格式要求

✅ 好的回复：
标题：Python 异步编程入门
标签：Python, 异步, asyncio
内容：（Markdown 格式的文章）

❌ 不好的回复：
我来帮你写一篇关于 Python 的文章...（没有格式）
```

---

## 六、总结

| 概念 | 一句话 |
|------|------|
| CLAUDE.md | 给 AI 的项目说明书 |
| SKILL.md | 给 AI 的能力插件包 |
| Skill vs MCP | Skill 是知识+指令，MCP 是工具接入协议 |
| Skill vs FC | Skill 是预设能力，FC 是即时工具调用 |
| 设计原则 | 单一职责 + 精确指令 + 给例子 + 安全边界 |

> Skill 的本质：**把人类专家的最佳实践编码成 AI 能理解的指令。** 好的 Skill 不是告诉 AI「你是什么」，而是告诉 AI「在这种情况下，你应该怎么做」。

---

> 🔖 下一篇：**《Function Calling 内部原理：LLM 怎么「学会」用工具》**——从 Special Token 注入到 Tool Choice 内部决策。

*标签：#Skill #ClaudeCode #AI插件 #Agent #MCP #程序员必读*