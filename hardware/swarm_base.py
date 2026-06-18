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


class SwarmBase(ABC):
    @property
    @abstractmethod
    def state(self) -> SwarmState:
        """Return the current state of the swarm."""
        pass

    @abstractmethod
    def connect(self, base_address: str, num_drones: int) -> None:
        """Connect to *num_drones* drones derived from *base_address*."""
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """Disconnect all drones."""
        pass

    @abstractmethod
    def takeoff(self) -> None:
        """Arm all connected drones, take off, and start the force-field loop."""
        pass

    @abstractmethod
    def land(self) -> None:
        """Navigate to pad positions and land."""
        pass

    @abstractmethod
    def emergency_land(self) -> None:
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
