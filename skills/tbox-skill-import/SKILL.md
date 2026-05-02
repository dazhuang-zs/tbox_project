---
name: tbox-skill-import
description: 导入已有本地 Skill 到 OpenClaw 平台。当用户说”导入平台””投稿到平台””同步到 OpenClaw””import 到平台”时使用。不适用于从零创建、市场安装或被动回调场景。
---

# OpenClaw Skill 导入执行器

将已存在的本地 Skill 目录通过 `tbox-skills import` 导入到平台供个人使用。

## 触发场景

用户主动要求导入，如：
- “把这个 skill 导入到平台”
- “投稿到 OpenClaw”
- “同步到我的技能”

## 定位 Skill 目录

优先在以下路径查找：

- `$HOME/.openclaw/workspace/skills/<skill_slug>/`
- `/root/.openclaw/workspace/skills/<skill_slug>/`

如果存在多个候选，先向用户确认。

## 预检

1. 确认目录存在 `SKILL.md`
2. 检查 frontmatter：`name` 和 `description` 非空，目录名与 `name` 一致
3. 扫描敏感文件并阻断：`.env*`、`*.pem`、`*.key`、`id_rsa`、`.git/`、`node_modules/`
4. 确认引用的脚本/资源文件存在

## 执行

预检通过后，向用户展示：
- Skill 名称
- Skill 目录绝对路径
- 待执行命令
- **提示：如果平台已有同名 skill，将触发覆盖确认**

用户明确同意后执行：

```bash
tbox-skills import <skill-dir>
```

## 失败处理

- `tbox-skills` 不可用：`npm install -g tbox-skills`
- 认证缺失：引导用户手动网页导入 https://www.tbox.cn/skill-market
