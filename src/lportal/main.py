"""CLI 入口"""

import asyncio
import os
import signal
import subprocess
import sys
from typing import Optional

import typer
from prompt_toolkit import PromptSession
from prompt_toolkit.patch_stdout import patch_stdout

from .commands import CommandHandler
from .config import ServerConfig
from .i18n import _, set_locale
from .qr import get_local_ip, generate_qr_ascii
from .server import Server
from .ui import print_banner, print_message, print_new_message


def check_existing_process() -> bool:
    """检查是否已有同名进程在运行
    
    Returns:
        True: 已有进程在运行
        False: 没有检测到运行中的进程
    """
    current_pid = os.getpid()
    
    # 根据操作系统使用不同命令
    if sys.platform == 'darwin':  # macOS
        try:
            result = subprocess.run(
                ['pgrep', '-f', 'lportal'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                pids = [int(p.strip()) for p in result.stdout.strip().split('\n') if p.strip()]
                # 排除当前进程
                other_pids = [p for p in pids if p != current_pid]
                return len(other_pids) > 0
        except Exception:
            pass
    elif sys.platform == 'linux':
        try:
            result = subprocess.run(
                ['pgrep', '-f', 'lportal'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                pids = [int(p.strip()) for p in result.stdout.strip().split('\n') if p.strip()]
                other_pids = [p for p in pids if p != current_pid]
                return len(other_pids) > 0
        except Exception:
            pass
    elif sys.platform == 'win32':  # Windows
        try:
            result = subprocess.run(
                ['wmic', 'process', 'where', 'name="python.exe"', 'get', 'ProcessId,CommandLine'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                count = 0
                for line in lines:
                    if 'lportal' in line.lower():
                        parts = line.strip().split()
                        if parts:
                            try:
                                pid = int(parts[-1])
                                if pid != current_pid:
                                    count += 1
                            except ValueError:
                                continue
                return count > 0
        except Exception:
            pass
    
    return False

app = typer.Typer(
    add_completion=False,
    help=_("Local Portal - LAN voice input relay tool")
)


class PortalApp:
    """Local Portal 主应用"""
    
    def __init__(self, config: ServerConfig):
        self.config = config
        self.server = Server(config)
        self.cmd_handler = CommandHandler(config, self.server, self)
        self.session = PromptSession()
        self.running = True
        self.linked_device_name: str = ""
        self.linked_login_id: str = ""
    
    async def run(self) -> None:
        """主运行循环"""
        # 启动服务器
        try:
            actual_port = await self.server.start()
        except RuntimeError as e:
            print_message(_("[ERROR] Startup failed: {e}").format(e=e), style="bold red")
            return
        
        # 打印横幅和二维码
        print_banner(self.config)
        
        # 首次启动显示二维码
        qr_url = self.config.qr_url
        qr_ascii = generate_qr_ascii(qr_url)
        print_message(_("Scan QR code with phone to connect"))
        print_message(qr_ascii)
        print_message(f"{_('Pairing code')}: {self.config.pairing_code}")
        print_message(f"{_('Address')}: {qr_url}")
        print_message("")
        
        # 设置信号处理（禁用 Ctrl+C 退出，保留复制功能）
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGTERM,):
            try:
                loop.add_signal_handler(sig, self._signal_handler)
            except NotImplementedError:
                # Windows 不支持某些信号
                pass
        
        # 启动终端消息处理任务
        asyncio.create_task(self._process_terminal_messages())
        
        # 命令行交互循环
        try:
            while self.running:
                try:
                    with patch_stdout():
                        prompt_text = f"lportal[{self.linked_device_name}]> " if self.linked_device_name else "lportal> "
                        cmd = await self.session.prompt_async(prompt_text)
                    
                    if not cmd.strip():
                        continue
                    
                    # 如果处于 link 模式且输入不是命令，则作为消息发送
                    if self.linked_login_id and not cmd.startswith("/"):
                        entry = await self.server.send_server_text(cmd.strip(), self.linked_login_id)
                        if entry:
                            from datetime import datetime
                            time_str = datetime.now().strftime("%H:%M:%S")
                            print_message(f"[{time_str}] -> {self.linked_device_name}: {entry.preview[:30]}...")
                        else:
                            print_message(_("Failed to send, device may be offline"))
                        continue
                    
                    result = await self.cmd_handler.handle(cmd)
                    if result:
                        print_message(result)
                
                except SystemExit:
                    break
                except KeyboardInterrupt:
                    # Ctrl+C 已禁用退出，保留用于复制
                    print_message(_("[Hint] Ctrl+C is disabled for exit, use /exit to quit"))
                    continue
                except Exception as e:
                    print_message(_("[ERROR] Error: {e}").format(e=e), style="red")
        
        finally:
            await self.shutdown()
    
    def _signal_handler(self) -> None:
        """信号处理函数"""
        self.running = False
    
    async def _process_terminal_messages(self) -> None:
        """处理来自 WebSocket 的终端消息 - 事件驱动，无消息时零CPU"""
        while self.running:
            try:
                # 阻塞等待消息（无消息时零CPU占用）
                msg = await self.server.terminal_queue.get()
                
                # None 是退出信号
                if msg is None:
                    break
                
                if msg["type"] == "new_message":
                    entry = msg["entry"]
                    auto_copied = msg.get("auto_copied", False)
                    print_new_message(entry, auto_copied)
                
                elif msg["type"] == "clipboard_error":
                    error = msg.get("error", _("Unknown error"))
                    print_message(f"[WARN] {_('Clipboard error')}: {error}")
                
                elif msg["type"] == "file_received":
                    from datetime import datetime
                    path = msg.get("path", "")
                    time_str = datetime.now().strftime("%H:%M:%S")
                    print_message(f"[{time_str}] {_('File received')}: {path}")
                
                elif msg["type"] == "server_message_sent":
                    # 已在发送时打印，这里不再重复显示
                    pass
            
            except Exception:
                continue
    
    async def shutdown(self) -> None:
        """强制关闭服务"""
        print_message(_("Closing service..."))
        # 发送退出信号给消息处理任务
        await self.server.terminal_queue.put(None)
        await self.server.stop(force=True)
        print_message(_("Service closed"))


@app.command()
def run(
    port: int = typer.Option(14554, "--port", "-p", help="Service port"),
    auto_copy: bool = typer.Option(True, "--auto-copy/--no-auto-copy", help="Auto copy mode"),
    max_history: int = typer.Option(10, "--max-history", help="Max history entries"),
    zh: bool = typer.Option(False, "--zh", help="Force Chinese language"),
    en: bool = typer.Option(False, "--en", help="Force English language"),
) -> None:
    """
    启动 Local Portal 服务
    
    手机语音输入 -> 电脑剪贴板实时同步
    """
    # 设置语言（命令行参数优先）
    if zh:
        set_locale("zh")
    elif en:
        set_locale("en")
    # 否则保持自动检测
    
    # 检查是否已有同名进程在运行
    if check_existing_process():
        print_message(_("Another instance is already running"), style="bold red")
        print_message(_("Please stop the existing service first, or use /exit to quit"))
        sys.exit(1)
    
    # 创建配置
    config = ServerConfig(
        port=port,
        auto_copy=auto_copy,
        max_history=max_history
    )
    
    # 运行应用
    portal = PortalApp(config)
    try:
        asyncio.run(portal.run())
    except KeyboardInterrupt:
        pass


def main() -> None:
    """入口函数"""
    app()
