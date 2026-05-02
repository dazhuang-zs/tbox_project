---
name: doc-writing-skill
description: Generate structured Chinese Markdown documents using built-in text-file reading, with optional MCP image generation and explicit save-directory reporting.
license: Proprietary
compatibility: opencode
metadata:
  audience: knowledge-worker
  workflow: longform-writing
  language: zh-CN
---

## What I do

I orchestrate an end-to-end document writing workflow:

1. Parse user request and infer a suitable writing genre.
2. Read only necessary plain-text files using built-in capabilities.
3. Apply genre-specific structure and quality constraints.
4. Generate complete Markdown content.
5. Optionally call MCP `generate_image` for illustrations.
6. Save output and explicitly report document directory and full path.

I do not process binary files (docx, xlsx, pdf, image OCR) in this skill.

## When to use me

Use this skill when the user asks for:

- Business plans, proposals, reports, meeting minutes, work summaries.
- PRD, technical docs, speech drafts, and social-style longform copy.
- Structured Markdown output with clear section hierarchy.

Avoid this skill for binary file understanding tasks.

## Runtime dependency (optional MCP)

This skill can optionally use MCP server alias `multimodal-model` with tool `generate_image`.

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

## Input contract

Required fields:

- `request_id`
- `task`

Recommended fields:

- `genre` (`business_plan`, `proposal`, `report_business`, `meeting_minutes`, `work_summary`, `prd`, `tech_doc`, `wechat_official`, `xiaohongshu`, `others`)
- `topic`
- `target_word_range` (example: `1500-2500`)
- `output_name` (without extension)
- `output_dir` (optional absolute directory path)
- `need_image` (default `false`)
- `tone`, `audience`, `must_include`, `must_avoid`
- `context_files` (plain-text file paths only)

## Execution rules

1. Start with a brief professional restatement of user objective, then execute directly.
2. Read only user-provided or clearly relevant plain-text files.
3. Do not ask follow-up questions unless critical information is missing.
4. Enforce Markdown-only output and clear heading hierarchy (`#`, `##`, `###`).
5. Prefer Chinese full-width punctuation in Chinese prose.
6. If `need_image=true`, generate only necessary images and embed with Markdown image syntax.
7. If image generation fails, continue with text-only deliverable.
8. Save output as `DOC_{output_name or inferred_name}.md`.

Tool budget:

- External generation tools total <= 6 calls.
- Keep workflow concise and avoid exploratory overuse.

## Save behavior

- Default save directory is current working directory (`cwd`).
- If `output_dir` is provided, save file to that directory.
- Always resolve absolute save path before returning success.
- After save, explicitly tell user:
  - document directory
  - file name
  - absolute file path

Required user-facing save message format:

- `文档已生成到目录：{output_dir}`
- `文件名：{file_name}`
- `完整路径：{file_path}`

## Genre policy (compact)

- `business_plan`: formal, persuasive, data-backed business framework.
- `proposal`: problem-solution-benefit with execution plan.
- `report_business`: objective analytical report, source-aware where needed.
- `meeting_minutes`: concise factual record with clear action items.
- `work_summary`: outcome-first recap with metrics and next steps.
- `prd`: structured requirements, user scenarios, constraints, acceptance criteria.
- `tech_doc`: setup-first, examples, troubleshooting, and FAQ clarity.
- `wechat_official`: readable narrative with practical insight.
- `xiaohongshu`: lightweight social tone with practical tips.
- `others`: general professional writing standard.

## Output contract

Always return JSON with:

- `request_id`
- `status` (`ok` | `partial` | `error`)
- `data.output_dir` (absolute directory path)
- `data.file_name`
- `data.file_path` (absolute file path)
- `data.saved_message` (human-readable save result)
- `data.title`
- `data.genre_used`
- `data.word_count`
- `data.image_used`
- `data.context_files_used`
- `error` (null or structured error)

Status behavior:

- `ok`: document generated and saved successfully with valid absolute file path.
- `partial`: document saved but optional image step failed.
- `error`: failed before producing a usable document.

Strict `ok` criteria:

- Must include non-empty absolute `data.file_path`.
- Must include non-empty absolute `data.output_dir`.
- Must include non-empty `data.file_name`.

## Error model

Use stable error codes:

- `INVALID_INPUT`
- `FILE_READ_FAILED`
- `IMAGE_TOOL_ERROR`
- `WRITE_FAILED`
- `INTERNAL_ERROR`

## Safety and quality guardrails

- Do not fabricate citations or unverifiable claims as facts.
- Keep structure complete, concise, and internally consistent.
- Use professional tone unless user explicitly requests another style.
- Do not output HTML/CSS/JS wrappers.
- Never claim save success without real absolute save path.

## Local validation checklist

1. Confirm file path is `~/.config/opencode/skills/doc-writing-skill/SKILL.md`.
2. Confirm frontmatter `name` is `doc-writing-skill`.
3. Confirm skill can be discovered by opencode skill loader.
4. Confirm generated files report directory, file name, and absolute path.
5. If image mode is used, confirm MCP `multimodal-model` is enabled.
