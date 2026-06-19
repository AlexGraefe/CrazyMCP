"""Abstract base class for swarm implementations.

Provides the common interface shared by both real and simulated swarm implementations.
"""

from abc import ABC, abstractmethod
from enum import Enum, auto

# Testbed dimensions for coordinate scaling
# LLM generates setpoints in [-1, 1]^3:
# - x, y: -1 to 1 maps to horizontal workspace
# - z: -1 is floor, 1 is maximum flight height
SCALE_XY = 1.5
SCALE_Z = 1.0
OFFSET_Z = 1.0


def scale_setpoint(x: float, y: float, z: float) -> tuple[float, float, float]:
    """Convert LLM normalized coordinates in [-1,1]^3 to real-world coordinates.
    
    Args:
        x, y, z: Normalized coordinates in [-1, 1].
        
    Returns:
        Real-world coordinates in meters.
        x,y in [-1.5, 1.5], z in [0, 2] where z=0 is floor.
    """
    return (x * SCALE_XY, y * SCALE_XY, z * SCALE_Z + OFFSET_Z)


class SwarmState(Enum):
    UNCONNECTED = auto()
    CONNECTED = auto()
    FLYING = auto()
    LANDED = auto()
    ERROR = auto()


class SwarmBase(ABC):
    @property
    @abstractmethod
    def state(self) -> SwarmState:
        """Return the current state of the swarm."""
        pass

    @abstractmethod
    async def connect(self, base_address: str, num_drones: int) -> None:
        """Connect to *num_drones* drones derived from *base_address*."""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect all drones."""
        pass

    @abstractmethod
    async def takeoff(self) -> None:
        """Arm all connected drones, take off, and start the force-field loop."""
        pass

    @abstractmethod
    async def land(self) -> None:
        """Navigate to pad positions and land."""
        pass

    @abstractmethod
    async def emergency_land(self) -> None:
        """Immediately land all connected drones regardless of current state."""
        pass

    @abstractmethod
    def safegoto(self, positions: list) -> None:
        """Update target positions consumed by the force-field loop."""
        pass

    @abstractmethod
    def get_positions(self) -> list[tuple[float, float, float]] | None:
        """Return current positions of all drones as (x, y, z) tuples."""
        pass

    def goto(self, positions: list) -> None:
        """Alias for safegoto - update target positions."""
        return self.safegoto(positions)
