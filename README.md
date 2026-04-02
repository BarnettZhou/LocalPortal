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

### 方式一：uv 全局安装（推荐日常使用）

使用 uv 工具模式全局安装，安装后可直接运行 `lportal`：

```bash
# 从本地路径全局安装
uv tool install -e .

# 或从 PyPI 安装（发布后）
uv tool install localportal
```

安装完成后，确保 `%APPDATA%\Python\Scripts` 在你的 PATH 环境变量中，然后直接运行：

```bash
lportal
```

**特点**：
- 依赖隔离在 `%APPDATA%\uv\tools\lportal\` 目录
- 全局可用，无需进入项目目录
- 不依赖 uv 运行时，安装后可独立运行

**更新/卸载**：
```bash
uv tool upgrade localportal   # 更新
uv tool uninstall localportal # 卸载
```

### 方式二：uv 本地运行（开发调试）

在项目目录下使用虚拟环境运行：

```bash
uv sync        # 安装依赖
uv run lportal # 运行
```

**特点**：
- 依赖安装在项目 `.venv` 目录
- 适合开发调试
- 需要进入项目目录才能运行

### 方式三：pip 安装（无需 uv）

如果你不想使用 uv，可以只用 Python 和 pip：

**本地开发安装（可编辑模式）**：
```bash
# 创建虚拟环境（推荐）
python -m venv .venv

# 激活虚拟环境
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

# 安装依赖和包
pip install -e .

# 运行
lportal
```

**从 PyPI 安装（发布后）**：
```bash
pip install localportal

# 运行
lportal
```

**本地构建 wheel 安装**：
```bash
# 构建 wheel 包
python -m build

# 安装生成的 wheel
pip install dist/localportal-0.1.0-py3-none-any.whl

# 运行
lportal
```

**注意**：pip 安装不会像 uv tool 那样自动管理虚拟环境，建议手动创建虚拟环境避免依赖冲突。

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
| `/help` | 显示帮助 |
| `/exit` | 退出程序 |

### 设备会话模式

进入会话模式后，可以直接输入文字发送给设备，无需斜杠命令：

```
lportal> /link iPhone
[OK] 已进入设备会话模式: iPhone (a3f9b2c1)

lportal[iPhone]> 你好，这是服务端消息
[11:30:15] -> iPhone: 你好，这是服务端消息...

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
