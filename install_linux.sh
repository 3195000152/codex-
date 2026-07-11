#!/usr/bin/env bash
set -euo pipefail

APP_ID="codex-provider-repair"
APP_NAME="Codex 对话恢复与清理工具"
SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
APP_DIR="$DATA_HOME/$APP_ID"
BIN_DIR="$HOME/.local/bin"
DESKTOP_DIR="$DATA_HOME/applications"
WRAPPER="$BIN_DIR/$APP_ID"
DESKTOP_FILE="$DESKTOP_DIR/$APP_ID.desktop"

mkdir -p "$APP_DIR" "$BIN_DIR" "$DESKTOP_DIR"

cp "$SOURCE_DIR/provider_repair_gui.py" "$APP_DIR/"
cp "$SOURCE_DIR/start_provider_repair.sh" "$APP_DIR/"
cp "$SOURCE_DIR/LICENSE" "$APP_DIR/"
cp "$SOURCE_DIR/README.md" "$APP_DIR/"
rm -rf "$APP_DIR/assets"
cp -R "$SOURCE_DIR/assets" "$APP_DIR/assets"
chmod +x "$APP_DIR/start_provider_repair.sh"

cat >"$WRAPPER" <<EOF
#!/usr/bin/env bash
set -euo pipefail

export CODEX_PROVIDER_REPAIR_BACKUP_DIR="\${XDG_DATA_HOME:-\$HOME/.local/share}/$APP_ID/backups"
exec "$APP_DIR/start_provider_repair.sh" "\$@"
EOF
chmod +x "$WRAPPER"

cat >"$DESKTOP_FILE" <<EOF
[Desktop Entry]
Type=Application
Name=$APP_NAME
Comment=修复和清理 Codex 对话记录
Exec=$WRAPPER
Icon=$APP_DIR/assets/panel-preview.png
Terminal=false
Categories=Utility;
StartupNotify=true
EOF
chmod 644 "$DESKTOP_FILE"

if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database "$DESKTOP_DIR" >/dev/null 2>&1 || true
fi

cat <<EOF
安装完成。

你现在可以在应用菜单中搜索并打开：
  $APP_NAME

也可以在终端运行：
  $APP_ID

如果终端提示找不到命令，请把 ~/.local/bin 加到 PATH。
EOF
