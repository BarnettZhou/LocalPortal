"""斜杠命令处理器"""

import asyncio
import shlex
from pathlib import Path
from typing import TYPE_CHECKING, Optional

import pyperclip

from .beauty import beautify_text
from .file_transfer import get_file_transfer_manager
from .i18n import _
from .ui import console, print_beauty_list, print_help

if TYPE_CHECKING:
    from .config import ServerConfig
    from .main import PortalApp
    from .server import Server


class CommandHandler:
    """命令处理器"""
    
    def __init__(self, config: "ServerConfig", server: "Server", app: Optional["PortalApp"] = None):
        self.config = config
        self.server = server
        self.app = app
    
    async def handle(self, cmd_line: str) -> str:
        """
        处理命令行输入
        返回值: 要显示的消息（空字符串表示无输出）
        """
        try:
            # 使用 posix=False 避免反斜杠被当作转义字符（Windows 路径）
            parts = shlex.split(cmd_line.strip(), posix=False)
        except ValueError:
            # shlex 解析失败（如引号不匹配），回退到简单 split
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
            case "/downloads":
                return self._handle_downloads()
            case "/help":
                return self._handle_help()
            case "/exit":
                return self._handle_exit()
            case "/refresh-qrcode" | "/rq":
                return self._handle_refresh_qrcode()
            case "/mode":
                return await self._handle_mode(args)
            case "/new-session":
                return self._handle_new_session()
            case "/beauty":
                return await self._handle_beauty(args)
            case "/beauty-history":
                return self._handle_beauty_history()
            case "/beauty-copy":
                return self._handle_beauty_copy(args)
            case "/devices":
                return self._handle_devices()
            case "/link":
                return await self._handle_link(args)
            case "/unlink":
                return self._handle_unlink()
            case "/send":
                return await self._handle_send(args)
            case _:
                return f"{_('[?] Unknown command')}: {cmd}, {_('type /help for available commands')}"
    
    def _handle_auto(self, args: list[str]) -> str:
        """处理 /auto 命令"""
        if not args:
            status = _("ON [OK]") if self.config.auto_copy else _("OFF [X]")
            return _("Auto copy mode: {status}").format(status=status)
        
        match args[0].lower():
            case "on" | "1" | "true":
                self.config.auto_copy = True
                return _("[OK] Auto copy mode: ON")
            case "off" | "0" | "false":
                self.config.auto_copy = False
                return _("[OK] Auto copy mode: OFF")
            case _:
                return _("Usage: /auto [on|off]")
    
    def _handle_copy(self, args: list[str]) -> str:
        """处理 /copy 命令"""
        try:
            if not args:
                # 复制最近一条
                if len(self.config.history) == 0:
                    return _("[!] No history messages")
                entry = self.config.history.get(1)
            else:
                # 复制指定索引
                index = int(args[0])
                entry = self.config.history.get(index)
            
            # 找到同一 session 的所有消息
            session_entries = [
                e for e in self.config.history.list()
                if e.session_id == entry.session_id
            ]
            # 按时间正序排列（最早的在前）
            session_entries.reverse()
            copy_text = '\n'.join(e.text for e in session_entries)
            count = len(session_entries)
            
            # 构建预览文本
            if count > 1:
                preview = f"[{count}{_('items')}] {entry.preview[:20]}..."
            else:
                preview = entry.preview[:30] + "..." if len(entry.preview) > 30 else entry.preview
            
            pyperclip.copy(copy_text)
            return f"{_('[OK] Copied')}: {preview}"
        
        except (ValueError, IndexError) as e:
            return _("[!] {e}").format(e=e)
    
    def _handle_list(self) -> str:
        """处理 /list 命令"""
        from .ui import print_session_list
        entries = self.config.history.list()
        if not entries:
            return _("No history messages")
        
        # 统一按 session 分组显示
        print_session_list(entries)
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
        return f"{_('[OK] Opened in browser')} {url}"
    
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
            _("Scan the QR code with your phone or visit the address below"),
            "",
            qr_ascii,
            "",
            f"{_('Pairing code')}: {pairing_code}",
            f"{_('Address')}: {url}",
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
    
    def _handle_refresh_qrcode(self) -> str:
        """处理 /refresh-qrcode 命令 - 刷新配对码"""
        old_code = self.config.pairing_code
        new_code = self.config.refresh_pairing_code()
        # 断开所有已验证客户端（需要重新登录）
        for client in list(self.server.verified_clients):
            if not client.closed:
                asyncio.create_task(client.send_json({
                    "type": "auth_failed",
                    "message": _("Pairing code refreshed, please re-login")
                }))
                asyncio.create_task(client.close())
        self.server.verified_clients.clear()
        return f"{_('[OK] Pairing code refreshed')}: {old_code} -> {new_code}, {_('All clients disconnected')}"
    
    async def _handle_mode(self, args: list[str]) -> str:
        """处理 /mode 命令 - 切换复制模式"""
        if not args:
            mode_desc = _("append") if self.config.copy_mode == 'add' else _("cover")
            return f"{_('Current copy mode')}: {self.config.copy_mode} ({mode_desc})"
        
        mode = args[0].lower()
        if mode == 'cover':
            if self.config.copy_mode != 'cover':
                self.config.copy_mode = 'cover'
                # 切换模式时重置会话，确保新消息与旧消息分开
                self.config.new_session()
                self.config.session_buffer = ''
                await self.server.broadcast({
                    "type": "mode_changed",
                    "mode": "cover",
                    "message": _("Switched to cover mode")
                })
            return _("[OK] Copy mode: cover (overwrite)")
        elif mode == 'add':
            if self.config.copy_mode != 'add':
                self.config.copy_mode = 'add'
                # 切换模式时重置会话，确保新消息与旧消息分开
                self.config.new_session()
                await self.server.broadcast({
                    "type": "mode_changed",
                    "mode": "add",
                    "message": _("Switched to append mode")
                })
            return _("[OK] Copy mode: add (append)")
        else:
            return _("Usage: /mode [cover|add]\n  cover - overwrite mode, new message overwrites previous (default)\n  add   - append mode, new message appends to end")
    
    def _handle_new_session(self) -> str:
        """处理 /new-session 命令 - 追加模式下刷新会话"""
        if self.config.copy_mode != 'add':
            return _("[!] /new-session is only available in append mode, currently in overwrite mode")
        
        self.config.session_buffer = ''
        return _("[OK] Session refreshed, next message will be the first")
    
    async def _handle_beauty(self, args: list[str]) -> str:
        """处理 /beauty 命令 - 使用 LLM 美化文本"""
        try:
            if not args:
                if len(self.config.history) == 0:
                    return _("[!] No history messages")
                entry = self.config.history.get(1)
            else:
                index = int(args[0])
                entry = self.config.history.get(index)
            
            # 找到同一 session 的所有消息
            session_entries = [
                e for e in self.config.history.list()
                if e.session_id == entry.session_id
            ]
            session_entries.reverse()
            original_text = '\n'.join(e.text for e in session_entries)
            
            # 调用 LLM 进行流式美化
            result = await beautify_text(original_text, console)
            
            # 保存到美化历史（继承原消息的设备信息）
            self.config.beauty_history.add(
                original_text, result,
                device_name=entry.device_name,
                login_id=entry.login_id
            )
            
            # 复制到剪贴板
            pyperclip.copy(result)
            
            return _("[OK] Beautified and copied to clipboard")
        
        except (ValueError, IndexError) as e:
            return _("[!] {e}").format(e=e)
        except Exception as e:
            return f"{_('[!] Beautification failed')}: {e}"
    
    def _handle_beauty_history(self) -> str:
        """处理 /beauty-history 命令"""
        entries = self.config.beauty_history.list()
        if not entries:
            return _("No beautification records")
        print_beauty_list(entries)
        return ""
    
    def _handle_beauty_copy(self, args: list[str]) -> str:
        """处理 /beauty-copy 命令"""
        try:
            if not args:
                if len(self.config.beauty_history) == 0:
                    return _("[!] No beautification records")
                entry = self.config.beauty_history.get(1)
            else:
                index = int(args[0])
                entry = self.config.beauty_history.get(index)
            
            pyperclip.copy(entry.result)
            preview = entry.preview[:30] + "..." if len(entry.preview) > 30 else entry.preview
            return f"{_('[OK] Copied')}: {preview}"
        
        except (ValueError, IndexError) as e:
            return _("[!] {e}").format(e=e)
    
    def _handle_devices(self) -> str:
        """处理 /devices 命令 - 查看已登录设备"""
        from .ui import print_devices
        online_devices = [
            info for info in self.server.devices.values()
            if info.ws is not None and not info.ws.closed
        ]
        if not online_devices:
            return _("No online devices")
        print_devices(online_devices)
        return ""
    
    async def _handle_link(self, args: list[str]) -> str:
        """处理 /link 命令 - 进入设备会话模式"""
        if not args:
            if self.app and self.app.linked_device_name:
                return f"{_('Currently linked device')}: {self.app.linked_device_name} ({self.app.linked_login_id})"
            return _("Usage: /link <device_name or login_id>")
        
        target = args[0].strip()
        
        # 先按 login_id 精确匹配
        device = self.server.devices.get(target)
        if not device:
            # 再按设备名称匹配在线设备
            for info in self.server.devices.values():
                if info.device_name == target and info.ws is not None and not info.ws.closed:
                    device = info
                    break
        
        if not device or not device.ws or device.ws.closed:
            return f"{_('[!] Online device not found')}: {target}"
        
        if self.app:
            self.app.linked_device_name = device.device_name
            self.app.linked_login_id = device.login_id
        
        return f"{_('[OK] Entered device session mode')}: {device.device_name} ({device.login_id})\n{_('Hint: type directly to send, /unlink to exit')}"
    
    def _handle_unlink(self) -> str:
        """处理 /unlink 命令 - 退出设备会话模式"""
        if self.app:
            old_name = self.app.linked_device_name
            self.app.linked_device_name = ""
            self.app.linked_login_id = ""
            if old_name:
                return _("[OK] Exited session mode with {name}").format(name=old_name)
        return _("[!] Not in any device session mode")
    
    async def _handle_send(self, args: list[str]) -> str:
        """处理 /send 命令 - 向已连接设备发送文件"""
        if not self.app or not self.app.linked_login_id:
            return _("[!] /send must be used after /link session mode, please run /link <device_name> first")
        
        if not args:
            return _("Usage: /send <filepath>\nExample: /send C:\\Users\\xx\\Documents\\file.pdf")
        
        filepath = " ".join(args)  # 支持带空格的路径
        # 去除可能的引号
        filepath = filepath.strip('"\'')
        file_path = Path(filepath).expanduser().resolve()
        
        if not file_path.exists():
            return f"{_('[!] File does not exist')}: {filepath}"
        
        if not file_path.is_file():
            return f"{_('[!] Not a file')}: {filepath}"
        
        # 检查文件大小（最大 100MB）
        max_size = 100 * 1024 * 1024
        file_size = file_path.stat().st_size
        if file_size > max_size:
            return f"{_('[!] File too large')}: {file_size / 1024 / 1024:.1f}MB ({_('max 100MB')})"
        
        try:
            result = await self.server.send_server_file(
                str(file_path),
                self.app.linked_login_id
            )
            if result:
                return f"{_('[OK] File sent to')} {self.app.linked_device_name}: {file_path.name} ({file_size / 1024:.1f}KB)"
            else:
                return _("[!] Send failed, device may be offline")
        except Exception as e:
            return f"{_('[!] Send failed')}: {e}"
    
    def _handle_downloads(self) -> str:
        """处理 /downloads 命令 - 打开下载文件夹"""
        try:
            ftm = get_file_transfer_manager()
            ftm.open_downloads_folder()
            return f"{_('[OK] Download folder opened')}: {ftm.download_dir}"
        except Exception as e:
            return f"{_('[!] Failed to open download folder')}: {e}"
