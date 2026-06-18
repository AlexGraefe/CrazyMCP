import asyncio
import matplotlib.pyplot as plt


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
                xs = tuple(p[0] for p in positions)
                ys = tuple(p[1] for p in positions)
                zs = tuple(p[2] for p in positions)
                if self._scatter:
                    self._scatter._offsets3d = (xs, ys, zs)
                self._ax.set_xlim([-2, 2])
                self._ax.set_ylim([-2, 2])
                self._ax.set_zlim([0, 2.5])
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