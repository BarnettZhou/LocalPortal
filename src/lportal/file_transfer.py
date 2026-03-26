"""文件传输管理器"""

import base64
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional
import platform


def get_default_download_dir() -> Path:
    r"""获取系统默认下载目录
    
    优先级：
    1. 环境变量 LPORTAL_DOWNLOAD_DIR
    2. Windows: %USERPROFILE%\Downloads
    3. macOS/Linux: ~/Downloads
    """
    # 1. 检查环境变量
    env_dir = os.environ.get('LPORTAL_DOWNLOAD_DIR')
    if env_dir:
        return Path(env_dir).expanduser()
    
    # 2. 根据不同系统获取
    system = platform.system()
    
    if system == "Windows":
        # Windows: 使用 USERPROFILE 环境变量
        user_profile = os.environ.get('USERPROFILE')
        if user_profile:
            return Path(user_profile) / "Downloads"
    
    # macOS/Linux 或 fallback: 使用用户主目录
    return Path.home() / "Downloads"


@dataclass
class FileInfo:
    """文件信息"""
    name: str
    size: int
    mime_type: str
    file_id: str
    chunks: list = field(default_factory=list)
    received_size: int = 0
    download_dir: Path = field(default=None)
    
    def __post_init__(self):
        if self.download_dir is None:
            self.download_dir = get_default_download_dir()
    
    @property
    def save_path(self) -> Path:
        """生成保存路径"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # 清理文件名，移除危险字符
        safe_name = "".join(c for c in self.name if c.isalnum() or c in "._-")
        filename = f"lportal_{timestamp}_{safe_name}"
        return self.download_dir / filename


class FileTransferManager:
    """文件传输管理器"""
    
    # 允许的文件类型
    ALLOWED_TYPES = {
        'image/jpeg', 'image/png', 'image/gif', 'image/webp',
        'video/mp4', 'video/quicktime', 'video/webm', 'video/x-msvideo'
    }
    
    # 最大文件大小 (100MB)
    MAX_FILE_SIZE = 100 * 1024 * 1024
    
    # 分片大小 (64KB)
    CHUNK_SIZE = 64 * 1024
    
    def __init__(self, download_dir: Optional[str] = None):
        if download_dir:
            self.download_dir = Path(download_dir).expanduser()
        else:
            self.download_dir = get_default_download_dir()
        
        # 确保下载目录存在
        self.download_dir.mkdir(parents=True, exist_ok=True)
        
        # 活跃的文件传输
        self.active_transfers: Dict[str, FileInfo] = {}
    
    def can_accept_file(self, mime_type: str, size: int) -> tuple[bool, str]:
        """检查是否可以接收文件"""
        if mime_type not in self.ALLOWED_TYPES:
            return False, f"不支持的文件类型: {mime_type}"
        
        if size > self.MAX_FILE_SIZE:
            return False, f"文件过大: {size} bytes (最大 {self.MAX_FILE_SIZE} bytes)"
        
        # 检查磁盘空间 (粗略估计，需要至少 2 倍空间)
        try:
            import shutil
            stat = shutil.disk_usage(self.download_dir)
            if stat.free < size * 2:
                return False, "磁盘空间不足"
        except Exception:
            pass  # 如果无法检查，继续尝试
        
        return True, ""
    
    def start_transfer(self, name: str, size: int, mime_type: str) -> tuple[Optional[str], str]:
        """
        开始接收文件
        返回: (file_id, 错误信息) 如果成功 file_id 不为 None
        """
        # 检查文件类型和大小
        can_accept, error = self.can_accept_file(mime_type, size)
        if not can_accept:
            return None, error
        
        file_id = str(uuid.uuid4())[:8]
        file_info = FileInfo(
            name=name,
            size=size,
            mime_type=mime_type,
            file_id=file_id,
            download_dir=self.download_dir
        )
        
        self.active_transfers[file_id] = file_info
        return file_id, ""
    
    def receive_chunk(self, file_id: str, chunk_data: bytes, index: int) -> tuple[bool, str]:
        """接收文件分片"""
        if file_id not in self.active_transfers:
            return False, "传输不存在或已过期"
        
        file_info = self.active_transfers[file_id]
        
        # 确保分片列表足够长
        while len(file_info.chunks) <= index:
            file_info.chunks.append(None)
        
        file_info.chunks[index] = chunk_data
        file_info.received_size += len(chunk_data)
        
        return True, ""
    
    def complete_transfer(self, file_id: str) -> tuple[Optional[Path], str]:
        """
        完成传输，保存文件
        返回: (保存路径, 错误信息)
        """
        if file_id not in self.active_transfers:
            return None, "传输不存在或已过期"
        
        file_info = self.active_transfers[file_id]
        
        try:
            # 合并所有分片
            save_path = file_info.save_path
            
            with open(save_path, 'wb') as f:
                for chunk in file_info.chunks:
                    if chunk is not None:
                        f.write(chunk)
            
            # 清理
            del self.active_transfers[file_id]
            
            return save_path, ""
        except Exception as e:
            return None, f"保存文件失败: {e}"
    
    def cancel_transfer(self, file_id: str):
        """取消传输"""
        if file_id in self.active_transfers:
            del self.active_transfers[file_id]
    
    def get_transfer_progress(self, file_id: str) -> tuple[int, int]:
        """获取传输进度 (已接收, 总数)"""
        if file_id not in self.active_transfers:
            return 0, 0
        
        file_info = self.active_transfers[file_id]
        return file_info.received_size, file_info.size
    
    def open_downloads_folder(self):
        """打开下载文件夹"""
        import subprocess
        import os
        
        path = str(self.download_dir)
        
        if platform.system() == "Windows":
            os.startfile(path)
        elif platform.system() == "Darwin":  # macOS
            subprocess.run(["open", path])
        else:  # Linux
            subprocess.run(["xdg-open", path])


# 全局文件传输管理器实例
_file_transfer_manager: Optional[FileTransferManager] = None


def get_file_transfer_manager() -> FileTransferManager:
    """获取文件传输管理器单例"""
    global _file_transfer_manager
    if _file_transfer_manager is None:
        _file_transfer_manager = FileTransferManager()
    return _file_transfer_manager
