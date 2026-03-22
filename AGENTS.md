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
│       ├── qr.py                # 二维码生成、获取本地 IP、浏览器唤起
│       └── ui.py                # 终端 UI 输出 (rich console)
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
5. **history.py - History**: 循环缓冲区实现的历史记录（内存存储，不持久化）
6. **qr.py**: 二维码生成、局域网 IP 获取、浏览器唤起
7. **ui.py**: 终端 UI 输出，使用 rich 库美化

### WebSocket 通信协议

**客户端 → 服务端**：
```typescript
{ type: 'auth'; code: string }           // 配对码验证
{ type: 'text'; content: string; client_id?: string }
```

**服务端 → 客户端**：
```typescript
{ type: 'auth_success' }                 // 验证成功
{ type: 'auth_failed'; message: string } // 验证失败
{ type: 'history'; data: MessageEntry[] }
{ type: 'new'; data: MessageEntry }
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
| `/list` | 列出历史消息 |
| `/status` | 显示服务状态 |
| `/open` | 浏览器打开主页面 |
| `/qrcode` | 浏览器打开二维码页面 |
| `/refresh` | 刷新配对码（断开所有客户端） |
| `/help` | 显示帮助 |
| `/exit` | 退出程序 |

## Development Conventions

### 代码风格

- **注释语言**：中文（面向中国开发者）
- **字符串引号**：单引号优先，但保持一致即可
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
4. **信号处理**：支持 `Ctrl+C` 优雅退出（Windows 兼容）

### 安全机制

- **配对码验证**：4 位数字随机码，客户端连接时必须验证
- **超时机制**：配对码验证超时 10 秒
- **刷新配对码**：`/refresh` 命令可刷新配对码，强制断开所有客户端

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

## TODO (from README)

- [ ] 支持图片传输
- [ ] 支持文件传输
- [ ] 消息持久化存储
- [ ] 多设备同时在线管理
- [ ] 加密传输支持
- [ ] Web 端黑暗/明亮主题切换
