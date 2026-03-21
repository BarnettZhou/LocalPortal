"""终端 UI - 使用 rich 库"""

from datetime import datetime
from typing import TYPE_CHECKING, List

from rich.console import Console

if TYPE_CHECKING:
    from .config import ServerConfig
    from .history import MessageEntry


console = Console()


def print_banner(host: str, port: int, lan_ip: str) -> None:
    """打印启动横幅"""
    console.print()
    console.print("Local Portal 启动中...", style="bold green")
    console.print("-" * 40)
    console.print()
    console.print("服务地址:")
    console.print(f"   本机:   http://localhost:{port}")
    console.print(f"   局域网: http://{lan_ip}:{port}")
    console.print()
    console.print("提示: 使用 /qrcode 命令在浏览器中打开二维码页面，方便手机扫码")
    console.print()
    console.print("-" * 40)
    console.print("可用命令: /auto, /copy, /list, /status, /open, /qrcode, /exit, /help")
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
    
    # 运行状态
    console.print("运行状态")
    auto_status = "开启 [OK]" if config.auto_copy else "关闭 [X]"
    console.print(f"  自动复制模式:  {auto_status}")
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


def print_message(msg: str, style: str = "") -> None:
    """打印普通消息 - 使用纯文本避免样式问题"""
    print(msg)


def print_new_message(entry: "MessageEntry", auto_copied: bool = False) -> None:
    """打印新消息通知 - 使用纯文本避免样式问题"""
    time_str = entry.time.strftime("%H:%M:%S")
    status = " [auto]" if auto_copied else ""
    print(f"[{time_str}] 收到消息{status}")
    preview = entry.text[:60] + "..." if len(entry.text) > 60 else entry.text
    print(f"  -> {preview}")


def print_help() -> str:
    """返回帮助信息文本"""
    help_text = """
Local Portal 命令帮助

/auto [on|off]     开启/关闭自动复制模式
/copy [N]          复制历史消息（N=1-10，无参=最近一条）
/list              列出最近10条消息摘要
/status            显示服务运行状态
/open              在浏览器中打开主页面
/qrcode            在浏览器中打开二维码页面
/help              显示此帮助信息
/exit              退出程序
"""
    return help_text.strip()
