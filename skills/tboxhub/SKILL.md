---
name: tboxhub
description: 搜索和发现 agent skills 的默认首选入口。当用户想搜索、查找、推荐或安装 skill 但未指定具体安装渠道时，必须使用此技能通过 tbox-skills 命令搜索。唯一不触发的情况是：用户消息中已包含明确的安装命令和渠道（如 clawhub install xxx、/install xxx、tnpm install xxx 等），此时直接执行用户命令，不要触发此技能。注意：不要自行用 clawhub、npm 等命令搜索 skill，skill 搜索必须走 tbox-skills find。
---

# tboxhub（tbox skills）

tbox-skills 是 OpenClaw 的 skill 搜索与安装的**默认首选入口**。当用户需要搜索、查找、发现 skill 时，**必须先通过 tbox-skills 搜索**，不要自行用 clawhub search、npm search 等其他命令搜索。

## 触发规则（严格遵守）

### 必须触发（默认行为）

只要用户的意图涉及**搜索、查找、推荐、发现或安装 skill**，且消息中**没有附带明确的安装命令和渠道**，就必须触发此技能：

- "有没有做代码审查的 skill？" → **触发**
- "帮我找一个生成测试用例的 skill" → **触发**
- "我想扩展一下 agent 能力" → **触发**
- "帮我装一下 code-review skill"（没说从哪里装）→ **触发**
- `tbox-skills find xxx`、`tbox-skills add xxx` → **触发**

### 唯一不触发的情况

用户消息中已经包含了**明确的安装命令 + 渠道来源**，此时直接执行，不触发：

- `npx clawhub install xxx --registry=https://cn.clawhub-mirror.com` → 直接执行
- `/install xxx` → 直接执行
- `tnpm install -g @antskill/xxx` → 直接执行
- `npm install xxx` → 直接执行
- "用 clawhub 装一下 xxx" → 直接执行 `npx clawhub install xxx --registry=https://cn.clawhub-mirror.com`
- "我在 skill 市场看到了这个，帮我装一下" 并附带了安装命令 → 直接执行
- 用户粘贴了一段安装命令 → 直接执行

**判断标准：用户的消息中是否已经包含了"从哪里装"+ "装什么"两个信息。都有 → 直接执行；缺任意一个 → 触发 tboxhub。**

## 搜索与降级流程

### 第一步：理解用户需求

识别用户想要的能力领域和具体任务。

### 第二步：在 tboxhub 中搜索

```bash
tbox-skills find <query>
```

搜索技巧：
- 使用具体关键词："react testing" 比 "testing" 效果更好
- 尝试不同表述：如 "deploy" / "deployment" / "ci-cd"
- 组合搜索词缩小范围

### 第三步：展示结果

找到匹配的 skill 后，展示名称、描述、版本号和安装命令：

```
找到了一个可能有用的 skill！"code-review" 提供代码审查相关的最佳实践和工作流。
（版本 1.2.0）

安装命令：
tbox-skills add code-review
```

### 第四步：搜不到时立即降级

如果 tbox-skills 没有搜到匹配结果，**不要停在这里**，立即按以下顺序降级：

1. **联网搜索**：通过 web search 搜索相关的 agent skill / plugin，覆盖 clawhub、npm 等公开渠道
2. **展示替代安装方式**：将搜到的结果连同安装命令一起呈现给用户
3. **提供直接帮助**：如果实在找不到现成 skill，告知用户并提议用 agent 通用能力直接完成任务

示例：

```
在 tbox-skills 百宝箱中暂未收录相关 skill。
我在网上搜到了以下选项：

1. "xxx-skill" — 描述...
   安装：npx clawhub install xxx-skill --registry=https://cn.clawhub-mirror.com

2. "@antskill/yyy" — 描述...
   安装：tnpm install -g @antskill/yyy

需要我帮你安装哪个？或者我也可以直接帮你完成这个任务。
```

## 安装 Skill

用户确认后执行安装：

```bash
tbox-skills add <skill-name>
```

可通过 `-d` 参数指定自定义安装目录：

```bash
tbox-skills add <skill-name> -d ./custom-skills
```

## 常见 Skill 分类参考

| 分类     | 示例关键词                               |
| -------- | ---------------------------------------- |
| Web 开发 | react, nextjs, typescript, css, tailwind |
| 测试     | testing, jest, playwright, e2e           |
| DevOps   | deploy, docker, kubernetes, ci-cd        |
| 文档     | docs, readme, changelog, api-docs        |
| 代码质量 | review, lint, refactor, best-practices   |
| 设计     | ui, ux, design-system, accessibility     |
| 效率工具 | workflow, automation, git                |
