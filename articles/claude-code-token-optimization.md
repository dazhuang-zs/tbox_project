# 强烈推荐收藏！Claude Code 烧钱太快？3个方法让 Token 消耗减半，第2个90%的人不知道

> 拆开 Claude Code 的黑箱，从 System Prompt 到每轮对话，把 token 流经的 14 个消耗点逐个标出来。看完你会重新理解 `/usage` 里那些数字。

---

## 开篇：我查了一次账单，发现全在给文件读取交学费

上周我一查 `/usage`，单次 session 烧了 \$4.7——我连代码都没写几行，全用来读文件了。当时的感觉就是：我到底花钱请了个程序员，还是请了个图书管理员？

你大概率也遇到过类似的场景：让 Claude Code 改个 bug，它为了"理解上下文"读了 12 个文件，跑了一遍测试，中间 grep 了三次，上下文窗口直接飙到 85%。然后它就开始"失忆"——你 10 分钟前说的话，它当没听过。你以为是模型不行，其实是你给它塞了太多它嚼不动的东西。

我花了两个周末把 Claude Code 的 token 消耗链路从头拆了一遍——从 System Prompt 到每一轮对话——发现一个反直觉的事实：**你看到的「缓存 token 占比 78%」不是在浪费钱，是在帮你省钱。** 真正的 token 黑洞根本不是你以为的那个地方。

这篇文章把 token 流经的 14 个消耗点逐个标出来，每种场景给一套立即可用的优化方案。没有"官方文档搬运"，全是踩坑后验证过的数据。

---

## 目录

1. [Token 消耗全景路线图](#1-token-消耗全景路线图)
2. [Prompt Caching 深度解析](#2-prompt-caching-深度解析)
3. [上下文窗口生命周期](#3-上下文窗口生命周期)
4. [高阶优化策略](#4-高阶优化策略)
5. [专家工作流模式](#5-专家工作流模式)
6. [监控与度量](#6-监控与度量)
7. [反模式与常见错误](#7-反模式与常见错误)
8. [速查手册](#8-速查手册)

---

## 1. Token 消耗全景路线图

### 1.1 完整消耗链路

```
┌─────────────────────────────────────────────────────────────────┐
│                    SESSION 启动（一次性）                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  [1] System Prompt          ~4,200 tokens   ← 核心指令+工具定义   │
│       ├── 行为准则、工具使用规范                                   │
│       ├── 响应格式要求                                            │
│       └── 安全边界                                                │
│                                                                  │
│  [2] Auto Memory            ~680 tokens     ← MEMORY.md 前200行   │
│       └── Claude 自动记录的项目模式/偏好                          │
│                                                                  │
│  [3] Environment Info       ~280 tokens     ← 环境元数据           │
│       ├── 工作目录、平台、Shell、OS 版本                           │
│       └── Git 分支/状态/最近提交                                  │
│                                                                  │
│  [4] MCP Tool Names         ~120 tokens     ← 仅工具名（schema延迟）│
│       └── 默认只列名，完整schema用到时才加载                      │
│                                                                  │
│  [5] Skill Descriptions     ~450 tokens     ← 所有可用 skill 的一行描述│
│       └── 完整 SKILL.md 仅在实际调用时加载                        │
│                                                                  │
│  [6] ~/.claude/CLAUDE.md    ~320 tokens     ← 用户全局指令         │
│                                                                  │
│  [7] Project CLAUDE.md      ~1,800 tokens   ← 项目级指令（最大头之一）│
│                                                                  │
│  [8] Git Context            ~200 tokens     ← 加载在system prompt末尾│
│       ├── 当前分支                                              │
│       ├── git status 摘要                                        │
│       └── 最近 commits                                           │
│                                                                  │
│  启动静态总消耗: ~8,000 tokens（全部进入缓存）                     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    每轮对话（持续增长）                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  [9] User Prompt             variable       ← 你的输入            │
│                                                                  │
│  [10] Claude 工具调用                                         │
│       ├── Read file           2,000-5,000/shot  ← 单文件读取       │
│       ├── Grep/Glob           500-2,000/shot  ← 搜索结果           │
│       ├── Bash output         1,000-10,000+/shot ← 命令输出（变量最大）│
│       ├── Edit file           400-1,000/shot  ← 编辑操作           │
│       └── Web fetch           1,000-8,000/shot ← 网页内容          │
│                                                                  │
│  [11] Hook 注入 (如有)                                          │
│       ├── PostToolUse hook    100-500/shot   ← additionalContext  │
│       └── 注意：stdout 正常退出不进入上下文，只有 JSON 中的       │
│           additionalContext 字段才会注入                         │
│                                                                  │
│  [12] Path-Scoped Rules       ~300-500/shot ← 触发时延迟加载      │
│       └── .claude/rules/ 中匹配当前文件路径的规则                 │
│                                                                  │
│  [13] Nested CLAUDE.md        变长          ← 子目录中的CLAUDE.md │
│       └── 当读取子目录文件时自动加载                              │
│                                                                  │
│  [14] Claude 的回复           800-3,000/shot ← 分析/总结文本       │
│                                                                  │
│  每轮新增: 2,000-25,000+ tokens（取决于文件读取量和命令输出）      │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 Token 消耗热力图（按影响程度排序）

| 消耗源 | 单次消耗量 | 累计影响 | 可控性 | 优化优先级 |
|--------|-----------|---------|--------|-----------|
| **文件读取** | 2k-5k/文件 | 🔴 极高 | 高（精准 prompt） | P0 |
| **Bash 命令输出** | 1k-10k+/次 | 🔴 极高 | 高（hook 过滤） | P0 |
| **CLAUDE.md（大文件）** | 2k-8k/会话 | 🟡 高 | 高（瘦身/move to skill） | P1 |
| **对话历史积累** | 持续增长 | 🟡 高 | 中（compact） | P1 |
| **Web 内容** | 1k-8k/次 | 🟡 中 | 中 | P2 |
| **Hook additionalContext** | 100-500/次 | 🟢 低 | 高 | P2 |
| **MCP 工具列表** | 120-500/会话 | 🟢 低 | 中（关不用的） | P3 |
| **Skill 描述列表** | 450/会话 | 🟢 低 | 中（disable-model-invocation） | P3 |

---

## 2. Prompt Caching 深度解析

### 2.1 缓存机制原理

Anthropic 的 prompt caching 不是"智能去重"，而是**前缀匹配缓存**：

```
每次 API 请求的结构：
┌──────────────────────────────────┐
│  System Prompt (cached)          │  ← 写入一次，后续命中 1/10 价格
├──────────────────────────────────┤
│  Tools/Skills 列表 (cached)      │  ← 同上
├──────────────────────────────────┤
│  CLAUDE.md 内容 (cached)         │  ← 同上
├──────────────────────────────────┤
│  Messages[1..n-1] (cached)       │  ← 历史消息，部分缓存
├──────────────────────────────────┤ ← 缓存断点（cache breakpoint）
│  最新 Messages[n] (uncached)     │  ← 全价
│  + 新文件内容 (uncached)          │  ← 全价
│  + 新命令输出 (uncached)          │  ← 全价
└──────────────────────────────────┘
```

**关键事实**：
- 缓存按 **前缀匹配**，不是语义匹配——只要前面的字符不同，缓存就 miss
- 缓存有 **TTL（5分钟）**，闲置超时需要重新写入
- 缓存写入按全价计费，读取按 1/10 价格
- `/compact` 会打破缓存（因为历史被摘要替换了），需要重新建立

### 2.2 缓存命中占比解读

你看到的"缓存 token 占比大"是**正常且期望的**现象：

```
典型 session 的 token 分布（以200k窗口、100轮对话为例）:

缓存部分（~25%）:
  ████████ System Prompt + CLAUDE.md + 工具定义
  ████████ 历史对话消息
  → 价格 = 全价的 1/10

未缓存部分（~75%）:
  ████████████████████████████████ 最新消息 + 新读入的文件 + 命令输出
  → 价格 = 全价
```

**缓存占比大 ≈ 你在省钱**。需要关注的是未缓存部分的绝对值。

### 2.3 缓存失效场景

| 操作 | 是否打破缓存 | 代价 |
|------|-------------|------|
| 切换模型 (`/model`) | ✅ 是 | 整个历史需重新读取，无缓存 |
| `/compact` | ✅ 是 | 历史被摘要替换，需重建缓存 |
| 新 session (`/clear`) | ✅ 是 | 全新上下文 |
| 正常对话 | ❌ 否 | 仅新增部分不缓存 |
| 读取新文件 | ❌ 否 | 不影响已有缓存前缀 |
| 修改 CLAUDE.md（session 内） | ❌ 部分 | 新 session 才生效 |

---

## 3. 上下文窗口生命周期

### 3.1 窗口模型

```
200,000 token 上下文窗口

0% ──────────────────────────────────────────────────── 100%
│                                                        │
│  启动静态 (~8k)                                        │
│  ████                                                  │
│       ↓ 对话推进                                       │
│  ████████████████ (~40k, 10轮后)                       │
│       ↓ 大规模探索                                     │
│  ████████████████████████████████ (~80k)               │
│       ↓ 接近阈值                                       │
│  ██████████████████████████████████████████ → /compact  │
│       ↓ compact 后                                     │
│  ████████ (~25k, 摘要+启动静态)                        │
│       ↓ 继续...                                        │
```

### 3.2 Auto-Compact 机制

Claude Code 在上下文接近上限时**自动触发 compaction**：

1. **触发条件**：上下文使用超过一定阈值
2. **执行方式**：Claude 生成一段摘要，包含：
   - 已完成的任务
   - 代码变更摘要
   - 测试结果
   - 关键讨论
   - 未完成的 TODO
3. **保留规则**：
   - 启动静态内容（system prompt, CLAUDE.md 等）重新注入
   - Skill 描述列表**不重新注入**（只有实际用过的 skill 保留）
   - Subagent 记忆独立管理
4. **自定义 compact 策略**（在 CLAUDE.md 中）：

```markdown
# Compact instructions
When compacting, prioritize: 
- Code changes made and their reasons
- Test output and failures
- Key architectural decisions
- Open TODOs and next steps
Discard:
- File exploration logs
- Raw search/grep results
- Debugging dead ends
```

### 3.3 上下文压力对模型表现的影响

学术界和工程实践共识：

```
上下文使用率         模型表现
─────────────────────────────────
0-30%               🟢 最佳性能（"黄金区"）
30-60%              🟡 轻微退化，偶有疏漏
60-85%              🟠 明显退化，"忘记"早期指令
85-100%             🔴 严重退化，幻觉增加，逻辑断裂
>100%（compact前）   🔴 强制 compact 或报错
```

**实操建议**：主动用 `/compact` 在 60-70% 时压缩，不要等自动触发。

---

## 4. 高阶优化策略

### 4.1 CLAUDE.md 工程化（P0）

**原则：CLAUDE.md 是执行上下文，不是文档库。**

#### ❌ 反面模式

```markdown
# CLAUDE.md - 500 行
## 项目架构（150行详细描述）
## 部署流程（80行步骤）
## API 文档（200行 endpoint 列表）
## 编码规范（70行）
```

#### ✅ 优化后

**CLAUDE.md（<200行，仅事实和规则）**：

```markdown
# Project Context
- Build: `pnpm build` | Test: `pnpm test` | Lint: `pnpm lint`
- Node 20+, pnpm 9+, TypeScript strict mode
- Monorepo: packages/ (core, web, api, shared)

## Key Rules
- NEVER modify .env files — use .env.example as template
- API handlers: single-responsibility, <100 lines
- DB queries: always use parameterized, never string interpolation
- Errors: throw typed AppError, never return null for error states

## Architecture
- Core: business logic, zero deps on framework
- API: tRPC routers → Core services
- Web: React 18 + Next.js App Router
- See `.claude/skills/architecture.md` for full architecture reference

## Test Conventions
- Unit: Vitest, colocated `*.test.ts`
- Integration: `tests/integration/`, run with `pnpm test:integration`
- E2E: Playwright, `tests/e2e/`, run with `pnpm test:e2e`

## Compact Instructions
When compacting: keep code changes + test results. Discard exploration logs.
```

**移出的内容**：
- 架构细节 → `.claude/skills/architecture/SKILL.md`
- 部署流程 → `.claude/skills/deploy/SKILL.md`
- API 参考 → `.claude/skills/api-reference/SKILL.md`

**Token 节省**：从 5,000+ → 1,200，节省 ~3,800/会话。

### 4.2 Path-Scoped Rules（P1）

把规则精确绑定到文件路径或文件类型，只在相关时加载：

```
.claude/rules/
├── api-conventions.md    # paths: ["src/api/**"]
├── css-guidelines.md     # paths: ["*.css", "*.scss"]
├── testing-standards.md  # paths: ["*.test.*", "*.spec.*"]
└── db-migrations.md     # paths: ["migrations/**"]
```

**示例 `.claude/rules/api-conventions.md`**：

```markdown
---
paths:
  - "src/api/**"
  - "src/handlers/**"
---

# API Conventions

- All endpoints return `{ data, error }` shape
- Use Zod for request validation
- Errors: `throw new AppError(code, message, statusCode)`
- Response headers: always include `X-Request-Id`
```

**节省原理**：一条 400 token 的规则，只在对 `src/api/` 操作时才加载，而不是每次会话都加载。

### 4.3 Subagent 策略（P0）

subagent 的核心价值不是并行，是**上下文隔离**：

```
主 session 上下文:
┌──────────────────────────────┐
│ 你的业务对话                  │
│ 关键决策                      │
│ 代码变更                      │
│ (干净、精炼)                  │
└──────────────────────────────┘
         │ spawn
         ↓
Subagent 独立上下文:
┌──────────────────────────────┐
│ 探索性搜索 (大量文件读取)      │
│ grep 结果 (大量输出)           │
│ 返回: 仅摘要 (~200 tokens)     │
│ (用完即弃)                    │
└──────────────────────────────┘
```

#### 高阶用法：自定义 Subagent

```markdown
# .claude/agents/researcher.md
---
name: researcher
description: Deep-dive codebase research agent. Use when the task requires 
  reading many files or searching extensively. Returns concise findings.
model: haiku
tools: Read, Grep, Glob, Bash(read-only)
maxTurns: 15
---

You are a codebase research agent. Your job is to:
1. Search the codebase for relevant code
2. Understand how components interact
3. Return a CONCISE summary (max 200 words) with:
   - Key files involved
   - Data flow overview
   - Any issues or patterns found
   - Recommended next steps

DO NOT return raw file contents. Summarize.
```

#### 高阶用法：Worktree 隔离 Subagent

```markdown
# .claude/agents/refactor-agent.md
---
name: refactor-agent
description: Refactoring agent that works in isolated worktree
model: sonnet
isolation: worktree
tools: Read, Write, Edit, Bash
---
```

Subagent 在自己的 worktree 中操作，修改不污染主工作区，完成后 worktree 自动清理。

### 4.4 Hook 输出过滤（P0）

让 hook 预过滤大输出，Claude 只看到精华：

```json
// .claude/settings.json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Bash(npm test *)",
        "command": "jq -R -s '{
          \"hookSpecificOutput\": {
            \"hookEventName\": \"PostToolUse\",
            \"additionalContext\": (split(\"\\n\") | map(select(test(\"FAIL|Error|passing|failing|Tests:\"))) | .[0:20] | join(\"\\n\"))
          }
        }'",
        "type": "command"
      }
    ]
  }
}
```

**节省原理**：`npm test` 输出 10,000 行 → hook 只提取失败行（~50 行），节省 9,000+ token/次。

### 4.5 Model 选择策略（P1）

```
任务复杂度 → 推荐模型:
────────────────────────────
简单搜索/grep      → Haiku  (最便宜, ~$0.25/1M input)
日常编码/CRUD      → Sonnet (性价比, ~$3/1M input)
复杂架构/重构      → Opus   (最强推理, ~$15/1M input)

混合策略:
→ opusplan: Plan Phase 用 Opus, Execute Phase 用 Sonnet
→ custom subagent: 研究者用 Haiku, 实现者用 Sonnet
```

**`opusplan` 模式**：

```bash
claude --model opusplan
# 或 settings.json:
{ "model": "opusplan" }
```

效果：Plan 阶段用 Opus 做推理，执行阶段自动切 Sonnet。一个 session 省 30-50% 费用。

### 4.6 会话管理策略（P1）

| 操作 | 命令 | 效果 |
|------|------|------|
| 切换任务时清上下文 | `/clear` | 重置上下文窗口 |
| 先命名再清（可恢复） | `/rename bug-123` → `/clear` | 可 `/resume bug-123` |
| 任务间隔离 | `claude --worktree feature-x` | 独立 worktree，隔离 git 状态 |
| 并行任务 | 多个终端 + worktree | 真正并行，不互相污染 |
| 从 PR 恢复 | `claude --from-pr 1234` | 恢复关联的 session |

### 4.7 Skill 延迟加载（P2）

默认情况下，所有 skill 的一行描述列表加载到启动上下文。如果一个 skill 只在你手动调用时才有用，可以禁止模型自动加载：

```markdown
# .claude/skills/deploy/SKILL.md
---
description: Deploy to production using the company deployment checklist
disable-model-invocation: true
---
```

这样 `/deploy` 命令仍然存在，但它的描述不占启动 token。只有当你主动输入 `/deploy` 时才加载完整 skill。

### 4.8 MCP 工具搜索优化（P2）

默认情况下 MCP 只加载工具名（~120 tokens）。更精细的控制：

```bash
# 环境变量或 settings.json
ENABLE_TOOL_SEARCH=auto    # 默认：工具 schema 在适合时预加载（窗口10%内）
ENABLE_TOOL_SEARCH=false   # 全部加载（token 消耗大）
# 不设置 = 延迟模式（每个工具只在第一次使用时加载schema）
```

生产建议：**不设置，保持默认延迟模式**。

### 4.9 Bare Mode（CI/脚本场景）

```bash
# 跳过所有自动发现：hooks, skills, plugins, MCP, auto memory, CLAUDE.md
claude --bare -p "Summarize this file" --allowedTools "Read"
```

节省：跳过 ~8,000 token 的启动开销。适合一次性脚本任务。

### 4.10 Pipe 代替文件读取

```bash
# ❌ Claude 读文件 (消耗 token)
claude -p "Analyze this log"

# ✅ Pipe 输入 (不占用上下文窗口的"文件读取"配额)
cat error.log | claude -p "Analyze the root cause of these errors, be concise"
```

注意：stdin 有 10MB 上限。

---

## 5. 专家工作流模式

### 5.1 四阶段工作法（Explore → Plan → Implement → Commit）

这是 Anthropic 内部团队验证的最高效模式：

```
Phase 1: EXPLORE (plan mode)
  目标: 理解现状，不确定时不乱改
  命令: Shift+Tab → plan mode
  Prompt: "read /src/auth, understand session handling, 
           check env variable management for secrets"

Phase 2: PLAN (plan mode)
  目标: 产出实现计划
  Prompt: "I want to add Google OAuth. What files need to change? 
           Create a detailed plan."
  可选: Ctrl+G 在编辑器中直接编辑计划

Phase 3: IMPLEMENT (default mode)
  目标: 按计划编码
  Prompt: "implement the OAuth flow from your plan. 
           write tests, run suite, fix failures."

Phase 4: COMMIT
  Prompt: "commit with descriptive message and create a PR"
```

**Token 节省原理**：Plan 阶段只用 read-only 工具，不产生编辑→测试→修复的 token 螺旋。

### 5.2 "一问到底" vs "分步对话" 策略

```
场景 A: 简单任务（修 typo, 加日志, 重命名变量）
  ✅ 一问到底: "fix the typo in auth.ts line 42 and commit"
  节省: 避免多轮对话积累上下文

场景 B: 复杂任务（跨多个文件的重构）
  ✅ 分步: 1) 探索  2) 制定计划  3) 逐步实现  4) commit
  每完成一个里程碑 /compact
  节省: 中间探索结果不带到实现阶段
```

### 5.3 Subagent 委托模式

```
你的角色: Architect（决策者）
  ↓ 委托
Subagent 1: Researcher (Haiku, read-only)
  → "研究 session timeout 在所有服务中的实现"
  → 返回: 200 token 摘要
  ↓
Subagent 2: Implementer (Sonnet, worktree 隔离)
  → "实现统一的 session timeout 中间件"
  → 在独立 worktree 工作
  ↓
你的主 session: 干净，只看到摘要和最终 diff
```

### 5.4 连续多任务工作流

```bash
# Terminal 1: 主开发
claude --worktree feature-auth -n auth-refactor

# Terminal 2: Bug 修复（并行）
claude --worktree bugfix-123 -n fix-login

# Terminal 3: 代码审查
claude --worktree review -n pr-review

# 随时切换:
claude --resume auth-refactor
claude --resume fix-login
```

每个 worktree 有独立的上下文和 git 状态。

### 5.5 Compact 策略优化

**被动 compact（差）**：等 Claude 自动触发，此时上下文已 90%+ 满，模型表现已退化。

**主动 compact（好）**：
```bash
# 1. 安装 statusline 监控上下文使用率
/statusline show context percentage with progress bar

# 2. 每完成一个逻辑单元主动压缩
/compact Focus on code changes and test results

# 3. 或用自定义 compact 指令
/compact Keep: implemented changes, test output, open TODOs. 
         Discard: file reading logs, grep results.
```

### 5.6 分阶段 /compact 策略

```
长 session timeline:
──────────────────────────────────────────────────
[启动] → [探索阶段] → /compact → [实现阶段] → /compact → [测试阶段]
 8k        +40k         摘要       +30k         摘要        +20k
                         ↓                      ↓
                       回到15k                 回到18k
```

每次 `/compact` 把上下文压缩回 ~15-20k，给后续工作留出空间。

---

## 6. 监控与度量

### 6.1 自定义 Statusline

实时监控上下文使用率是最重要的优化前提：

```bash
# 一键生成 statusline
/statusline show model name, context % with progress bar, session cost, and git branch
```

**手动高级版** (`~/.claude/statusline.sh`)：

```bash
#!/bin/bash
input=$(cat)

MODEL=$(echo "$input" | jq -r '.model.display_name')
PCT=$(echo "$input" | jq -r '.context_window.used_percentage // 0' | cut -d. -f1)
COST=$(echo "$input" | jq -r '.session.total_cost_usd // 0')
BRANCH=$(echo "$input" | jq -r '.git.branch // "no-git"')
DURATION=$(echo "$input" | jq -r '.session.duration_seconds // 0')

# 颜色编码
if [ "$PCT" -gt 80 ]; then
  COLOR='\033[0;31m'  # 红
elif [ "$PCT" -gt 60 ]; then
  COLOR='\033[0;33m'  # 黄
else
  COLOR='\033[0;32m'  # 绿
fi

# 进度条
BAR_LEN=20
FILLED=$(( PCT * BAR_LEN / 100 ))
EMPTY=$(( BAR_LEN - FILLED ))
BAR=$(printf "%${FILLED}s" | tr ' ' '█')
BAR="${BAR}$(printf "%${EMPTY}s" | tr ' ' '░')"

echo -e "[${MODEL}] 🌿 ${BRANCH} | ${COLOR}${BAR} ${PCT}%\033[0m | \$${COST} | ⏱ ${DURATION}s"
```

### 6.2 `/usage` 命令

```bash
/usage
# 输出:
# Total cost:            $0.55
# Total duration (API):  6m 19.7s
# Total duration (wall): 6h 33m 10.2s
# Context window:        45% (90,000/200,000 tokens)
# Cache hit rate:        78%
```

### 6.3 `/context` 命令

列出当前上下文窗口中的内容分布，帮助诊断是什么在占用空间。

---

## 7. 反模式与常见错误

### 7.1 ❌ CLAUDE.md 当文档写

```
症状: CLAUDE.md 500+ 行，包含完整 API 文档和部署手册
后果: 每次会话白烧 5,000-8,000 token
修复: 核心规则留 CLAUDE.md，细节移入 skills/rules
```

### 7.2 ❌ "通灵"式 Prompt

```
❌ "fix the bug"
✅ "fix the 401 error in auth.ts after token refresh, 
    the issue is in the rotation order"
```

不精确的 prompt → Claude 要读 5-10 个文件才能定位 → 浪费 15,000+ token。

### 7.3 ❌ 不监控上下文使用率

```
后果: 不知道窗口满到 90%，Claude 表现已退化，继续用
修复: /statusline show context percentage
```

### 7.4 ❌ 超级长 Session 从不 compact

```
症状: 一个 session 开 8 小时，200 轮对话
后果: 后 100 轮的表现显著差于前 100 轮
修复: 每完成一个功能点就 /compact 或 /clear + /resume
```

### 7.5 ❌ 在 Opus 上做简单任务

```
症状: grep、读文件、简单修改全部用 Opus
后果: 费用是 Sonnet 的 5 倍，相同效果
修复: 日常用 Sonnet，仅复杂推理切 Opus；探索类 subagent 用 Haiku
```

### 7.6 ❌ MCP Server 过多

```
症状: 配了 10 个 MCP server，但只用其中 2 个
后果: 工具名字列表占 500+ token/会话
修复: /mcp → 关闭不用的 server
```

---

## 8. 结尾：你的优化数字是多少？

我用这套方法把单次 session 费用压到了原来的三分之一。但说实话，最让我意外的不是省钱——是 Claude 在上下文 60% 以下时的代码质量，跟在 90% 时简直像两个模型。中间那 30% 的差距，就是你烧掉的 token 在反向吃掉模型的推理能力。

这篇文章本质上是一份「上下文审计手册」——下次 Claude 开始"健忘"、答非所问、逻辑断裂，别急着骂模型退化，先跑一个 `/usage`，翻到第 4 节查优化策略。

**你平时怎么管理 Claude Code 的上下文？跑 `/compact` 的频率是多少？评论区聊聊你的数字，我们互相抄作业。** 👇

🔖 **收藏备用**：下次看到 `/usage` 里那个吓人的数字，直接回来翻对应的优化方案。

---

## 速查手册

### 关键命令速查

| 命令 | 作用 |
|------|------|
| `/usage` | 查看 token 用量和费用 |
| `/context` | 查看上下文内容分布 |
| `/compact [instructions]` | 主动压缩上下文 |
| `/clear` | 清空上下文（先 `/rename`） |
| `/model [name]` | 切换模型 |
| `/statusline ...` | 配置状态栏监控 |
| `/resume [name]` | 恢复历史 session |
| `/mcp` | 管理 MCP server |
| `/agents` | 管理 subagent |
| `/config` | 打开设置界面 |
| `claude --worktree name` | 创建隔离 worktree |
| `claude --model opusplan` | Plan 用 Opus + 执行用 Sonnet |
| `claude --bare -p "..."` | 最小开销的非交互模式 |

### 决策树：选择哪种优化

```
你遇到的情况 → 最佳优化
────────────────────────────────────────────
CLAUDE.md >200行        → 移到 skills/rules
大文件读取导致窗口暴涨   → subagent 隔离
npm test 输出太多        → PostToolUse hook 过滤
长 session 表现退化      → 主动 /compact
日常任务费用高           → 切到 Sonnet/opusplan
多任务并行互相污染       → worktree 隔离
每次会话重复同样指令     → 写入 CLAUDE.md
MCP 工具过多            → /mcp 关闭不用
```

### 优化收益估算表

| 优化措施 | 每次会话节省 | 难度 | ROI |
|---------|-------------|------|-----|
| CLAUDE.md 瘦身 | 3,000-5,000 tokens | 低 | ⭐⭐⭐⭐⭐ |
| Subagent 隔离探索 | 10,000-30,000 tokens | 中 | ⭐⭐⭐⭐⭐ |
| Hook 过滤输出 | 5,000-15,000 tokens/次 | 中 | ⭐⭐⭐⭐ |
| Active /compact | 保持 30-60% 窗口 | 低 | ⭐⭐⭐⭐ |
| Path-scoped rules | 300-500 tokens/触发 | 低 | ⭐⭐⭐ |
| Skill 代 CLAUDE.md 细节 | 1,000-3,000 tokens | 中 | ⭐⭐⭐ |
| 切 opusplan / Sonnet | 30-50% 费用 | 低 | ⭐⭐⭐⭐ |
| 关无用 MCP | 100-300 tokens | 低 | ⭐⭐ |
| Bare mode (CI) | 8,000 tokens/次 | 低 | ⭐⭐⭐⭐ |

---

## 参考资料

- [Claude Code 上下文窗口可视化](https://code.claude.com/docs/en/context-window)
- [Claude Code 成本管理](https://code.claude.com/docs/en/costs)
- [Claude Code 内存/CLAUDE.md](https://code.claude.com/docs/en/memory)
- [Claude Code Skills](https://code.claude.com/docs/en/skills)
- [Claude Code Subagents](https://code.claude.com/docs/en/sub-agents)
- [Claude Code Hooks](https://code.claude.com/docs/en/hooks-guide)
- [Claude Code 最佳实践](https://code.claude.com/docs/en/best-practices)
- [Claude Code 模型配置](https://code.claude.com/docs/en/model-config)
- [Claude Code Worktrees](https://code.claude.com/docs/en/worktrees)
- [Claude Code Sessions](https://code.claude.com/docs/en/sessions)

---

> **核心心法**：Token 优化的本质不是"省钱"，而是让 Claude 的上下文窗口留给真正重要的事——你的代码逻辑和关键决策，而不是被文件读取日志和测试输出淹没。缓存占比大不是 bug 是 feature，真正的战场在每轮对话的增量部分。
