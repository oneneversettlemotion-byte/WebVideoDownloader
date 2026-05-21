#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

# 优先使用 python3.11
if command -v python3.11 >/dev/null 2>&1; then
  PYTHON=python3.11
elif command -v python3 >/dev/null 2>&1; then
  PYTHON=python3
else
  echo "❌ 未找到 Python 3，请先安装 Python 3.11"
  exit 1
fi

echo "🐍 使用 $($PYTHON --version)"

# 安装依赖
$PYTHON -m pip install -q -r requirements.txt

# 启动
exec $PYTHON server.py
