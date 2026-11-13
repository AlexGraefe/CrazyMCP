"""Abstract base class for swarm implementations.

Provides the common interface shared by both real and simulated swarm implementations.
"""

from abc import ABC, abstractmethod
from enum import Enum, auto


class SwarmState(Enum):
    UNCONNECTED = auto()
    CONNECTED = auto()
    FLYING = auto()
    LANDED = auto()
    ERROR = auto()


def rgb_to_wrgb(rgb) -> int:
    """Pack an ``(r, g, b)`` color (0-255 per channel) into WRGB8888 (0xWWRRGGBB).

    The color LED deck has a dedicated white LED, so the common part of the
    three channels is moved into the white channel (same conversion as the
    cfclient Color LED tab).  Out-of-range values are clamped.
    """
    r, g, b = (max(0, min(255, int(round(float(c))))) for c in rgb)
    w = min(r, g, b)
    return (w << 24) | ((r - w) << 16) | ((g - w) << 8) | (b - w)


class SwarmBase(ABC):
    @property
    @abstractmethod
    def state(self) -> SwarmState:
        """Return the current state of the swarm."""
        pass

    @abstractmethod
    async def connect(self, base_address: str, num_drones: int, address_offset: int = 0) -> None:
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
    def safegoto(self, positions: list, yaws: list | None = None, colors: list | None = None) -> None:
        """Update target positions (in real-world meters) consumed by the force-field loop.

        *colors* is an optional list of ``(r, g, b)`` tuples (0-255), one per drone.
        """
        pass

    @abstractmethod
    def get_positions(self) -> list[tuple[float, float, float]] | None:
        """Return current positions of all drones as (x, y, z) tuples."""
        pass

    def goto(self, positions: list, yaws: list | None = None, colors: list | None = None) -> None:
        """Alias for safegoto - update target positions."""
        return self.safegoto(positions, yaws, colors)
