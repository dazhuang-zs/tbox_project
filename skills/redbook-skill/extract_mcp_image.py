#!/usr/bin/env python3
import argparse
import base64
import json
import os
import re
import sys
from typing import Optional


def _decode_json_escaped(raw: str) -> str:
    try:
        return json.loads(f'"{raw}"')
    except Exception:
        return raw


def _extract_image_b64(raw: str) -> Optional[str]:
    patterns = [
        r'"type"\s*:\s*"image"\s*,\s*"data"\s*:\s*"([^"]+)"',
        r'"inlineData"\s*:\s*\{[^\}]*"data"\s*:\s*"([^"]+)"',
        r'"inline_data"\s*:\s*\{[^\}]*"data"\s*:\s*"([^"]+)"',
    ]
    for pattern in patterns:
        match = re.search(pattern, raw)
        if match:
            return _decode_json_escaped(match.group(1))
    return None


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Extract image base64 from MCP SSE output and save PNG."
    )
    parser.add_argument(
        "--input", required=True, help="Path to MCP SSE raw output file"
    )
    parser.add_argument("--output", required=True, help="Absolute output PNG file path")
    args = parser.parse_args()

    with open(args.input, "r", encoding="utf-8", errors="ignore") as file_obj:
        raw = file_obj.read()

    image_b64 = _extract_image_b64(raw)
    if not image_b64:
        print("IMAGE_PAYLOAD_NOT_FOUND", file=sys.stderr)
        return 2

    try:
        image_bytes = base64.b64decode(image_b64, validate=True)
    except Exception:
        print("IMAGE_BASE64_INVALID", file=sys.stderr)
        return 3

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "wb") as file_obj:
        file_obj.write(image_bytes)

    if not os.path.exists(args.output) or os.path.getsize(args.output) <= 0:
        print("IMAGE_WRITE_FAILED", file=sys.stderr)
        return 4

    print(os.path.abspath(args.output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
