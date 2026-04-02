# Local Portal (lportal) - AI Agent Guide

## Project Overview

Local Portal（本地传送门）是一个局域网文本实时中转工具，用于将手机输入的文本实时同步到电脑剪贴板。

**核心场景**：
- 公司电脑有安全软件限制，无法安装语音输入法
- 通过纯浏览器方案，手机无需安装 App 即可使用
- 手机语音输入 → 电脑剪贴板实时同步

**项目信息**：
- 名称：`lportal`
- 版本：`0.1.0`
- 许可证：MIT
- 语言：中文（代码注释和文档主要使用中文）

## Technology Stack

| 功能 | 库/工具 | 说明 |
|------|---------|------|
| 包管理 | `uv` | 现代 Python 包管理器（取代 pip） |
| 构建系统 | `hatchling` | pyproject.toml 构建后端 |
| CLI 框架 | `typer` | 现代、类型提示、自动生成帮助 |
| 交互式终端 | `prompt_toolkit` | 支持斜杠命令、历史、补全 |
| 终端美化 | `rich` | 终端样式、颜色输出 |
| HTTP/WebSocket | `aiohttp` | 异步 HTTP 框架 |
| WebSocket 客户端 | `websockets` | 标准 asyncio 实现 |
| 剪贴板 | `pyperclip` | 跨平台剪贴板方案 |
| 二维码生成 | `qrcode` + `Pillow` | 二维码图片生成 |
| 浏览器唤起 | `webbrowser` | Python 标准库 |

**Python 版本要求**：>= 3.9

## Project Structure

```
D:\workspace\local-portal/
├── src/
│   └── lportal/                 # 主包目录
│       ├── __init__.py          # 包初始化，版本号
│       ├── __main__.py          # python -m lportal 入口
│       ├── main.py              # CLI 入口，主应用 PortalApp
│       ├── server.py            # HTTP/WebSocket 服务器 (aiohttp)
│       ├── commands.py          # 斜杠命令处理器 CommandHandler
│       ├── config.py            # 配置状态 ServerConfig，配对码生成
│       ├── history.py           # 历史记录管理 (循环缓冲区)
│       ├── beauty.py            # 文本美化：LLM 调用、流式输出、美化历史
│       ├── qr.py                # 二维码生成、获取本地 IP、浏览器唤起
│       └── ui.py                # 终端 UI 输出 (rich console)
├── src/
│   └── prompt/
│       └── text-beauty.md       # 文本美化系统提示词
├── static/
│   └── index.html               # 移动端 Web 界面（纯 HTML/CSS/JS）
├── LocalPortal-Design/          # 设计方案文档（独立目录，被 .gitignore 排除）
│   ├── DESIGN.md                # 详细设计文档
│   ├── frontend/                # 前端设计参考
│   └── backend/                 # 后端设计参考
├── pyproject.toml               # 项目配置（uv/hatchling）
├── uv.lock                      # uv 依赖锁定文件
├── README.md                    # 用户文档（中文）
├── .gitignore                   # Git 忽略配置
└── .venv/                       # uv 虚拟环境
```

## Build and Run Commands

### 开发调试（本地运行）

```bash
# 安装依赖（根据 uv.lock）
uv sync

# 运行（使用虚拟环境）
uv run lportal

# 或指定参数
uv run lportal --port 8080 --no-auto-copy --max-history 20
```

### 全局安装（日常使用）

```bash
# 从本地路径全局安装
uv tool install -e .

# 安装后可直接运行
lportal

# 更新/卸载
uv tool upgrade lportal
uv tool uninstall lportal
```

### 其他 uv 命令

```bash
# 添加依赖
uv add <package>

# 更新锁定文件
uv lock

# 构建分发包
uv build
```

## Architecture

### 系统架构图

```
┌─────────────────────────────────────────────────────────┐
│                     lportal CLI                          │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐  │
│  │ 交互式终端   │◄──►│  命令处理器  │◄──►│ WebSocket   │  │
│  │ (prompt)    │    │  (/auto等)  │    │  服务端      │  │
│  └─────────────┘    └──────┬──────┘    └──────┬──────┘  │
│                            │                   │         │
│                       ┌────┴────┐         ┌────┴────┐   │
│                       │ 配置状态  │         │ 客户端连接 │   │
│                       │(auto模式)│         │(手机浏览器)│   │
│                       └────┬────┘         └─────────┘   │
│                            │                             │
│                       ┌────┴────┐                        │
│                       │ 历史队列  │                        │
│                       │(Circular)│                        │
│                       └─────────┘                        │
└─────────────────────────────────────────────────────────┘
```

### 核心模块说明

1. **main.py - PortalApp**: 主应用类，协调服务器、命令处理器、交互式终端
2. **server.py - Server**: aiohttp HTTP/WebSocket 服务器，处理客户端连接和消息
3. **commands.py - CommandHandler**: 处理斜杠命令（/auto, /copy, /list 等）
4. **config.py - ServerConfig**: 配置和运行时状态管理，包括 4 位数字配对码生成
5. **history.py - History**: 循环缓冲区实现的历史记录（内存存储，不持久化），支持 session 分组
6. **file_transfer.py - FileTransferManager**: 文件传输管理，处理图片/视频上传
7. **beauty.py**: 文本美化模块，通过 OpenAI 兼容接口调用 LLM，支持流式输出和思维链显示
8. **qr.py**: 二维码生成、局域网 IP 获取、浏览器唤起
9. **ui.py**: 终端 UI 输出，使用 rich 库美化
10. **static/index.html**: Web 端界面，支持复制模式切换、会话管理、设备注册
11. **prompt/text-beauty.md**: 文本美化的系统提示词

### WebSocket 通信协议

**客户端 → 服务端**：
```typescript
{ type: 'auth'; code: string }           // 配对码验证
{ type: 'register'; device_name: string }  // 设备注册
{ type: 'text'; content: string; client_id?: string }
{ type: 'file_start'; name: string; size: number; mime_type: string }
{ type: 'file_chunk'; file_id: string; index: number; data: string }
{ type: 'file_end'; file_id: string }
{ type: 'command'; command: 'new_session' }  // 刷新会话
{ type: 'command'; command: 'set_mode'; mode: 'cover' | 'add' }  // 切换模式
```

**服务端 → 客户端**：
```typescript
{ type: 'auth_success' }                 // 验证成功
{ type: 'auth_failed'; message: string } // 验证失败
{ type: 'register_success'; login_id: string; device_name: string }  // 注册成功
{ type: 'register_failed'; message: string }  // 注册失败
{ type: 'history'; data: MessageEntry[] }  // 仅包含该设备相关的消息
{ type: 'new'; data: MessageEntry }        // 仅发送给消息来源设备
{ type: 'file_accept'; file_id: string }
{ type: 'file_progress'; file_id: string; received: number; total: number }
{ type: 'file_saved'; file_id: string; path: string; size: number }
{ type: 'file_error'; file_id: string; error: string }
{ type: 'session_reset'; message: string }   // 追加模式下会话已刷新
{ type: 'mode_changed'; mode: string; message: string }  // 模式已切换
{ type: 'server_text'; data: MessageEntry }     // 服务端主动向设备发送的文本
{ type: 'server_close'; message: string }
```

## CLI Commands

### 启动参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--port, -p` | 14554 | 服务端口，被占用时自动递增 |
| `--auto-copy / --no-auto-copy` | True | 自动复制模式 |
| `--max-history` | 10 | 最大历史条数 |

### 交互式斜杠命令

| 命令 | 功能 |
|------|------|
| `/auto [on\|off]` | 自动复制模式开关 |
| `/copy [N]` | 复制历史消息（N=1-10，无参=最近一条） |
| `/list` (`/ls`) | 列出历史消息 |
| `/status` | 显示服务状态 |
| `/open` | 浏览器打开主页面 |
| `/qrcode` (`/qr`) | 显示 ASCII 二维码（扫码连接） |
| `/downloads` | 打开下载文件夹 |
| `/mode` | 切换复制模式 (cover/add)，广播通知所有在线设备 |
| `/new-session` | 追加模式下刷新会话 |
| `/beauty [N]` | 使用 LLM 美化第 N 条历史消息（默认最近一条） |
| `/beauty-history` | 查看最近 10 次文字美化任务 |
| `/beauty-copy [N]` | 复制第 N 次美化结果（默认最近一条） |
| `/devices` | 查看所有已登录设备 |
| `/link <name\|id>` | 进入与指定设备的会话模式 |
| `/unlink` | 退出设备会话模式 |
| `/send <filepath>` | 向当前会话设备发送文件 |
| `/refresh-qrcode` (`/rq`) | 刷新配对码（断开所有客户端） |
| `/help` | 分组显示所有命令及下载目录设置说明 |
| `/exit` | 退出程序 |

## Development Conventions

### 代码风格

- **注释语言**：中文（面向中国开发者）
- **字符串引号**：单引号优先，但保持一致即可
- **模式管理**：`copy_mode` 控制复制行为，`session_buffer` 存储追加模式内容
- **类型注解**：使用 Python 3.9+ 类型提示（`list[str]` 而非 `List[str]`）
- **异步代码**：使用 `asyncio` 和 `async`/`await`
- **导入风格**：
  - 标准库导入在前
  - 第三方库导入其次
  - 本地模块导入最后，使用相对导入（`from .module import X`）

### 模块设计原则

1. **单一职责**：每个模块负责一个明确功能
2. **配置集中**：`ServerConfig` 统一管理配置和状态
3. **消息队列**：使用 `asyncio.Queue` 进行模块间通信
4. **信号处理**：禁用 `Ctrl+C` 退出，保留用于复制功能；使用 `/exit` 退出程序

### 安全机制

- **配对码验证**：4 位数字随机码，客户端连接时必须验证
- **设备注册**：配对码验证后需输入设备名称，不可与在线设备重名
- **超时机制**：配对码验证和设备注册各超时 10 秒
- **刷新配对码**：`/refresh-qrcode` 命令可刷新配对码，强制断开所有客户端
- **文件类型白名单**：只允许图片（jpeg/png/gif/webp）和视频（mp4/mov/webm）
- **文件大小限制**：默认最大 100MB
- **文件名清理**：去除路径分隔符，防止目录遍历攻击

### 文本美化（LLM）

- **配置来源**：支持多处放置 `.env` 文件（优先级从高到低）：
  1. 当前工作目录 `.env`（适合项目级配置）
  2. 用户配置目录（适合全局安装用户）：
     - Windows: `%APPDATA%\localportal\.env`
     - macOS: `~/Library/Application Support/localportal/.env`
     - Linux: `~/.config/localportal/.env`
- **配置项**：`OPENAI_BASE_URL`、`OPENAI_API_KEY`、`OPENAI_MODEL`
- **提示词**：`src/prompt/text-beauty.md`，支持自定义修改
- **流式输出**：使用 SSE 流式接收 LLM 响应，实时打印到终端
- **思维链显示**：`reasoning_content` 字段或 `<think>` 标签内的内容以灰色 (`dim gray`) 显示
- **正文显示**：`content` 字段以白色显示
- **自动复制**：LLM 处理完成后，正文内容自动复制到剪贴板
- **历史记录**：内存存储最近 10 次美化结果，通过 `/beauty-history` 和 `/beauty-copy` 查看/复制

### 设备管理与消息隔离

- **设备注册**：`Server` 维护 `devices`、`ws_to_login_id`、`device_registry` 三个映射表
- **login_id 复用**：`device_registry` 按 `device_name` 持久化映射到 `login_id`，服务端未重启时断线重连复用原 ID
- **消息隔离**：每个设备只能收到自己发送的 `new` 消息，历史记录也仅下发与该 `login_id` 相关的条目
- **服务端定向发送**：`send_to_device(login_id, message)` 支持服务端主动向指定设备发消息
- **自动恢复登录**：Web 端通过 `localStorage` 保存 `device_name` 和 `login_id`，刷新页面后自动重新注册

### 设备会话模式

- **进入会话**：`/link <device_name 或 login_id>` 查找在线设备，进入专属会话模式
- **会话提示符**：`PortalApp` 维护 `linked_device_name` 和 `linked_login_id`，动态生成 `lportal[设备名]>` 提示符
- **直接发送**：会话模式下非斜杠输入直接调用 `server.send_server_text()` 发送到设备
- **文件发送**：`/send <filepath>` 命令调用 `server.send_server_file()` 向设备发送文件
- **消息标记**：服务端发送的消息 `login_id="server"`，`target_login_id` 指向目标设备，使用负数的 `session_id` 确保独立显示块
- **退出会话**：`/unlink` 清除 link 状态，恢复普通模式

### 复制模式与 Session 管理

**覆盖模式 (cover)**：
- 每条消息有独立的 session_id
- 新消息覆盖剪贴板内容
- `/list` 中每条消息单独显示

**追加模式 (add)**：
- 同一 session 的多条消息共享 session_id
- 新消息追加到剪贴板，自动换行合并
- `/list` 中同一 session 的消息合并显示为 `[N条]`
- 使用 `/new-session` 或 Web 端"新会话"按钮开始新 session

**模式切换时的行为**：
- 切换模式会自动调用 `new_session()`，确保新旧消息分开
- Web 端和 CLI 端模式同步，通过 `set_mode` 命令通知服务端，服务端广播 `mode_changed` 给所有在线设备

## Testing

**当前状态**：项目暂未配置测试框架。

**建议添加**：
```bash
# 添加测试依赖
uv add --dev pytest pytest-asyncio

# 测试应覆盖
- 历史记录循环缓冲区逻辑
- 命令处理器各种命令
- WebSocket 消息处理
- 配对码生成和验证
```

## Deployment

### 作为工具分发

```bash
# 构建 wheel
uv build

# 分发到 PyPI（需要配置 token）
uv publish
```

### 本地开发安装

```bash
# 可编辑安装
uv tool install -e .
```

## Important Notes

1. **端口占用**：默认端口 14554，如果被占用会自动尝试递增（最多 10 次）
2. **剪贴板依赖**：`pyperclip` 依赖系统剪贴板工具（Windows 无需额外依赖）
3. **局域网访问**：服务绑定 `0.0.0.0`，同局域网设备可访问
4. **配对码**：每次启动生成新的 4 位随机码，用于客户端验证
5. **历史记录**：仅内存存储，重启后清空，最大条数可配置
6. **静态文件**：`static/index.html` 作为移动端界面，打包时会包含在 wheel 中
7. **下载目录**：默认保存到 `~/Downloads`，可通过 `LPORTAL_DOWNLOAD_DIR` 环境变量自定义（支持 Windows PowerShell/CMD、macOS/Linux bash/zsh 等设置方式）
8. **文件传输**：支持图片和视频，最大 100MB，分 64KB 切片传输
9. **复制模式**：CLI 和 Web 端都支持切换覆盖/追加模式，切换时自动刷新 session
10. **Web 端 UI**：顶部工具栏可切换模式，追加模式下显示"新会话"按钮，注册成功后显示当前 `login_id`
11. **自动恢复登录**：Web 端通过 localStorage 保存设备信息，刷新页面后自动完成注册流程
12. **设备会话模式**：服务端可通过 `/link` 进入与指定设备的专属会话，直接输入文字即可推送
13. **文件发送**：`/send` 命令支持服务端向设备发送文件，设备端自动下载
13. **LLM 配置**：文本美化依赖 `.env` 中的 OpenAI 兼容接口配置，可从用户配置目录或当前工作目录读取，未配置时 `/beauty` 命令会提示配置文件位置

## TODO (from README)

- [x] 支持图片传输
- [x] 支持视频传输
- [x] 复制模式切换 (cover/add)
- [x] 追加模式下会话刷新 (/new-session)
- [x] 网页端模式切换 UI
- [ ] 消息持久化存储
- [ ] 多设备同时在线管理
- [ ] 加密传输支持
- [ ] Web 端黑暗/明亮主题切换
