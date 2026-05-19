# MCP 服务调用详解

本文档详细说明 MCP 服务的调用方式、参数映射和工具选择逻辑。

---

## 前置步骤：获取尺寸信息

在调用MCP工具之前，**必须优先执行 `get_size.py` 脚本**获取模型需要的尺寸配置信息。

**脚本位置**：`skills/image_generation/scripts/get_size.py`

### 调用方式

```bash
# 固定执行方式：用 python 直接运行脚本，传入 JSON 字符串参数
python skills/image_generation/scripts/get_size.py '{"radio":"2048x2048","image_size":"2K"}'
```

> ⚠️ **执行说明**：
> - 必须使用 `python` 命令执行，不得猜测 `.cjs` / `.js` 等其他形式
> - 脚本路径以 `skills/image_generation/scripts/get_size.py` 为准
> - 如果脚本尚不支持命令行参数，在代码末尾添加以下入口即可：
>   ```python
>   if __name__ == "__main__":
>       import sys, json
>       print(json.dumps(get_image_size(json.loads(sys.argv[1]))))
>   ```

### 返回结果

```json
{
    "use_tool1": true,
    "image_size": "2K",
    "image_config": {
        "aspect_ratio": "1:1",
        "image_size": "2K"
    }
}
```

### 字段说明

| 字段                        | 类型 | 说明                                                |
| --------------------------- | ---- | --------------------------------------------------- |
| `use_tool1`                | bool | 是否使用工具1（宽高比符合工具1要求）                |
| `image_size`                | str  | 图片尺寸，优先使用radio值，否则使用image_size值     |
| `image_config`              | dict | 图片配置信息，包含aspect_ratio和image_size          |
| `image_config.aspect_ratio` | str  | 匹配的宽高比（如"16:9"），仅当use_tool1为True时有值 |
| `image_config.image_size`   | str  | 默认的图片尺寸规格（"1K"/"2K"/"4K"）                |

---

## MCP 工具概览

图像生成通过调用 `multimodal-model` MCP 服务，提供两个生图工具：

1. **generate_image_model1_with_watermark** (优先调用，工具1)
2. **generate_image_model2_with_watermark** (降级调用，工具2)

---

## Tool Selector 强制规范

> ⛔ **必须使用点号（`.`）连接 server 名称和工具名称，严禁使用空格。**
>
> ```bash
> # ✅ 正确格式（点号连接）
> mcporter call multimodal-model.generate_image_model1_with_watermark ...
> mcporter call multimodal-model.generate_image_model2_with_watermark ...
>
> # ❌ 错误格式（空格分隔，会导致元数据加载失败或参数位置错位）
> mcporter call multimodal-model generate_image_model1_with_watermark ...
> ```

---

## MCP工具调用优先级

根据 `get_size.py` 返回的 `use_tool1` 字段，决定调用哪个MCP工具。

### 调用逻辑流程

```
步骤1：执行 get_size.py 获取尺寸信息
  └─ 返回 size_result，包含 use_tool1 字段

步骤2：判断是否为图生图（类型3）
  ├─ 如果是图生图（包含 referenceImageUrls）→ 直接调用 generate_image_model2_with_watermark (工具2)
  │  ├─ 如果调用成功 → 返回图片链接
  │  └─ 如果调用失败 或 返回图片链接为空 → 输出"图片生成失败了，请稍后再试。"
  │
  └─ 如果是文生图：根据 use_tool1 判断调用哪个工具
     ├─ 如果 use_tool1 == True
     │  ├─ 优先调用 generate_image_model1_with_watermark (工具1)
     │  │  ├─ 如果调用成功 → 返回图片链接
     │  │  └─ 如果调用失败 或 返回图片链接为空 → 进入降级调用
     │  └─ 降级调用 generate_image_model2_with_watermark (工具2)
     │     ├─ 如果调用成功 → 返回图片链接
     │     └─ 如果调用失败 或 返回图片链接为空 → 输出"图片生成失败了，请稍后再试。"
     │
     └─ 如果 use_tool1 == False
        └─ 直接调用 generate_image_model2_with_watermark (工具2)
           ├─ 如果调用成功 → 返回图片链接
           └─ 如果调用失败 或 返回图片链接为空 → 输出"图片生成失败了，请稍后再试。"
```

### 调用优先级总结

| 场景                      | 优先调用工具                                   | 降级调用工具                                   |
| ------------------------- | ---------------------------------------------- | ---------------------------------------------- |
| 文生图 + use_tool1=True   | `generate_image_model1_with_watermark` (工具1) | `generate_image_model2_with_watermark` (工具2) |
| 文生图 + use_tool1=False  | `generate_image_model2_with_watermark` (工具2) | 无（不调用工具1）                              |
| 图生图（类型3，任何尺寸） | `generate_image_model2_with_watermark` (工具2) | 无                                             |

### 降级调用条件

- 工具1调用失败（网络错误、服务异常、超时等）
- 工具1返回的图片链接为空或无效

### ⚠️ 超时配置（仅工具1，强制要求）

> **工具1生成耗时较长，调用前必须设置环境变量，并在调用时显式传入超时参数，两者缺一不可。工具2无需设置。**

```bash
# 第一步：设置环境变量（覆盖平台默认的60秒）
export MCPORTER_CALL_TIMEOUT=300000
```

| 工具                                          | 环境变量                                    | `--timeout` 参数                |
| --------------------------------------------- | ------------------------------------------- | ------------------------------- |
| 工具1（generate_image_model1_with_watermark） | `MCPORTER_CALL_TIMEOUT=300000` **必须设置** | `--timeout 300000` **必须传入** |
| 工具2（generate_image_model2_with_watermark） | 不需要                                      | 不需要                          |

⛔ 调用工具1时，**严禁**依赖平台默认超时（默认仅60秒），必须同时设置环境变量和 `--timeout 300000`。

### 错误提示输出

当所有工具都调用失败时，输出以下提示：
```
图片生成失败了，请稍后再试。
```

---

## 工具1: generate_image_model1_with_watermark
> ⛔ **调用工具1前，必须先设置超时环境变量，否则默认60秒会导致超时失败。**

### 标准调用格式（key=value 显式传参）

```bash
export MCPORTER_CALL_TIMEOUT=300000
mcporter call multimodal-model.generate_image_model1_with_watermark \
  --timeout 300000 \
  prompt="提示词内容" \
  aspectRatio="16:9" \
  imageSize="2K"
```

> **传参说明**：
> - 字符串参数用引号包裹，如 `prompt="..."` `aspectRatio="16:9"`
> - 数组参数用单引号包裹 JSON，如 `referenceImageUrls='["url1","url2"]'`
> - prompt 含中文、换行、特殊字符时，用单引号包裹：`prompt='中文内容'`

### 参数映射关系

| MCP参数              | 对应skill模块                      | 说明                                                                                    | 示例值                                                                                      |
| -------------------- | ---------------------------------- | --------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------- |
| `prompt`             | 提示词智能提取                     | 图像生成提示词，从提示词数组中取单个元素                                                | `"一只可爱的猫咪在阳光下睡觉"`                                                              |
| `aspectRatio`        | 尺寸参数提取 + get_size.py         | 图片宽高比，从 `image_config.aspect_ratio` 获取                                         | `"16:9"` 或 `"1:1"` 或 `"9:16"`                                                             |
| `imageSize`          | 尺寸参数提取 + get_size.py         | 图片尺寸规格，使用 `image_size` 参数                                                    | `"1K"` 或 `"2K"` 或 `"4K"`                                                                  |
| `referenceImageUrls` | 用户提供的参考图或上一轮生成的图片 | 参考图片的URL列表，图生图时必填。来源包括：1)用户提供的参考图URL；2)上一轮生成的图片URL | `["https://example.com/reference.jpg"]` |

---

## 工具2: generate_image_model2_with_watermark
### 标准调用格式（key=value 显式传参）

```bash
mcporter call multimodal-model.generate_image_model2_with_watermark \
  prompt="提示词内容" \
  size="1920x1080"
```

有参考图时（图生图）：

```bash
mcporter call multimodal-model.generate_image_model2_with_watermark \
  prompt="提示词内容" \
  size="2048x2048" \
  referenceImageUrls='["https://example.com/reference.jpg"]'
```

### 参数映射关系

| MCP参数              | 对应skill模块                      | 说明                                                                                    | 示例值                                                    |
| -------------------- | ---------------------------------- | --------------------------------------------------------------------------------------- | --------------------------------------------------------- |
| `prompt`             | 提示词智能提取                     | 图像生成提示词，从提示词数组中取单个元素                                                | `"一只可爱的猫咪在阳光下睡觉"`                            |
| `size`               | 尺寸参数提取 + get_size.py         | 图片尺寸，使用 `image_size` 参数                                                        | `"2048x2048"` 或 `"1920x1080"` 或 `"2K"`                  |
| `referenceImageUrls` | 用户提供的参考图或上一轮生成的图片 | 参考图片的URL列表，图生图时必填。来源包括：1)用户提供的参考图URL；2)上一轮生成的图片URL | `["https://example.com/reference.jpg"]` |

---

## 传参方式说明

### 唯一合法方式：key=value 显式传参

```bash
mcporter call multimodal-model.generate_image_model1_with_watermark \
  --timeout 300000 \
  prompt="一只猫咪" aspectRatio="1:1" imageSize="2K"
```

- 参数名和值直接展开，不需要 JSON 序列化
- 避免了整段 JSON 字符串在 exec → shell → mcporter 多层传递时的引号、换行、数组、中文被拆坏的风险

> ⛔ **严禁以下传参方式**：
> ```bash
> # 禁止！--args 方式在多层 shell 解析中容易损坏参数
> mcporter call multimodal-model.generate_image_model1_with_watermark \
>   --timeout 300000 \
>   --args '{"prompt":"一只猫咪","aspectRatio":"1:1","imageSize":"2K"}'
>
> # 禁止！--json 方式
> mcporter call multimodal-model.generate_image_model1_with_watermark --json
> ```

---

## 调用次数说明

根据提示词智能提取的类型确定调用次数：

| 类型            | 说明                   | 调用次数                                           |
| --------------- | ---------------------- | -------------------------------------------------- |
| 类型1（宫格）   | 单个提示词描述宫格布局 | 1次                                                |
| 类型2（差异化） | 多个不同的提示词       | N次（等于数组长度）                                |
| 类型3（图生图） | 单个图生图提示词       | 1次（需要传入参考图URL，可能来自用户或上一轮生成） |
| 类型4（常规）   | 多个相同或相似的提示词 | N次（等于数组长度）                                |

---

## 常见错误示例

### ❌ 错误：用户上传图片但识别为常规生图

```bash
# 用户请求：[上传了一张图片] 生成一张春节海报
# 错误：识别为类型4（常规生图），没有获取参考图

# 错误调用（缺少referenceImageUrls参数）：
export MCPORTER_CALL_TIMEOUT=300000
mcporter call multimodal-model.generate_image_model1_with_watermark \
  --timeout 300000 \
  prompt="春节海报" aspectRatio="1:1" imageSize="2K"

# 结果：生成了一张全新的春节海报，没有参考用户上传的图片
```

### ✅ 正确做法

```bash
# 正确：识别为类型3（图生图），提取用户上传的图片URL，只能走 model2
mcporter call multimodal-model.generate_image_model2_with_watermark \
  prompt="基于参考图生成春节海报，保持原图风格和元素" \
  size="2048x2048" \
  referenceImageUrls='["https://user-uploaded.example.com/image.jpg"]'

# 结果：基于用户上传的图片生成春节海报，保留了原图的风格和元素
```

### ❌ 错误：tool selector 用空格分隔

```bash
# 错误！空格分隔会导致元数据加载失败或参数位置错位
mcporter call multimodal-model generate_image_model1_with_watermark ...

# 正确：必须用点号连接
mcporter call multimodal-model.generate_image_model1_with_watermark ...
```

**关键提示**：
- 用户上传图片时，**必须优先检查图片附件**，无论用户描述如何
- 详细的类型识别优先级见[提示词类型详细说明](prompt_types.md#意图识别流程)
