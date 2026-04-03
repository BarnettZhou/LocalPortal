"""终端 UI - 使用 rich 库"""

from datetime import datetime
from typing import TYPE_CHECKING, List

from rich.console import Console

from .i18n import _

if TYPE_CHECKING:
    from .beauty import BeautyEntry
    from .config import ServerConfig
    from .history import MessageEntry
    from .server import DeviceInfo


console = Console()


def print_banner(config: "ServerConfig") -> None:
    """打印启动横幅"""
    console.print()
    console.print(_("Local Portal starting..."), style="bold green")
    console.print("-" * 40)
    console.print()
    console.print(f"{_('Service address')}:")
    console.print(f"   {_('Local')}:   {config.local_url}")
    console.print(f"   {_('LAN')}: {config.lan_url}")
    console.print()
    console.print(f"{_('Pairing code')}: {config.pairing_code}")
    console.print()
    mode_desc = _("append") if config.copy_mode == 'add' else _("cover")
    console.print(f"{_('Copy mode')}: {mode_desc} {_('Switch with /mode')}")
    console.print(_("Hint: use /qr to show QR code"))
    console.print()
    console.print("-" * 40)
    console.print(_("Hint: type /help for available commands"))
    console.print()


def print_status(config: "ServerConfig") -> None:
    """打印服务状态面板"""
    from .qr import get_local_ip
    
    console.print()
    console.print(_("Local Portal status"), style="bold")
    console.print()
    
    # 服务地址
    console.print(_("Service address"))
    console.print(f"  {_('Local')}:   {config.local_url}")
    console.print(f"  {_('LAN')}: {config.lan_url}")
    console.print()
    
    # 安全
    console.print(_("Security"))
    console.print(f"  {_('Pairing code')}:        {config.pairing_code}")
    console.print()
    
    # 运行状态
    console.print(_("Runtime status"))
    auto_status = _("ON [OK]") if config.auto_copy else _("OFF [X]")
    mode_status = _("append") if config.copy_mode == 'add' else _("cover")
    console.print(f"  {_('Auto copy mode')}:  {auto_status}")
    console.print(f"  {_('Copy mode')}:      {mode_status} (/mode)")
    if config.copy_mode == 'add' and config.session_buffer:
        buffer_preview = config.session_buffer[:30] + "..." if len(config.session_buffer) > 30 else config.session_buffer
        console.print(f"  {_('Session buffer')}:    \"{buffer_preview}\"")
    console.print(f"  {_('Online clients')}:    {len(config.connected_clients)}")
    console.print(f"  {_('History messages')}:    {len(config.history)} / {config.history.maxsize}")
    console.print(f"  {_('Uptime')}:      {config.uptime}")
    console.print()
    
    # 最近活动
    console.print(_("Recent activity"))
    last_time = config.history.last_received_time()
    if last_time:
        time_str = last_time.strftime("%H:%M:%S")
        delta = datetime.now() - last_time
        if delta.seconds < 60:
            ago = _("Just now")
        elif delta.seconds < 3600:
            ago = f"{delta.seconds // 60}{_('minutes ago')}"
        else:
            ago = f"{delta.seconds // 3600}{_('hours ago')}"
        console.print(f"  {_('Last received')}:      {time_str} ({ago})")
        
        # 最近消息预览
        if len(config.history) > 0:
            last_msg = config.history.list()[0]
            preview = last_msg.preview[:30] + "..." if len(last_msg.preview) > 30 else last_msg.preview
            console.print(f"  {_('Message preview')}:      \"{preview}\"")
    else:
        console.print(f"  {_('Last received')}:      {_('None')}")
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
        console.print(_("No history messages"))
        return
    
    console.print()
    
    # 固定预览宽度：20个全角字符 = 40个半角字符宽度
    PREVIEW_MAX_WIDTH = 40
    
    # 打印表头
    header = f"{_('ID'):<4} {_('Preview'):<{PREVIEW_MAX_WIDTH}} {_('Time'):<8}"
    console.print(header, style="dim")
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
        console.print(_("No history messages"))
        return
    
    console.print()
    
    PREVIEW_MAX_WIDTH = 28
    SOURCE_MAX_WIDTH = 20
    
    # 打印表头
    header = f"{_('ID'):<4} {_('Preview'):<{PREVIEW_MAX_WIDTH}} {_('Source'):<{SOURCE_MAX_WIDTH}} {_('Time'):<8}"
    console.print(header, style="dim")
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
            preview_text = f"[{session['count']}{_('items')}] {session['text']}"
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
        console.print(_("No beautification records"))
        return
    
    console.print()
    PREVIEW_MAX_WIDTH = 28
    SOURCE_MAX_WIDTH = 20
    
    header = f"{_('ID'):<4} {_('Preview'):<{PREVIEW_MAX_WIDTH}} {_('Source'):<{SOURCE_MAX_WIDTH}} {_('Time'):<8}"
    console.print(header, style="dim")
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
        console.print(_("No online devices"))
        return
    
    console.print()
    header = f"{_('Device name'):<16} {_('Login ID'):<10} {_('Login time'):<20}"
    console.print(header, style="dim")
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
    status = f" [{_('received [auto]').split(' ')[-1]}]" if auto_copied else ""
    source = f"[{entry.device_name}]" if entry.device_name else ""
    preview = _truncate_text(entry.text, 20)
    verb = _("received [auto]").split(' ')[0] if auto_copied else _("received").split(' ')[0]
    print(f"[{time_str}] {verb}{status} {source}: {preview}")


def print_help() -> str:
    """打印帮助信息"""
    from rich.text import Text
    
    console.print(f"\n[bold green]{_('Local Portal Command Help')}[/bold green]\n")

    def print_cmd(cmd: str, desc: str):
        """打印命令行，命令部分带颜色，描述部分普通"""
        t = Text()
        t.append(f"  {cmd:<22}", style="cyan")
        t.append(desc)
        console.print(t)

    console.print(f"[bold yellow]{_('Basic operations')}[/bold yellow]")
    print_cmd("/copy [N]", _("Copy history message (N=1-10, no arg = most recent)"))
    print_cmd("/list (/ls)", _("List last 10 message summaries"))
    print_cmd("/status", _("Show service runtime status"))
    print_cmd("/open", _("Open main page in browser"))
    print_cmd("/qrcode (/qr)", _("Show QR code (scan to connect)"))
    print_cmd("/downloads", _("Open download folder"))

    console.print(f"\n[bold yellow]{_('Mode & Session')}[/bold yellow]")
    print_cmd("/auto [on|off]", _("Enable/disable auto copy mode"))
    print_cmd("/mode [cover|add]", _("Switch copy mode (cover=overwrite, add=append)"))
    print_cmd("/new-session", _("Refresh session in append mode, clear buffer"))

    console.print(f"\n[bold yellow]{_('Device management')}[/bold yellow]")
    print_cmd("/devices", _("View all logged-in devices"))
    print_cmd("/link <name|id>", _("Enter session mode with a specific device"))
    print_cmd("/unlink", _("Exit device session mode"))
    print_cmd("/send <filepath>", _("Send a file to current session device (use after /link)"))

    console.print(f"\n[bold yellow]{_('Text beautification')}[/bold yellow]")
    print_cmd("/beauty [N]", _("Beautify the Nth history message via LLM (default: most recent)"))
    print_cmd("/beauty-history", _("View last 10 text beautification tasks"))
    print_cmd("/beauty-copy [N]", _("Copy the Nth beautification result (default: most recent)"))

    console.print(f"\n[bold yellow]{_('Others')}[/bold yellow]")
    print_cmd("/refresh-qrcode (/rq)", _("Refresh pairing code (all clients need to re-login)"))
    print_cmd("/help", _("Show this help"))
    print_cmd("/exit", _("Exit program"))

    console.print(f"\n[bold]{_('Mode description')}:[/bold]")
    console.print(f"  [dim]cover ({_('default')})[/dim] - {_('cover (default) - new message overwrites the previous one, good for single copy')}")
    console.print(f"  [dim]add[/dim]          - {_('add - new message appends to the end, good for merging multiple')}")

    console.print(f"\n[bold]{_('Download directory settings')}:[/bold]")
    console.print(f"  {_('Default save to system download folder, customize via')} [cyan]LPORTAL_DOWNLOAD_DIR[/cyan]")
    console.print(f"\n  [bold]{_('Windows (PowerShell)')}: [/bold]")
    console.print('    [green]$env:LPORTAL_DOWNLOAD_DIR="C:\\Users\\xx\\Downloads"[/green]')
    console.print(f"  [bold]{_('Windows (CMD)')}: [/bold]")
    console.print("    [green]set LPORTAL_DOWNLOAD_DIR=C:\\Users\\xx\\Downloads[/green]")
    console.print(f"\n  [bold]{_('macOS / Linux (bash / zsh)')}: [/bold]")
    console.print("    [green]export LPORTAL_DOWNLOAD_DIR=/Users/xx/Downloads[/green]")
    console.print(f"  [bold]{_('Permanent (append to ~/.bashrc or ~/.zshrc)')}: [/bold]")
    console.print('    [green]echo "export LPORTAL_DOWNLOAD_DIR=/Users/xx/Downloads" >> ~/.zshrc[/green]')
    console.print("    [green]source ~/.zshrc[/green]")

    console.print(f"\n[bold]{_('LLM config (text beautification)')}: [/bold]")
    console.print(f"  {_('Create .env file in one of the following places')}:")
    console.print(f"    - {_('Current working directory')}: [cyan]./[/cyan]")
    console.print(f"    - {_('Windows')}: [cyan]%APPDATA%\\localportal\\.env[/cyan]")
    console.print(f"    - {_('macOS')}: [cyan]~/Library/Application Support/localportal/.env[/cyan]")
    console.print(f"    - {_('Linux')}: [cyan]~/.config/localportal/.env[/cyan]")
    console.print(f"\n  {_('Config content')}:")
    console.print('    [green]OPENAI_BASE_URL=https://api.openai.com/v1[/green]')
    console.print('    [green]OPENAI_API_KEY=sk-xxxxxx[/green]')
    console.print('    [green]OPENAI_MODEL=gpt-3.5-turbo[/green]')

    console.print(f"\n[bold]{_('Custom prompt')}:[/bold]")
    console.print(f"  {_('Place text-beauty.md in user config dir to override default prompt')}")
    console.print()
    return ""
