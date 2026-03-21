"""配置状态管理"""

from datetime import datetime

from .history import History
from .qr import get_local_ip


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
    
    @property
    def history(self) -> History:
        return self._history
    
    @property
    def local_url(self) -> str:
        """本机访问地址"""
        return f"http://localhost:{self.port}"
    
    @property
    def lan_url(self) -> str:
        """局域网访问地址"""
        return f"http://{get_local_ip()}:{self.port}"
    
    @property
    def uptime(self) -> str:
        """运行时长"""
        delta = datetime.now() - self.start_time
        hours, remainder = divmod(int(delta.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
