# utils/async_path.py - 异步操作
import aiofiles
import aiofiles.os
from pathlib import Path

async def async_read_text(path: Path, encoding: str = "utf-8") -> str:
    async with aiofiles.open(path, encoding=encoding) as f:
        return await f.read()

async def async_write_text(path: Path, content: str, encoding: str = "utf-8") -> None:
    async with aiofiles.open(path, 'w', encoding=encoding) as f:
        await f.write(content)

async def async_is_file(path: Path) -> bool:
    return await aiofiles.os.path.isfile(path)

async def async_exists(path: Path) -> bool:
    return await aiofiles.os.path.exists(path)