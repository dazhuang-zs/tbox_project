# Prompt Templates (Frozen)

## Purpose

本目录包含三个冻结的prompt模板，用于确保视频脚本生成的一致性输出。

## Files

| 文件 | 用途 | 来源 |
|------|------|------|
| `strategy.prompt.md` | 策略规划师prompt | 逐字拷贝自 `src/prompts/strategy_prompt.txt` |
| `storyboard.prompt.md` | 首席分镜师prompt | 逐字拷贝自 `src/prompts/storyboard_prompt.txt` |
| `summary.prompt.md` | 总结撰写者prompt | 逐字拷贝自 `src/prompts/summary_prompt.txt` |

## Freeze Policy

**这些prompt是冻结的，不得修改。**

- **原因：** 保证所有使用此skill的AI工具产出一致结果
- **一致性：** 与项目代码运行时的prompt完全相同
- **变更流程：** 若需修改，必须同时更新：
  1. 本目录中的prompt文件
  2. `src/prompts/*.txt` 源文件
  3. Skill版本号更新

## Usage in Workflow

- **Step 3 (Strategy):** 使用 `strategy.prompt.md` 作为System prompt
- **Step 4 (Storyboard):** 使用 `storyboard.prompt.md` 作为System prompt
- **Step 5 (Summary):** 使用 `summary.prompt.md` 作为System prompt

## Validation

执行前验证：
- [ ] 文件存在且可读
- [ ] 内容与源文件 `src/prompts/*.txt` 一致
- [ ] 未被意外修改（可通过文件hash验证）

## Modification Impact

**警告：修改这些prompt将破坏确定性保证**

若prompt被修改：
- 不同AI工具可能产出不一致的结果
- 与项目代码运行结果不一致
- 破坏用户对skill的信任

**正确的修改流程：**
1. 先在项目代码中更新 `src/prompts/*.txt`
2. 测试验证新prompt的效果
3. 更新skill中的prompt文件
4. 更新skill版本号
5. 通知所有使用者
