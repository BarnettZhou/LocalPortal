"""斜杠命令处理器"""

import asyncio
from typing import TYPE_CHECKING, Optional

import pyperclip

from .ui import print_help

if TYPE_CHECKING:
    from .config import ServerConfig
    from .server import Server


class CommandHandler:
    """命令处理器"""
    
    def __init__(self, config: "ServerConfig", server: "Server"):
        self.config = config
        self.server = server
    
    def handle(self, cmd_line: str) -> str:
        """
        处理命令行输入
        返回值: 要显示的消息（空字符串表示无输出）
        """
        parts = cmd_line.strip().split()
        if not parts:
            return ""
        
        cmd = parts[0].lower()
        args = parts[1:]
        
        match cmd:
            case "/auto":
                return self._handle_auto(args)
            case "/copy":
                return self._handle_copy(args)
            case "/list" | "/ls":
                return self._handle_list()
            case "/status":
                return self._handle_status()
            case "/open":
                return self._handle_open()
            case "/qrcode" | "/qr":
                return self._handle_qrcode()
            case "/help":
                return self._handle_help()
            case "/exit":
                return self._handle_exit()
            case "/refresh":
                return self._handle_refresh()
            case _:
                return f"[?] 未知命令: {cmd}，输入 /help 查看可用命令"
    
    def _handle_auto(self, args: list[str]) -> str:
        """处理 /auto 命令"""
        if not args:
            status = "开启 [OK]" if self.config.auto_copy else "关闭 [X]"
            return f"自动复制模式: {status}"
        
        match args[0].lower():
            case "on" | "1" | "true":
                self.config.auto_copy = True
                return "[OK] 自动复制模式: 开启"
            case "off" | "0" | "false":
                self.config.auto_copy = False
                return "[OK] 自动复制模式: 关闭"
            case _:
                return "用法: /auto [on|off]"
    
    def _handle_copy(self, args: list[str]) -> str:
        """处理 /copy 命令"""
        try:
            if not args:
                # 复制最近一条
                if len(self.config.history) == 0:
                    return "[!] 暂无历史消息"
                entry = self.config.history.get(1)
            else:
                # 复制指定索引
                index = int(args[0])
                entry = self.config.history.get(index)
            
            pyperclip.copy(entry.text)
            preview = entry.preview[:30] + "..." if len(entry.preview) > 30 else entry.preview
            return f"[OK] 已复制: {preview}"
        
        except (ValueError, IndexError) as e:
            return f"[!] {e}"
    
    def _handle_list(self) -> str:
        """处理 /list 命令"""
        from .ui import print_list
        entries = self.config.history.list()
        if not entries:
            return "暂无历史消息"
        print_list(entries)
        return ""
    
    def _handle_status(self) -> str:
        """处理 /status 命令"""
        from .ui import print_status
        print_status(self.config)
        return ""
    
    def _handle_open(self) -> str:
        """处理 /open 命令"""
        from .qr import open_browser
        url = self.config.local_url
        open_browser(url)
        return f"[OK] 已在浏览器中打开 {url}"
    
    def _handle_qrcode(self) -> str:
        """处理 /qrcode 命令 - 在终端显示 ASCII 二维码"""
        from .qr import generate_qr_ascii
        
        url = self.config.qr_url
        pairing_code = self.config.pairing_code
        
        # 生成 ASCII 二维码
        qr_ascii = generate_qr_ascii(url)
        
        # 构建输出
        lines = [
            "",
            "=" * 50,
            "手机扫描二维码或访问以下地址：",
            "",
            qr_ascii,
            "",
            f"配对码: {pairing_code}",
            f"地址: {url}",
            "=" * 50,
            "",
        ]
        
        return "\n".join(lines)
    
    def _handle_help(self) -> str:
        """处理 /help 命令"""
        return print_help()
    
    def _handle_exit(self) -> str:
        """处理 /exit 命令"""
        raise SystemExit
    
    def _handle_refresh(self) -> str:
        """处理 /refresh 命令 - 刷新配对码"""
        old_code = self.config.pairing_code
        new_code = self.config.refresh_pairing_code()
        # 断开所有已验证客户端（需要重新登录）
        for client in list(self.server.verified_clients):
            if not client.closed:
                asyncio.create_task(client.send_json({
                    "type": "auth_failed",
                    "message": "配对码已刷新，请重新登录"
                }))
                asyncio.create_task(client.close())
        self.server.verified_clients.clear()
        return f"[OK] 配对码已刷新: {old_code} -> {new_code}，所有客户端已断开"
