"""CLI 入口"""

import asyncio
import signal
from typing import Optional

import typer
from prompt_toolkit import PromptSession
from prompt_toolkit.patch_stdout import patch_stdout

from .commands import CommandHandler
from .config import ServerConfig
from .qr import get_local_ip, generate_qr_ascii
from .server import Server
from .ui import print_banner, print_message, print_new_message

app = typer.Typer(
    add_completion=False,
    help="Local Portal - 局域网语音输入中转工具"
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
            print_message(f"[ERROR] 启动失败: {e}", style="bold red")
            return
        
        # 打印横幅和二维码
        print_banner(self.config)
        
        # 首次启动显示二维码
        qr_url = self.config.qr_url
        qr_ascii = generate_qr_ascii(qr_url)
        print_message("手机扫描二维码连接：")
        print_message(qr_ascii)
        print_message(f"配对码: {self.config.pairing_code}")
        print_message(f"地址: {qr_url}")
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
                            print_message("[!] 发送失败，设备可能已离线")
                        continue
                    
                    result = await self.cmd_handler.handle(cmd)
                    if result:
                        print_message(result)
                
                except SystemExit:
                    break
                except KeyboardInterrupt:
                    # Ctrl+C 已禁用退出，保留用于复制
                    print_message("[提示] Ctrl+C 已禁用退出，使用 /exit 退出程序")
                    continue
                except Exception as e:
                    print_message(f"[ERROR] 错误: {e}", style="red")
        
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
                    error = msg.get("error", "未知错误")
                    print_message(f"[WARN] 剪贴板错误: {error}")
                
                elif msg["type"] == "file_received":
                    from datetime import datetime
                    path = msg.get("path", "")
                    time_str = datetime.now().strftime("%H:%M:%S")
                    print_message(f"[{time_str}] 收到文件 [已保存]: {path}")
                
                elif msg["type"] == "server_message_sent":
                    entry = msg["entry"]
                    from datetime import datetime
                    time_str = datetime.now().strftime("%H:%M:%S")
                    preview = entry.preview[:30] + "..." if len(entry.preview) > 30 else entry.preview
                    print_message(f"[{time_str}] -> 设备: {preview}")
            
            except Exception:
                continue
    
    async def shutdown(self) -> None:
        """强制关闭服务"""
        print_message("正在关闭服务...")
        # 发送退出信号给消息处理任务
        await self.server.terminal_queue.put(None)
        await self.server.stop(force=True)
        print_message("服务已关闭")


@app.command()
def run(
    port: int = typer.Option(14554, "--port", "-p", help="服务端口"),
    auto_copy: bool = typer.Option(True, "--auto-copy/--no-auto-copy", help="自动复制模式"),
    max_history: int = typer.Option(10, "--max-history", help="最大历史条数"),
) -> None:
    """
    启动 Local Portal 服务
    
    手机语音输入 -> 电脑剪贴板实时同步
    """
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
