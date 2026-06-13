"""LoggingTask class for managing live log streams from multiple Crazyflie drones."""

import asyncio


class LoggingTask:
    def __init__(self, crazyflies: list, variables: list[str], interval_ms: int) -> None:
        self._crazyflies = crazyflies
        self._variables = variables
        self._interval_ms = interval_ms
        self._log_streams: list[object] = []
        self._latest_logs: list[dict | None] = []
        self._tasks: list[asyncio.Task] = []
        self._running = False

    async def start(self) -> None:
        if self._running:
            await self.stop()

        self._latest_logs = [None for _ in self._crazyflies]
        self._log_streams = []
        self._tasks = []
        self._running = True

        for i, cf in enumerate(self._crazyflies):
            log = cf.log()
            block = await log.create_block()
            for var in self._variables:
                await block.add_variable(var)
            stream = await block.start(self._interval_ms)
            self._log_streams.append(stream)

            async def _reader(idx: int, ls: object) -> None:
                while self._running:
                    try:
                        result = await ls.next()
                        self._latest_logs[idx] = result.data
                    except asyncio.CancelledError:
                        break
                    except Exception:
                        break

            task = asyncio.create_task(_reader(i, stream))
            self._tasks.append(task)

    async def read_once(self) -> list[dict | None]:
        async def _read_single(cf: object) -> dict | None:
            log = cf.log()
            block = await log.create_block()
            for v in self._variables:
                await block.add_variable(v)
            stream = await block.start(self._interval_ms)
            try:
                result = await stream.next()
                return result.data
            finally:
                stop = getattr(stream, "stop", None)
                if callable(stop):
                    result = stop()
                    if asyncio.iscoroutine(result):
                        await result

        return await asyncio.gather(*[_read_single(cf) for cf in self._crazyflies])

    def get_log(self, cf_index: int) -> dict | None:
        if 0 <= cf_index < len(self._latest_logs):
            return self._latest_logs[cf_index]
        return None

    async def stop(self) -> None:
        if not self._running:
            return

        self._running = False

        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks = []

        for stream in self._log_streams:
            stop = getattr(stream, "stop", None)
            if callable(stop):
                result = stop()
                if asyncio.iscoroutine(result):
                    await result
        self._log_streams = []
        self._latest_logs = []

    def __del__(self) -> None:
        if self._running and self._log_streams:
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None

            if loop is not None:
                for stream in self._log_streams:
                    stop = getattr(stream, "stop", None)
                    if callable(stop):
                        result = stop()
                        if asyncio.iscoroutine(result):
                            loop.create_task(result)