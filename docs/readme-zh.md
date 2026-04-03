# Local Portal (lportal)

局域网文本实时中转工具 —— 本地传送门

## 功能

- **手机输入 → 电脑剪贴板实时同步**：在手机上输入文字，电脑剪贴板立即获得内容
- **文件传输**：手机发送图片、视频，直接保存到电脑下载目录
- **复制模式切换**：支持覆盖模式（默认）和追加模式，追加模式下多条消息自动合并
- **文本美化**：通过 LLM 将口语化输入转为结构化文档，支持流式输出和思维链显示
- **多设备隔离**：每个设备独立注册、独立会话，消息和历史记录完全隔离
- **设备会话模式**：服务端可直接与指定设备建立会话，双向发送消息
- **纯浏览器方案**：手机端无需安装 App，直接浏览器访问即可使用
- **交互式命令行**：电脑端提供 CLI 终端，支持斜杠命令控制
- **配对码安全**：4位数字配对码验证，防止未授权访问

支持场景：
- 快速发送网址、验证码、长文本到电脑
- 手机拍照/视频直接传输到电脑
- 临时传输笔记、待办事项
- 手机打字，电脑粘贴使用
- 语音输入后一键结构化整理为专业文档
- 多设备同时接入，各自数据互不干扰
- 服务端主动向指定设备推送消息和通知

## 安装

### 推荐方式：通过 PyPI 安装

```bash
pip install localportal
```

安装完成后直接运行：

```bash
lportal
```

### 替代方式：使用 uv 全局安装

如果你使用 [uv](https://docs.astral.sh/uv/)，也可以通过工具模式全局安装：

```bash
uv tool install localportal
```

`uv tool` 会将包安装到一个独立的隔离环境中（Windows 下为 `%APPDATA%\uv\tools\lportal\`，Linux/macOS 下为 `~/.local/share/uv/tools/lportal/`），并在用户脚本目录创建可执行文件入口，不会污染系统 Python。

**更新 / 卸载**：
```bash
uv tool upgrade localportal   # 更新
uv tool uninstall localportal # 卸载
```

### 开发安装

如果你想从源码运行或参与开发：

**使用 uv**：
```bash
uv sync        # 安装依赖
uv run lportal # 运行
```

**使用 pip（可编辑模式）**：
```bash
# 创建虚拟环境（推荐）
python -m venv .venv

# 激活虚拟环境
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

# 可编辑模式安装
pip install -e .

# 运行
lportal
```

**本地构建 wheel 安装**：
```bash
python -m build
pip install dist/localportal-*.whl
lportal
```

## 使用

```bash
# 默认启动（端口 14554）
lportal

# 指定端口
lportal --port 8080

# 禁用自动复制
lportal --no-auto-copy

# 设置历史条数
lportal --max-history 20
```

### 设置下载目录

文件（图片、视频）默认保存到系统的下载目录（`~/Downloads`）。可以通过环境变量 `LPORTAL_DOWNLOAD_DIR` 自定义下载路径：

```bash
# Windows PowerShell
$env:LPORTAL_DOWNLOAD_DIR="D:\\MyDownloads"
lportal

# Windows CMD
set LPORTAL_DOWNLOAD_DIR=D:\\MyDownloads
lportal

# Linux / Mac
export LPORTAL_DOWNLOAD_DIR=/home/user/MyDownloads
lportal
```

### LLM 配置（文本美化功能）

`/beauty` 命令需要配置 OpenAI 兼容接口。创建 `.env` 文件，放在以下任一位置：

**方式一：用户配置目录（推荐全局安装用户）**

```bash
# Windows
mkdir "%APPDATA%\localportal"
echo OPENAI_BASE_URL=https://api.openai.com/v1 > "%APPDATA%\localportal\.env"
echo OPENAI_API_KEY=sk-xxxxxx >> "%APPDATA%\localportal\.env"
echo OPENAI_MODEL=gpt-4o-mini >> "%APPDATA%\localportal\.env"

# macOS
mkdir -p ~/Library/Application\ Support/localportal
cat > ~/Library/Application\ Support/localportal/.env << EOF
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_API_KEY=sk-xxxxxx
OPENAI_MODEL=gpt-4o-mini
EOF

# Linux
mkdir -p ~/.config/localportal
cat > ~/.config/localportal/.env << EOF
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_API_KEY=sk-xxxxxx
OPENAI_MODEL=gpt-4o-mini
EOF
```

**方式二：当前工作目录（适合开发调试）**

在项目目录或任意工作目录创建 `.env` 文件：

```bash
OPENAI_BASE_URL=https://api.openai.com/v1/chat/completions
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
OPENAI_MODEL=gpt-4o-mini
```

**注意**：当前工作目录的配置会覆盖用户配置目录的配置。

系统提示词位于 `src/prompt/text-beauty.md`，可根据需要自行修改。

### 设备注册机制

手机端连接后需要经过两步验证：

1. **配对码验证**：输入电脑端显示的 4 位配对码
2. **设备注册**：输入设备名称（不可与当前在线设备重名），注册成功后获得唯一的 `login_id`

- 同一设备断线重连时，只要服务端未重启，`login_id` 保持不变，历史记录可同步恢复
- 使用 `/devices` 命令可查看所有在线设备

### 配对码安全机制

启动时会生成 4 位数字配对码，手机端需要输入正确的配对码才能连接。

- **扫码连接**：使用 `/qr` 命令显示二维码，手机扫码自动填充配对码
- **手动连接**：浏览器访问地址后输入配对码
- **刷新配对码**：使用 `/refresh-qrcode` (`/rq`) 命令生成新配对码，旧连接将断开
- **切换复制模式**：使用 `/mode [cover|add]` 切换覆盖/追加模式，变更会同步到所有在线设备
- **刷新会话**：追加模式下使用 `/new-session` 开始新会话
- **文本美化**：使用 `/beauty [N]` 将第 N 条历史消息通过 LLM 结构化整理

## 命令

| 命令 | 功能 |
|------|------|
| `/auto [on\|off]` | 自动复制模式开关 |
| `/copy [N]` | 复制历史消息（N=1-10，无参=最近一条） |
| `/list` (`/ls`) | 列出历史消息 |
| `/status` | 显示服务状态（含配对码） |
| `/open` | 浏览器打开主页面 |
| `/qrcode` (`/qr`) | 显示 ASCII 二维码（扫码连接） |
| `/downloads` | 打开下载文件夹 |
| `/refresh-qrcode` (`/rq`) | 刷新配对码（断开所有连接） |
| `/mode [cover\|add]` | 切换复制模式：cover=覆盖模式，add=追加模式 |
| `/new-session` | 追加模式下刷新会话（清空缓冲区） |
| `/beauty [N]` | 使用 LLM 美化第 N 条历史消息（默认最近一条） |
| `/beauty-history` | 查看最近 10 次文字美化任务 |
| `/beauty-copy [N]` | 复制第 N 次美化结果（默认最近一条） |
| `/devices` | 查看所有已登录设备（名称、login_id、登录时间） |
| `/link <name\|id>` | 进入与指定设备的会话模式，提示符变为 `lportal[设备名]>` |
| `/unlink` | 退出设备会话模式 |
| `/send <filepath>` | 向当前会话设备发送文件（需在 `/link` 后使用） |
| `/help` | 显示帮助 |
| `/exit` | 退出程序 |

### 设备会话模式

进入会话模式后，可以直接输入文字发送给设备，无需斜杠命令。也可以使用 `/send` 命令发送文件：

```
lportal> /link iPhone
[OK] 已进入设备会话模式: iPhone (a3f9b2c1)

lportal[iPhone]> 你好，这是服务端消息
[11:30:15] -> iPhone: 你好，这是服务端消息...

lportal[iPhone]> /send C:\Users\xx\Documents\file.pdf
[OK] 已发送文件到 iPhone: file.pdf (123.4KB)

lportal[iPhone]> /unlink
[OK] 已退出与 iPhone 的会话模式
```

## 技术栈

- Python 3.9+
- aiohttp (HTTP/WebSocket)
- typer (CLI)
- prompt_toolkit (交互式终端)
- rich (终端美化)
- pyperclip (剪贴板)

## TODO

- [x] 支持图片传输
- [x] 支持视频传输
- [x] 复制模式切换（覆盖/追加）
- [x] 会话管理（追加模式下分组显示）
- [ ] 消息持久化存储
- [ ] 多设备同时在线管理
- [ ] 加密传输支持
- [ ] Web 端黑暗/明亮主题切换

## 许可证

MIT
