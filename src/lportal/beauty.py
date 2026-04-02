"""文本美化 - LLM 结构化处理"""

import json
import os
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

import aiohttp
from rich.console import Console


@dataclass
class BeautyEntry:
    """美化历史条目"""
    id: int
    text: str  # 原始文本
    result: str  # 美化后的文本
    time: datetime
    preview: str
    device_name: str = ""  # 关联设备名称
    login_id: str = ""     # 关联设备 login_id


class BeautyHistory:
    """美化历史记录 - 循环缓冲区，内存存储"""

    def __init__(self, maxsize: int = 10):
        self._queue: deque[BeautyEntry] = deque(maxlen=maxsize)
        self._counter = 0

    def add(
        self,
        original: str,
        result: str,
        device_name: str = "",
        login_id: str = ""
    ) -> BeautyEntry:
        """添加新记录，返回创建的条目"""
        self._counter += 1
        preview = result[:50] + "..." if len(result) > 50 else result
        entry = BeautyEntry(
            id=self._counter,
            text=original,
            result=result,
            time=datetime.now(),
            preview=preview,
            device_name=device_name,
            login_id=login_id
        )
        self._queue.appendleft(entry)
        return entry

    def get(self, index: int) -> BeautyEntry:
        """
        获取指定索引的记录
        index: 1-N, 1=最近的一条
        """
        if not 1 <= index <= len(self._queue):
            raise IndexError(f"无效索引 {index}，当前有 {len(self._queue)} 条记录")
        return self._queue[index - 1]

    def list(self) -> list[BeautyEntry]:
        """获取所有记录（按时间倒序，最新的在前，ID 重新编号为 1-N）"""
        entries = list(self._queue)
        for new_id, entry in enumerate(entries, start=1):
            entry.id = new_id
        return entries

    def __len__(self) -> int:
        return len(self._queue)

    @property
    def maxsize(self) -> int:
        return self._queue.maxlen or 0


def _project_root() -> Path:
    """获取项目根目录"""
    return Path(__file__).parent.parent.parent.resolve()


def _user_config_dir() -> Path:
    r"""获取用户配置目录
    
    - Windows: %APPDATA%\localportal
    - macOS: ~/Library/Application Support/localportal
    - Linux: ~/.config/localportal
    """
    import platform
    
    system = platform.system()
    
    if system == "Windows":
        app_data = os.environ.get("APPDATA")
        if app_data:
            return Path(app_data) / "localportal"
    elif system == "Darwin":  # macOS
        home = Path.home()
        return home / "Library" / "Application Support" / "localportal"
    
    # Linux 和其他系统
    config_home = os.environ.get("XDG_CONFIG_HOME")
    if config_home:
        return Path(config_home) / "localportal"
    return Path.home() / ".config" / "localportal"


def _load_env() -> dict[str, str]:
    r"""加载 .env 文件配置
    
    加载优先级（从高到低）：
    1. 当前工作目录的 .env 文件（方便项目级配置）
    2. 用户配置目录的 .env 文件（~/.config/localportal/.env 或 %APPDATA%\localportal\.env）
    """
    env: dict[str, str] = {}
    
    # 尝试加载路径，后加载的覆盖先加载的
    env_paths: list[Path] = []
    
    # 1. 用户配置目录
    user_config = _user_config_dir()
    env_paths.append(user_config / ".env")
    
    # 2. 当前工作目录（项目级配置，最高优先级）
    env_paths.append(Path(os.getcwd()) / ".env")
    
    for env_path in env_paths:
        if env_path.exists():
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    key, value = line.split("=", 1)
                    env[key.strip()] = value.strip()
    
    return env


def _load_prompt() -> str:
    """加载系统提示词
    
    加载优先级（从高到低）：
    1. 用户配置目录的自定义提示词（text-beauty.md）
    2. 包自带的默认提示词
    """
    # 1. 尝试从用户配置目录加载自定义提示词
    user_config = _user_config_dir()
    user_prompt = user_config / "text-beauty.md"
    if user_prompt.exists():
        with open(user_prompt, "r", encoding="utf-8") as f:
            return f.read()
    
    # 2. 从包目录加载默认提示词
    # 注意：打包后提示词位于 lportal/prompt/ 下
    package_dir = Path(__file__).parent
    package_prompt = package_dir / "prompt" / "text-beauty.md"
    if package_prompt.exists():
        with open(package_prompt, "r", encoding="utf-8") as f:
            return f.read()
    
    # 3. 开发环境回退
    dev_prompt = _project_root() / "src" / "prompt" / "text-beauty.md"
    if dev_prompt.exists():
        with open(dev_prompt, "r", encoding="utf-8") as f:
            return f.read()
    
    return ""


def _process_content_chunk(chunk: str, in_think: bool) -> tuple[list[tuple[str, str]], bool]:
    """
    处理 content 中的 <think> 标签
    返回: [(text, style), ...], new_in_think
    style: 'white' 或 'dim gray'
    """
    result: list[tuple[str, str]] = []
    remaining = chunk

    while remaining:
        if not in_think:
            if "<think>" in remaining:
                before, _, after = remaining.partition("<think>")
                if before:
                    result.append((before, "white"))
                in_think = True
                remaining = after
            else:
                result.append((remaining, "white"))
                remaining = ""
        else:
            if "</think>" in remaining:
                think_part, _, after = remaining.partition("</think>")
                if think_part:
                    result.append((think_part, "dim gray"))
                in_think = False
                remaining = after
            else:
                result.append((remaining, "dim gray"))
                remaining = ""

    return result, in_think


async def beautify_text(text: str, console: Console) -> str:
    """
    调用 LLM 对文本进行结构化美化，流式输出到终端
    返回最终正文内容（不含思维链）
    """
    env = _load_env()
    base_url = env.get("OPENAI_BASE_URL", "")
    api_key = env.get("OPENAI_API_KEY", "")
    model = env.get("OPENAI_MODEL", "")
    prompt = _load_prompt()

    if not all([base_url, api_key, model]):
        user_config = _user_config_dir()
        raise RuntimeError(
            f"缺少 LLM 配置，请在以下位置之一创建 .env 文件：\n"
            f"  1. 当前工作目录: {Path(os.getcwd()) / '.env'}\n"
            f"  2. 用户配置目录: {user_config / '.env'}\n"
            f"\n必需配置项：\n"
            f"  OPENAI_BASE_URL=https://api.openai.com/v1\n"
            f"  OPENAI_API_KEY=sk-xxxxxx\n"
            f"  OPENAI_MODEL=gpt-3.5-turbo"
        )

    if not prompt:
        raise RuntimeError("未找到系统提示词文件，请检查 src/prompt/text-beauty.md")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": prompt},
            {"role": "user", "content": text}
        ],
        "stream": True
    }

    full_content = ""
    full_reasoning = ""
    in_think = False

    async with aiohttp.ClientSession() as session:
        async with session.post(base_url, headers=headers, json=payload) as resp:
            if resp.status != 200:
                error_text = await resp.text()
                raise RuntimeError(f"LLM 请求失败 ({resp.status}): {error_text}")

            async for raw_line in resp.content:
                line = raw_line.decode("utf-8").strip()
                if not line or line == "data: [DONE]":
                    continue
                if line.startswith("data: "):
                    line = line[6:]

                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    continue

                choices = data.get("choices", [])
                if not choices:
                    continue

                delta = choices[0].get("delta", {})
                reasoning_chunk = delta.get("reasoning_content", "")
                content_chunk = delta.get("content", "")

                # 处理 reasoning_content 字段（如 DeepSeek-R1 的思维链）
                if reasoning_chunk:
                    full_reasoning += reasoning_chunk
                    console.print(reasoning_chunk, style="dim gray", end="")

                # 处理 content 字段（包含可能的 <think> 标签）
                if content_chunk:
                    segments, in_think = _process_content_chunk(content_chunk, in_think)
                    for seg_text, seg_style in segments:
                        if seg_style == "white":
                            full_content += seg_text
                        else:
                            full_reasoning += seg_text
                        console.print(seg_text, style=seg_style, end="")

            # 流式输出结束后换行
            console.print()

    return full_content
