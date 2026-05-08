# 【Claude Code 内核揭秘】2026年深度拆解：6层上下文架构如何拼出 AI 的"记忆"

> **标签**：`#ClaudeCode` `#AI编程` `#上下文管理` `#AI Agent` `#技术深度`

> **版本**：本文基于 Claude Code v2.x（2026年5月），机制描述来源于源码行为反推 + 官方文档交叉验证。

> 很多人以为 Claude Code 的"记忆"就是那个 CLAUDE.md 文件——本质上它确实是。但背后的上下文拼接、System Prompt 注入、会话历史管理**六层架构设计**，远比一个 Markdown 文件精彩得多。本文从源码行为反推 + 对比 7 款 AI 编码工具的角度，帮你彻底搞懂 Claude Code 是怎么"记住"你和你的项目的。

---

## 一、先抛结论：Claude Code 没有传统意义上的"记忆"

如果你理解的"记忆"是**会话结束后还能回忆起上一轮聊了什么**——那 Claude Code **没有**。

Claude Code 的记忆模型可以用一句话概括：

> **每次启动 = 从零开始读文件 → 拼成 Prompt → 扔给模型。关了窗口，什么都没了。**

这和 OpenClaw、Mem0、Letta（MemGPT）等自带**持久化记忆系统**的 AI Agent 有本质区别。

---

## 二、三层上下文架构：Claude Code 到底给模型"喂"了什么

Claude Code 不记忆，但它有精心设计的**上下文拼接机制**。每次对话，它按以下顺序把信息拼成一个巨大的 System Prompt：

```
┌─────────────────────────────────────┐
│  Layer 1: System Prompt（Anthropic 内置）   │  ← 角色定义、安全规则、工具描述
├─────────────────────────────────────┤
│  Layer 2: CLAUDE.md (用户级)               │  ← ~/.claude/CLAUDE.md
├─────────────────────────────────────┤
│  Layer 3: CLAUDE.md (项目级)               │  ← <project>/CLAUDE.md 
├─────────────────────────────────────┤
│  Layer 4: .claude/settings.json           │  ← 权限配置、allowedTools
├─────────────────────────────────────┤
│  Layer 5: /memory 命令追加的内容            │  ← 用户手动添加的持久化片段
├─────────────────────────────────────┤
│  Layer 6: 当前会话历史                       │  ← 本轮对话的全部消息
└─────────────────────────────────────┘
```

### 逐层拆解

### Layer 1: System Prompt（不可见、不可改）

Anthropic 内置的 System Prompt 约 8000+ token，包含：
- 角色定义（"你是一个 AI 编程助手"）
- 工具调用规范
- 安全边界（不执行危险命令等）
- Sub-agent 调度逻辑
- 代码搜索、文件读写策略

**这部分用户完全不可见**，不像 OpenClaw 的 SOUL.md / AGENTS.md 可以直接编辑。

### Layer 2-3: CLAUDE.md（唯一的"可编程记忆"）

`CLAUDE.md` 是 Claude Code 记忆体系里唯一能被用户控制的持久化入口。

**两层加载逻辑：**
```
启动 Claude Code
    ↓
检查 ~/.claude/CLAUDE.md 是否存在 → 有就加载
    ↓
检查 当前项目/CLAUDE.md 是否存在 → 有就追加（覆盖同名配置）
```

**加载时机**：每次新会话启动时一次性读取，**会话中途修改 CLAUDE.md 不会自动生效**。

**CLAUDE.md 的典型用法：**
```markdown
# 项目技术栈
- Node.js 20 + TypeScript
- 数据库：PostgreSQL 16

# 关键命令
- 构建：pnpm build
- 测试：pnpm test -- --coverage
- 启动：pnpm dev

# 代码风格
- 禁止 any 类型
- 优先使用 async/await
- 组件文件放在 src/components/

# 我的偏好
- 回复用中文
- 先解释原理再写代码
- 不要过度抽象
```

**局限性**：CLAUDE.md 完全靠用户手动维护。Claude Code **不会自动更新它**——你在项目中踩的坑、发现的规律、学到的最佳实践，除非你主动写进去，否则下次启动就忘了。

### Layer 4: settings.json（权限记忆）

`.claude/settings.json` 存储的是**工具权限配置**，不是对话记忆：

```json
{
  "permissions": {
    "allow": [
      "Bash(npm test:*)",
      "Bash(git:*)",
      "Read(~/**)"
    ],
    "deny": [],
    "ask": []
  }
}
```

这层更像是**安全护栏**而非上下文记忆。但它确实影响 Claude Code 的"行为记忆"——哪个命令可以直接执行、哪个需要确认。

### Layer 5: `/memory` 命令

Claude Code 支持 `/memory` 命令，可以在当前会话中追加一段文本到持久化存储：

```
/memory 这个项目使用 pnpm workspace，所有包在 packages/ 下
```

这段文字会被保存在 `.claude/memory` 文件中，**跨会话持久化**，下次启动时自动加载。

**但 `/memory` 不会自动触发**——Claude Code 不会自己判断"这个信息值得记住"。它完全依赖你手动输入。

### Layer 6: 会话历史（会话内有效）

当前对话的完整历史（用户消息 + AI 回复 + 工具调用结果）会在**同一个会话内**被保留并发送给模型。

但这是**有窗口限制的**——当上下文接近模型最大窗口时，旧的对话会被截断或压缩。

⚠️ **关键差异**：会话结束 = 历史清空 = 模型完全失忆。下次新建会话，它不会记得你们刚才聊过什么。

---

## 三、对比其他 AI 编程工具的记忆设计

| 工具 | 记忆方式 | 自动记录 | 跨会话 | 粒度 |
|------|---------|---------|--------|------|
| **Claude Code** | CLAUDE.md + /memory | ❌ | ✅（仅手动） | 文件级 |
| **Cursor** | .cursorrules + Notepad | ❌ | ✅（手动+Notepad持久化） | 文件级 |
| **GitHub Copilot** | .github/copilot-instructions.md | ❌ | ✅ | 文件级 |
| **OpenClaw** | MEMORY.md + 每日日记 + 语义搜索 | ✅ | ✅ | 天级/事件级 |
| **Windsurf** | Rules (.windsurfrules) + Memories | ❌ | ✅ | 文件级 |
| **Codex (OpenAI)** | 会话内上下文 + Instructions | ❌ | ❌ | 会话级 |
| **Cline** | .clinerules | ❌ | ✅ | 文件级 |

你会发现一个有趣的现象：**主流 AI 编码工具的"记忆"本质上都是"启动时读一个 Markdown 文件"**。没有人真正做了持久化的对话记忆系统。

只有 **OpenClaw** 做到了"AI 自己写日记、自己从错误中学习、自己更新记忆"——因为它的定位不是编码工具，而是 AI Agent 操作系统。

---

## 四、Claude Code 记忆模型的优点和坑

### ✅ 优点

1. **简单可控**：CLAUDE.md 就是一个文件，你能看到 Claude Code 到底"知道"什么
2. **零幻觉**：不存在"模型自己编造了一段记忆"的问题——它只读你写的
3. **可版本控制**：CLAUDE.md 可以加入 Git，团队共享项目上下文
4. **token 消耗透明**：你知道它读了多少字，不会暗地里吃掉大量上下文

### ❌ 坑和局限

1. **"便利贴困境"**：它只是记住了你写的，不是"真正学会了"——下次遇到同样的错误，它不会自动避开
2. **手动维护成本高**：你需要持续更新 CLAUDE.md，否则它就越过时
3. **无适应性记忆**：不会根据项目演进自动调整"它知道什么"
4. **会话之间完全断裂**：聊了3小时的重要结论，关闭会话就丢了——除非你手动写进 CLAUDE.md
5. **无用户模型**：不会记住"你偏好什么风格的代码"、"你上次搞砸了什么"

---

## 五、提升 Claude Code "记忆力"的实战技巧

### 技巧 1：用好 `/init` 命令

在项目目录下运行 `/init`，Claude Code 会自动扫描代码库并生成一个 CLAUDE.md：

```
/init
```

它会分析：
- package.json / requirements.txt → 技术栈
- 目录结构 → 项目架构
- 配置文件 → 构建/部署方式

然后生成一个结构化的 CLAUDE.md。**但 /init 只跑一次**，后续需要手动维护。

### 技巧 2：把 CLAUDE.md 当场外大脑

```
# CLAUDE.md 最佳实践

## 项目认知（每次 init 后更新）
- 技术栈
- 核心架构

## 踩坑记录（自己手动追加）
- [2026-05-07] xxxx库的v3版本不支持Node 22，必须用v4
- [2026-05-06] 数据库连接池设为20会OOM，上限10

## 偏好设置
- 不要用 any 类型
- 测试用 vitest 不是 jest
- 回复用中文

## 常用命令
- 热重载：npm run dev
- 构建：npm run build
```

### 技巧 3：会话结束时主动归档

每次重要会话结束前，让 Claude Code 帮你总结：

```
请帮我总结本次会话中讨论的重要内容、达成的决策、遇到的坑，
以适合写入 CLAUDE.md 的格式输出。
```

然后把输出的内容手动追加到 CLAUDE.md。

### 技巧 4：用 `/memory` 保存"一次性配置"

```bash
/memory 这个仓库的CI跑在 GitHub Actions，部署到 Vercel，不能用 Cloudflare Pages
```

`/memory` 适合记那些"不需要放在 CLAUDE.md 里给团队共享、但你自己不想每次重复解释"的东西。

---

## 六、未来展望：AI 编码工具的记忆应该长什么样

从 Claude Code 当前的设计能看出 Anthropic 的思路：**保守、可控、用户主导**。

但未来 AI 编码工具的记忆系统一定会进化：

1. **自动归档**：会话结束时 AI 自动提炼关键信息存入记忆
2. **分层记忆**：短期（本次会话）→ 中期（本周）→ 长期（项目级知识）
3. **语义检索**：不再是一次性加载整个文件，而是按需检索相关记忆片段
4. **纠错式学习**：从用户的纠正中自动更新"它知道的东西"
5. **跨项目迁移**：在一个项目中学会的偏好自动带到新项目

OpenClaw 目前是唯一一个接近上述能力的 AI Agent 系统——它的 `memory/YYYY-MM-DD.md` 日志 + `MEMORY.md` 长记忆 + 语义搜索 + self-improvement skill 已经实现了分层、自适应、自动化的记忆模型。

Claude Code 要走这条路，可能需要突破"纯文件"的架构限制。

---

## 七、总结

| 你关心的问题 | Claude Code 的答案 |
|:--|:--|
| 有记忆吗？ | 没有传统意义上的"记忆" |
| 怎么"记住"我的项目？ | 启动时读取 CLAUDE.md |
| 会自动记录吗？ | 不会，全靠手动 |
| 会话结束记得啥？ | 什么都不记得 |
| 能跨项目共享记忆吗？ | 通过 `~/.claude/CLAUDE.md` |
| 记忆上限多大？ | 受模型上下文窗口限制（约200K token） |

**一句话**：Claude Code 的记忆 = 一块你需要自己写的白板。它能让你写得很漂亮，但不会"替你记住什么"。

如果你需要一个真正有记忆的 AI Agent——会写日记、能从错误中学习、跨会话保持上下文的——Claude Code 做不到。但这不一定是缺点：对很多开发者来说，**明确可控的白板 > 一个自己瞎编的"记忆"**。

---

---

## 参考资源

- [Claude Code 官方文档](https://docs.anthropic.com/en/docs/claude-code/overview)
- [Anthropic System Prompts 研究](https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching)
- [OpenClaw 记忆系统设计](https://docs.openclaw.ai)

---

*这篇文章是你想要的吗？还想深挖哪一层？评论区聊聊。*
