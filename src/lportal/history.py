"""历史记录管理 - 循环缓冲区实现"""

from collections import deque
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class MessageEntry:
    """消息条目"""
    id: int
    text: str
    time: datetime
    preview: str
    session_id: int = 1  # 所属会话ID（追加模式下用于分组）


class History:
    """循环缓冲区历史记录 - 内存存储，不持久化"""
    
    def __init__(self, maxsize: int = 10):
        self._queue: deque[MessageEntry] = deque(maxlen=maxsize)
        self._counter = 0
        self._maxsize = maxsize
    
    def add(self, text: str, session_id: int = 1) -> MessageEntry:
        """添加新消息，返回创建的条目"""
        self._counter += 1
        preview = text[:50] + "..." if len(text) > 50 else text
        entry = MessageEntry(
            id=self._counter,
            text=text,
            time=datetime.now(),
            preview=preview,
            session_id=session_id
        )
        self._queue.appendleft(entry)  # 新消息在前
        return entry
    
    def get(self, index: int) -> MessageEntry:
        """
        获取指定索引的消息
        index: 1-N, 1=最近的一条
        """
        if not 1 <= index <= len(self._queue):
            raise IndexError(f"无效索引 {index}，当前有 {len(self._queue)} 条消息")
        return self._queue[index - 1]
    
    def list(self) -> list[MessageEntry]:
        """获取所有历史消息（按时间倒序，最新的在前，ID 重新编号为 1-N）"""
        entries = list(self._queue)
        # 重新编号 ID：最新的为 1，次新的为 2，以此类推
        for new_id, entry in enumerate(entries, start=1):
            entry.id = new_id
        return entries
    
    def last_received_time(self) -> Optional[datetime]:
        """最后接收消息的时间"""
        return self._queue[0].time if self._queue else None
    
    def __len__(self) -> int:
        return len(self._queue)
    
    @property
    def maxsize(self) -> int:
        return self._maxsize
