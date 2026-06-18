# Live Swarm Visualization Implementation Plan

## Overview
Add a live 3D visualization of drone positions using matplotlib, querying positions every 100ms via an async task.

## Changes

### 1. Update `hardware/swarm_base.py`
- Add abstract method `get_positions() -> list[tuple[float, float, float]] | None` to `SwarmBase`

### 2. Update `hardware/swarm.py`
- Implement `get_positions()` method in `Swarm` class
- Query `_position_logger` for each connected drone and return `(x, y, z)` tuples

### 3. Update `simulator/swarm.py`
- Implement `get_positions()` method in `SimulatedSwarm`
- Returns positions from `_virtual_positions` or `_position_logger`

### 4. Update `hardware/swarm_controller.py`
- Modify `get_positions()` to delegate to `self._swarm.get_positions()`

### 5. Create `visualization.py`
- New module with `SwarmVisualizer` class
- Uses matplotlib `mplot3d` for 3D scatter plot
- Async `_update_loop()` method queries `controller.get_positions()` every 100ms
- Efficient updates using `set_offsets()` and `set_3d_properties()`
- `start()` and `stop()` methods for lifecycle management

### 6. Update `console_llm.py`
- Import `SwarmVisualizer`
- Create and start visualizer alongside swarm controller
- Stop visualizer on shutdown

## Implementation Details

### SwarmBase (hardware/swarm_base.py)
Add to the abstract base class:
```python
@abstractmethod
def get_positions(self) -> list[tuple[float, float, float]] | None:
    """Return current positions of all drones as (x, y, z) tuples."""
    pass
```

### Swarm.get_positions() (hardware/swarm.py)
```python
def get_positions(self) -> list[tuple[float, float, float]] | None:
    if not self._position_logger:
        return None
    positions = []
    for i in range(len(self._connected_cfs)):
        log = self._position_logger.get_log(i)
        if log:
            positions.append((
                float(log.get("stateEstimate.x", 0.0)),
                float(log.get("stateEstimate.y", 0.0)),
                float(log.get("stateEstimate.z", 0.0))
            ))
        else:
            positions.append((0.0, 0.0, 0.0))
    return positions
```

### SimulatedSwarm.get_positions() (simulator/swarm.py)
```python
def get_positions(self) -> list[tuple[float, float, float]] | None:
    if not self._connected_cfs:
        return None
    if self._position_logger:
        positions = []
        for i in range(len(self._connected_cfs)):
            log = self._position_logger.get_log(i)
            if log:
                positions.append((
                    float(log.get("stateEstimate.x", 0.0)),
                    float(log.get("stateEstimate.y", 0.0)),
                    float(log.get("stateEstimate.z", 0.0))
                ))
        return positions
    if self._virtual_positions:
        return [(float(p[0]), float(p[1]), float(p[2])) for p in self._virtual_positions]
    return None
```

### SwarmController.get_positions() (hardware/swarm_controller.py)
```python
def get_positions(self) -> list[tuple[float, float, float]] | None:
    return self._swarm.get_positions()
```

### SwarmVisualizer (visualization.py)
```python
import asyncio
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import numpy as np

class SwarmVisualizer:
    def __init__(self, controller):
        self._controller = controller
        self._update_task: asyncio.Task | None = None
        self._running = False
        self._fig = None
        self._ax = None
        self._scatter = None

    async def start(self) -> None:
        self._running = True
        self._fig = plt.figure()
        self._ax = self._fig.add_subplot(111, projection='3d')
        self._ax.set_xlabel('X (m)')
        self._ax.set_ylabel('Y (m)')
        self._ax.set_zlabel('Z (m)')
        self._ax.set_title('Drone Swarm Position')
        self._scatter = self._ax.scatter([], [], [], c='red', s=100)
        self._update_task = asyncio.create_task(self._update_loop())
        plt.show(block=False)
        plt.pause(0.01)

    async def _update_loop(self) -> None:
        while self._running:
            positions = self._controller.get_positions()
            if positions:
                xs, ys, zs = zip(*positions)
                if self._scatter:
                    self._scatter._offsets3d = (xs, ys, zs)
                self._ax.set_xlim([-2, 2])
                self._ax.set_ylim([-2, 2])
                self._ax.set_zlim([0, 2.5])
                self._fig.canvas.draw_idle()
                self._fig.canvas.flush_events()
            await asyncio.sleep(0.1)  # 100ms

    async def stop(self) -> None:
        self._running = False
        if self._update_task and not self._update_task.done():
            self._update_task.cancel()
        if self._fig:
            plt.close(self._fig)
```

## Dependencies
- matplotlib (standard scientific plotting library)
- No additional dependencies beyond what's already used