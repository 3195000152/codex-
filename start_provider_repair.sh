#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

PYTHON_BIN="${PYTHON:-python3}"

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "未找到 Python：$PYTHON_BIN"
  echo "请先安装 Python 3.8 或更高版本。"
  exit 1
fi

if ! "$PYTHON_BIN" - <<'PY' >/dev/null 2>&1
import tkinter
PY
then
  cat <<'EOF'
当前 Python 缺少 Tkinter，无法启动图形界面。

常见安装方式：
  Ubuntu/Debian: sudo apt install python3-tk
  Fedora:        sudo dnf install python3-tkinter
  Arch Linux:    sudo pacman -S tk

安装完成后重新运行本脚本。
EOF
  exit 1
fi

exec "$PYTHON_BIN" provider_repair_gui.py
