"""HTTP + WebSocket 服务"""

import asyncio
import json
from pathlib import Path
from typing import Optional

import pyperclip
from aiohttp import web

from .config import ServerConfig
from .history import History, MessageEntry
from .qr import generate_qr_html, generate_qr_png, get_local_ip


class Server:
    """HTTP/WebSocket 服务器"""
    
    def __init__(self, config: ServerConfig):
        self.config = config
        self.app = web.Application()
        self.runner: Optional[web.AppRunner] = None
        self.site: Optional[web.TCPSite] = None
        self._setup_routes()
        
        # 终端消息队列（用于从 WebSocket 处理器传递消息到主线程）
        self.terminal_queue: asyncio.Queue = asyncio.Queue()
    
    def _setup_routes(self) -> None:
        """设置 HTTP 路由"""
        self.app.router.add_get('/', self.handle_index)
        self.app.router.add_get('/qr', self.handle_qr_page)
        self.app.router.add_get('/qr.png', self.handle_qr_image)
        self.app.router.add_get('/ws', self.handle_websocket)
    
    async def handle_index(self, request: web.Request) -> web.Response:
        """主页面 - 移动端输入界面"""
        static_dir = Path(__file__).parent.parent.parent / "static"
        index_file = static_dir / "index.html"
        if index_file.exists():
            return web.FileResponse(index_file)
        return web.Response(text="index.html not found", status=404)
    
    async def handle_qr_page(self, request: web.Request) -> web.Response:
        """二维码页面"""
        lan_url = f"http://{get_local_ip()}:{self.config.port}"
        html = generate_qr_html(lan_url)
        return web.Response(text=html, content_type='text/html')
    
    async def handle_qr_image(self, request: web.Request) -> web.Response:
        """二维码图片接口"""
        lan_url = f"http://{get_local_ip()}:{self.config.port}"
        img_buffer = generate_qr_png(lan_url)
        return web.Response(body=img_buffer, content_type='image/png')
    
    async def handle_websocket(self, request: web.Request) -> web.WebSocketResponse:
        """WebSocket 连接处理"""
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        
        # 注册客户端
        self.config.connected_clients.add(ws)
        
        try:
            # 发送历史记录
            history_data = [
                {
                    "id": e.id,
                    "text": e.text,
                    "time": e.time.isoformat(),
                    "preview": e.preview
                }
                for e in self.config.history.list()
            ]
            await ws.send_json({"type": "history", "data": history_data})
            
            # 监听消息
            async for msg in ws:
                if msg.type == web.WSMsgType.TEXT:
                    try:
                        data = json.loads(msg.data)
                        if data.get("type") == "text":
                            await self._handle_text_message(
                                data.get("content", ""), 
                                ws,
                                data.get("client_id")  # 传递客户端临时ID
                            )
                    except json.JSONDecodeError:
                        pass
                elif msg.type == web.WSMsgType.ERROR:
                    break
        finally:
            # 注销客户端
            self.config.connected_clients.discard(ws)
        
        return ws
    
    async def _handle_text_message(self, text: str, sender: web.WebSocketResponse, client_id: str = None) -> None:
        """处理文本消息"""
        if not text:
            return
        
        # 1. 存入历史
        entry = self.config.history.add(text)
        
        # 2. 自动复制（如果开启）
        auto_copied = False
        if self.config.auto_copy:
            try:
                # 剪贴板操作需要在单独线程中执行
                await asyncio.get_event_loop().run_in_executor(
                    None, pyperclip.copy, text
                )
                auto_copied = True
            except Exception as e:
                await self.terminal_queue.put({
                    "type": "clipboard_error",
                    "error": str(e)
                })
        
        # 3. 通知终端显示
        await self.terminal_queue.put({
            "type": "new_message",
            "entry": entry,
            "auto_copied": auto_copied
        })
        
        # 4. 发送确认给发送者（不广播给其他客户端 - 按需求）
        if not sender.closed:
            await sender.send_json({
                "type": "ack",
                "id": client_id or entry.id,  # 返回客户端提供的临时ID
                "server_id": entry.id
            })
    
    async def start(self) -> int:
        """启动服务器，返回实际使用的端口"""
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        
        # 尝试绑定端口，如果被占用则递增
        port = self.config.port
        max_attempts = 10
        
        for attempt in range(max_attempts):
            try:
                self.site = web.TCPSite(self.runner, self.config.host, port)
                await self.site.start()
                self.config.port = port  # 更新实际端口
                return port
            except OSError:
                if attempt < max_attempts - 1:
                    port += 1
                else:
                    raise RuntimeError(f"无法绑定端口 {self.config.port}-{port}")
        
        return port
    
    async def stop(self, force: bool = True) -> None:
        """停止服务器
        
        Args:
            force: 是否强制关闭（不等待连接优雅关闭）
        """
        # 1. 先通知所有客户端服务即将关闭
        if self.config.connected_clients:
            close_msg = {"type": "server_close", "message": "服务已关闭"}
            # 并发发送关闭通知
            await asyncio.gather(
                *[client.send_json(close_msg) for client in self.config.connected_clients if not client.closed],
                return_exceptions=True
            )
            # 关闭所有 WebSocket 连接
            for client in list(self.config.connected_clients):
                if not client.closed:
                    await client.close()
        
        # 2. 停止 HTTP 服务
        if self.site:
            await self.site.stop()
        if self.runner:
            await self.runner.cleanup()
