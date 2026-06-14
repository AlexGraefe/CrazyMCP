import asyncio
import numpy as np
from .swarm import Swarm, SwarmState

FF_POSITION_TOLERANCE = 0.05

class SwarmController:
    def __init__(self, swarm: Swarm) -> None:
        self._swarm = swarm
        self._exec_queue: asyncio.Queue[str | None] = asyncio.Queue()
        self._exec_task: asyncio.Task | None = None

    def start_execution_task(self) -> None:
        if self._exec_task is None or self._exec_task.done():
            self._exec_task = asyncio.create_task(self._execution_loop())

    async def _execution_loop(self) -> None:
        while True:
            code = await self._exec_queue.get()
            if code is None:
                break
            try:
                namespace = {
                    "swarm": self,
                    "asyncio": asyncio,
                    "np": np,
                }
                exec(code, namespace)
            except Exception as e:
                print(f"Execution error: {e}")

    @property
    def state(self) -> str:
        return self._swarm.state.name

    def connect(self, base_address: str, num_drones: int) -> str:
        if self._swarm.state != SwarmState.UNCONNECTED:
            return f"Cannot connect: swarm is already in {self._swarm.state.name} state"
        self._swarm.connect(base_address, num_drones)
        return f"Connecting to {num_drones} drone(s) at {base_address}..."

    def takeoff(self) -> str:
        if self._swarm.state != SwarmState.CONNECTED:
            return f"Cannot takeoff: swarm must be in CONNECTED state (current: {self._swarm.state.name})"
        self._swarm.start()
        return "Takeoff sequence initiated..."

    def land(self) -> str:
        if self._swarm.state != SwarmState.FLYING:
            return f"Cannot land: swarm must be in FLYING state (current: {self._swarm.state.name})"
        self._swarm.land()
        return "Landing initiated..."

    def emergency_stop(self) -> None:
        self._swarm.emergency_land()

    def disconnect(self) -> str:
        if self._swarm.state == SwarmState.UNCONNECTED:
            return "Swarm is not connected"
        asyncio.create_task(self._swarm.disconnect())
        return "Disconnecting..."

    async def _disconnect_sync(self) -> None:
        if self._swarm.state != SwarmState.UNCONNECTED:
            await self._swarm.disconnect()

    def goto(self, positions: list[tuple[float, float, float] | None]) -> str:
        if self._swarm.state != SwarmState.FLYING:
            return f"Cannot goto: swarm must be in FLYING state (current: {self._swarm.state.name})"
        self._swarm.safegoto(positions)
        return f"Navigating drones to {positions}..."

    def get_positions(self) -> list[tuple[float, float, float]] | None:
        if not self._swarm._position_logger:
            return None
        positions = []
        for i in range(len(self._swarm._connected_cfs)):
            log = self._swarm._position_logger.get_log(i)
            if log:
                positions.append((
                    float(log.get("stateEstimate.x", 0.0)),
                    float(log.get("stateEstimate.y", 0.0)),
                    float(log.get("stateEstimate.z", 0.0))
                ))
            else:
                positions.append((0.0, 0.0, 0.0))
        return positions

    def num_drones(self) -> int:
        return len(self._swarm._connected_cfs)

    def queue_code(self, code: str) -> None:
        self._exec_queue.put_nowait(code)

    async def shutdown(self) -> None:
        self._exec_queue.put_nowait(None)
        if self._exec_task is not None:
            await self._exec_task
        await self._disconnect_sync()