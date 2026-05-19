#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXTRACTOR="${SCRIPT_DIR}/extract_mcp_image.py"

MCP_URL="${MCP_URL:-http://proxy.agent.tbox.cn/proxy/multimodal-model-mcp/mcp}"
OUT_DIR="/Users/chenqingyang/Pictures/redbook"
REQUEST_ID="req"
PROMPT_FILE=""
PROMPT_TEXT=""
PROMPT_DIR=""
KEEP_PROMPT_FILE="false"
ASPECT_RATIO="3:4"
IMAGE_SIZE="2K"
MIME_TYPE="image/png"
MAX_RETRIES="2"
CREATED_PROMPT_FILE=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --prompt-file)
      PROMPT_FILE="$2"
      shift 2
      ;;
    --out-dir)
      OUT_DIR="$2"
      shift 2
      ;;
    --prompt-text)
      PROMPT_TEXT="$2"
      shift 2
      ;;
    --prompt-dir)
      PROMPT_DIR="$2"
      shift 2
      ;;
    --keep-prompt-file)
      KEEP_PROMPT_FILE="$2"
      shift 2
      ;;
    --request-id)
      REQUEST_ID="$2"
      shift 2
      ;;
    --aspect-ratio)
      ASPECT_RATIO="$2"
      shift 2
      ;;
    --image-size)
      IMAGE_SIZE="$2"
      shift 2
      ;;
    --mime-type)
      MIME_TYPE="$2"
      shift 2
      ;;
    --max-retries)
      MAX_RETRIES="$2"
      shift 2
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 1
      ;;
  esac
done

if [[ -n "${PROMPT_FILE}" && -n "${PROMPT_TEXT}" ]]; then
  echo "Provide only one of --prompt-file or --prompt-text" >&2
  exit 1
fi

if [[ -z "${PROMPT_FILE}" && -z "${PROMPT_TEXT}" ]]; then
  echo "Missing prompt input: use --prompt-file or --prompt-text" >&2
  exit 1
fi

if [[ ! -f "${EXTRACTOR}" ]]; then
  echo "Extractor not found: ${EXTRACTOR}" >&2
  exit 1
fi

mkdir -p "${OUT_DIR}"

if [[ -z "${PROMPT_DIR}" ]]; then
  PROMPT_DIR="${OUT_DIR}/.tmp_prompts"
fi

mkdir -p "${PROMPT_DIR}"

if [[ -n "${PROMPT_TEXT}" ]]; then
  PROMPT_FILE="${PROMPT_DIR}/prompt_${REQUEST_ID}_$(date +%Y%m%d_%H%M%S).txt"
  printf "%s" "${PROMPT_TEXT}" > "${PROMPT_FILE}"
  CREATED_PROMPT_FILE="${PROMPT_FILE}"
fi

if [[ -n "${PROMPT_FILE}" && ! -f "${PROMPT_FILE}" ]]; then
  echo "Prompt file not found: ${PROMPT_FILE}" >&2
  exit 1
fi

if [[ -n "${PROMPT_FILE}" ]]; then
  case "${PROMPT_FILE}" in
    "${OUT_DIR}"/*) ;;
    *)
      LOCAL_PROMPT_FILE="${PROMPT_DIR}/prompt_${REQUEST_ID}_$(date +%Y%m%d_%H%M%S).txt"
      cp "${PROMPT_FILE}" "${LOCAL_PROMPT_FILE}"
      PROMPT_FILE="${LOCAL_PROMPT_FILE}"
      CREATED_PROMPT_FILE="${LOCAL_PROMPT_FILE}"
      ;;
  esac
fi

PROMPT_CONTENT="$(<"${PROMPT_FILE}")"
TMP_ROOT="$(mktemp -d)"

cleanup() {
  rm -rf "${TMP_ROOT}"
  if [[ "${KEEP_PROMPT_FILE}" != "true" && -n "${CREATED_PROMPT_FILE}" && -f "${CREATED_PROMPT_FILE}" ]]; then
    rm -f "${CREATED_PROMPT_FILE}"
  fi
}
trap cleanup EXIT

run_once() {
  local attempt="$1"
  local run_dir="${TMP_ROOT}/attempt_${attempt}"
  local boot_headers="${run_dir}/boot.headers"
  local init_out="${run_dir}/init.sse"
  local call_out="${run_dir}/call.sse"
  local out_file=""
  local timestamp=""

  mkdir -p "${run_dir}"

  curl -sS -D "${boot_headers}" \
    -H "Accept: application/json" \
    "${MCP_URL}" -o /dev/null || true

  SESSION_ID="$(awk 'tolower($1)=="mcp-session-id:" {print $2}' "${boot_headers}" | tr -d '\r' | tail -n 1)"

  if [[ -z "${SESSION_ID}" ]]; then
    echo "Failed to acquire mcp-session-id from ${MCP_URL}" >&2
    return 1
  fi

  curl -sS -N \
    -H "Accept: application/json, text/event-stream" \
    -H "Content-Type: application/json" \
    -H "mcp-session-id: ${SESSION_ID}" \
    -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"redbook-skill","version":"1.0.0"}}}' \
    "${MCP_URL}" > "${init_out}"

  curl -sS -N \
    -H "Accept: application/json, text/event-stream" \
    -H "Content-Type: application/json" \
    -H "mcp-session-id: ${SESSION_ID}" \
    -d '{"jsonrpc":"2.0","method":"notifications/initialized","params":{}}' \
    "${MCP_URL}" > /dev/null

  PAYLOAD=$(python3 - <<'PY' "${PROMPT_CONTENT}" "${ASPECT_RATIO}" "${IMAGE_SIZE}" "${MIME_TYPE}"
import json
import sys

prompt = sys.argv[1]
aspect_ratio = sys.argv[2]
image_size = sys.argv[3]
mime_type = sys.argv[4]

body = {
    "jsonrpc": "2.0",
    "id": 3,
    "method": "tools/call",
    "params": {
        "name": "generate_image",
        "arguments": {
            "prompt": prompt,
            "aspectRatio": aspect_ratio,
            "imageSize": image_size,
            "mimeType": mime_type,
            "referenceImageUrls": [],
            "referenceImageMimeType": "image/png",
        },
    },
}
print(json.dumps(body, ensure_ascii=False))
PY
)

  curl -sS -N \
    -H "Accept: application/json, text/event-stream" \
    -H "Content-Type: application/json" \
    -H "mcp-session-id: ${SESSION_ID}" \
    -d "${PAYLOAD}" \
    "${MCP_URL}" > "${call_out}"

  timestamp="$(date +%Y%m%d_%H%M%S)"
  out_file="${OUT_DIR}/redbook_cover_${REQUEST_ID}_${timestamp}.png"

  python3 "${EXTRACTOR}" --input "${call_out}" --output "${out_file}"
}

retry_backoff_seconds() {
  local retry_index="$1"
  if [[ "${retry_index}" -eq 1 ]]; then
    echo "0.4"
  elif [[ "${retry_index}" -eq 2 ]]; then
    echo "1.2"
  else
    echo "2.0"
  fi
}

if ! [[ "${MAX_RETRIES}" =~ ^[0-9]+$ ]]; then
  echo "--max-retries must be a non-negative integer" >&2
  exit 1
fi

attempt=0
while true; do
  if run_once "${attempt}"; then
    exit 0
  fi

  if [[ "${attempt}" -ge "${MAX_RETRIES}" ]]; then
    break
  fi

  retry_no=$((attempt + 1))
  sleep "$(retry_backoff_seconds "${retry_no}")"
  attempt=$((attempt + 1))
done

echo "Image generation/save failed after $((MAX_RETRIES + 1)) attempts" >&2
exit 1
