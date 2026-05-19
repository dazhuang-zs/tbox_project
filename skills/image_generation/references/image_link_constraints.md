# 图片链接输出约束

## 核心原则

**MCP 返回什么链接，就原样输出什么链接！**

- **零修改**：不修改任何字符
- **零添加**：不添加任何字符
- **零删除**：不删除任何字符
- **零优化**：不优化任何字符
- **零缓存**：严格禁止使用缓存的图片链接，必须每次都使用 skill 实时生成的图片链接

---

## 正确做法示例

**场景**：MCP 服务返回图片链接

```
系统返回：https://mdn.alipayobjects.com/doraemon_plugin/afts/img/AAAA123456/original
```

**正确输出**（双行格式说明见 SKILL.md，本文档关注 URL 保真度）：

```
![五一出游插画](https://mdn.alipayobjects.com/doraemon_plugin/afts/img/AAAA123456/original)
MEDIA:https://mdn.alipayobjects.com/doraemon_plugin/afts/img/AAAA123456/original
```

两行的 URL 必须**完全相同**，且必须是 MCP 实时返回的原始链接。

---

## 错误做法示例（❌ 严格禁止）

### ❌ 错误1：修改了链接 ID 部分

```markdown
# MCP 返回：https://mdn.alipayobjects.com/doraemon_plugin/afts/img/AAAA123456/original
# 错误输出：![图片描述](https://mdn.alipayobjects.com/doraemon_plugin/afts/img/BBBB123456/original)
# ^^^^ 修改了 ID（AAAA → BBBB）
```

### ❌ 错误2：删除了部分路径

```markdown
# MCP 返回：https://mdn.alipayobjects.com/doraemon_plugin/afts/img/AAAA123456/original
# 错误输出：![图片描述](https://mdn.alipayobjects.com/doraemon_plugin/afts/img/AAAA123456)
# ^^^^^^^^^ 删除了 /original
```

### ❌ 错误3：添加了额外参数

```markdown
# MCP 返回：https://mdn.alipayobjects.com/doraemon_plugin/afts/img/AAAA123456/original
# 错误输出：MEDIA:https://mdn.alipayobjects.com/doraemon_plugin/afts/img/AAAA123456/original?size=1024
# ^^^^^^^^^^^ 添加了查询参数
```

### ❌ 错误4：ID 部分连续相同字符修改

```markdown
# MCP 返回 4 个 A：.../img/AAAA123456/original
# 错误输出 3 个 A：.../img/AAA123456/original
# 错误输出 5 个 A：.../img/AAAAA123456/original
# 即使看起来相似，也必须逐字符核对
```

### ❌ 错误5：两行 URL 不一致

```
![图片](https://mdn.alipayobjects.com/doraemon_plugin/afts/img/AAAA123456/original)
MEDIA:https://mdn.alipayobjects.com/doraemon_plugin/afts/img/BBBB789012/original
# ^^^^ 两行的 URL 必须完全一致
```

### ❌ 错误6：使用缓存的图片链接

```markdown
# 本次 MCP 返回：https://mdn.alipayobjects.com/doraemon_plugin/afts/img/NEW123456/original
# 错误输出（使用了之前缓存的链接）：
![图片](https://mdn.alipayobjects.com/doraemon_plugin/afts/img/OLD789012/original)
MEDIA:https://mdn.alipayobjects.com/doraemon_plugin/afts/img/OLD789012/original
# ^^^ 严格禁止使用缓存的旧链接，必须用本次 MCP 实时返回的新链接
```

---

## 验证方法

**步骤 1**：从系统日志/命令输出中找到 MCP 返回的完整链接

```bash
# 示例系统输出
[INFO] MCP调用成功，返回图片URL：https://mdn.alipayobjects.com/doraemon_plugin/afts/img/AAAA123456/original
```

**步骤 2**：直接复制该链接（不要手动输入）

```python
# 正确：直接复制
image_url = "https://mdn.alipayobjects.com/doraemon_plugin/afts/img/AAAA123456/original"

# 错误：手动输入（容易出错）
image_url = "https://mdn.alipayobjects.com/doraemon_plugin/afts/img/AAA123456/original"
# ^^^ 少了一个 A
```

**步骤 3**：按 SKILL.md 的双格式规则输出，**两行 URL 必须完全相同**

**步骤 4**：逐字符核对两行的链接是否与 MCP 返回完全一致

```
系统返回：https://mdn.alipayobjects.com/doraemon_plugin/afts/img/AAAA123456/original
输出第1行：![描述](https://mdn.alipayobjects.com/doraemon_plugin/afts/img/AAAA123456/original)
输出第2行：MEDIA:https://mdn.alipayobjects.com/doraemon_plugin/afts/img/AAAA123456/original
核对结果：✅ 三者完全一致
```

---

## 常见错误案例对照表

| 错误类型     | MCP 返回链接              | 错误输出链接             | 问题说明                         |
| ------------ | ------------------------- | ------------------------ | -------------------------------- |
| ID 修改      | `.../img/AAAA123456/...`  | `.../img/BBBB123456/...` | 修改了 ID 部分（AAAA → BBBB）    |
| 路径删除     | `.../AAAA123456/original` | `.../AAAA123456`         | 删除了 `/original`               |
| 添加参数     | `.../original`            | `.../original?size=1024` | 添加了查询参数                   |
| 连续字符修改 | `.../img/AAAA/...`        | `.../img/AAA/...`        | 删除了一个 A（AAAA → AAA）       |
| 连续字符修改 | `.../img/AAAA/...`        | `.../img/AA/...`         | 删除了两个 A（AAAA → AA）        |
| 连续字符修改 | `.../img/AAAA/...`        | `.../img/A/...`          | 删除了三个 A（AAAA → A）         |
| 连续字符修改 | `.../img/AAAA/...`        | `.../img/AAAAA/...`      | 添加了一个 A（AAAA → AAAAA）     |
| 连续字符修改 | `.../img/AAAA/...`        | `.../img/AAAAAA/...`     | 添加了两个 A（AAAA → AAAAAA）    |
| 连续字符修改 | `.../img/AAAA/...`        | `.../img/AAAAAAA/...`    | 添加了三个 A（AAAA → AAAAAAA）   |
| 大小写修改   | `.../img/ABCD/...`        | `.../img/abcd/...`       | 修改了大小写                     |
| 特殊字符修改 | `.../img/A-B_C/...`       | `.../img/ABC/...`        | 删除了特殊字符（`-` 和 `_`）     |
| 使用缓存链接 | `.../img/NEW123456/...`   | `.../img/OLD789012/...`  | 使用了缓存的旧链接，而非实时生成 |
| 两行不一致   | `.../img/AAAA/...`        | 第1行 AAAA，第2行 BBBB   | markdown 行和 MEDIA: 行 URL 不同 |

---

## 关键提醒

1. **不要凭记忆输入链接**：必须从系统日志中复制
2. **不要优化链接格式**：MCP 返回什么就输出什么
3. **不要修改任何字符**：包括大小写、特殊字符、连续相同字符
4. **必须逐字符核对**：确保输出链接与系统返回链接完全一致
5. **ID 部分连续相同字符要特别注意**：如 MCP 返回 `AAAA`（4个A），不能输出 `AAA`（3个A）、`AAAAA`（5个A）、`AAAAAA`（6个A）或更多/更少个A
6. **严禁使用缓存链接**：必须每次都使用 skill 实时生成的图片链接，禁止使用之前缓存的旧链接
7. **markdown 行和 MEDIA: 行的 URL 必须 byte-identical**
