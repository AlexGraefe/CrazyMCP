"""Simulated swarm implementation for testing without hardware."""

import asyncio

import numpy as np
from hardware.swarm_base import SwarmBase, SwarmState, scale_setpoint


TAKEOFF_HEIGHT = 1.0


class SimulatedPositionLogger:
    """Stub position logger for simulated swarm."""
    
    def __init__(self, positions: list):
        self._positions = positions
    
    def update_positions(self, positions: list) -> None:
        """Update positions for simulated logging."""
        self._positions = positions
    
    def get_log(self, index: int) -> dict | None:
        """Return simulated position data for a drone."""
        if 0 <= index < len(self._positions):
            p = self._positions[index]
            return {
                "stateEstimate.x": p[0],
                "stateEstimate.y": p[1],
                "stateEstimate.z": p[2],
            }
        return None


class SimulatedSwarm(SwarmBase):
    """Simulated swarm that mimics the real Swarm's state machine without hardware.

    All async operations complete immediately with minimal delays for testing.
    """

    def __init__(self) -> None:
        self._state = SwarmState.UNCONNECTED
        self._connected_uris: list[str] = []
        self._position_logger: SimulatedPositionLogger | None = None
        self._connected_cfs: list[str] = []
        self._ff_task: asyncio.Task | None = None
        self._virtual_positions: list[np.ndarray] = []
        self._target_positions: list[np.ndarray | None] = []

    # -- State ---------------------------------------------------------------

    @property
    def state(self) -> SwarmState:
        return self._state

    def _set_state(self, state: SwarmState) -> None:
        print(f"[SimulatedSwarm] {self._state.name} -> {state.name}")
        self._state = state

    # -- Public API ----------------------------------------------------------

    async def connect(self, base_address: str, num_drones: int) -> None:
        """Immediately transition to CONNECTED state."""
        self._connected_uris = [f"{base_address}{index:02X}" for index in range(1, num_drones + 1)]
        self._connected_cfs = [f"drone_{i}" for i in range(num_drones)]
        print(f"Simulated connect to {num_drones} drone(s): {', '.join(self._connected_uris)}")
        self._set_state(SwarmState.CONNECTED)

    async def disconnect(self) -> None:
        """Transition to UNCONNECTED state."""
        self._connected_uris = []
        self._connected_cfs = []
        self._virtual_positions = []
        self._target_positions = []
        self._position_logger = None
        self._set_state(SwarmState.UNCONNECTED)

    async def takeoff(self) -> None:
        """Transition to FLYING state, initialize virtual positions."""
        if self._state != SwarmState.CONNECTED:
            return
        await self._takeoff_impl()

    async def _takeoff_impl(self) -> None:
        """Simulate takeoff - initialize virtual positions at hover height."""
        self._set_state(SwarmState.FLYING)
        await asyncio.sleep(0.001)
        
        self._virtual_positions = [np.array([0.0, 0.0, TAKEOFF_HEIGHT]) for _ in self._connected_cfs]
        self._target_positions = [p.copy() for p in self._virtual_positions]
        self._position_logger = SimulatedPositionLogger(
            [(float(p[0]), float(p[1]), float(p[2])) for p in self._virtual_positions]
        )
        
        print("Simulated takeoff complete, hovering...")
        self._set_state(SwarmState.FLYING)

    async def land(self) -> None:
        """Transition to LANDED state."""
        if self._state != SwarmState.FLYING:
            return
        
        await self._land_impl()

    async def _land_impl(self) -> None:
        """Simulate landing - transition to LANDED."""
        self._set_state(SwarmState.LANDED)
        await asyncio.sleep(0.001)
        
        self._virtual_positions = []
        self._target_positions = []
        self._position_logger = None
        
        print("Simulated landing complete...")
        self._set_state(SwarmState.CONNECTED)

    async def emergency_land(self) -> None:
        """Immediately transition to LANDED then CONNECTED."""
        self._virtual_positions = []
        self._target_positions = []
        self._position_logger = None
        
        self._set_state(SwarmState.LANDED)
        print("Emergency land: simulated...")
        await asyncio.sleep(0.001)
        self._set_state(SwarmState.CONNECTED)

    def safegoto(self, positions: list, yaws: list | None = None) -> None:
        """Update virtual positions to targets immediately.
        
        LLM setpoints in [-1,1]^3 are automatically scaled to real-world coordinates.
        """
        if self._state != SwarmState.FLYING:
            return
        
        # Scale LLM normalized coordinates to real-world coordinates
        scaled_positions = [scale_setpoint(*p) if p is not None else None for p in positions]

        n = len(self._connected_cfs)
        self._target_positions = [
            np.array(scaled_positions[i], dtype=float) if i < len(scaled_positions) and scaled_positions[i] is not None
            else (self._virtual_positions[i].copy() if i < len(self._virtual_positions) else None)
            for i in range(n)
        ]
        
        self._virtual_positions = [
            p.copy() if p is not None else np.array([0.0, 0.0, TAKEOFF_HEIGHT])
            for p in self._target_positions
        ]
        
        if self._position_logger:
            self._position_logger.update_positions(
                [(float(p[0]), float(p[1]), float(p[2])) for p in self._virtual_positions]
            )
        
        # print(f"Simulated goto: {scaled_positions}")

    def get_positions(self) -> list[tuple[float, float, float]] | None:
        if not self._connected_cfs:
            return None
        if self._virtual_positions:
            return [(float(p[0]), float(p[1]), float(p[2])) for p in self._virtual_positions]
        return None