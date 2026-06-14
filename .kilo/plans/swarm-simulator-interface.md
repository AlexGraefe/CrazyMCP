# Swarm Simulator Implementation Plan

## Overview
Create a simulator that mimics the hardware swarm's state machine without requiring actual Crazyflie drones. Both `Swarm` (real) and `SimulatedSwarm` will inherit from a common abstract base class.

## Architecture Changes

### 1. Create Abstract Base Class (`/home/alex/Documents/CrazyMCP/hardware/swarm_base.py`)
Extract the common interface into an abstract base class:

- **SwarmState** enum (shared by both implementations)
- **SwarmBase** ABC with:
  - `state: SwarmState` property (abstract)
  - `connect(base_address, num_drones) -> None` (abstract)
  - `disconnect() -> None` (abstract)
  - `takeoff() -> None` (abstract)
  - `land() -> None` (abstract)
  - `emergency_land() -> None` (abstract)
  - `safegoto(positions: list) -> None` (abstract)

### 2. Refactor Existing Swarm (`/home/alex/Documents/CrazyMCP/hardware/swarm.py`)
- Remove `SwarmState` enum (move to base)
- Make `Swarm` inherit from `SwarmBase`
- Keep all existing hardware-specific implementations

### 3. Implement Simulated Swarm (`/home/alex/Documents/CrazyMCP/simulator/swarm.py`)
Create `SimulatedSwarm` class with:
- Inherit from `SwarmBase`
- State transitions: UNCONNECTED → CONNECTED → FLYING → LANDED (same as real)
- `connect()`: Immediately transitions to CONNECTED, sets `num_drones`
- `takeoff()`: Transitions to FLYING, initializes `_virtual_positions` at hover height (1.0m)
- `safegoto()`: Updates `_virtual_positions` to targets, prints positions
- `land()`: Transitions to LANDED
- `disconnect()`: Transitions to UNCONNECTED
- `emergency_land()`: Transitions to LANDED
- Simulated `_virtual_positions` management

### 4. Update Simulator Init (`/home/alex/Documents/CrazyMCP/simulator/__init__.py`)
Create `simulator/__init__.py` exporting `SimulatedSwarm` and `SwarmState`

### 5. Update Console for Testing
Modify `console_llm.py` to support a `--simulated` flag that uses `SimulatedSwarm` instead of `Swarm`.

## State Machine Behavior (Simulated)

```
UNCONNECTED
   └─ connect() ─> CONNECTED
                        └─ takeoff() ─> FLYING
                        │                └─ safegoto() ─> updates positions
                        │                └─ land() ─> LANDED
                        └─ disconnect() ─> UNCONNECTED
   └─ disconnect() ─> no-op (already unconnected)

FLYING
   └─ emergency_land() ─> CONNECTED (can reconnect)

LANDED
   └─ connect() ─> CONNECTED (new connection)
```

## Key Differences from Real Swarm

| Aspect | Real Swarm | Simulated Swarm |
|--------|-----------|-----------------|
| connect | Async, connects to radio | Immediate, sets drone count |
| takeoff | Arms drones, takes real flight time | Immediate transition, 1ms sleep |
| land | Navigates to pad, real landing | Immediate transition, 1ms sleep |
| safegoto | Sends go_to to firmware | Updates `_virtual_positions` directly |
| Positions | From real sensors | From internal state |

## Files to Modify/Create

1. **NEW**: `hardware/swarm_base.py` - Abstract base class
2. **MODIFY**: `hardware/swarm.py` - Inherit from SwarmBase, remove SwarmState
3. **NEW**: `simulator/swarm.py` - SimulatedSwarm implementation
4. **NEW**: `simulator/__init__.py` - Package exports
5. **MODIFY** (optional): `console_llm.py` - Add --simulated flag support

## Interchangeability

Both classes will be fully interchangeable from the `SwarmController` perspective:
- Same `state` property type
- Same `connect`, `disconnect`, `takeoff`, `land`, `emergency_land`, `safegoto` method signatures
- Same `_virtual_positions` attribute for position tracking
- Same `_connected_cfs` list (simulated will use simple count)