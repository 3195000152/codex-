#!/usr/bin/env bash
set -euo pipefail

APP_ID="codex-provider-repair"
DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
APP_DIR="$DATA_HOME/$APP_ID"
BIN_PATH="$HOME/.local/bin/$APP_ID"
DESKTOP_FILE="$DATA_HOME/applications/$APP_ID.desktop"
BACKUP_DIR="$APP_DIR/backups"

rm -f "$BIN_PATH" "$DESKTOP_FILE"

if [ -d "$BACKUP_DIR" ]; then
  find "$APP_DIR" -mindepth 1 -maxdepth 1 ! -name backups -exec rm -rf {} +
  echo "已卸载程序入口和应用文件，备份目录已保留：$BACKUP_DIR"
else
  rm -rf "$APP_DIR"
  echo "已卸载程序入口和应用文件。"
fi

if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database "$DATA_HOME/applications" >/dev/null 2>&1 || true
fi
