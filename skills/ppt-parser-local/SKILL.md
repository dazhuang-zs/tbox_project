---
name: ppt-parser-local
description: 本地解析 .pptx 文件并输出结构化 JSON/Markdown（主题色、标题、文本、图片、缓存）。当用户需要抽取 PPT 内容、导出图片、保留阅读顺序且不需要远端上传能力时使用。
---

# PPT Parser Local

使用本 skill 在本地解析 `.pptx`，保留复杂版式解析能力，并输出稳定的结构化结果。

## 执行步骤

1. 检查依赖并安装：
```bash
python3 -m pip install python-pptx Pillow
```

2. 解析为 Markdown（默认模式，带缓存）：
```bash
python3 scripts/parse_ppt_local.py /abs/path/demo.pptx
```

3. 解析为 JSON：
```bash
python3 scripts/parse_ppt_local.py /abs/path/demo.pptx --mode json --pretty
```

4. 指定输出根目录（可选）：
```bash
python3 scripts/parse_ppt_local.py /abs/path/demo.pptx --output-dir /abs/path/output
```

## 输出契约

`json` 模式输出结构：

```json
{
  "theme_colors": {},
  "total_pages": 0,
  "slides": [
    {
      "page": 1,
      "title": "",
      "text": [],
      "images": [
        {
          "image_path": "/abs/path/to/image.png",
          "size": [1920, 1080]
        }
      ]
    }
  ]
}
```

约束：
- `slides[].images[]` 仅包含 `image_path` 和 `size`。
- 不输出 `image_url` 字段。

## 行为说明

- 主题色：从 PPTX 主题 XML 读取颜色槽位。
- 标题：优先占位符与 `slide.shapes.title`，再使用启发式兜底。
- 文本顺序：按 `top/left` 坐标进行行内排序。
- 组合形状：支持组合与嵌套组合形状的坐标变换。
- 图片来源：支持独立图片、填充图片、rels 兜底提取，并按二进制内容去重。
- 缓存目录：`pptParseResult/{ppt_name}_{md5}/content.md`。

## 故障处理

- 文件不存在：抛出 `FileNotFoundError`。
- 部分形状解析异常：记录日志后继续解析其余内容。
- 图片尺寸识别失败：`size` 置为 `[0, 0]`，不影响整体结果。
