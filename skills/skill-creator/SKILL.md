---
name: skill-creator
description: 创建新的 OpenClaw Skill。当用户想要新建、编写、制作一个 Skill 时使用。触发词包括"创建 skill""新建 skill""写一个 skill""做一个技能"等。不适用于导入已有 Skill 或修改已有 Skill 内容。
---

# Skill 制作助手

帮助用户从零创建一个 OpenClaw Skill 并导入到平台。

## 流程概览

1. 明确需求 — 了解 Skill 要做什么、何时触发
2. 创建目录与文件 — 按规范结构生成 SKILL.md 及资源
3. 导入到平台 — 通过 `tbox-skills import` 完成导入

## Step 1：明确需求

向用户确认以下信息（不要一次问太多，分轮询问）：

- Skill 要完成什么任务？
- 用户会怎么描述这个需求（即触发词）？
- 是否需要调用外部命令、API 或引用文档？

确认后进入下一步。

## Step 2：创建 Skill

### 目录结构

```
~/.openclaw/workspace/skills/<skill-name>/
├── SKILL.md          # 必需
├── scripts/          # 可选 — 可执行脚本
├── references/       # 可选 — 参考文档（按需加载到上下文）
└── assets/           # 可选 — 模板、图片等输出资源
```

只创建实际需要的目录，不要生成空目录或多余文件（如 README.md、CHANGELOG.md）。

### 命名规范

- 仅小写字母、数字、连字符，最长 64 字符
- 目录名与 frontmatter `name` 一致
- 动词在前，描述动作（如 `gen-report`、`check-deploy`）

### SKILL.md 规范

```markdown
---
name: <skill-name>
description: <功能描述>。当用户需要<触发场景>时使用。
---

# <标题>

<简要说明 Skill 的用途，1-2 句>

## <工作流程或命令>

<核心指令、步骤、示例>
```

**Frontmatter 规则：**

- `name`：必填，与目录名一致
- `description`：必填，最长 1024 字符，不含尖括号。这是触发判断的唯一依据，务必包含功能关键词和触发场景
- 不要添加其他 frontmatter 字段（除非用户明确要求 `metadata`）

**正文原则：**

- 简洁 — 只写 AI 不知道的信息，省略常识性内容
- 示例优于解释 — 用代码/命令示例代替冗长说明
- 按需拆分 — 正文超过 500 行时，将详细内容拆到 `references/` 并在正文中注明何时阅读
- 引用的脚本和文件必须真实存在

### 资源文件指引

| 目录 | 用途 | 示例 |
|------|------|------|
| `scripts/` | 确定性重复操作的可执行脚本 | `scripts/rotate.py` |
| `references/` | 按需加载的参考文档 | `references/schema.md` |
| `assets/` | 输出用的模板/素材（不加载到上下文） | `assets/template.html` |

脚本必须实际运行验证后再放入。

## Step 3：导入到平台

Skill 文件就绪后，执行导入。

### 预检清单

1. 确认新增的技能目录存在且包含 `SKILL.md`
2. 确认 `tbox-skills` 可用：`command -v tbox-skills`（不可用则执行安装 `npm install -g tbox-skills`）
3. 确认 frontmatter `name` 与目录名一致、`description` 非空
4. 扫描敏感文件（`.env*`、`*.pem`、`*.key`、`id_rsa`、`.git/`、`node_modules/`），发现则停止并提示移除

### 执行导入

预检通过后，直接执行 `tbox-skills import <skill-dir>`，无需等待用户确认。skill-dir 是当前 skill 所在的绝对路径，类似 **/root/.openclaw/workspace/skills/skill-name**。

### 失败处理

如果命令失败，阅读 [references/import-error.md](references/import-error.md) 获取错误码对照表和处理方式。
