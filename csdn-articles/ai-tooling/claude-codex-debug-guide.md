# 强烈推荐收藏！Claude Code & Codex 调试完全指南：日志解读、MCP排查、repomix上下文、断点技巧——AI编程工具问题排查手册

> Claude Code 突然找不到你的文件了？Codex 卡在"正在思考"？MCP Server 莫名连接不上？这些问题网上几乎搜不到答案。本文整理了 Claude Code 和 Codex 最常见的 12 个调试场景，从日志文件位置到 MCP 协议排错，从 repomix 上下文诊断到 Token 消耗追踪，一篇文章让你从抓瞎到从容。

---

## 一、日志文件在哪里——所有问题排查的第一步

### 1.1 Claude Code 日志位置

```bash
# macOS
~/Library/Logs/Claude/

# Windows
%APPDATA%\Claude\logs\

# Linux
~/.config/Claude/logs/
```

```bash
# 实时查看日志
tail -f ~/Library/Logs/Claude/mcp*.log

# 搜索错误
grep -i "error\|fail\|timeout" ~/Library/Logs/Claude/*.log
```

关键日志文件：

| 文件 | 记录什么 |
|------|------|
| `mcp.log` | MCP Server 启动/连接/调用日志 |
| `claude.log` | Claude Code 主进程日志 |
| `agent-*.log` | Agent 会话日志（每次对话一个文件） |

### 1.2 Codex 日志位置

```bash
# macOS / Linux
~/.codex/logs/

# Windows
%USERPROFILE%\.codex\logs\

# Codex Desktop 日志
# macOS: ~/Library/Logs/Codex/
# Windows: %APPDATA%\Codex\logs\
```

```bash
# 查看最近的会话日志
ls -lt ~/.codex/logs/ | head -5
cat ~/.codex/logs/session-*.log
```

### 1.3 日志级别设置

```bash
# Claude Code - 开启详细日志
export CLAUDE_LOG_LEVEL=debug
claude

# Codex CLI - 开启详细日志
codex --log-level debug

# Codex Desktop - 设置 → 开发者选项 → 日志级别 → Debug
```

---

## 二、MCP Server 排错——最容易出问题的地方

### 2.1 MCP Server 启动失败

```json
// ~/Library/Application Support/Claude/claude_desktop_config.json
{
  "mcpServers": {
    "weather": {
      "command": "python",
      "args": ["/Users/me/mcp/weather.py"]
    }
  }
}
```

**常见错误 1**：路径不存在

```bash
# 验证
ls -la /Users/me/mcp/weather.py
python /Users/me/mcp/weather.py  # 看能不能独立启动
```

**常见错误 2**：Python 环境问题

```bash
# Claude Desktop 用的是系统 Python，不是你虚拟环境里的
# 修复：用绝对路径指定 Python
{
  "command": "/Users/me/.pyenv/shims/python",
  "args": ["/Users/me/mcp/weather.py"]
}

# 或者用 uv 自动处理依赖
{
  "command": "uv",
  "args": ["run", "--with", "mcp", "/Users/me/mcp/weather.py"]
}
```

**常见错误 3**：端口冲突

```bash
# 检查端口是否被占用
lsof -i :8080
# 换个端口
mcp run weather.py --transport streamable-http --port 8081
```

### 2.2 调试 MCP 通信

```bash
# MCP Inspector - 官方的调试工具
npx @modelcontextprotocol/inspector python weather.py

# Inspector 能做：
# 1. 列出所有 tools/resources/prompts
# 2. 手动调用工具看返回
# 3. 查看 JSON-RPC 原始消息
```

### 2.3 MCP 常见报错速查

| 报错 | 原因 | 修复 |
|------|------|------|
| `ECONNREFUSED` | MCP Server 没启动或端口不对 | 检查进程是否在运行 `ps aux \| grep mcp` |
| `Method not found` | JSON-RPC 方法名拼错 | 检查 Server 注册的 tool name |
| `Invalid arguments` | 工具参数不符合 Schema | 检查 Function Calling 传入的参数类型 |
| `Timeout` | Server 处理超时 | 工具执行不要太久（<30s），异步处理 |
| `Not initialized` | 没走 MCP 握手流程 | Server 启动后等 Client 发 initialize 请求 |

---

## 三、repomix / repomap 上下文诊断

### 3.1 Claude Code 的代码库理解机制

Claude Code 启动时会分析项目结构，生成一个 `repomap`（代码库地图）：

```bash
# 查看 Claude Code 看到什么
claude --debug  # 启动时输出 repomap

# 或者手动生成
npx repomix  # 生成 XML 上下文文件
```

### 3.2 问题：Claude Code 说"找不到文件"

```
症状：claude "帮我看看 src/auth/routes.py" → "I cannot find that file"
诊断：
  1. 文件是不是在 .gitignore 里？repomap 默认忽略 gitignore 的文件
  2. 文件是不是在 node_modules 等默认忽略目录？
  3. 是不是 Claude Code 的工作目录不对？
```

```bash
# 检查工作目录
pwd  # 确保在项目根目录

# .gitignore 会影响 repomap
cat .gitignore | grep "src/auth"  # 如果匹配，文件被忽略了

# 修复：在 CLAUDE.md 中明确告诉 Claude Code 这个文件
# .claude/CLAUDE.md
## 项目文件结构
- src/auth/routes.py: 认证相关 API 路由
```

### 3.3 Token 上下文过大

```bash
# 查看当前 repomix 生成的上下文大小
npx repomix --output repomix-output.xml
wc -c repomix-output.xml  # 文件大小
# > 如果超过 100KB，说明项目太大，需要裁剪

# 裁剪策略
npx repomix --include "src/**/*.py" --ignore "tests/**,docs/**"
```

---

## 四、Codex 专项调试

### 4.1 Codex CLI "一直显示正在思考"

```bash
# 原因 1：API 连接问题（国内最常见）
# 诊断
codex --log-level debug "hello" 2>&1 | grep -i "api\|timeout\|error"

# 修复：配置 API 中转
export OPENAI_API_BASE="https://api.ofox.ai/v1"
export OPENAI_API_KEY="your-key"
```

```bash
# 原因 2：工作目录太大，上下文扫描耗时
# 诊断：查看工作目录文件数
find . -type f -not -path './node_modules/*' -not -path './.git/*' | wc -l
# > 如果超过 1000 个文件，考虑用 .codexignore

# 创建 .codexignore（类似 .gitignore）
echo "node_modules/" >> .codexignore
echo ".git/" >> .codexignore
echo "dist/" >> .codexignore
```

### 4.2 Codex Desktop 常见问题

| 问题 | 解决 |
|------|------|
| 打开后白屏 | 清除缓存：`rm -rf ~/Library/Caches/Codex` |
| 无法登录 | 检查网络代理；尝试 CLI 模式 |
| 文件夹加载失败 | 权限问题 — 检查文件夹是否可读 |
| Thread 历史丢失 | 检查 `~/.codex/threads/` 目录 |

### 4.3 Codex 的 Thread 管理调试

```bash
# 查看所有 Thread
ls -la ~/.codex/threads/

# 导出 Thread（备份）
cp -r ~/.codex/threads/ ~/Desktop/codex-backup/

# 查看 Thread 的 token 用量
cat ~/.codex/usage.json | jq '.'

# 清理旧 Thread（释放磁盘空间）
find ~/.codex/threads/ -mtime +30 -exec rm -rf {} \;
```

---

## 五、CLAUDE.md / CODE.md 编写调试

### 5.1 指令太多了？测试加载效果

```bash
# 查看 Claude Code 实际加载了多少上下文
claude --debug 2>&1 | grep "CLAUDE.md" 

# 如果输出太多，说明 CLAUDE.md 太长
wc -c .claude/CLAUDE.md
# > 建议控制在 2000 字以内
```

### 5.2 CLAUDE.md 常见反模式

```markdown
# ❌ 写了 3000 字的项目文档
# ❌ 把 README 原样复制进去
# ✅ 只写 AI 需要知道的例外规则和习惯
```

```markdown
# ✅ 精简版的 CLAUDE.md
## 这不是默认的
- 测试用 pytest，不是 unittest
- API 返回格式是 {"code": 0, "data": ...}，不是直接返回 data
- 数据库表名用蛇形命名，不是驼峰

## 特别注意
- src/legacy/ 下的代码不要动
- .env 里的密钥不要在日志里打印
```

### 5.3 A/B 测试 CLAUDE.md 的效果

```bash
# 切换不同版本的 CLAUDE.md
claude --project-dir ./  # 用 .claude/CLAUDE.md
CLAUDE_CUSTOM_INSTRUCTIONS="..." claude  # 临时覆盖

# 对比：同一个任务，有 CLAUDE.md 和没有的结果
# 1. 先不用 CLAUDE.md 执行任务
# 2. 启用 CLAUDE.md 再执行同样任务
# 3. 比较 Token 消耗和代码质量
```

---

## 六、性能与 Token 追踪

### 6.1 查看 Token 消耗

```bash
# Claude Code：每次对话结束后显示 Token 用量
# 也可以查看日志
grep "tokens" ~/Library/Logs/Claude/agent-*.log

# Codex：查看用量统计
codex usage
cat ~/.codex/usage.json
```

### 6.2 请求重试与超时

```bash
# Claude Code 的超时配置（环境变量）
export CLAUDE_TIMEOUT=120000  # 毫秒，默认 120 秒
export CLAUDE_MAX_RETRIES=3   # 失败重试次数

# Codex 的超时配置
export CODEX_TIMEOUT=60000
```

### 6.3 网络问题诊断（国内用户重点）

```bash
# 测试 API 连通性
curl -I https://api.anthropic.com

# 如果超时 → 需要代理
export HTTPS_PROXY=http://127.0.0.1:7890
claude  # 现在走代理

# Claude Code 用 ofox.ai 中转（国内推荐）
export ANTHROPIC_BASE_URL=https://api.ofox.ai/anthropic
export ANTHROPIC_AUTH_TOKEN=your-ofox-key
```

---

## 七、工具/Plugin/Skill 问题排查

### 7.1 Skill 没加载

```bash
# 检查 Skill 目录
ls -la .claude/skills/

# 验证 SKILL.md 格式
cat .claude/skills/my-skill/SKILL.md
# 必须有 name 和 description 字段

# 重新加载 Skill
claude --reload-skills
```

### 7.2 Codex Plugin 安装失败

```bash
# Plugin 安装日志
cat ~/.codex/logs/plugin-install.log

# 手动安装
codex plugin add https://github.com/xxx/plugin
# 如果失败，检查 GitHub 是否可访问

# 查看已安装的 Plugin
codex plugin list
```

---

## 八、调试工作流最佳实践

```bash
# 1. 复现问题 → 开最小化案例
echo "用最简单的方式复现这个错误" | claude --print

# 2. 查看日志 → 定位错误
grep -A 5 "ERROR" ~/Library/Logs/Claude/*.log

# 3. 隔离变量 → 逐个排除
# 先关掉所有 MCP Server
# 再关掉所有 Skill
# 再清空 CLAUDE.md
# 逐步加回来，看哪个触发了问题

# 4. 对比环境 → 别人的能跑我的不能？
claude --version
codex --version
node --version
python --version
```

---

## 九、总结

| 问题类别 | 第一诊断步骤 | 关键命令 |
|------|------|------|
| 启动失败 | 看日志 | `tail -f ~/Library/Logs/Claude/mcp*.log` |
| MCP 连不上 | MCP Inspector | `npx @modelcontextprotocol/inspector python server.py` |
| 找不到文件 | repomap | `claude --debug` |
| Token 超标 | 裁剪上下文 | `.codexignore` / CLAUDE.md 精简 |
| 网络超时 | API 连通性 | `curl -I` / 配置中转 |
| Skill 没加载 | 目录+格式 | `ls .claude/skills/` + SKILL.md 检查 |

> AI 编程工具的调试和传统 IDE 完全不同——你看不到断点，看不到调用栈。但日志文件、MCP Inspector、repomap 是三个最重要的调试入口。遇到问题先看这三个，80% 的 bug 都能定位。

---

*标签：#ClaudeCode #Codex #AI编程 #MCP #调试 #问题排查 #程序员必读*