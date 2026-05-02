---
name: redbook
description: Generate Xiaohongshu-style copy and optional cover image via MCP `generate_image`, with structured JSON output and graceful fallback.
license: Proprietary
compatibility: opencode
metadata:
  audience: content-ops
  workflow: copy-plus-image
  language: zh-CN
---

## What I do

I orchestrate a complete Redbook draft workflow:

1. Generate post copy (`titles`, `body`, `hashtags`).
2. Generate a `visual_prompt` aligned to the copy.
3. Optionally call MCP tool `generate_image` for cover generation.
4. Auto-save generated image to local filesystem when image is generated.
5. Return a machine-consumable JSON payload with stable error handling.

I do not call vendor model APIs directly. I only use configured MCP tools.

## When to use me

Use this skill when the user asks for:

- Xiaohongshu/Redbook post drafting.
- Title optimization plus body copy generation.
- Hashtag suggestions for discoverability.
- A cover-image prompt or direct image generation.

Avoid this skill for pure long-form article writing, non-social content workflows, or tasks unrelated to post generation.

## Runtime dependency (MCP)

This skill expects an MCP server alias `multimodal-model` with tool `generate_image`.

```json
{
  "mcp": {
    "multimodal-model": {
      "type": "remote",
      "url": "http://proxy.agent.tbox.cn/proxy/multimodal-model-mcp/mcp",
      "enabled": true
    }
  }
}
```

Expected tool contract:

- Tool: `generate_image`
- Required input: `prompt: string`
- Optional input: `aspectRatio`, `imageSize`, `mimeType`, `referenceImageUrls`, `referenceImageMimeType`
- Output: `image` (base64), optional `text`

## Input contract

Required fields:

- `request_id`
- `topic`

Recommended fields:

- `audience`, `tone`, `goal`
- `need_image` (default `true`)
- `save_image` (default `true`)
- `mode` (default `fast`, optional `debug`)
- `save_options` with `output_dir`, `file_name`, `file_name_prefix`
- `cover_text_spec` (recommended when `need_image=true`)
- `cover_layout_mode` (default `auto`; candidates: `title-top`, `title-left`, `center-poster`, `card-overlay`, `magazine-split`)
- `visual_style_family` (default `auto`; e.g. `clean-lifestyle`, `new-chinese`, `editorial`, `filmic`)
- `image_requirements` with `style`, `aspect_ratio`, `image_size`, `mime_type`, `reference_image_urls`
- `constraints` with `max_title_count`, `max_hashtag_count`, `body_length_hint`

`cover_text_spec` fields:

- `title` (strongly recommended; used as the page-1 cover title)
- `subtitle` (optional; used as secondary text on page-1 cover)
- `highlight_words` (optional list)

`cover_layout_mode` behavior:

- `auto`: select one layout mode from the layout pool based on topic/style.
- explicit mode: force the specified layout mode.
- retry: must switch to a different layout mode from previous failed attempt.

Example input:

```json
{
  "request_id": "req_20260304_001",
  "topic": "summer commute outfits",
  "audience": "female office workers age 25-30",
  "tone": "authentic",
  "goal": "product-seeding",
  "need_image": true,
  "save_image": true,
  "save_options": {
    "output_dir": "/Users/chenqingyang/Pictures/redbook",
    "file_name_prefix": "redbook_cover"
  },
  "cover_text_spec": {
    "title": "夏日通勤穿搭｜3套不费力高级感",
    "subtitle": "30秒出门也能好看",
    "highlight_words": ["通勤", "高级感", "不费力"]
  },
  "image_requirements": {
    "style": "clean lifestyle",
    "aspect_ratio": "3:4",
    "image_size": "2K",
    "mime_type": "image/png",
    "reference_image_urls": []
  },
  "constraints": {
    "max_title_count": 3,
    "max_hashtag_count": 8,
    "body_length_hint": 450
  }
}
```

## Execution rules

1. Validate required fields and normalize defaults.
2. Draft `titles`, `body`, `hashtags` first, then build page-1 `[封面]` spec.
3. For page-1 `[封面]`, always produce: `标题`, `副标题`, `背景/场景`, `版式建议`, `视觉关键词`.
4. When `need_image=true`, enforce page-1 cover text requirements before image generation.
5. Build `visual_prompt` with structured sections aligned to image generation requirements.
6. Call `generate_image` once and immediately attempt local save.
7. If generation/save fails, retry with fallback-C raw MCP save pipeline (max 2 retries).
8. If retry still fails, return copy-only result with `status=partial`.
9. Keep output schema stable for upstream automation.

Single-turn generation contract:

- Normal path must complete in one conversation turn: `generate_image -> save -> return saved_path`.
- Do not claim success unless image binary payload is present and file is actually written.
- If tool response has text-only content or missing image payload, treat as generation failure and trigger retry.
- Retry is only for actual generation/save failure; no extra exploratory steps on success path.
- In `fast` mode, do not run MCP connectivity diagnostics (`ping`, `tools/list`, manual `curl`, protocol probing).

Fallback-C retry behavior (required on first failure):

- Retry path must use script: `/Users/chenqingyang/.config/opencode/skills/redbook/mcp_generate_and_save.sh`.
- This retry performs one atomic operation: raw MCP `tools/call(generate_image)` + payload extraction + local file write.
- This is the only allowed retry in `fast` mode.
- Do not run separate `ping`, `tools/list`, or manual protocol debugging before/after retry.
- Retry limit for fallback-C is `2`.
- On each retry, switch `cover_layout_mode` to a different mode (do not reuse previous failed layout).

Image auto-save rules:

- Default `save_image=true`.
- Default output directory: `/Users/chenqingyang/Pictures/redbook`.
- If `save_options.output_dir` is provided, use it; create directory if missing.
- File naming priority:
  1) `save_options.file_name` when provided
  2) `{file_name_prefix}_{request_id}_{YYYYMMDD_HHMMSS}.png`
  3) `redbook_{request_id}_{YYYYMMDD_HHMMSS}.png`
- Save using PNG binary decoded from tool output image base64.
- Success criteria for `saved=true`: image payload exists, file write succeeds, and absolute local path exists.
- If save fails, set `status=partial` and return `IMAGE_SAVE_FAILED` while preserving copy and generation metadata.
- Always return absolute `saved_path` and a user-facing `saved_message`.

Fallback-C save command:

```bash
bash "/Users/chenqingyang/.config/opencode/skills/redbook/mcp_generate_and_save.sh" \
  --prompt-text "<visual_prompt>" \
  --out-dir "<output_dir>" \
  --request-id "<request_id>" \
  --max-retries "2"
```

Prompt file requirement:

- Preferred: pass `--prompt-text` directly.
- If a prompt file is needed, store it under `<output_dir>/.tmp_prompts/` only.
- Do not place prompt files under the skill source directory.
- Default behavior should auto-clean temporary prompt files after generation.

Page-1 cover hard requirements (quality gate):

- The first image is always treated as `[封面]`.
- Cover must include a clearly readable title text. Image without title text is invalid.
- If `cover_text_spec.title` exists, the rendered title must match it verbatim (character-level, no omission, no paraphrase).
- If `cover_text_spec.subtitle` exists, render it as secondary text under or near the title.
- Title is dominant visual hierarchy (largest text block), with high contrast and mobile readability.
- Keep portrait `3:4`; no rotated/upside-down layout.
- No phone frame, no white border, no Xiaohongshu logo, no user id watermark, no corner watermark.
- Cover must follow first-page semantics from outline requirements: title page with `标题 + 副标题` and strong hook value.

Cover visual prompt requirements (must be included in `visual_prompt` when generating image):

- Use concise Chinese-only instructions; avoid mixed Chinese-English imperative patterns.
- Follow this structured order in prompt body:
  1) 页面内容
  2) 页面类型
  3) 设计要求（整体风格/文字排版/视觉元素）
  4) 页面类型特殊要求（重点写 `[封面]`）
  5) 技术规格
  6) 整体风格一致性
- Use explicit Chinese text-lock wording: `标题：<TITLE>` and `副标题：<SUBTITLE>` and require verbatim rendering.
- Explicitly require clear Chinese typography and mobile legibility.
- Explicitly forbid text omission, gibberish, decorative replacement symbols, and watermark/logo artifacts.

Layout pool (for diversity):

- `title-top`: top headline block + lower scene narrative.
- `title-left`: left vertical text block + right subject focus.
- `center-poster`: centered title card + symmetric visual balance.
- `card-overlay`: semi-transparent text card over scene focal area.
- `magazine-split`: split composition with editorial title system.

Style pool (for diversity):

- `clean-lifestyle`
- `new-chinese`
- `editorial`
- `filmic`

Recommended high-yield cover prompt template:

```text
请生成一张小红书风格的图文封面图片（必须直接输出图片，不要输出任何解释文字）。

页面内容：
- 主题：{topic}
- 背景/场景：{scene_elements}
- 视觉关键词：{visual_keywords}

页面类型：封面（第一页）

设计要求：
1. 整体风格
- 选择风格家族：{visual_style_family}
- 风格描述：{style_hint}
- 清新、精致、有设计感，适合手机端浏览

2. 文字排版
- 标题与副标题必须完整、逐字一致
- 标题为最大视觉层级，副标题次级
- 文字清晰可读，留白合理，信息层次清楚

3. 视觉元素
- 元素适度，不堆满，避免画面脏乱
- 强化节日/主题识别元素，但保持高级感

4. 页面类型特殊要求（[封面]）
- 版式模式：{cover_layout_mode}
- 标题占据主要信息入口，副标题辅助说明
- 需要一眼吸引点击，具备封面冲击力

5. 技术规格
- 竖版 3:4 比例
- 高清画质
- 适合手机屏幕查看
- 排版不可旋转、倒置、镜像

6. 整体风格一致性
- 色调、字体气质、装饰语言保持统一

封面文案（必须完整出现，逐字一致）：
标题：{cover_title}
副标题：{cover_subtitle}

禁止项（硬性）：
- 禁止白边、手机边框、logo、水印、账号名、角标
- 禁止漏字、错字、乱码、装饰符号替代文案

只返回最终图片。
```

Image-first retry prompt (when first attempt returns text/no image):

```text
请重试并只输出图片。保持同一主题与文案，优先保证标题与副标题清晰完整，其他装饰元素可减少。
本次重试必须切换到不同的 `cover_layout_mode`，不得复用上次失败版式。
```

Mapping to MCP arguments:

```json
{
  "prompt": "{visual_prompt}",
  "aspectRatio": "{image_requirements.aspect_ratio | default 1:1}",
  "imageSize": "{image_requirements.image_size | default 2K}",
  "mimeType": "{image_requirements.mime_type | default image/png}",
  "referenceImageUrls": "{image_requirements.reference_image_urls | default []}",
  "referenceImageMimeType": "image/png"
}
```

## Output contract

Always return JSON with:

- `request_id`, `trace_id`, `status`
- `data.titles`, `data.body`, `data.hashtags`, `data.visual_prompt`
- `data.cover.title_render_required` (boolean)
- `data.cover.title_text`, `data.cover.subtitle_text`
- `data.cover.layout_mode_used`
- `data.cover.visual_keywords_used`
- `data.image.generated` and related image fields
- `data.image.saved` (boolean)
- `data.image.saved_path` (absolute path or `null`)
- `data.image.saved_message` (human-readable save result)
- `error` (or `null`)
- `meta.mcp_server`, `meta.mcp_tool`, optional `meta.latency_ms`

Status behavior:

- `ok`: copy generation succeeds, and image step (if requested) succeeds.
- `partial`: copy generation succeeds but image step fails.
- `error`: validation/system failure before usable copy is produced.

Strict `ok` criteria:

- `status=ok` requires all of: `data.image.generated=true`, `data.image.saved=true`, non-null absolute `data.image.saved_path`.
- If any of the above is missing, return `status=partial` or `status=error` (never `ok`).

Cover text quality behavior:

- If cover generation result is missing required title text, treat as image-step failure.
- Retry once with strengthened cover-text/image-first constraints via fallback-C save script.
- If first attempt returns text-only or no image payload, fallback-C retry is mandatory.
- Total retries allowed after first failure: up to `2`.
- Each retry must switch layout mode for diversity and failure recovery.

Save behavior:

- `ok`: image generation succeeds and file save succeeds.
- `partial`: copy succeeds, but image generation fails or file save fails.

## Error model

Use these stable error codes:

- `INVALID_INPUT`
- `MCP_UNAVAILABLE`
- `MCP_TIMEOUT`
- `MCP_TOOL_ERROR`
- `IMAGE_INVALID_RESPONSE`
- `IMAGE_SAVE_FAILED`
- `INTERNAL_ERROR`

Recommended retry policy:

- Max retries: `2` (two retries after first failure)
- Backoff: `400ms`, then `1200ms`
- Retry on: `MCP_UNAVAILABLE`, `MCP_TIMEOUT`, `MCP_TOOL_ERROR`, `IMAGE_INVALID_RESPONSE`, `IMAGE_SAVE_FAILED`
- No retry on: `INVALID_INPUT`
- No diagnostic tool-chain retries in `fast` mode.

## Safety and quality guardrails

- Do not hardcode secrets.
- Keep MCP endpoint configurable (env/config).
- Refuse disallowed or unsafe content generation requests.
- Avoid unverifiable claims, medical/legal guarantees, or fabricated product facts.
- Keep style platform-native: practical, specific, and readable.
- For cover image, never output a title-less design when title is required.
- Prioritize text readability over decorative complexity on the cover.
- Never claim auto-save success without a real absolute saved path.
- In non-debug runs, do not perform connectivity/protocol probing before generation.

## Fallback-C scripts

- Raw MCP save runner: `/Users/chenqingyang/.config/opencode/skills/redbook/mcp_generate_and_save.sh`
- SSE image extractor: `/Users/chenqingyang/.config/opencode/skills/redbook/extract_mcp_image.py`

Usage notes:

- The retry script returns saved absolute path on stdout when successful.
- If script exits non-zero, treat as retry failure and return `IMAGE_SAVE_FAILED`.
- Keep `status=ok` only when returned path exists locally.
- Script default temp prompt directory: `<output_dir>/.tmp_prompts/`.

## Local validation checklist

1. Confirm file path is exactly `~/.config/opencode/skills/redbook/SKILL.md`.
2. Confirm frontmatter `name` equals directory name: `redbook`.
3. Verify this skill appears in `<available_skills>` in tool description.
4. If missing, check permission config in `opencode.json` (`skill.redbook` not denied).
5. Test MCP connectivity with inspector:

```bash
npx -y @modelcontextprotocol/inspector@0.21.1 --url http://proxy.agent.tbox.cn/proxy/multimodal-model-mcp/mcp
```

6. Validate local save path permissions (default: `/Users/chenqingyang/Pictures/redbook`).
7. Ensure fallback scripts are executable.
