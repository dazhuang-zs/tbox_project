---
name: video-script-generation-skill
description: 指导AI助手执行完整的短视频脚本生成工作流（输入解析→策略规划→分镜脚本→总结输出），产出与项目代码运行一致的Markdown产物。
---

# Video Script Generation Skill

## About This Skill

本skill捕获"视频脚本生成系统"的完整执行流程，使任何AI工具都能按相同步骤产出一致结果。

**关键特性：**
- 完整5步工作流（解析→决策→策略→分镜→总结）
- 确定性输出（严格遵循prompt模板）
- 工具调用决策规则（何时读取用户文件）
- 固定产物格式（`【创作策略】*.md` + `【视频脚本】*.md` + summary）

## When To Use

触发此skill的场景：
- 用户需要生成短视频脚本（包含策略规划 + 分镜表 + 总结）
- 用户提供Markdown格式的需求描述（包含二级标题分区）
- 需要产出可直接用于拍摄的分镜头脚本

## Prerequisites

**输入格式要求：**
用户输入必须是Markdown格式，包含以下二级标题（缺失则按空串处理）：

```markdown
## 项目需求
[描述视频的核心需求、目标受众、产物形式等]

## 项目计划
[可选：多个Plan选项]

## 你的任务
[当前要执行的具体任务]

## 项目环境
[工作目录路径，格式：电脑工作目录: /home/ubuntu/files/<conversation_id>/]

## 项目信息
[可选：文件路径或其他产物信息。若为"无"则禁用文件读取工具]
```

## Execution Workflow (MUST Follow Exactly)

### Step 1: Parse Markdown Input

**操作：**解析用户输入，提取结构化字段

**使用工具：**参考 `@references/workflow-spec.md` 中的解析规则

**输出：**
- `project_requirements` (str)
- `project_plan` (str)
- `task` (str)
- `work_dir` (str)
- `project_info` (str)

**决策：**
- 若输入不符合Markdown二级标题格式，报错终止
- 缺失字段按空串处理

### Step 2: Decide Tool Usage (File Reading)

**判断规则：**

| 条件 | 操作 |
|------|------|
| `project_info == "无"` | **禁用** `read_file` 工具 |
| `project_info != "无"` 且包含完整文件路径 | **可启用** `read_file` 工具 |
| 文件路径不在允许列表（非 `/home/ubuntu` 开头或含 `..`） | **拒绝**读取，返回错误信息 |

**约束：**
- 只能读取用户输入中**明确声明**的文件路径
- 路径必须以 `/home/ubuntu` 开头
- 路径不能包含 `..`（防止目录遍历）

### Step 3: Generate Strategy

**Prompt模板：**使用 `@references/prompts/strategy.prompt.md`（冻结，不可修改）

**输入：**
- System: 策略规划师prompt
- User: 拼接后的需求文本
  ```
  项目需求是：{project_requirements}
  你的任务是{task}
  当前需求可使用的文件产物信息是：{project_info}
  ```
  或（当 `project_info == "无"` 时）：
  ```
  项目需求是：{project_requirements}
  你的任务是{task}
  当前需求无可以使用的文件产物信息，不可以使用tool调用读取文件
  ```

**工具调用：**
- 若启用工具且模型决定读取文件：调用 `read_file(filePath=<用户声明的路径>)`
- 验证路径合法性后，将文件内容注入到上下文

**输出：**
- 流式输出策略文本
- 完成后提取一级标题（`# <标题>`）
- 保存文件：`【创作策略】{标题}.md`
- 若无标题，文件名回退为"脚本框架"

### Step 4: Generate Storyboard

**Prompt模板：**使用 `@references/prompts/storyboard.prompt.md`（冻结，不可修改）

**输入：**
- System: 首席分镜师prompt
- User: 策略文本 + 用户需求
  ```
  用户的需求是：{user_input}
  你的任务是根据以下视频创作策略，生成一个详细的分镜脚本：
  {full_strategy}
  ```

**约束：**
- 必须严格遵守策略中指定的总时长
- 时长误差控制在±1秒内
- 每完成5个镜头需核算累计时长

**输出：**
- 流式输出分镜脚本（Markdown表格格式）
- 完成后提取一级标题
- 保存文件：`【视频脚本】{标题}.md`
- 发送文件产物消息（包含下载链接）

### Step 5: Generate Summary

**Prompt模板：**使用 `@references/prompts/summary.prompt.md`（冻结，不可修改）

**输入：**
- System: 总结撰写者prompt
- User: 分镜脚本内容
  ```
  用户的脚本内容是：
  {storyboard_content}
  请根据上述内容，生成一个简洁的脚本总结。
  ```

**约束：**
- 必须以"我已为您制作了一个xxx"开头
- 字数严格控制在200字以内
- 温度参数设为0.3（稳定输出）

**输出：**
- 流式输出总结文本
- 打印到用户界面

## Output Artifacts

执行完成后，必须产出以下文件：

1. **`【创作策略】{标题}.md`**
   - 包含：核心概念、人物设定、故事蓝图、结构框架
   - 格式：参考 `@assets/examples/output-strategy-example.md`

2. **`【视频脚本】{标题}.md`**
   - 包含：分镜表（镜号、场景、画面、景别、机位、台词、音效、时长）
   - 格式：Markdown表格，参考 `@assets/examples/output-storyboard-example.md`

3. **Summary（控制台输出）**
   - 格式：以"我已为您制作了一个xxx"开头，≤200字
   - 示例：参考 `@assets/examples/output-summary-example.md`

## Validation Checklist

执行完成后，逐项验证：

- [ ] 输入是否包含5个必需的二级标题字段？
- [ ] 若 `project_info == "无"`，是否未调用文件读取工具？
- [ ] 若读取文件，路径是否合法（`/home/ubuntu` 开头且无 `..`）？
- [ ] 策略文件是否保存为 `【创作策略】*.md`？
- [ ] 分镜文件是否保存为 `【视频脚本】*.md`？
- [ ] 分镜总时长是否与策略规划一致（误差≤1秒）？
- [ ] Summary是否以"我已为您制作了一个"开头且≤200字？

## Determinism Contract

**MUST:**
- 严格使用冻结的prompt模板（不可修改）
- 按顺序执行5步工作流
- 遵循工具调用决策规则
- 产出固定格式的文件名

**MUST NOT:**
- 跳过任何步骤
- 自定义prompt内容
- 读取未声明或非法路径的文件
- 修改输出格式或文件命名规则

## Resources

- **Workflow Specification**: `@references/workflow-spec.md` - 详细协议与I/O schema
- **Prompt Templates**: `@references/prompts/` - 冻结的三个prompt文件
- **Examples**: `@assets/examples/` - 输入输出样例
