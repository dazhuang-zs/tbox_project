# Workflow Specification

## Overview

本文档定义视频脚本生成工作流的确定性协议，确保任何执行者都能产出一致结果。

## Input Contract

### Required Markdown Structure

用户输入必须包含以下二级标题（`##`），缺失字段按空串处理：

```markdown
## 项目需求
<content>

## 项目计划
<content>

## 你的任务
<content>

## 项目环境
<content>

## 项目信息
<content>
```

### Field Definitions

| 字段 | 类型 | 必须 | 描述 |
|------|------|------|------|
| `project_requirements` | str | 是 | 视频的核心需求、目标受众、产物形式 |
| `project_plan` | str | 否 | 多个Plan选项（Plan1/Plan2/...） |
| `task` | str | 是 | 当前要执行的具体任务描述 |
| `work_dir` | str | 否 | 工作目录路径，格式：`电脑工作目录: /home/ubuntu/files/<conversation_id>/` |
| `project_info` | str | 否 | 文件路径或其他产物信息。特殊值：`"无"` 表示无可用文件 |

### Parsing Algorithm

1. 使用正则表达式 `^## (.+)$` 分割文本
2. 对每个section，提取标题和内容
3. 映射到对应字段：
   - `项目需求` → `project_requirements`
   - `项目计划` → `project_plan`
   - `你的任务` → `task`
   - `项目环境` → `work_dir`
   - `项目信息` → `project_info`
4. 未出现的字段设置为空字符串

## Tool Usage Decision Table

### File Reading Permission

| project_info 值 | 文件路径条件 | 决策 |
|----------------|-------------|------|
| `"无"` | - | **禁用** `read_file` 工具 |
| 非空且 ≠ `"无"` | 以 `/home/ubuntu` 开头 且 不含 `..` | **允许** `read_file` |
| 非空且 ≠ `"无"` | 不以 `/home/ubuntu` 开头 或 包含 `..` | **拒绝** 并返回错误 |

### Security Constraints

**MUST:**
- 只读取用户输入中**明确声明**的文件路径
- 路径必须符合安全规范（`/home/ubuntu` 前缀，无目录遍历）

**MUST NOT:**
- 猜测或构造未声明的文件路径
- 读取系统敏感文件（如 `/etc/passwd`）
- 允许包含 `..` 的路径（防止目录遍历攻击）

## Step-by-Step I/O Schema

### Step 1: Parse Input

**Input:** `user_query` (str) - 原始用户输入文本

**Output:**
```python
{
  "project_requirements": str,
  "project_plan": str,
  "task": str,
  "work_dir": str,
  "project_info": str
}
```

**Failure:** 若无任何有效的二级标题，抛出 `ValueError`

### Step 2: Build Strategy Query

**Input:** 解析后的字段字典

**Output:** `strategy_query` (str)

**Logic:**
```python
if project_info == "无":
    strategy_query = f"项目需求是：{project_requirements}\n你的任务是{task}\n当前需求无可以使用的文件产物信息，不可以使用tool调用读取文件"
else:
    strategy_query = f"项目需求是：{project_requirements}\n你的任务是{task}\n当前需求可使用的文件产物信息是：{project_info}"
```

### Step 3: Generate Strategy

**Input:**
- System prompt: `strategy.prompt.md` (冻结)
- User message: `strategy_query`
- Tool: `read_file` (可选，根据决策表启用)

**Output:**
- Stream: 策略文本片段
- File: `【创作策略】{title}.md`
- Title extraction: 正则 `^# (.+)$`，若无标题则回退"脚本框架"

**Tool Call Flow:**
1. 模型决定是否调用 `read_file`
2. 若调用，验证路径合法性
3. 若合法，读取文件内容并注入上下文
4. 若不合法，返回错误信息并跳过

### Step 4: Generate Storyboard

**Input:**
- System prompt: `storyboard.prompt.md` (冻结)
- User message: `用户的需求是：{user_input}\n你的任务是根据以下视频创作策略，生成一个详细的分镜脚本：\n{full_strategy}`

**Output:**
- Stream: 分镜脚本片段（Markdown表格）
- File: `【视频脚本】{title}.md`
- Title extraction: 同Step 3

**Constraints:**
- 总时长必须与策略规划一致
- 时长误差 ≤ 1秒
- 每5个镜头核算累计时长

### Step 5: Generate Summary

**Input:**
- System prompt: `summary.prompt.md` (冻结)
- User message: `用户的脚本内容是：\n{storyboard_content}\n请根据上述内容，生成一个简洁的脚本总结。`
- Temperature: 0.3

**Output:**
- Stream: 总结文本
- Console: 打印到用户界面

**Format Constraints:**
- 开头固定："我已为您制作了一个xxx"
- 长度限制：≤ 200字

## Output File Naming

| 产物 | 文件名格式 | 提取规则 |
|------|-----------|---------|
| 策略文档 | `【创作策略】{title}.md` | 从策略文本提取 `# <title>` |
| 分镜脚本 | `【视频脚本】{title}.md` | 从分镜文本提取 `# <title>` |
| Summary | 无文件，控制台输出 | - |

**Fallback:** 若无法提取标题，使用固定名称：
- 策略："脚本框架"
- 分镜："分镜脚本"

## Termination Criteria

工作流在以下情况终止：

**Success:**
- 所有5步执行完成
- 策略文件已保存
- 分镜文件已保存
- Summary已输出

**Failure:**
- Step 1: 输入格式无效
- Step 2: 字段缺失导致无法构建查询
- Step 3/4/5: LLM调用失败或工具调用错误

## Error Handling

| 错误类型 | 处理方式 |
|---------|---------|
| 输入格式错误 | 返回错误信息，终止工作流 |
| 文件路径非法 | 返回错误信息，跳过工具调用 |
| LLM调用失败 | 返回错误信息，终止工作流 |
| 标题提取失败 | 使用回退名称继续执行 |
