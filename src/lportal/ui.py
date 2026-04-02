"""终端 UI - 使用 rich 库"""

from datetime import datetime
from typing import TYPE_CHECKING, List

from rich.console import Console

if TYPE_CHECKING:
    from .beauty import BeautyEntry
    from .config import ServerConfig
    from .history import MessageEntry
    from .server import DeviceInfo


console = Console()


def print_banner(config: "ServerConfig") -> None:
    """打印启动横幅"""
    console.print()
    console.print("Local Portal 启动中...", style="bold green")
    console.print("-" * 40)
    console.print()
    console.print("服务地址:")
    console.print(f"   本机:   {config.local_url}")
    console.print(f"   局域网: {config.lan_url}")
    console.print()
    console.print(f"配对码: {config.pairing_code}")
    console.print()
    mode_desc = "追加" if config.copy_mode == 'add' else "覆盖"
    console.print(f"复制模式: {mode_desc} 模式 (/mode 切换)")
    console.print("提示: 使用 /qr 命令显示二维码")
    console.print()
    console.print("-" * 40)
    console.print("提示: 输入 /help 查看所有可用命令")
    console.print()


def print_status(config: "ServerConfig") -> None:
    """打印服务状态面板"""
    from .qr import get_local_ip
    
    console.print()
    console.print("Local Portal 状态", style="bold")
    console.print()
    
    # 服务地址
    console.print("服务地址")
    console.print(f"  本机:   {config.local_url}")
    console.print(f"  局域网: {config.lan_url}")
    console.print()
    
    # 安全
    console.print("安全")
    console.print(f"  配对码:        {config.pairing_code}")
    console.print()
    
    # 运行状态
    console.print("运行状态")
    auto_status = "开启 [OK]" if config.auto_copy else "关闭 [X]"
    mode_status = "追加" if config.copy_mode == 'add' else "覆盖"
    console.print(f"  自动复制模式:  {auto_status}")
    console.print(f"  复制模式:      {mode_status} (/mode 切换)")
    if config.copy_mode == 'add' and config.session_buffer:
        buffer_preview = config.session_buffer[:30] + "..." if len(config.session_buffer) > 30 else config.session_buffer
        console.print(f"  会话缓冲区:    \"{buffer_preview}\"")
    console.print(f"  在线客户端:    {len(config.connected_clients)}")
    console.print(f"  历史消息数:    {len(config.history)} / {config.history.maxsize}")
    console.print(f"  运行时间:      {config.uptime}")
    console.print()
    
    # 最近活动
    console.print("最近活动")
    last_time = config.history.last_received_time()
    if last_time:
        time_str = last_time.strftime("%H:%M:%S")
        delta = datetime.now() - last_time
        if delta.seconds < 60:
            ago = "刚刚"
        elif delta.seconds < 3600:
            ago = f"{delta.seconds // 60}分钟前"
        else:
            ago = f"{delta.seconds // 3600}小时前"
        console.print(f"  最后接收:      {time_str} ({ago})")
        
        # 最近消息预览
        if len(config.history) > 0:
            last_msg = config.history.list()[0]
            preview = last_msg.preview[:30] + "..." if len(last_msg.preview) > 30 else last_msg.preview
            console.print(f"  消息预览:      \"{preview}\"")
    else:
        console.print("  最后接收:      无")
    console.print()


def _text_width(text: str) -> int:
    """计算文本显示宽度（中文字符算2，英文算1）"""
    width = 0
    for char in text:
        if ord(char) > 127:  # 非ASCII字符（中文等）
            width += 2
        else:
            width += 1
    return width


def _truncate_text(text: str, max_width: int) -> str:
    """截断文本到指定显示宽度，尾部加..."""
    if _text_width(text) <= max_width:
        return text
    
    result = ""
    width = 0
    for char in text:
        char_width = 2 if ord(char) > 127 else 1
        if width + char_width > max_width - 3:  # 预留...的位置
            break
        result += char
        width += char_width
    return result + "..."


def print_list(entries: List["MessageEntry"]) -> None:
    """打印历史消息列表 - 简洁风格，预览固定12个全角字符宽度"""
    if not entries:
        console.print("暂无历史消息")
        return
    
    console.print()
    
    # 固定预览宽度：20个全角字符 = 40个半角字符宽度
    PREVIEW_MAX_WIDTH = 40
    
    # 打印表头
    console.print("ID   预览                                        时间    ", style="dim")
    console.print("-" * 61, style="dim")
    
    # 打印数据行
    for entry in entries:
        time_str = entry.time.strftime("%H:%M:%S")
        # 截断预览到固定宽度
        preview = _truncate_text(entry.preview, PREVIEW_MAX_WIDTH)
        # 补齐空格使对齐（简单方案：预览占24宽度，不足补空格）
        preview_width = _text_width(preview)
        padding = " " * (PREVIEW_MAX_WIDTH - preview_width)
        
        row = f"{entry.id:<4} {preview}{padding} {time_str}"
        console.print(row)
    
    console.print()


def print_session_list(entries: List["MessageEntry"]) -> None:
    """打印历史消息列表 - 追加模式下按 session 分组显示"""
    if not entries:
        console.print("暂无历史消息")
        return
    
    console.print()
    
    PREVIEW_MAX_WIDTH = 28
    SOURCE_MAX_WIDTH = 20
    
    # 打印表头
    console.print(f"{'ID':<4} {'预览':<{PREVIEW_MAX_WIDTH}} {'来源':<{SOURCE_MAX_WIDTH}} {'时间':<8}", style="dim")
    console.print("-" * (4 + 1 + PREVIEW_MAX_WIDTH + 1 + SOURCE_MAX_WIDTH + 1 + 8), style="dim")
    
    # 按 session_id 分组（entries 是按时间倒序的）
    from itertools import groupby
    
    sessions = []
    for session_id, group in groupby(entries, key=lambda e: e.session_id):
        msgs = list(group)
        sessions.append({
            'id': msgs[0].id,
            'count': len(msgs),
            'text': ' | '.join(m.text for m in reversed(msgs)),
            'time': msgs[0].time,
            'session_id': session_id,
            'device_name': msgs[0].device_name,
            'login_id': msgs[0].login_id
        })
    
    for session in sessions:
        time_str = session['time'].strftime("%H:%M:%S")
        
        if session['count'] > 1:
            preview_text = f"[{session['count']}条] {session['text']}"
        else:
            preview_text = session['text']
        
        preview = _truncate_text(preview_text, PREVIEW_MAX_WIDTH)
        preview_padding = " " * (PREVIEW_MAX_WIDTH - _text_width(preview))
        
        source_text = f"{session['device_name']}-{session['login_id']}" if session['login_id'] else "-"
        source = _truncate_text(source_text, SOURCE_MAX_WIDTH)
        source_padding = " " * (SOURCE_MAX_WIDTH - _text_width(source))
        
        row = f"{session['id']:<4} {preview}{preview_padding} {source}{source_padding} {time_str}"
        console.print(row)
    
    console.print()


def print_beauty_list(entries: List["BeautyEntry"]) -> None:
    """打印美化历史记录列表"""
    if not entries:
        console.print("暂无美化记录")
        return
    
    console.print()
    PREVIEW_MAX_WIDTH = 28
    SOURCE_MAX_WIDTH = 20
    
    console.print(f"{'ID':<4} {'预览':<{PREVIEW_MAX_WIDTH}} {'来源':<{SOURCE_MAX_WIDTH}} {'时间':<8}", style="dim")
    console.print("-" * (4 + 1 + PREVIEW_MAX_WIDTH + 1 + SOURCE_MAX_WIDTH + 1 + 8), style="dim")
    
    for entry in entries:
        time_str = entry.time.strftime("%H:%M:%S")
        preview = _truncate_text(entry.preview, PREVIEW_MAX_WIDTH)
        preview_padding = " " * (PREVIEW_MAX_WIDTH - _text_width(preview))
        
        source_text = f"{entry.device_name}-{entry.login_id}" if entry.login_id else "-"
        source = _truncate_text(source_text, SOURCE_MAX_WIDTH)
        source_padding = " " * (SOURCE_MAX_WIDTH - _text_width(source))
        
        row = f"{entry.id:<4} {preview}{preview_padding} {source}{source_padding} {time_str}"
        console.print(row)
    
    console.print()


def print_message(msg: str, style: str = "") -> None:
    """打印普通消息 - 使用纯文本避免样式问题"""
    print(msg)


def print_devices(devices: List["DeviceInfo"]) -> None:
    """打印在线设备列表"""
    if not devices:
        console.print("暂无在线设备")
        return
    
    console.print()
    console.print(f"{'设备名称':<16} {'login_id':<10} {'登录时间':<20}", style="dim")
    console.print("-" * 50, style="dim")
    
    for info in devices:
        time_str = info.login_time.strftime("%Y-%m-%d %H:%M:%S")
        name = _truncate_text(info.device_name, 16)
        name_padding = " " * (16 - _text_width(name))
        console.print(f"{name}{name_padding} {info.login_id:<10} {time_str}")
    
    console.print()


def print_new_message(entry: "MessageEntry", auto_copied: bool = False) -> None:
    """打印新消息通知 - 单行显示，限制10个全角字符"""
    time_str = entry.time.strftime("%H:%M:%S")
    status = " [auto]" if auto_copied else ""
    source = f"[{entry.device_name}]" if entry.device_name else ""
    preview = _truncate_text(entry.text, 20)
    print(f"[{time_str}] 收到消息{status} {source}: {preview}")


def print_help() -> str:
    """打印帮助信息"""
    from rich.text import Text
    
    console.print("\n[bold green]Local Portal 命令帮助[/bold green]\n")

    def print_cmd(cmd: str, desc: str):
        """打印命令行，命令部分带颜色，描述部分普通"""
        t = Text()
        t.append(f"  {cmd:<22}", style="cyan")
        t.append(desc)
        console.print(t)

    console.print("[bold yellow]基础操作[/bold yellow]")
    print_cmd("/copy [N]", "复制历史消息（N=1-10，无参=最近一条）")
    print_cmd("/list (/ls)", "列出最近10条消息摘要")
    print_cmd("/status", "显示服务运行状态")
    print_cmd("/open", "在浏览器中打开主页面")
    print_cmd("/qrcode (/qr)", "显示二维码（扫码连接）")
    print_cmd("/downloads", "打开下载文件夹")

    console.print("\n[bold yellow]模式与会话[/bold yellow]")
    print_cmd("/auto [on|off]", "开启/关闭自动复制模式")
    print_cmd("/mode [cover|add]", "切换复制模式 (cover=覆盖模式, add=追加模式)")
    print_cmd("/new-session", "追加模式下刷新会话，清空缓冲区")

    console.print("\n[bold yellow]设备管理[/bold yellow]")
    print_cmd("/devices", "查看所有已登录设备")
    print_cmd("/link <name|id>", "进入与指定设备的会话模式")
    print_cmd("/unlink", "退出设备会话模式")

    console.print("\n[bold yellow]文本美化[/bold yellow]")
    print_cmd("/beauty [N]", "使用 LLM 美化第 N 条历史消息（默认最近一条）")
    print_cmd("/beauty-history", "查看最近 10 次文字美化任务")
    print_cmd("/beauty-copy [N]", "复制第 N 次美化结果（默认最近一条）")

    console.print("\n[bold yellow]其他[/bold yellow]")
    print_cmd("/refresh-qrcode (/rq)", "刷新配对码（所有客户端需重新登录）")
    print_cmd("/help", "显示此帮助信息")
    print_cmd("/exit", "退出程序")

    console.print("\n[bold]模式说明:[/bold]")
    console.print("  [dim]cover (默认)[/dim] - 新消息覆盖上一条，适合单条复制")
    console.print("  [dim]add[/dim]          - 新消息追加到末尾，适合多条合并")

    console.print("\n[bold]下载目录设置:[/bold]")
    console.print("  默认保存到系统下载文件夹，可通过环境变量 [cyan]LPORTAL_DOWNLOAD_DIR[/cyan] 自定义")
    console.print("\n  [bold]Windows (PowerShell):[/bold]")
    console.print('    [green]$env:LPORTAL_DOWNLOAD_DIR="C:\\Users\\xx\\Downloads"[/green]')
    console.print("  [bold]Windows (CMD):[/bold]")
    console.print("    [green]set LPORTAL_DOWNLOAD_DIR=C:\\Users\\xx\\Downloads[/green]")
    console.print("\n  [bold]macOS / Linux (bash / zsh):[/bold]")
    console.print("    [green]export LPORTAL_DOWNLOAD_DIR=/Users/xx/Downloads[/green]")
    console.print("  [bold]永久生效（写入 ~/.bashrc 或 ~/.zshrc）:[/bold]")
    console.print('    [green]echo "export LPORTAL_DOWNLOAD_DIR=/Users/xx/Downloads" >> ~/.zshrc[/green]')
    console.print("    [green]source ~/.zshrc[/green]")

    console.print("\n[bold]LLM 配置（文本美化功能）:[/bold]")
    console.print("  创建 .env 文件，放在以下任一位置：")
    console.print("    - 当前工作目录: [cyan]./[/cyan]")
    console.print("    - Windows: [cyan]%APPDATA%\\localportal\\.env[/cyan]")
    console.print("    - macOS: [cyan]~/Library/Application Support/localportal/.env[/cyan]")
    console.print("    - Linux: [cyan]~/.config/localportal/.env[/cyan]")
    console.print("\n  配置内容：")
    console.print('    [green]OPENAI_BASE_URL=https://api.openai.com/v1[/green]')
    console.print('    [green]OPENAI_API_KEY=sk-xxxxxx[/green]')
    console.print('    [green]OPENAI_MODEL=gpt-3.5-turbo[/green]')

    console.print("\n[bold]自定义提示词:[/bold]")
    console.print("  在用户配置目录放置 [cyan]text-beauty.md[/cyan] 文件可覆盖默认提示词")
    console.print()
    return ""
