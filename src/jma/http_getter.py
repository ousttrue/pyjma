import json
from typing import Optional, NamedTuple, List
import pathlib
import logging
import urllib.parse
import asyncio
import aiohttp

logger = logging.getLogger(__name__)


class GetTask(NamedTuple):
    url: str
    future: asyncio.Future


class HttpGetter:
    def __init__(self, loop: asyncio.AbstractEventLoop, cache_dir: pathlib.Path) -> None:
        self.cache_dir = cache_dir
        self.interval = 0.5

        # start loader
        self.loop = loop
        self.queue: List[GetTask] = []
        self.task_map = {}
        self.is_running = True
        self.loop.create_task(self.load_async_loop())

    def shutdown(self):
        self.is_running = False

    async def load_async_loop(self):
        while self.is_running:
            if self.queue:
                url, future = self.queue.pop(0)
                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as response:
                        value = await response.read()
                        logger.debug(f'{url} done')
                        self.set_cache(url, value)
                        future.set_result(value)

            await asyncio.sleep(self.interval)

    def get_cache_path(self, url) -> pathlib.Path:
        parsed = urllib.parse.urlparse(url)
        return self.cache_dir / f'{parsed.hostname}{parsed.path}'

    def get_cache(self, url: str) -> Optional[bytes]:
        path = self.get_cache_path(url)
        if path.exists():
            return path.read_bytes()

    def set_cache(self, url: str, data: bytes):
        path = self.get_cache_path(url)
        logger.info(f'save {path} ...')
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def create_task(self, url) -> asyncio.Future:
        task = self.loop.create_future()
        get_task = GetTask(url, task)
        self.queue.append(get_task)
        self.task_map[url] = get_task
        return task

    async def get_async(self, url: str, *, use_cache=True) -> bytes:
        logger.info(f'get {url} ...')
        if use_cache:
            value = self.get_cache(url)
            if value:
                return value

        match self.task_map.get(url):
            case asyncio.Future() as future:
                return await future
            case GetTask() as get_task:
                return await get_task.future
            case None:
                return await self.create_task(url)
            case _:
                raise RuntimeError()

    async def get_json_async(self, url: str, *, use_cache=True) -> dict:
        data = await self.get_async(url, use_cache=use_cache)
        return json.loads(data)
