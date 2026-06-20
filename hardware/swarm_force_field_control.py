import numpy as np

# Force field constants (mirrored from swarm.py)
FF_D_MIN = 0.5
FF_D_MAX = 0.4
FF_K_REPULSIVE = 1.5
FF_K_ATTRACTIVE = 3.0
FF_K_BOUNDARY = 3.0
FF_WAYPOINT_INTERVAL = 0.1
FF_VIRTUAL_UPDATES_PER_GOTO = 10
FF_VIRTUAL_UPDATE_INTERVAL = FF_WAYPOINT_INTERVAL / FF_VIRTUAL_UPDATES_PER_GOTO
FF_MAX_VELOCITY = 0.5
FF_POSITION_TOLERANCE = 0.05
FF_BOUNDARY_MIN = np.array([-1.2, -1.2, 0.1])
FF_BOUNDARY_MAX = np.array([ 1.2,  1.2, 1.5])

class ForceFieldController:
    """Encapsulates the force‑field navigation logic.

    Initialized with the current virtual positions and a reference to the target
    positions list maintained by :class:`Swarm`.  The ``step`` method advances the
    virtual model one update interval and returns the new virtual positions.
    """

    def __init__(self, virtual_positions: list[np.ndarray]):
        self._virtual_positions = virtual_positions

    def step(self, target_positions) -> list[np.ndarray]:
        """Compute the next virtual positions using the force‑field model.

        Returns the updated list of virtual positions.  The internal state is
        updated so subsequent calls continue from the new positions.
        """
        n = len(self._virtual_positions)
        if not self._virtual_positions or len(self._virtual_positions) != n:
            return self._virtual_positions

        next_positions = list(self._virtual_positions)
        for i in range(n):
            target = target_positions[i] if i < len(target_positions) else None
            # print(f"Controller step: Drone {i}, Current: {self._virtual_positions[i]}, Target: {target}")
            if target is None:
                continue
            others = [self._virtual_positions[j] for j in range(n) if j != i]
            next_positions[i] = self._ff_next_position(self._virtual_positions[i], target, others)

        self._virtual_positions = next_positions
        return next_positions

    @staticmethod
    def _ff_repulsive(p1: np.ndarray, p2: np.ndarray) -> np.ndarray:
        d = p1 - p2
        dist = float(np.linalg.norm(d))
        if dist > FF_D_MAX or dist < 1e-3:
            return np.zeros(3)
        d_eff = max(FF_D_MIN, dist)
        return (d / (dist + 1e-7)) * (1.0 / (d_eff + 1e-6))

    @staticmethod
    def _ff_boundary_repulsive(p: np.ndarray, margin: float = 0.3) -> np.ndarray:
        force = np.zeros(3)
        for i in range(3):
            dist_min = float(p[i]) - float(FF_BOUNDARY_MIN[i])
            if dist_min < margin:
                force[i] += 1.0 / (dist_min + 1e-6) ** 2
            dist_max = float(FF_BOUNDARY_MAX[i]) - float(p[i])
            if dist_max < margin:
                force[i] -= 1.0 / (dist_max + 1e-6) ** 2
        return force

    @staticmethod
    def _ff_attractive(p: np.ndarray, target: np.ndarray, max_force: float = 1.0) -> np.ndarray:
        d = target - p
        dist = float(np.linalg.norm(d))
        if dist < 1e-3:
            return np.zeros(3)
        return (d / dist) * min(dist, max_force)

    @staticmethod
    def _ff_next_position(current: np.ndarray, target: np.ndarray, others: list) -> np.ndarray:
        force = np.zeros(3)
        for other in others:
            if other is not None and np.linalg.norm(current - other) > 1e-3:
                force += FF_K_REPULSIVE * ForceFieldController._ff_repulsive(current, other)
        force += FF_K_BOUNDARY * ForceFieldController._ff_boundary_repulsive(current)
        force += FF_K_ATTRACTIVE * ForceFieldController._ff_attractive(current, target)
        velocity = force * FF_VIRTUAL_UPDATE_INTERVAL
        mag = float(np.linalg.norm(velocity))
        if mag > FF_MAX_VELOCITY * FF_VIRTUAL_UPDATE_INTERVAL:
            velocity = velocity / mag * FF_MAX_VELOCITY * FF_VIRTUAL_UPDATE_INTERVAL
        new_pos = current + velocity
        new_pos = np.maximum(new_pos, FF_BOUNDARY_MIN)
        new_pos = np.minimum(new_pos, FF_BOUNDARY_MAX)
        return new_pos
