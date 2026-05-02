# 导入错误处理

## 错误码与处理方式

| 错误码 | 含义 | 处理 |
|--------|------|------|
| `CLI_MISSING` | `tbox-skills` 未安装 | 执行 `npm install -g tbox-skills` |
| `AUTH_INFO_MISSING` | 当前环境缺少导入认证信息 | 不要引导用户做 OpenClaw 登录，直接走手动网页导入 |
| `INVALID_SKILL_DIR` | Skill 目录无效或缺少 SKILL.md | 检查目录结构，确保 SKILL.md 存在 |
| `INVALID_FRONTMATTER` | frontmatter 格式错误或缺少必填字段 | 检查 YAML 格式、`name` 和 `description` 是否完整 |
| `NAME_MISMATCH` | 目录名与 frontmatter `name` 不一致 | 统一两者命名 |
| `MISSING_REFERENCED_FILE` | SKILL.md 中引用的文件不存在 | 补齐缺失文件或移除无效引用 |
| `SENSITIVE_FILE_DETECTED` | 目录中包含敏感文件 | 移除 `.env*`、`*.pem`、`*.key` 等文件后重试 |
| `IMPORT_FAILED` | 导入命令执行失败（网络/服务端等） | 走手动网页导入兜底 |

## 手动网页导入（兜底）

当自动导入失败时，引导用户：

1. 将 Skill 目录打包为 zip（确保 zip 根目录包含 SKILL.md，不含敏感文件）
2. 访问 https://www.tbox.cn/skill-market
3. 点击「导入技能」上传 zip 完成导入

## 关键注意事项

- 如果错误信息中出现"缺少 auth 文件""认证信息缺失""未授权"等字样，一律按 `AUTH_INFO_MISSING` 处理，不要解释成 OpenClaw 登录问题
- 不要向用户索取 token、Cookie、账号密码等凭据
