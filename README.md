# Codex 对话恢复与清理工具

用于修复 Codex 在切换中转站、供应商或 `model_provider` 后，历史对话无法恢复、聊天窗口消失、打开旧对话报错的问题，并支持聊天清理与批量删除。

![工具界面预览](assets/panel-preview.png)

当前版本支持识别当前供应商链接、统计聊天记录内存、区分聊天窗口与归档对话，并提供安全备份后的清理与修复能力。

## 这个工具能做什么

- 自动识别当前正在使用的 Provider
- 自动识别当前供应商链接和 Codex 配置里实际使用的链接
- 扫描聊天窗口、归档对话、历史会话文件
- 显示聊天数量、已同步数量、总聊天记录内存
- 显示每条聊天记录对应的内存占用
- 支持单选、批量勾选删除聊天记录
- 删除前自动备份数据库、会话文件和配置
- 修复 `config.toml` 中缺失的历史 provider 映射
- 识别并修复 `openai` 等保留内置 provider ID 被当作自定义配置名使用的问题
- 在需要时可高级重写历史记录中的 provider 名称

## 适用场景

- 切换中转站后，旧对话打不开
- 更换供应商后提示找不到 `model_provider`
- 聊天列表里还有记录，但点开报错
- 想批量清理聊天窗口或归档对话
- 想确认当前到底连的是哪个供应商地址

## 当前版本的修复思路

默认优先修复配置，而不是直接篡改历史记录。

这样做更稳：

- 旧聊天原始 provider 信息会尽量保留
- 只给当前配置补上兼容别名
- 后面再次切换供应商时，不容易把历史彻底改乱

如果你明确需要，也可以使用高级模式，把数据库和会话文件里的历史 provider 统一改成当前 provider。

## 主要功能说明

### 1. 扫描

扫描以下内容：

- `config.toml`
- `state_5.sqlite`
- `sessions`
- `archived_sessions`

会显示：

- 当前 Provider
- 当前供应商
- 当前供应商链接
- Codex 配置当前使用的链接
- 聊天窗口数量
- 归档对话数量
- 已同步数量
- 总聊天记录内存

### 2. 备份并修复配置

适合大多数“旧聊天打不开”的情况。

逻辑是：

1. 自动识别当前实际启用的供应商配置
2. 备份 `config.toml`
3. 将 `openai` 等保留的内置 provider ID 重命名为安全的自定义名称，例如 `openai-custom`
4. 将历史聊天里出现过、但当前配置缺失的 provider 名称补成兼容别名
5. 让这些历史 provider 指向当前可用的供应商配置

### 3. 高级重写历史

这个功能更激进，会直接修改：

- 数据库 `threads.model_provider`
- 会话文件首行 `session_meta.payload.model_provider`

只有在你确认需要统一历史 provider 时再使用。

### 4. 聊天管理

支持：

- 查看聊天窗口和归档对话
- 显示每条聊天记录内存
- 单个勾选
- 全选
- 清空勾选
- 批量删除

删除时会同步处理：

- 数据库记录
- `session_index.jsonl`
- 对应的会话文件

## 备份机制

程序会在修复或删除前自动备份数据库、会话文件和配置。

备份位置：

- Windows 双击或从源码目录直接运行时：当前目录下的 `备份/`
- Linux 安装为桌面应用后：`~/.local/share/codex-provider-repair/backups/`

这样既保留了源码目录直接运行的便携性，也避免 Linux 桌面启动时把备份散落到不明确的位置。

## 默认目录

默认扫描：

```text
~/.codex
```

你也可以在界面里手动切换到其他 Codex 目录。

## 启动方式

### Windows

双击下面任意一个文件即可：

- `start_provider_repair.bat`
- `启动恢复工具.bat`

### Linux

推荐安装为桌面应用：

```bash
./install_linux.sh
```

安装完成后，可以在应用菜单里搜索并打开：

```text
Codex 对话恢复与清理工具
```

也可以在终端运行：

```bash
codex-provider-repair
```

卸载：

```bash
./uninstall_linux.sh
```

卸载默认会保留备份目录。

如果只是临时从源码目录启动，也可以执行：

```bash
./start_provider_repair.sh
```

### macOS

在项目目录执行：

```bash
./start_provider_repair.sh
```

也可以直接执行：

```bash
python3 provider_repair_gui.py
```

## 环境与启动要求

- Windows、Linux 或 macOS
- Python 3.8 及以上
- Tkinter

这个项目默认不依赖第三方 Python 包。

也就是说：

- 不需要执行 `pip install -r requirements.txt`
- 不需要额外安装 `requests`、`toml`、`pillow` 之类的包
- 只要 Python 自带标准库可用，并且带有 `Tkinter`，就可以直接运行

当前代码使用到的都是 Python 标准库：

- `datetime`
- `json`
- `os`
- `shutil`
- `sqlite3`
- `subprocess`
- `sys`
- `threading`
- `traceback`
- `uuid`
- `webbrowser`
- `tkinter`

注意：

- 这个工具不会自动安装 Python
- 也不会自动安装依赖环境
- Windows 启动脚本只是执行 `python provider_repair_gui.py`
- Linux/macOS 启动脚本会执行 `python3 provider_repair_gui.py`
- Linux 安装脚本会把应用复制到 `~/.local/share/codex-provider-repair/`，并创建 `~/.local/share/applications/codex-provider-repair.desktop`
- 如果系统里没有 Python，或当前 Python 没带 `Tkinter`，程序就无法启动
- 如果你的 Python 缺少 `Tkinter`，程序会直接报错并退出

Linux 常见 Tkinter 安装方式：

```bash
# Ubuntu / Debian
sudo apt install python3-tk

# Fedora
sudo dnf install python3-tkinter

# Arch Linux
sudo pacman -S tk
```

建议：

- 推荐安装 Python 3.10、3.11 或 3.12
- Windows 安装 Python 时勾选 `Add Python to PATH`
- 安装完成后可在命令行执行 `python --version` 检查是否生效

## 文件说明

- `provider_repair_gui.py`：主程序
- `start_provider_repair.bat`：英文启动脚本
- `启动恢复工具.bat`：中文启动脚本
- `start_provider_repair.sh`：Linux/macOS 启动脚本
- `install_linux.sh`：Linux 用户级安装脚本，会创建应用菜单入口
- `uninstall_linux.sh`：Linux 用户级卸载脚本
- `备份/`：运行后自动生成的备份目录
