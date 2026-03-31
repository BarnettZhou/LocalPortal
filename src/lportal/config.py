"""配置状态管理"""

import random
from datetime import datetime

from .beauty import BeautyHistory
from .history import History
from .qr import get_local_ip


def generate_pairing_code() -> str:
    """生成4位数字配对码"""
    return f"{random.randint(0, 9999):04d}"


class ServerConfig:
    """服务器配置和运行时状态"""
    
    def __init__(
        self,
        auto_copy: bool = True,
        port: int = 14554,
        max_history: int = 10,
        host: str = "0.0.0.0"
    ):
        self.auto_copy = auto_copy
        self.port = port
        self.max_history = int(max_history)
        self.host = host
        self.start_time = datetime.now()
        self.connected_clients: set = set()
        self._history = History(self.max_history)
        self._beauty_history = BeautyHistory(10)
        self.pairing_code: str = generate_pairing_code()
        
        # 复制模式: 'cover' (覆盖模式, 默认) 或 'add' (追加模式)
        self.copy_mode: str = 'cover'
        # 追加模式下的会话缓冲区
        self.session_buffer: str = ''
        # 当前会话ID (用于追加模式下的消息分组)
        self.current_session_id: int = 1
    
    def new_session(self) -> int:
        """开始新会话，返回新的会话ID"""
        self.current_session_id += 1
        self.session_buffer = ''
        return self.current_session_id
    
    def refresh_pairing_code(self) -> str:
        """刷新配对码，返回新的配对码"""
        self.pairing_code = generate_pairing_code()
        return self.pairing_code
    
    @property
    def history(self) -> History:
        return self._history
    
    @property
    def beauty_history(self) -> BeautyHistory:
        return self._beauty_history
    
    @property
    def local_url(self) -> str:
        """本机访问地址"""
        return f"http://localhost:{self.port}"
    
    @property
    def lan_url(self) -> str:
        """局域网访问地址"""
        return f"http://{get_local_ip()}:{self.port}"
    
    @property
    def qr_url(self) -> str:
        """带配对码的二维码地址"""
        return f"http://{get_local_ip()}:{self.port}/?code={self.pairing_code}"
    
    @property
    def uptime(self) -> str:
        """运行时长"""
        delta = datetime.now() - self.start_time
        hours, remainder = divmod(int(delta.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
