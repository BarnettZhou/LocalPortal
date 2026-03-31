"""HTTP + WebSocket 服务"""

import asyncio
import base64
import json
import secrets
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

import pyperclip
from aiohttp import web

from .config import ServerConfig
from .file_transfer import get_file_transfer_manager
from .history import History, MessageEntry
from .qr import generate_qr_html, generate_qr_png, get_local_ip


@dataclass
class DeviceInfo:
    """设备信息"""
    device_name: str
    login_id: str
    login_time: datetime
    ws: Optional[web.WebSocketResponse]


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
        self.verified_clients: set = set()
        
        # 设备管理
        self.devices: dict[str, DeviceInfo] = {}  # login_id -> DeviceInfo
        self.ws_to_login_id: dict[web.WebSocketResponse, str] = {}  # ws -> login_id
        self.device_registry: dict[str, str] = {}  # device_name -> login_id（断线重连复用）
    
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
        url_with_code = self.config.qr_url
        html = generate_qr_html(url_with_code)
        return web.Response(text=html, content_type='text/html')
    
    async def handle_qr_image(self, request: web.Request) -> web.Response:
        """二维码图片接口 - 带配对码"""
        url_with_code = self.config.qr_url
        img_buffer = generate_qr_png(url_with_code)
        return web.Response(body=img_buffer, content_type='image/png')
    
    def _generate_login_id(self) -> str:
        """生成 8 位 login_id"""
        return secrets.token_hex(4)
    
    def _get_online_device_names(self) -> set[str]:
        """获取当前在线的设备名称"""
        return {
            info.device_name
            for info in self.devices.values()
            if info.ws is not None and not info.ws.closed
        }
    
    def get_device_by_ws(self, ws: web.WebSocketResponse) -> Optional[DeviceInfo]:
        """通过 WebSocket 连接获取设备信息"""
        login_id = self.ws_to_login_id.get(ws)
        if login_id:
            return self.devices.get(login_id)
        return None
    
    async def send_to_device(self, login_id: str, message: dict) -> bool:
        """向指定设备发送消息"""
        device = self.devices.get(login_id)
        if device and device.ws and not device.ws.closed:
            try:
                await device.ws.send_json(message)
                return True
            except Exception:
                pass
        return False
    
    async def broadcast(self, message: dict) -> None:
        """广播消息给所有已验证客户端"""
        for client in list(self.verified_clients):
            if not client.closed:
                try:
                    await client.send_json(message)
                except Exception:
                    pass
    
    async def handle_websocket(self, request: web.Request) -> web.WebSocketResponse:
        """WebSocket 连接处理"""
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        
        # 1. 等待配对码验证
        authenticated = False
        for attempt in range(3):
            try:
                auth_msg = await asyncio.wait_for(ws.receive(), timeout=10.0)
                if auth_msg.type == web.WSMsgType.TEXT:
                    data = json.loads(auth_msg.data)
                    if data.get("type") == "auth":
                        code = data.get("code", "")
                        if code != self.config.pairing_code:
                            await ws.send_json({"type": "auth_failed", "message": "配对码错误"})
                            continue
                        await ws.send_json({"type": "auth_success"})
                        authenticated = True
                        break
                    else:
                        await ws.send_json({"type": "auth_failed", "message": "请先发送配对码"})
                        continue
                else:
                    continue
            except asyncio.TimeoutError:
                await ws.send_json({"type": "auth_failed", "message": "连接超时，请重新输入配对码"})
                continue
            except json.JSONDecodeError:
                continue
        
        if not authenticated:
            await ws.close()
            return ws
        
        # 2. 等待设备注册
        registered = False
        device_info: Optional[DeviceInfo] = None
        for attempt in range(3):
            try:
                reg_msg = await asyncio.wait_for(ws.receive(), timeout=10.0)
                if reg_msg.type == web.WSMsgType.TEXT:
                    data = json.loads(reg_msg.data)
                    if data.get("type") == "register":
                        device_name = data.get("device_name", "").strip()
                        if not device_name:
                            await ws.send_json({"type": "register_failed", "message": "设备名称不能为空"})
                            continue
                        
                        # 检查是否有同名设备在线
                        online_names = self._get_online_device_names()
                        if device_name in online_names:
                            await ws.send_json({"type": "register_failed", "message": f"设备名称 '{device_name}' 已被使用"})
                            continue
                        
                        # 复用或生成 login_id
                        if device_name in self.device_registry:
                            login_id = self.device_registry[device_name]
                        else:
                            login_id = self._generate_login_id()
                            while login_id in self.devices:
                                login_id = self._generate_login_id()
                            self.device_registry[device_name] = login_id
                        
                        device_info = DeviceInfo(
                            device_name=device_name,
                            login_id=login_id,
                            login_time=datetime.now(),
                            ws=ws
                        )
                        self.devices[login_id] = device_info
                        self.ws_to_login_id[ws] = login_id
                        
                        await ws.send_json({
                            "type": "register_success",
                            "login_id": login_id,
                            "device_name": device_name
                        })
                        registered = True
                        break
                    else:
                        await ws.send_json({"type": "register_failed", "message": "请先发送设备注册信息"})
                        continue
                else:
                    continue
            except asyncio.TimeoutError:
                await ws.send_json({"type": "register_failed", "message": "注册超时，请重新连接"})
                continue
            except json.JSONDecodeError:
                continue
        
        if not registered or device_info is None:
            await ws.close()
            return ws
        
        # 3. 注册客户端到在线集合
        self.config.connected_clients.add(ws)
        self.verified_clients.add(ws)
        
        try:
            # 4. 发送历史记录（只发送与该设备相关的）
            current_login_id = device_info.login_id
            filtered_history = [
                {
                    "id": e.id,
                    "text": e.text,
                    "time": e.time.isoformat(),
                    "preview": e.preview,
                    "session_id": e.session_id,
                    "device_name": e.device_name,
                    "login_id": e.login_id
                }
                for e in self.config.history.list()
                if e.login_id == current_login_id or e.target_login_id == current_login_id
            ]
            await ws.send_json({"type": "history", "data": filtered_history})
            
            # 5. 监听消息
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
            # 6. 注销客户端（保留 device_registry 和 devices 记录以便重连）
            self.config.connected_clients.discard(ws)
            self.verified_clients.discard(ws)
            if ws in self.ws_to_login_id:
                login_id = self.ws_to_login_id.pop(ws)
                if login_id in self.devices:
                    self.devices[login_id].ws = None
        
        return ws
    
    async def _handle_text_message(self, text: str, sender: web.WebSocketResponse, client_id: str = None) -> None:
        """处理文本消息并回推给发送设备"""
        if not text:
            return
        
        device = self.get_device_by_ws(sender)
        device_name = device.device_name if device else ""
        login_id = device.login_id if device else ""
        
        # 1. 存入历史
        if self.config.copy_mode == 'cover':
            self.config.new_session()
        session_id = self.config.current_session_id
        entry = self.config.history.add(
            text, session_id,
            device_name=device_name,
            login_id=login_id
        )
        
        # 2. 自动复制（如果开启）
        auto_copied = False
        if self.config.auto_copy:
            try:
                if self.config.copy_mode == 'add':
                    if self.config.session_buffer:
                        self.config.session_buffer += '\n' + text
                    else:
                        self.config.session_buffer = text
                    copy_text = self.config.session_buffer
                else:
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
        
        # 4. 只回推给发送设备
        message_data = {
            "type": "new",
            "data": {
                "id": entry.id,
                "text": entry.text,
                "time": entry.time.isoformat(),
                "preview": entry.preview,
                "client_id": client_id,
                "session_id": entry.session_id,
                "device_name": entry.device_name,
                "login_id": entry.login_id
            }
        }
        
        if device:
            await self.send_to_device(device.login_id, message_data)
    
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
            await sender.send_json({
                "type": "file_saved",
                "file_id": file_id,
                "path": str(save_path),
                "size": save_path.stat().st_size
            })
            
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
    
    async def send_server_text(self, text: str, target_login_id: str) -> Optional[MessageEntry]:
        """服务端主动向指定设备发送文本消息"""
        if not text or not target_login_id:
            return None
        
        # 服务端消息使用独立的 session_id（负数，避免与设备 session 冲突）
        session_id = -self.config.history._counter - 1
        entry = self.config.history.add(
            text, session_id,
            device_name="服务端",
            login_id="server",
            target_login_id=target_login_id
        )
        
        message_data = {
            "type": "server_text",
            "data": {
                "id": entry.id,
                "text": entry.text,
                "time": entry.time.isoformat(),
                "preview": entry.preview,
                "session_id": entry.session_id,
                "device_name": entry.device_name,
                "login_id": entry.login_id
            }
        }
        
        await self.send_to_device(target_login_id, message_data)
        
        # 通知终端显示
        await self.terminal_queue.put({
            "type": "server_message_sent",
            "entry": entry
        })
        
        return entry
    
    async def _handle_command(self, data: dict, sender: web.WebSocketResponse) -> None:
        """处理客户端命令"""
        command = data.get("command", "")
        
        if command == "new_session":
            if self.config.copy_mode == 'add':
                self.config.new_session()
                await sender.send_json({
                    "type": "session_reset",
                    "message": "会话已刷新"
                })
        elif command == "set_mode":
            mode = data.get("mode", "")
            if mode in ("cover", "add"):
                old_mode = self.config.copy_mode
                if old_mode != mode:
                    self.config.copy_mode = mode
                    self.config.new_session()
                    if mode == "cover":
                        self.config.session_buffer = ""
                await self.broadcast({
                    "type": "mode_changed",
                    "mode": mode,
                    "message": f"已切换到{'追加' if mode == 'add' else '覆盖'}模式"
                })
    
    async def start(self) -> int:
        """启动服务器，返回实际使用的端口"""
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        
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
        
        if self.site:
            await self.site.stop()
        if self.runner:
            await self.runner.cleanup()
