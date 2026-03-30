"""HTTP + WebSocket 服务"""

import asyncio
import base64
import json
from pathlib import Path
from typing import Optional, Set

import pyperclip
from aiohttp import web

from .config import ServerConfig
from .file_transfer import get_file_transfer_manager
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
        
        # 已验证的客户端（通过配对码验证）
        self.verified_clients: Set[web.WebSocketResponse] = set()
    
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
        """二维码页面 - 带配对码"""
        # 生成带配对码的 URL
        url_with_code = self.config.qr_url
        html = generate_qr_html(url_with_code)
        return web.Response(text=html, content_type='text/html')
    
    async def handle_qr_image(self, request: web.Request) -> web.Response:
        """二维码图片接口 - 带配对码"""
        # 生成带配对码的 URL
        url_with_code = self.config.qr_url
        img_buffer = generate_qr_png(url_with_code)
        return web.Response(body=img_buffer, content_type='image/png')
    
    async def handle_websocket(self, request: web.Request) -> web.WebSocketResponse:
        """WebSocket 连接处理"""
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        
        # 1. 等待配对码验证（循环直到验证成功或超时）
        authenticated = False
        for attempt in range(3):  # 最多允许 3 次验证尝试
            try:
                # 设置超时 10 秒等待配对码
                auth_msg = await asyncio.wait_for(ws.receive(), timeout=10.0)
                if auth_msg.type == web.WSMsgType.TEXT:
                    data = json.loads(auth_msg.data)
                    if data.get("type") == "auth":
                        code = data.get("code", "")
                        if code != self.config.pairing_code:
                            # 配对码错误，不关闭连接，让前端重新输入
                            await ws.send_json({"type": "auth_failed", "message": "配对码错误"})
                            continue  # 继续循环，等待重新输入
                        # 配对码正确
                        await ws.send_json({"type": "auth_success"})
                        authenticated = True
                        break
                    else:
                        # 未提供配对码，继续监听
                        await ws.send_json({"type": "auth_failed", "message": "请先发送配对码"})
                        continue
                else:
                    # 非文本消息，继续监听
                    continue
            except asyncio.TimeoutError:
                # 超时，发送提示但不关闭
                await ws.send_json({"type": "auth_failed", "message": "连接超时，请重新输入配对码"})
                continue
            except json.JSONDecodeError:
                # 解析错误，继续监听
                continue
        
        # 验证失败，关闭连接
        if not authenticated:
            await ws.close()
            return ws
        
        # 2. 验证通过，注册客户端
        self.config.connected_clients.add(ws)
        self.verified_clients.add(ws)
        
        try:
            # 3. 发送历史记录
            history_data = [
                {
                    "id": e.id,
                    "text": e.text,
                    "time": e.time.isoformat(),
                    "preview": e.preview,
                    "session_id": e.session_id
                }
                for e in self.config.history.list()
            ]
            await ws.send_json({"type": "history", "data": history_data})
            
            # 4. 监听消息
            async for msg in ws:
                if msg.type == web.WSMsgType.TEXT:
                    try:
                        data = json.loads(msg.data)
                        msg_type = data.get("type")
                        
                        if msg_type == "text":
                            await self._handle_text_message(
                                data.get("content", ""), 
                                ws,
                                data.get("client_id")
                            )
                        elif msg_type == "file_start":
                            await self._handle_file_start(data, ws)
                        elif msg_type == "file_chunk":
                            await self._handle_file_chunk(data, ws)
                        elif msg_type == "file_end":
                            await self._handle_file_end(data, ws)
                        elif msg_type == "command":
                            await self._handle_command(data, ws)
                            
                    except json.JSONDecodeError:
                        pass
                elif msg.type == web.WSMsgType.ERROR:
                    break
        finally:
            # 5. 注销客户端
            self.config.connected_clients.discard(ws)
            self.verified_clients.discard(ws)
        
        return ws
    
    async def _handle_text_message(self, text: str, sender: web.WebSocketResponse, client_id: str = None) -> None:
        """处理文本消息并广播给所有已验证客户端"""
        if not text:
            return
        
        # 1. 存入历史
        # 覆盖模式：每条消息使用独立 session_id
        # 追加模式：使用当前 session_id
        if self.config.copy_mode == 'cover':
            self.config.new_session()
        session_id = self.config.current_session_id
        entry = self.config.history.add(text, session_id)
        
        # 2. 自动复制（如果开启）
        auto_copied = False
        if self.config.auto_copy:
            try:
                # 根据复制模式决定复制内容
                if self.config.copy_mode == 'add':
                    # 追加模式：追加到缓冲区
                    if self.config.session_buffer:
                        self.config.session_buffer += '\n' + text
                    else:
                        self.config.session_buffer = text
                    copy_text = self.config.session_buffer
                else:
                    # 覆盖模式：直接复制新消息（原有行为）
                    copy_text = text
                
                await asyncio.get_event_loop().run_in_executor(
                    None, pyperclip.copy, copy_text
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
        
        # 4. 广播给所有已验证客户端（包括发送者）
        message_data = {
            "type": "new",
            "data": {
                "id": entry.id,
                "text": entry.text,
                "time": entry.time.isoformat(),
                "preview": entry.preview,
                "client_id": client_id,
                "session_id": entry.session_id
            }
        }
        
        for client in list(self.verified_clients):
            if not client.closed:
                try:
                    await client.send_json(message_data)
                except Exception:
                    pass
    
    async def _handle_file_start(self, data: dict, sender: web.WebSocketResponse) -> None:
        """处理文件传输开始"""
        ftm = get_file_transfer_manager()
        
        name = data.get("name", "")
        size = data.get("size", 0)
        mime_type = data.get("mime_type", "")
        
        file_id, error = ftm.start_transfer(name, size, mime_type)
        
        if file_id:
            await sender.send_json({
                "type": "file_accept",
                "file_id": file_id
            })
        else:
            await sender.send_json({
                "type": "file_error",
                "error": error
            })
    
    async def _handle_file_chunk(self, data: dict, sender: web.WebSocketResponse) -> None:
        """处理文件分片"""
        ftm = get_file_transfer_manager()
        
        file_id = data.get("file_id", "")
        chunk_data = base64.b64decode(data.get("data", ""))
        index = data.get("index", 0)
        
        success, error = ftm.receive_chunk(file_id, chunk_data, index)
        
        if success:
            # 发送进度
            received, total = ftm.get_transfer_progress(file_id)
            await sender.send_json({
                "type": "file_progress",
                "file_id": file_id,
                "received": received,
                "total": total
            })
        else:
            await sender.send_json({
                "type": "file_error",
                "file_id": file_id,
                "error": error
            })
    
    async def _handle_file_end(self, data: dict, sender: web.WebSocketResponse) -> None:
        """处理文件传输完成"""
        ftm = get_file_transfer_manager()
        
        file_id = data.get("file_id", "")
        save_path, error = ftm.complete_transfer(file_id)
        
        if save_path:
            # 通知发送者
            await sender.send_json({
                "type": "file_saved",
                "file_id": file_id,
                "path": str(save_path),
                "size": save_path.stat().st_size
            })
            
            # 通知终端
            await self.terminal_queue.put({
                "type": "file_received",
                "name": save_path.name,
                "path": str(save_path),
                "size": save_path.stat().st_size
            })
        else:
            await sender.send_json({
                "type": "file_error",
                "file_id": file_id,
                "error": error
            })
    
    async def _handle_command(self, data: dict, sender: web.WebSocketResponse) -> None:
        """处理客户端命令"""
        command = data.get("command", "")
        
        if command == "new_session":
            # 重置会话缓冲区
            if self.config.copy_mode == 'add':
                # 生成新的会话ID
                self.config.new_session()
                await sender.send_json({
                    "type": "session_reset",
                    "message": "会话已刷新"
                })
        elif command == "set_mode":
            # 设置复制模式
            mode = data.get("mode", "")
            if mode in ("cover", "add"):
                old_mode = self.config.copy_mode
                if old_mode != mode:
                    self.config.copy_mode = mode
                    # 切换模式时重置会话，确保新消息与旧消息分开
                    self.config.new_session()
                    # 切换到覆盖模式时清空会话缓冲区
                    if mode == "cover":
                        self.config.session_buffer = ""
                await sender.send_json({
                    "type": "mode_changed",
                    "mode": mode,
                    "message": f"已切换到{'追加' if mode == 'add' else '覆盖'}模式"
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
                self.config.port = port
                return port
            except OSError:
                if attempt < max_attempts - 1:
                    port += 1
                else:
                    raise RuntimeError(f"无法绑定端口 {self.config.port}-{port}")
        
        return port
    
    async def stop(self, force: bool = True) -> None:
        """停止服务器"""
        # 1. 先通知所有客户端服务即将关闭
        if self.verified_clients:
            close_msg = {"type": "server_close", "message": "服务已关闭"}
            await asyncio.gather(
                *[client.send_json(close_msg) for client in self.verified_clients if not client.closed],
                return_exceptions=True
            )
            for client in list(self.verified_clients):
                if not client.closed:
                    await client.close()
        
        self.verified_clients.clear()
        self.config.connected_clients.clear()
        
        # 2. 停止 HTTP 服务
        if self.site:
            await self.site.stop()
        if self.runner:
            await self.runner.cleanup()
