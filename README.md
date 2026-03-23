# Local Portal (lportal)

局域网文本实时中转工具 —— 本地传送门

## 功能

- **手机输入 → 电脑剪贴板实时同步**：在手机上输入文字，电脑剪贴板立即获得内容
- **文件传输**：手机发送图片、视频，直接保存到电脑下载目录
- **纯浏览器方案**：手机端无需安装 App，直接浏览器访问即可使用
- **交互式命令行**：电脑端提供 CLI 终端，支持斜杠命令控制
- **配对码安全**：4位数字配对码验证，防止未授权访问

支持场景：
- 快速发送网址、验证码、长文本到电脑
- 手机拍照/视频直接传输到电脑
- 临时传输笔记、待办事项
- 手机打字，电脑粘贴使用

## 安装

### 方式一：uv 全局安装（推荐日常使用）

使用 uv 工具模式全局安装，安装后可直接运行 `lportal`：

```bash
# 从本地路径全局安装
uv tool install -e .

# 或从 PyPI 安装（发布后）
uv tool install lportal
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
uv tool upgrade lportal   # 更新
uv tool uninstall lportal # 卸载
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
pip install lportal

# 运行
lportal
```

**本地构建 wheel 安装**：
```bash
# 构建 wheel 包
python -m build

# 安装生成的 wheel
pip install dist/lportal-0.1.0-py3-none-any.whl

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

### 配对码安全机制

启动时会生成 4 位数字配对码，手机端需要输入正确的配对码才能连接。

- **扫码连接**：使用 `/qr` 命令显示二维码，手机扫码自动填充配对码
- **手动连接**：浏览器访问地址后输入配对码
- **刷新配对码**：使用 `/refresh` 命令生成新配对码，旧连接将断开

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
| `/refresh` | 刷新配对码（断开所有连接） |
| `/help` | 显示帮助 |
| `/exit` | 退出程序 |

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
- [ ] 消息持久化存储
- [ ] 多设备同时在线管理
- [ ] 加密传输支持
- [ ] Web 端黑暗/明亮主题切换

## 许可证

MIT
