#!/usr/bin/env bash
# 启动 FastAPI 服务（读取 .env 中的 HOST / PORT / DEBUG）
# 若端口已有服务在跑，会先停止旧进程再启动

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

if [[ ! -f .env ]]; then
  echo "缺少 .env，请先执行: cp .env.example .env"
  exit 1
fi

PYTHON="${ROOT}/.venv/bin/python"
if [[ ! -x "$PYTHON" ]]; then
  echo "未找到虚拟环境，请先执行:"
  echo "  python -m venv .venv && .venv/bin/pip install -r requirements.txt"
  exit 1
fi

read_env() {
  local key=$1
  local default_value=${2:-}
  local value
  value=$(grep -E "^${key}=" .env | head -1 | cut -d= -f2- | tr -d '\r"' || true)
  value="${value#"${value%%[![:space:]]*}"}"
  value="${value%"${value##*[![:space:]]}"}"
  if [[ -n "$value" ]]; then
    echo "$value"
  else
    echo "$default_value"
  fi
}

stop_port() {
  local port=$1
  local pids

  pids=$(lsof -nP -iTCP:"${port}" -sTCP:LISTEN -t 2>/dev/null || true)
  if [[ -z "$pids" ]]; then
    return 0
  fi

  echo "端口 ${port} 已有服务运行 (PID: ${pids//$'\n'/ })，正在停止..."
  # shellcheck disable=SC2086
  kill ${pids} 2>/dev/null || true
  sleep 1

  pids=$(lsof -nP -iTCP:"${port}" -sTCP:LISTEN -t 2>/dev/null || true)
  if [[ -n "$pids" ]]; then
    echo "旧进程未退出，强制停止..."
    # shellcheck disable=SC2086
    kill -9 ${pids} 2>/dev/null || true
    sleep 1
  fi
}

PORT=$(read_env PORT 8000)
stop_port "$PORT"

exec "$PYTHON" main.py "$@"
