import asyncio
import matplotlib.pyplot as plt
import numpy as np


class SwarmVisualizer:
    def __init__(self, controller):
        self._controller = controller
        self._update_task: asyncio.Task | None = None
        self._running = False
        self._fig = None
        self._ax = None
        self._scatter = None
        self._trajectories: list[list[tuple[float, float, float]]] = []
        self._trajectory_lines: list = []
        self._colors = ['red', 'green', 'blue', 'orange', 'purple', 'cyan', 'magenta', 'yellow']

    async def start(self) -> None:
        self._running = True
        self._trajectories = [[] for _ in range(10)]
        self._fig = plt.figure(figsize=(10, 8))
        self._ax = self._fig.add_subplot(111, projection='3d')
        self._ax.set_xlabel('X (m)')
        self._ax.set_ylabel('Y (m)')
        self._ax.set_zlabel('Z (m)')
        self._ax.set_title('Drone Swarm Trajectories')
        self._ax.set_xlim([-2, 2])
        self._ax.set_ylim([-2, 2])
        self._ax.set_zlim([0, 2.5])

        self._scatter = self._ax.scatter([], [], [], c='red', s=100)

        for i in range(len(self._colors)):
            line, = self._ax.plot([], [], [], color=self._colors[i], alpha=0.5, linewidth=1)
            self._trajectory_lines.append(line)

        self._update_task = asyncio.create_task(self._update_loop())
        plt.show(block=False)
        plt.pause(0.01)

    async def _update_loop(self) -> None:
        while self._running:
            positions = self._controller.get_positions()
            if positions:
                for i, pos in enumerate(positions):
                    if i < len(self._trajectories):
                        self._trajectories[i].append((pos[0], pos[1], pos[2]))
                        traj = self._trajectories[i]
                        if len(traj) > 1 and i < len(self._trajectory_lines):
                            xs = [p[0] for p in traj]
                            ys = [p[1] for p in traj]
                            zs = [p[2] for p in traj]
                            self._trajectory_lines[i].set_data_3d(xs, ys, zs)

                xs, ys, zs = zip(*positions)
                if self._scatter:
                    self._scatter._offsets3d = (xs, ys, zs)

                self._fig.canvas.draw_idle()
                self._fig.canvas.flush_events()
            await asyncio.sleep(0.1)

    async def stop(self) -> None:
        self._running = False
        if self._update_task and not self._update_task.done():
            self._update_task.cancel()
            try:
                await self._update_task
            except asyncio.CancelledError:
                pass
        if self._fig:
            plt.close(self._fig)